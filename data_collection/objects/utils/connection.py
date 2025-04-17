from . import log as l
from ..utils.config import API
import pylast as pl

l.run()


class Connection:
    
    def __init__(self):
        self.key = API.KEY
        self.secret = API.SECRET

    def getKey(self):
        return self.key

    def getSecret(self):
        return self.secret

    def connect(self):
        try:
            cn = pl.LastFMNetwork(self.key, self.secret)
            return cn
        except:
            l.logging.error('Errore di connessione')
            raise ConnectionError("Errore di connessione.")