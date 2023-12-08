#!/usr/bin/env python3

import csv
import matplotlib.pylab as plt
import os
import argparse
import numpy
from scipy.signal import lfilter
import math
from os import walk
from training import loading


def parseArguments ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ("dir")
    parser.add_argument ("--host", type=bool)
    parser.add_argument ("--sum_all", type=bool)

    return parser.parse_args ()

def sum_a_la_main (S) :
    R = 0
    for i in S :
        R = R + i
    return R

def sumperfs (PERFS, DIV, i):
    sum = 0
    for C in PERFS :
        sum = sum + PERFS [C][DIV][i]
    return sum

def perfs_all_vms(root_dir):
    def merge(a, b):
        for k, v in b.items():
            if k in a.keys():
                new = []
                len_a = len(a[k])
                len_b = len(b[k])
                for i in range(max(len_a, len_b)):
                    if i < len_a and i < len_b:
                        new.append(a[k][i] + b[k][i])
                    elif i >= len_a:
                        new.append(b[k][i])
                    else:
                        new.append(a[k][i])
                a[k] = new
            else:
                a[k] = v
        return a

    perfs = {}
    vms = [f.path for f in os.scandir(root_dir) if f.is_dir()]
    for vm in vms:
        pg = vm.split("/")[-1]
        perfs = merge(perfs, loading.parsePerfCountersCsv(vm + "/cgroups.csv"))

    return perfs

def main (args):
    host = args.dir + "/energy.csv"
    cgrh = args.dir + "/cgroups.csv"
    (RAPL, speeds) = loading.parseEnergyCsv (host)

    PERFS = {}
    for (dirpath, dirnames, filenames) in walk(args.dir):
        for d in dirnames :
            cgr1 = args.dir + "/" + d + "/cgroups.csv"
            PERFS[d] = loading.parsePerfCountersCsv (cgr1, including="test")

    PERFS_SYS = loading.parsePerfCountersCsv (cgrh, including="#SYSTEM", exluding="JJJJJ")

    DIV = 'PERF_COUNT_SW_CPU_CLOCK'
    min_len = len (RAPL)
    for i in PERFS :
        if len (PERFS [i][DIV]) < min_len :
            min_len = len (PERFS [i][DIV])

    ener = {C : [] for C in PERFS}
    m = max (PERFS_SYS [DIV])
    SUM = 0
    PERFS_ALL_VMS = perfs_all_vms(args.dir)
    for i in range (min_len):
        if args.sum_all:
            SUM = PERFS_ALL_VMS[DIV][i]
        else:
            SUM = sumperfs (PERFS, DIV, i)

        if (SUM != 0):
            for C in PERFS :
                A = PERFS[C][DIV][i] / SUM
                ener [C].append (A * RAPL[i])
        else :
            for C in PERFS:
                ener [C].append (0)

    for C in ener :
        print (C, "=", sum (ener [C]), " M = ", max (ener [C]), " T = ", len (ener [C]))
        with open ("/tmp/" + C, "w") as fp:
            for i in range (len (ener [C])):
                fp.write ("(" + str (i + 1) + ", " + str (RAPL [i]) + ")\n")

        plt.plot (ener [C], label=C)
    print ("Machine = ", sum (RAPL))
    print ("Active = ", sum (RAPL) - (len (ener [C]) * 22))


    plt.plot (RAPL, label="RAPL")
    plt.legend ()
    plt.savefig ("out.jpg")



    # for i in range (len (ener_P1)) :
    #     print ("(" + str (i) + ", " + str (ener_P2[i]) + ")")



if __name__ == "__main__" :
    main (parseArguments ())
