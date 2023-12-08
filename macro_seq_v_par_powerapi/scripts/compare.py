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

    return parser.parse_args ()

def readCsv (filename):
    rows = {}
    try:
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
    except Exception:
        return {'timestamp' : []}

def getInstant (ener, instant):
    for i in range (len (ener["timestamp"])):
        if (float (ener ["timestamp"][i]) == instant):
            return ener ["power"][i]
        elif float (ener ["timestamp"][i]) >= instant:
            return 0
    return -1

def generateFinalCsv (path, pg1, pg2):
    rapl = readCsv (path + "/sensor-rapl/PowerReport.csv")
    globl = readCsv (path + "/sensor-global/PowerReport.csv")
    pg1 = readCsv (path + f"/sensor-/{pg1}/PowerReport.csv")
    pg2 = readCsv (path + f"/sensor-/{pg2}/PowerReport.csv")

    with open ("/tmp/powerapi.csv", "w") as out :
        out.write ("timestamp,RAPL,glob,PG1,PG2\n")
        for i in range (len (rapl ["timestamp"])):
            instant = float (rapl ["timestamp"][i])
            r = rapl ["power"][i]
            gl = getInstant (globl, instant)
            p1 = getInstant (pg1, instant)
            p2 = getInstant (pg2, instant)

            out.write (f"{instant},{r},{gl},{p1},{p2}\n")


def plotSingleTraces (nameA, nameB):
    ener = readCsv ("/tmp/powerapi.csv")
    times = [(float (i) - float (ener["timestamp"][0])) / 1000 for i in ener ["timestamp"]]
    rapl = [float (i) for i in ener ["RAPL"]]
    glob = [float (i) for i in ener ["glob"]]
    pg1 = [float (i) for i in ener ["PG1"]]
    pg2 = [float (i) for i in ener ["PG2"]]

    times, rapl, glob, pg1, pg2 = (list(t) for t in zip(*sorted(zip(times, rapl, glob, pg1, pg2))))


    pg1 = [pg1 [i] + pg1 [i+1] for i in range (0, len (rapl) - 1, 2)]
    pg2 = [pg2 [i] + pg2 [i+1] for i in range (0, len (rapl) - 1, 2)]
    pg3 = [pg2 [i] + pg1 [i] for i in range (len (pg1))]
    glob = [glob [i] + glob [i+1] for i in range (0, len (rapl) - 1, 2)]
    times = [times [i] for i in range (0, len (times) - 1, 2)]
    rapl = [rapl [i] + rapl [i+1] for i in range (0, len (rapl) - 1, 2)]

    plt.clf ()

    plt.plot (times, rapl, label="rapl")
    plt.plot (times, glob, label="glob")
    plt.plot (times, pg1, label=nameA)
    plt.plot (times, pg2, label=nameB)

    print (sum (pg1), " ", nameA)
    print (sum (pg2), " ", nameB)
    # plt.plot (times, pg3, label="sum")


    # print (nameA)
    # for i in range (0, len (pg1)):
    #     print (f"({i}, {pg1[i]})")

    # print ()
    # print ("===")
    # print (nameB)
    # for i in range (0, len (pg2)):
    #     print (f"({i}, {pg2[i]})")

    plt.legend ()
    #plt.show ()
    try:
        os.mkdir (".build")
    except Exception:
        pass

    plt.savefig (f".build/{nameA}-v-{nameB}_powerapi.png", dpi = 300)


def main (args):
    generateFinalCsv (args.path, args.pg1, args.pg2)
    plotSingleTraces (args.pg1, args.pg2)


if __name__ == "__main__" :
    main (parseArguments ())
