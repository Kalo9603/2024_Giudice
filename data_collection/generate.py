from objects.artist import artist as ar
from objects.artist import artists as ars
from objects.couple import couple as c
from objects.couple import couples as cs
from objects.utils import log as l
from objects.utils.utils import CSVManager
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

l.run()

if __name__ == '__main__':

    ls = ars.Artists()

    """
    # STEP 1
    # Creazione degli artisti ed esportazione in CSV

    ls.addArtist("Annalisa")
    ls.addArtist("Giorgio Vanni")
    ls.addArtist("Katy Perry")
    ls.addArtist("Ado")

    # Esempio: per ogni artista 100 related se non sono presenti in lista vengono aggiunti.
    # Massimo 3 iterazioni

    ls.populate(related=100, it=3)

    ls.exportData("data_collection/data/artists.csv")

    # STEP 2
    # Importazione del CSV degli artisti, calcolo delle popolarità (per l'open question) e creazione delle coppie
    
    """

    ls.importData("data_collection/data/artists.csv")
    # ls.updatePopularity()

    cpls = cs.Couples(ls)

    cpls.link()