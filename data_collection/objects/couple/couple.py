from ..utils import log as l
from ..artist.artist import Artist
from ..artist.artists import Artists
from ..utils.connection import Connection
from ..utils.utils import CacheManager
from ..utils.config import Cache as ch
import json

l.run()

class Couple:
    
    similarsCache = CacheManager(ch.DB.SIMILARS, "similars",
                                {"ID": "SMALLINT NOT NULL",
                                "Similars": "TEXT NOT NULL"
                                }, primaryKeys=["ID"])
    
    def __init__(self, ls: Artists, artist1: str, artist2: str, sRatio: float = None, jRatio: float = None):

        self.api = Connection().connect()
        self.ls = ls
        self.ratio = {}
        self.artists = frozenset()

        try:
            ar1 = self.ls.getIDByArtistName(artist1)
            ar2 = self.ls.getIDByArtistName(artist2)

            if ar1 is None or ar2 is None:
                raise ValueError(f"Almeno uno degli artisti non esiste: {artist1}, {artist2}")

            if ar1 != ar2:
            
                self.artists = frozenset([ar1, ar2])
                
                if sRatio:
                    self.ratio["sample"] = sRatio
                if jRatio:
                    self.ratio["jaccard"] = jRatio
                else:
                    rt = Couple.setRatio(self.ls, self.ls.getArtistNameByID(ar1), self.ls.getArtistNameByID(ar2), self.similarsCache)
                    if rt:
                        self.ratio.update(rt)

        except ValueError as e:
            l.logging.error(f"Errore nella creazione della coppia: {str(e)}")
            raise e

    def getArtist(self, slot: int):
        if(slot in range(1, 3)):
            id = list(self.artists)[slot-1]
            return self.ls.getArtistByID(id)
        return None

    def getArtistName(self, slot: int):
        if slot in range(1, 3):
            return self.getArtist(slot).getArtistName()

    def getID(self, slot: int):
        if(slot in range(1, 3)):
            return list(self.artists)[slot-1]
        return None

    @staticmethod
    def setRatio(ls: Artists, artist1: str, artist2: str, sample: int = 250, sRatio: bool = True, jRatio: bool = True):
        
        try:

            # Trovo i set di [sample] artisti similari. Li interseco tra di loro insieme agli artisti presenti in lista
            # Il sample ratio è il numero di artisti simili in comune rispetto al massimo dei similari trovati di un artista (250)
            # Lo Jaccard ratio è il numero di artisti simili in comune rispetto il set di tutti i loro nodi similari (intersect / union)

            # Per velocizzare il processo (esaminando centinaia di milioni di possibili archi) si usa un sistema di cache

            def getCacheSimilars(ar: str, sample: int):
                try:
                    
                    art = ls.getIDByArtistName(ar)
                    
                    if not art:
                        return set()
                    
                    if Couple.similarsCache.verify("ID = ?", (art,)):
                        res = Couple.similarsCache.get(["Similars"], "ID = ?", (art,), asSet=True)
                        return res

                    artist = ls.getArtistByID(art)
                    if artist is None:
                        return set()
                    
                    similars = set(artist.getSimilarsList(sample))
                    Couple.similarsCache.write(ID=art, Similars=json.dumps(list(similars)))

                    return similars
                
                except Exception as e:
                    print(f"Error accessing cache: {e}")
                    return set()

            similars1 = getCacheSimilars(artist1, sample)
            similars2 = getCacheSimilars(artist2, sample)

            if len(similars1) > len(similars2):
                similars1, similars2 = similars2, similars1

            common = set.intersection(similars1, similars2)

            # Dalla sola intersezione posso calcolare quanti sono quelli dell'unione sommando il numero dei singoli similar
            # E sottraendo la lunghezza dell'intersezione. In questo modo evito di chiamare un altro metodo costoso come union

            lUnion = len(similars1) + len(similars2) - len(common)

            sRatio_value = round(len(common) / sample, 2) * 100 if sRatio else None
            jRatio_value = (round(len(common) / lUnion, 2) * 100 if jRatio else None) if lUnion != 0 else 0.0

            return {
                "sample": sRatio_value,
                "jaccard": jRatio_value
            }

        except ValueError as e:
            l.logging.error(f"Impossibile calcolare la similarità degli artisti: {str(e)}")
            raise e

    def getRatio(self):
        return self.ratio

    def __eq__(self, other):
        if not isinstance(other, Couple):
            return False
        return self.artists == other.artists

    def __hash__(self):
        return hash(self.artists)

    def __str__(self):
        return f"[{self.getArtistName(1)}, {self.getArtistName(2)} - SR: {self.ratio["sample"]}% | JR: {self.ratio["jaccard"]}%]"