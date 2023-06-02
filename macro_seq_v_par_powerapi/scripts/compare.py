#!/usr/bin/env python3

import matplotlib.pylab as plt
import time
import os
import subprocess
import pathlib
import shutil
import json
import argparse
from os import walk
from training import loading
import csv

all = []

def parseArguments ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ("f")

    return parser.parse_args ()

def cumul (values) :
    result = []
    for i in range (0, len (values), 2) :
        if (len (values) > i + 1) :
            result.append (values [i] + values [i + 1])
        else :
            result.append (values [i])
    return result

def readFile (file, name):
    global all
    (head, rows) = loading.readCsv (file)
    ener = [float (row [-3]) for row in rows]
    ener = cumul (ener)
    with open ("/tmp/" + name, 'w') as fp:
        for i in range (len (ener)) :
            fp.write ("(" + str (i + 1) + ", " + str (ener [i]) + ")\n")


    if len (all) == 0:
        all = ener
    else:
        for i in range (len (ener)):
            if i > len (all):
                all.append (ener [i])
            else :
                all [i] = all [i] + ener [i]

    plt.plot (ener, label=name)
    print (name, " ", sum (ener))


def read (path):
    f = []
    for (dirpath, dirnames, filenames) in walk(path + "/cpu-"):
        for d in dirnames :
            #if "pg" not in d and "vbox" not in d:
            readFile (path + "/cpu-/" + d + "/PowerReport.csv", d)

    for (dirpath, dirnames, filenames) in walk(path + "/sensor-"):
        for d in dirnames :
            #if "pg" not in d and "vbox" not in d:
            readFile (path + "/sensor-/" + d + "/PowerReport.csv", d)


def main (args):
    data = read (args.f)
    plt.plot (all, label="all")
    plt.legend ()
    plt.savefig ("out.jpg")




if __name__ == "__main__" :
    main (parseArguments ())
