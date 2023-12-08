#!/usr/bin/env python3

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
    parser.add_argument ("path")
    parser.add_argument ("pg1")
    parser.add_argument ("pg2")
    #parser.add_argument ("out")

    return parser.parse_args ()

def readCsv (filename):
    rows = {}
    with open (filename, 'r') as fp:
        reader = csv.reader (fp)
        head = next (reader)

        for row in reader:
            current = row
            for h in range (len (head)) :
                if not head [h] in rows :
                    rows [head[h]] = []
                rows [head[h]].append (current [h])

    return rows


def readJSon (file):
    consumers = {"host" : []}
    with open(file, "r") as f:
        results = json.load(f)
        for result in results:
            consumers ["host"].append (result ["host"]["consumption"] / 1000000)
            for consumer in result["consumers"]:
                if ("VBox" in consumer["exe"]) :
                    if (consumer ["pid"] in consumers) :
                        consumers [consumer ["pid"]].append (consumer["consumption"] / 1000000)
                    else :
                        consumers [consumer ["pid"]] = [consumer ["consumption"]  / 1000000]

    return consumers

def getInstant (ener, instant):
    for i in range (len (ener["timestamp"])):
        if (float (ener ["timestamp"][i]) == instant):
            return ener ["power"][i]
        elif float (ener ["timestamp"][i]) >= instant:
            return 0
    return -1

def generateFinalCsv (path, pg1, pg2):
    r = readJSon (path + "/results.json")

def plotSingleTraces (out, nameA, nameB):
    ener = readJSon (out + "/results.json")
    a = list (ener.keys()) [1]
    b = list (ener.keys()) [2]
    print (a, " ", b)
    print (ener[a])

    print (ener [b])

    rapl = [float (i) for i in ener ["host"]]
    pg1 = [float (i) for i in ener [a]]
    pg2 = [float (i) for i in ener [b]]

    plt.clf ()

    plt.plot (rapl, label="rapl")
    plt.plot (pg1, label=nameA)
    plt.plot (pg2, label=nameB)

    # plt.plot (times, pg3, label="sum")


    print (nameA)
    for i in range (0, len (pg1)):
        print (f"({i}, {pg1[i]})")

    print ()
    print ("===")
    print (nameB)
    for i in range (0, len (pg2)):
        print (f"({i}, {pg2[i]})")

    plt.legend ()
    plt.show ()
    # plt.savefig (f".build/{nameA}-v-{nameB}-{coreA}_{coreB}_powerapi.png", dpi = 300)


def main (args):
    # generateFinalCsv (args.path, args.pg1, args.pg2)

    # generateFinalCsv (args.path, args.pg1, args.pg2, args.out)
    plotSingleTraces (args.path, args.pg1, args.pg2)




if __name__ == "__main__" :
    main (parseArguments ())
