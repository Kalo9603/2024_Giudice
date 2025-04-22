from ..utils import log as l
import csv
import os
import time
import numpy as np
import pandas as pd
from ..utils.connection import Connection
from ..utils.utils import CacheManager
from ..utils.utils import CSVManager
from ..artist.artist import Artist
from ..utils.config import Cache as ch

l.run()


class Artists:

    def __init__(self):

        self.api = Connection().connect()
        self.list = {}
        self.cache = CacheManager(ch.DB.ARTISTS, "artists", {"ID": "SMALLINT NOT NULL", "Nome": "TEXT NOT NULL"}, 
                                  primaryKeys=["ID", "Nome"])
        
        # Servono per i controlli e per migliorare le prestazioni
        self.names = set()
        self.ids = set()

    def exists(self, name):
        return name in self.list

    def addArtist(self, name: str, id: int = None):
        try:
            
            if name in self.names or (id and id in self.ids):
                return
            
            cached = self.cache.get(["ID", "Nome"], "ID = ? AND Nome = ?", (id, name))
            
            if cached:
                id, name = cached[0], cached[1]

            if id is None:
                id = Artist.id

            if id not in self.list:
                artist = Artist(name, id)
                self.list[id] = artist
                self.names.add(name)
                self.ids.add(id)
                self.cache.write(ID=id, Nome=name)

                if(len(self.list) % 10000 == 0):
                    l.logging.info(f"[{len(self.list)}] artisti trovati")
                    
        except ValueError as e:
            l.logging.error("Nome artista non valido: " + str(e))

    def addRelatedArtists(self, name: str, limit=None):
        try:
            if not self.exists(name):
                self.addArtist(name)
            ls = self.list[name].getSimilars(limit)
            for artist in ls:
                self.addArtist(artist.item.get_name())
        except ValueError as e:
            l.logging.error("Nome artista non valido: " + str(e))

    def populate(self, begin="", related=20, it=100, limit=None):
        try:
            i = 1
            if len(self) == 0 and begin != "":
                self.addArtist(begin)
            while i <= it:
                if limit is not None:
                    if len(self) >= limit:
                        print(f"Raggiunti {limit} nodi.")
                        l.logging.warning(f"Raggiunti {limit} nodi.")
                    break
                l.logging.info(f"=== Iterazione {i}/{it} ===")
                ls = list(self.getListOfArtists())
                for artist in ls:
                    self.addRelatedArtists(artist, related)
                i += 1
        except Exception as e:
            l.logging.error("Errore durante la popolazione: " + str(e))

    def exportData(self, filename):
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["ID", "Artista"])
            writer.writeheader()
            for artist in self.list.values():
                writer.writerow({"ID": artist.getID(), "Artista": artist.getArtistName()})
            l.logging.info(f"Tutti gli artisti sono stati esportati in {filename}")

    def importData(self, filename):
        try:
            with open(filename, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    id = int(row['ID']) if row['ID'].isdigit() else None
                    self.addArtist(row['Artista'], id)
            l.logging.info(f"Tutti gli artisti sono stati importati da {filename}")
        except Exception as e:
            l.logging.error(f"Errore durante l'importazione: {str(e)}")

    def getArtist(self, name: str):
        return self.list[name]

    def getArtistByID(self, id: int):
        if id in self.list:
            return self.list[id]
        return None

    def getArtistNameByID(self, id: int):
        return self.getArtistByID(id).getArtistName()

    def getIDByArtistName(self, name: str):
        for artist in self.list.values():
            if artist.getArtistName() == name:
                return artist.getID()
        return None
    
    def getArtistByName(self, name: str):
        for artist in self.list.values():
            if artist.getArtistName() == name:
                return artist
        return None

    def getArtists(self):
        return self.list

    def getListOfArtists(self):
        return list(self.getArtists())
    
    def getListenersByID(self, id: int):
        try:
            artist = self.getArtistByID(id)
            return artist.getListeners()
        except:
            return 0
        
    def getPlayCountByID(self, id: int):
        try:
            artist = self.getArtistByID(id)
            return artist.getPlayCount()
        except:
            return 0
        
    def updatePopularity(self):

        def _truncate(value, decimals=5):
            f = 10.0 ** decimals
            return int(value * f) / f

        try:
            lastID = CSVManager.getLastID(ch.CSV.POPULARITY)
            if lastID is not None:
                lastID = int(lastID)
            process = True if lastID is None else False

            for artist in self.list.values():
                if not process:
                    if artist.getID() == lastID:
                        process = True
                    else:
                        continue

                while True:
                    try:
                        listeners = artist.getListeners()
                        playcount = artist.getPlayCount()

                        raw = _truncate(playcount / (listeners + 1), 5)
                        logRaw = _truncate(np.log1p(raw), 5)

                        row = {
                            "ID": artist.getID(),
                            "Nome": artist.getArtistName(),
                            "Ascoltatori": listeners,
                            "Ascolti": playcount,
                            "Popolarità": raw,
                            "PopolaritàLog": logRaw
                        }

                        CSVManager.update(ch.CSV.POPULARITY, kField="ID", kValue=artist.getID(), data=row)
                        l.logging.info(f"{artist.getID()}. {artist.getArtistName()} || Raw: {raw} | Log: {logRaw}")
                        break

                    except Exception as e:
                        l.logging.error(f"Errore per {artist.getID()} ({artist.getArtistName()}): {str(e)}. Riprovo...")
                        time.sleep(2)

            if not os.path.exists(ch.CSV.POPULARITY):
                l.logging.warning(f"File POPULARITY mancante. Interrotto calcolo ZIndex.")
                return

            df = pd.read_csv(ch.CSV.POPULARITY)
            if df.empty:
                l.logging.info(f"Nessun dato nel file {ch.CSV.POPULARITY}. ZIndex non calcolato.")
                return

            meanLog = _truncate(df["PopolaritàLog"].mean(), 5)
            stdLog = _truncate(df["PopolaritàLog"].std(), 5)

            df["ZIndex"] = df["PopolaritàLog"].apply(lambda x: _truncate((x - meanLog) / stdLog if stdLog != 0 else 0, 5))

            for _, row in df.iterrows():
                out = {
                    "ID": int(row["ID"]),
                    "Nome": row["Nome"],
                    "Ascoltatori": int(row["Ascoltatori"]),
                    "Ascolti": int(row["Ascolti"]),
                    "Popolarità": float(row["Popolarità"]),
                    "PopolaritàLog": float(row["PopolaritàLog"]),
                    "ZIndex": float(row["ZIndex"])
                }

                CSVManager.update(ch.CSV.POP_ZINDEX, kField="ID", kValue=out["ID"], data=out)
                l.logging.info(f"[Z-Score] {out['Nome']} || Raw: {out['Popolarità']} | Log: {out['PopolaritàLog']} | Z: {out['ZIndex']}")

        except Exception as e:
            l.logging.error(f"Errore durante l'aggiornamento della popolarità: {str(e)}")


    def resetID(self):
        Artist.id = 1
        l.logging.info("Indici resettati")

    def sortByArtistName(self, desc=False):
        self.list = dict(sorted(self.list.items(), key=lambda x: x[1].getArtistName(), reverse=desc))

    def sortByID(self, desc=False):
        self.list = dict(sorted(self.list.items(), key=lambda x: x[1].getID(), reverse=desc))

    def clear(self):
        self.list = {}
        self.resetID()
        l.logging.info("Tutti gli artisti sono stati rimossi")

    def __len__(self):
        return len(self.list)

    def __str__(self):
        l = ""
        for artist in self.list.values():
            l += str(artist) + "\n"
        return l