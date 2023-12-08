#!/usr/bin/env python3

import time
import os
import subprocess
import pathlib
import shutil
import json
import argparse
import csv
import numpy as np
from matplotlib import pyplot as plt
import statistics
from sklearn.metrics import r2_score


PG = {
    'ackermann': int (16667 / 3),
    'float64': int (18182 / 3),
    'matrixprod': int (22222 / 3),
    'rand': int (16000 / 3),
    'int64': int (18182 / 3),
    'decimal64': int (16667 / 3),
    'jmp': int (18182 / 3),
    'queens': int (18182 / 3),
    'fibonacci': int (15384 / 3),
    'double': int (16667 / 3),
    'int64float': int (18182 / 3),
    'int64double': int (18182 / 3)
}


machines = {
    "big-intel" : 32,
    "ptero" : 6,
    "nuc-intel" : 4,
    "ptero-2Ghz" : 6,
    "ptero-1.3GHz" : 6,
    "ptero-3Ghz" : 6,
    "ptero-capped" : 6
}

def resDirectory (machine, HT):
    if (HT):
        return ("micro_with_HT/" + machine, machines [machine] * 2)
    else :
        return ("micro_no_HT/" + machine, machines [machine])

def read (filename):
    rows = {}
    with open (filename, 'r') as fp:
        reader = csv.reader (fp)
        head = next (reader)[0].split (';')

        for row in reader:
            current = row[0].split (";")
            for h in range (len (head)) :
                if not head [h] in rows :
                    rows [head[h]] = []
                rows [head[h]].append (current [h])

    return rows



def getPowerInstant (timestamps, energy):
    """
    returns:
      - [0]: the maximum RAPL power observed in the traces
      - [1]: the timestamp of this observation
    """
    mx = 0
    instant = 0

    for i in range (5, len (timestamps)) :
        cpu = float (energy [i]) - float (energy [i - 1])
        if (cpu > mx) :
            mx = cpu
            instant = timestamps [i]

    return (mx, instant)

def getPowerInstantMaxes (timestamps, energy, nb):
    """
    returns:
      - [0]: the maximum RAPL power observed in the traces
      - [1]: the timestamp of this observation
    """
    mx = [0 for i in range (nb)]
    instants = [0 for i in range (nb)]
    currentMinIndex = 0

    for i in range (1, len (timestamps)) :
        cpu = float (energy [i]) - float (energy [i - 1])
        if (cpu > mx [currentMinIndex]) :
            mx [currentMinIndex] = cpu
            instants [currentMinIndex] = timestamps [i]
            currentMinIndex = mx.index (min (mx))

    return (mx, instants)



def getPerfEvent (timestamp, events, perf, cg):
    """
    returns: the value of the perf event 'perf' of the cgroup 'cg' at instant 'timestamp'
    """

    for i in range (len (events ["TIMESTAMP"])):
        if events ["TIMESTAMP"][i] == timestamp and cg in events ["CGROUP"][i]:
            return int (events [perf][i])
    return 0

def getEmptyConso (root):
    """
    return: the consumption of the machine when empty (idle)
    """

    ener = root + "/result/empty/energy.csv"
    ener = read (ener)

    return getPowerInstant (ener ["TIMESTAMP"], ener ["CPU"])[0]

def getPowerVersus (path, nameA, coreA, nameB, coreB, perf_event = "PERF_COUNT_HW_CPU_CYCLES"):
    """
    return:
       - [0]: the power consumption when running A and B at the same time
       - [1]: the number of cycle of A
       - [B]: the number of cycle of B
    """

    ener = read (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/energy.csv")
    cgroups = read (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/cgroups.csv")

    (cpu, instant) = getPowerInstant (ener ["TIMESTAMP"], ener ["CPU"])

    cycleA = getPerfEvent (instant, cgroups, perf_event, "pg1")
    cycleB = getPerfEvent (instant, cgroups, perf_event, "pg2")

    return (cpu, cycleA, cycleB)


def getPowerVersusMaxes (path, nameA, coreA, nameB, coreB, nb = 10, perf_event = "PERF_COUNT_HW_CPU_CYCLES"):
    """
    return:
       - [0]: the power consumption when running A and B at the same time
       - [1]: the number of cycle of A
       - [B]: the number of cycle of B
    """

    ener = read (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/energy.csv")
    cgroups = read (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/cgroups.csv")

    (cpu, instant) = getPowerInstantMaxes (ener ["TIMESTAMP"], ener ["CPU"], nb)

    cycleA = []
    cycleB = []
    for i in instant :
        cycleA.append (getPerfEvent (i, cgroups, perf_event, "pg1"))
        cycleB.append (getPerfEvent (i, cgroups, perf_event, "pg2"))

    return (cpu, cycleA, cycleB)


def getPowerAloneZ (path, A, z):
    """
    returns: the power consumption of the machine when running only 'A' with 'z' cores
    """
    ener = read (path + "/result/" + str (A) + "-" + str (z) + "/energy.csv")


    return getPowerInstant (ener ["TIMESTAMP"], ener ["CPU"])[0]

def getPowerAloneEvent (path, A, z, perf_event):
    """
    returns: the power consumption of the machine when running only 'A' with 'z' cores
    """

    ener = read (path + "/result/" + str (A) + "-" + str (z) + "/energy.csv")
    cgroups = read (path + "/result/" + str (A) + "-" + str (z) + "/cgroups.csv")

    (cpu, instant) = getPowerInstant (ener ["TIMESTAMP"], ener ["CPU"])
    cycleA = 0
    if (perf_event == "PERF_COUNT_SW_CPU_CLOCK"):
        cycleA = z * 500000000
    else:
        cycleA = getPerfEvent (instant, cgroups, perf_event, "pg1")

    return (cpu, cycleA)


# Polynomial Regression
def polyfit(x, y, degree):
    results = {}

    coeffs = np.polyfit(x, y, degree)

     # Polynomial Coefficients
    results['polynomial'] = coeffs.tolist()

    # r-squared
    p = np.poly1d(coeffs)
    # fit values, and mean
    yhat = p(x)                         # or [p(z) for z in x]
    ybar = np.sum(y)/len(y)          # or sum(y)/len(y)
    ssreg = np.sum((yhat-ybar)**2)   # or sum([ (yihat - ybar)**2 for yihat in yhat])
    sstot = np.sum((y - ybar)**2)    # or sum([ (yi - ybar)**2 for yi in y])
    results['determination'] = ssreg / sstot

    return results


def computeDistToOpt (x, y):
    points = list(zip(x, y))
    idealmin = np.asarray((-100, -100))
    idealmax = np.asarray((100, 100))


    error = sum ([abs (x [i] - y[i]) for i in range (len (x))]) / len (x)
    print ("Error : ", error)


    list_distances = []
    for point in points:
        d = 0
        if (point [0] < point[1]) :
            ideal = (point[0], point[0])
            d = abs (point[1] - ideal [1])
        else:
            ideal = (point [1], point [1])
            d = abs (point [0] - ideal [0])

        #list_distances.append(np.abs(np.cross(idealmax - idealmin, idealmax - point)) / np.linalg.norm(idealmax - idealmin))
        list_distances.append (d)

    return np.mean(list_distances), np.max (list_distances)


def removeExtremes (lst, lst2, variance = 10) :
    currentVariance = np.var (lst)
    if (currentVariance < variance or len (lst) < 3):
        return (lst, lst2)

    med = statistics.median (lst)
    mx = 0
    for i in range (len (lst)):
        if (abs (lst [i] - med) > abs (lst [mx] - med)):
            mx = i
    del lst [mx]
    del lst2 [mx]
    return removeExtremes (lst, lst2, variance = variance)



def computeResidualConsumption (machine, HT):
    # return residu [machine]

    (directory, cores) = resDirectory (machine, HT)
    all = 0
    nb = 0
    residu = []
    for p in PG :
        try :
            a = getPowerAloneZ (directory, p, 1)
            b = getPowerAloneZ (directory, p, cores)

            slope = (b - a) / (cores)
            residu.append (a - slope)

            all += slope
            nb += 1
        except Exception as e:
            print (e)
            # raise e
            pass

    print (residu)
    return sum (residu) / len (residu)
