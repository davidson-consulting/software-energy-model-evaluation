#!/usr/bin/env python3

import matplotlib.pylab as plt
import time
import os
import subprocess
import pathlib
import shutil
import json
import argparse



def parseArguments ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ("f")

    return parser.parse_args ()


def read (file):
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


def main (args):
    data = read (args.f + "/results.json")
    all = []
    for i in data :
        plt.plot (data [i], label=i)
        with open ("/tmp/" + str (i), 'w') as fp:
            for j in range (len (data[i])) :
                fp.write ("(" + str (j + 1) + ", " + str (data [i][j]) + ")\n")

        print (i, " ", sum (data [i]))
    plt.legend ()
    plt.savefig ("out.jpg")
    # plt.show ()




if __name__ == "__main__" :
    main (parseArguments ())
