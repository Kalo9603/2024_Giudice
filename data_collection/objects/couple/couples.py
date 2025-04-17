from ..utils import log as l
from ..utils.utils import CSVManager
from ..utils.utils import CacheManager
from multiprocessing import Pool, Manager
from ..artist.artists import Artists
from ..couple.couple import Couple
from ..utils.connection import Connection
from ..utils.config import Cache as ch, Index as ix

class Couples:
    
    cache = CacheManager(ch.DB.COUPLES, "couples",
                        {"ID1": "SMALLINT NOT NULL",
                        "ID2": "SMALLINT NOT NULL",
                        "SRatio": "SMALLINT NOT NULL",
                        "JRatio": "SMALLINT NOT NULL"}, primaryKeys=["ID1", "ID2"], indexes=["ID1", "ID2"])

    def __init__(self, ls: Artists):

        self.api = Connection().connect()
        self.ls = ls
        
    @staticmethod
    def addCouple(ls, ar1: str, ar2: str, prID, sRatio=True, jRatio=True, sValue=None, jValue=None):
        try:
            if ar1 is None or ar2 is None:
                raise ValueError("Coppia non valida: uno o entrambi gli artisti non sono inizializzati.")
                        
            if ar1 != ar2:
                id1, id2 = ls.getIDByArtistName(ar1), ls.getIDByArtistName(ar2)
                
                if id1 > id2:
                    id1, id2, ar1, ar2 = id2, id1, ar2, ar1
                                
                if Couples.cache.verify("ID1 = ? AND ID2 = ?", (id1, id2)):
                    return False
                
                ratios = Couples.cache.get(["SRatio", "JRatio"], "ID1 = ? AND ID2 = ?", (id1, id2))
                if ratios:
                    sValue, jValue = float(ratio[0] / 100), float(ratio[1] / 100)
                else:
                    ratio = Couple.setRatio(ls, ar1, ar2, sRatio=sRatio, jRatio=jRatio)
                    sValue, jValue = ratio["sample"], ratio["jaccard"]
                    Couples.cache.write(ID1=id1, ID2=id2, SRatio=int(100 * sValue), JRatio=int(100 * jValue))

                if ((sRatio and not jRatio and sValue >= ix.Threshold.SAMPLE) or
                    (jRatio and not sRatio and jValue >= ix.Threshold.JACCARD) or
                    (sRatio and jRatio and sValue >= ix.Threshold.SAMPLE and jValue >= ix.Threshold.JACCARD)):
                    
                    row = {"IDArtista1": id1,
                           "Artista1": ar1,
                           "IDArtista2": id2,
                           "Artista2": ar2,
                           "SampleRatio": sValue,
                           "JaccardRatio": jValue}
                    
                    CSVManager.writeRow(ch.CSV.EXPORT, row, 
                                        fieldnames=["IDArtista1", "Artista1", "IDArtista2", "Artista2", "SampleRatio", "JaccardRatio"])
                    return True
                
        except Exception as e:
            l.logging.error(f"Errore nell'aggiunta della coppia ({ar1}, {ar2}): {str(e)}")
        return False
    
    @staticmethod
    def _createSubsets(artists: list) -> list:

        total = len(artists)
        base = total // ix.PROCESSES
        extra = total % ix.PROCESSES
        subsets = []
        start = 0
        for i in range(ix.PROCESSES):
            chunk = base + (1 if i < extra else 0)
            sub1 = artists[start:start+chunk]
            sub2 = artists[start:]
            subsets.append((sub1, sub2))
            start += chunk
        return subsets

    @staticmethod
    def processCouples(sub1, sub2, ls, rQueue, sRatio, jRatio, prID):
        
        found = 0
        analyzed = 0
        total = sum(1 for ar1 in sub1 for ar2 in sub2 if ar2 > ar1)

        lastProcessed = None
        saved = 0
        def callback(row):
            nonlocal lastProcessed, saved
            if row["PrID"] == str(prID):
                lastProcessed = int(row["LastAr"])
                saved = int(row["Analyzed"])
        CSVManager.readRow(ch.CSV.LASTS, callback)
        
        if lastProcessed is not None:
            sub1 = [ar for ar in sub1 if ar > lastProcessed]
        
        names = {ar: ls.getArtistNameByID(ar) for ar in set(sub1 + sub2)}
        
        for i, ar1 in enumerate(sub1):
            
            percent = round(((i+1) / len(sub1)) * 100, 2)
            progress = analyzed + saved
            
            l.logging.info(f"[{prID}] - ({ar1}, {names[ar1]}) | {i+1}/{len(sub1)} | {percent}% | {progress}/{total} | {round(((progress / total) * 100), 2)}%")

            for ar2 in sub2[sub2.index(ar1)+1:]:
                
                if ar1 > ar2:
                    ar1, ar2 = ar2, ar1
                    
                if Couples.cache.verify("ID1 = ? AND ID2 = ?", (ar1, ar2)):
                    analyzed += 1
                    continue
                
                try:
                    if Couples.addCouple(ls, names[ar1], names[ar2], prID, sRatio=sRatio, jRatio=jRatio):
                        found += 1
                        prText = f"[{prID}] - " if prID is not None else ""
                        text = "coppie trovate" if found > 1 else "coppia trovata"
                        l.logging.info(f"{prText}[{found}] {text} | [{names[ar1]}, {names[ar2]}].")
                    analyzed += 1
                    
                except Exception as e:
                    l.logging.warning(f"Errore nella creazione della coppia ({names[ar1]}, {names[ar2]}): {str(e)}")

            totalSaved = saved + analyzed
            CSVManager.update(
                ch.CSV.LASTS,
                kField="PrID",
                kValue=prID,
                data={"LastAr": ar1, "Analyzed": totalSaved}
            )
            
        if totalSaved == total:
            l.logging.info(f"Processo [{prID}] completato.")
        else:
            l.logging.info(f"Processo [{prID}] terminato con {totalSaved}/{total} coppie analizzate.")
            
        rQueue.put((found, totalSaved))
        

    def link(self, sRatio=True, jRatio=True):

        CSVManager.removeDuplicates(ch.CSV.IMPORT)
        
        found = CSVManager.length(ch.CSV.IMPORT)
        analyzed = self.cache.count()
  
        total = int((len(self.ls.list) * (len(self.ls.list) - 1)) / 2) - analyzed
        ars = self.ls.getListOfArtists()
        
        if total == 0:
            l.logging.info("Nessuna coppia rimanente da analizzare.")
            return
        
        l.logging.info(f"{found} coppie trovate. Potenziali coppie rimanenti: {total}/{total+analyzed} ({round((total / (total + analyzed)) * 100, 2)}%)")

        # Per ottimizzare l'elaborazione delle possibili coppie si è pensato di lavorare in multiprocessing
        
        subs = Couples._createSubsets(ars)
        
        with Manager() as manager:
            
            queue = manager.Queue()

            with Pool(processes=ix.PROCESSES) as pool:
                for prID, (sub1, sub2) in enumerate(subs, start=1):
                    pool.apply_async(Couples.processCouples, args=(sub1, sub2, self.ls, queue, sRatio, jRatio, prID))

                pool.close()
                pool.join()

            while not queue.empty():
                f, a = queue.get()
                found += f
                analyzed += a

        l.logging.info(f"Totale coppie trovate: {found}/{total + analyzed} ({round(found / (total + analyzed) * 100, 2)}%)")
        l.logging.info(f"Totale coppie analizzate: {analyzed}/{total + analyzed} ({round(analyzed / (total + analyzed) * 100, 2)}%)")

    def exportData(self, filename):

        fieldnames = ["IDArtista1", "Artista1", "IDArtista2", "Artista2", "SampleRatio", "JaccardRatio"]
        
        try:
            for couple in self.couples.values():
                row = {
                    "IDArtista1": couple.getID(1),
                    "Artista1": couple.getArtistName(1),
                    "IDArtista2": couple.getID(2),
                    "Artista2": couple.getArtistName(2),
                    "SampleRatio": couple.getRatio()["sample"],
                    "JaccardRatio": couple.getRatio()["jaccard"]
                }
                CSVManager.writeRow(filename, row, fieldnames)
                
            l.logging.info(f"Tutte le coppie sono state esportate in {filename}")

        except Exception as e:
            l.logging.error(f"Errore durante l'esportazione dei dati in {filename}: {str(e)}")


    def importData(self, filename):
        try:
            def callback(row):
                ar1 = row["Artista1"]
                ar2 = row["Artista2"]
                sRatio = float(row["SampleRatio"])
                jRatio = float(row["JaccardRatio"])
                Couples.addCouple(self.ls, ar1, ar2, prID=None, sValue=sRatio, jValue=jRatio)

            CSVManager.readRow(filename, callback)
            l.logging.info(f"Tutte le coppie sono state importate da {filename}")

        except Exception as e:
            l.logging.error(f"Errore durante l'importazione: {str(e)}")