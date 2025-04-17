"""
    File di configurazione per l'elaborazione del dataset.
    Si specificano gli indici minimi di Sample e Jaccard Ratio, il numero di processi per lavorare in
    multiprocessing, le chiavi dell'API e gli URL di import/export dei CSV e dei DB di cache.
"""

class Index:
    
    class Threshold:
        SAMPLE = 50.0
        JACCARD = 50.0
    
    PROCESSES = 12

class Cache:
    
    class DB:
        ARTISTS = "data_collection/objects/utils/cache/artists.db"
        SIMILARS = "data_collection/objects/utils/cache/similars.db"
        COUPLES = "data_collection/objects/utils/cache/couples.db"
        
        
    class CSV:
        IMPORT = "data_collection/data/links.csv"
        EXPORT = "data_collection/data/links.csv"
        POPULARITY = "data_collection/data/popularity.csv"
        POP_ZINDEX = "data_collection/data/popularity_z.csv"
        LASTS = f"data_collection/objects/utils/cache/lasts_{Index.PROCESSES}.csv"

class API:
    KEY = ""
    SECRET = ""