from ..utils import log as l
import numpy as np
from ..utils.connection import Connection

l.run()

class Artist:

    id = 1

    def __init__(self, name: str, id : int = None):

        name = name.encode('utf-8').decode('utf-8')

        self.api = Connection().connect()

        try:
            self.id = Artist.setID(id)
            self.artist = self.api.get_artist(name)
        except:
            l.logging.error("Artista " + name + " NON creato.")
            raise ValueError("Nome artista non valido.")

    def getID(self):
        return self.id

    def setID(self, id : int = None):
        if id is not None:
            return id
        else:
            value = Artist.id
            Artist.id += 1 
            return value

    def getArtist(self):
        return self.artist

    def getArtistName(self):
        return self.artist.get_name()
    
    def getPlayCount(self):
        return self.artist.get_playcount()
    
    def getListeners(self):
        return self.artist.get_listener_count()

    def getSimilars(self, limit=None):
        try:
            i = 1
            similars = self.getArtist().get_similar(limit)
            similar_list = ""
            for similar in similars:
                similar_list += str(i) + ". " + similar.item.get_name() + "\n"
                i += 1
            return similars
        except Exception:
            raise Exception("Impossibile recuperare similarità.")

    def getSimilarsList(self, limit=None):
        ls = {}
        for artist in self.getSimilars(limit):
            ls[artist.item.get_name()] = artist.item.get_name()
        return ls 
    
    def __str__(self):
        return f"({self.getID()}, {self.getArtistName()})"