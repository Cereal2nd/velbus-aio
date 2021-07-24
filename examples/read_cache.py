import pickle
from os import listdir
from os.path import isfile, join

from velbusaio.const import CACHEDIR

for fil in [f for f in listdir(CACHEDIR) if isfile(join(CACHEDIR, f))]:
    print("")
    print(fil)
    fl = open("{}/{}".format(CACHEDIR, fil), "rb")
    print(pickle.load(fl))
