#!/usr/bin/env python3

from utils.common import *
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

from utils.common import *

import math
import traceback

def analyseVersus (machine, HT):
    """
    Plot the power consumption of the machine when running two application with or without hyperthreading
    """

    (directory, cores) = resDirectory (machine, HT)
    for nameA in PG :
        plt.clf ()
        empty = getPowerAlone (directory, cores / 2, nameA)[-1]
        # empty = 0

        for name in PG :
            power = getPowerVersus (directory, cores / 2, cores / 2, nameA, name)
            if (len (power) > 0):
                plt.plot ([i for i in range (cores / 2, cores + 1)], [empty] + power, label=name)
            #     step = [empty] + power
            #     step = [step [i] - step [i - 1] for i in range (1, len (step))]
            #     print (step)
            #     plt.plot ([i for i in range (1, len (step) + 1)], step, label=name)
        plt.legend()
        plt.suptitle (nameA + " " + str (cores) + " cores vs B 1-" + str (cores) + " cores")
        plt.savefig (nameA + ".png", dpi=300)

    names = [p + ".png" for p in PG]
    s = subprocess.Popen (["convert"] + names + [ ".build/out.pdf" ])
    s.wait ()

def analyseAlone (machine, HT):
    """
    Plot the power consumption of the machine when running only one application with or without hyperthreading
    """
    model = computeResidualConsumption (machine, HT)

    (directory, cores) = resDirectory (machine, HT)
    plt.clf ()
    empty = getEmptyConso (directory)

    max_ = [0]
    min_ = [1000]

    for name in PG :
        try :
            power = []
            for z in range (1, cores + 1):
                power.append (getPowerAloneZ (directory, name, z))
            if (len (power) > 0):
                if (power [-1] > max_ [-1]):
                    max_ = power
                elif (power [-1] < min_[-1]):
                    min_ = power

                if (name == "fibonacci" or name == "queens" or name == "float64"):
                    print (name, " ", power)

        except Exception as e:
            print (e, " ", name)
            #raise e
            pass
            # step = [empty] + power
            # step = [step [i] - step [i - 1] for i in range (1, len (step))]
            # print (step)
            # plt.plot ([i for i in range (1, len (step) + 1)], step, label=name)

    # print (machine)
    # print ("(0", math.ceil (empty), ")")
    # for i in range (1, cores + 1) :
    #     print ("(", int (i / cores * 100), ", ", math.ceil (min_[i - 1]), ")")

    # print ("(0", math.ceil (empty), ")")
    # for i in range (1, cores + 1) :
    #     print ("(", int (i / cores * 100), ", ", math.ceil (max_[i - 1]), ")")

    # for i in range (0, cores + 1) :
    #     print ("(", int (i / cores * 100), ", ", math.ceil (model[0][i] + model[2] + 2), ")")

    plt.plot ([empty] + min_, label=name + " min")
    plt.plot ([empty] + max_, label=name + " max")
    #plt.plot ([i + model[2] for i in model [0]])
    print (max_[-1] - model, max_ [-1],"  ", model, " ", min_[-1])
    plt.legend()
    plt.show ()
    plt.savefig (".build/" + machine + ".png", dpi=300)
    plt.clf ()



def plotSingleTraces (path, perf_events, scales):
    ener = read (path + "/energy.csv")
    cgroups = read (path + "/cgroups.csv")
    power = []
    for i in range (1, len (ener["TIMESTAMP"])):
        power.append (float (ener ["CPU"][i]) -  float (ener ["CPU"][i - 1]))

    pg1 = {}
    pg2 = {}
    for z in range (len (perf_events)):
        p = perf_events [z]
        pg1[p] = []
        pg2[p] = []
        for i in range (1, len (ener["TIMESTAMP"])):
            pg1[p].append (getPerfEvent (ener["TIMESTAMP"][i], cgroups, p, "pg1") / scales [z])
            pg2[p].append (getPerfEvent (ener["TIMESTAMP"][i], cgroups, p, "pg2") / scales [z])

        plt.plot (pg1[p])
        plt.plot (pg2[p])
    plt.plot (power)
    # plt.show ()
    # plt.clf ()

def plotSingleTracesFile (path):
    ener = read (path)
    power = []
    for i in range (1, len (ener["TIMESTAMP"])):
        power.append (float (ener ["CPU"][i]) -  float (ener ["CPU"][i - 1]))

    plt.plot (power, label="RAPL")
    # plt.show ()


def plotSinglePowerMaxes (machine, HT, nameA, coreA, nameB, coreB, perf_event, scale) :
    model = constructModel (machine, HT, perf_event)
    (path, cores) = resDirectory (machine, HT)

    (raplMs, cycleAMs, cycleBMs) = getPowerVersusMaxes (path, nameA, coreA, nameB, coreB, nb=10, perf_event=perf_event)
    plt.plot (raplMs)
    plt.plot ([i / scale for i in cycleAMs])
    plt.plot ([i / scale for i in cycleBMs])
    resultA = []
    resultB = []
    for i in range (len (raplMs)) :
        rapl = raplMs [i]
        cycleA = cycleAMs [i]
        cycleB = cycleBMs [i]

        residu = rapl - estimateConso (model, cycleA + cycleB, perf_event)

        consoA = estimateConso (model, cycleA, perf_event) + model[2]
        consoB = estimateConso (model, cycleB, perf_event) + model[2]

        ratioA = consoA / (consoA + consoB)
        ratioB = consoB / (consoA + consoB)

        cA = rapl * ratioA
        cB = rapl * ratioB

        resultA.append (cA / cB * 100 - 100)
        #resultB.append (cB)

    plt.plot (removeExtremes (resultA))
    plt.plot (resultB)
    # plt.show ()
    plt.clf ()

def getPowerVersusCustomCheating (path, nameA, coreA, nameB, coreB, residu):
    """
    returns:
       - [0]: the rapl max power consumption of the machine when running 'A' and 'B' at the same time
       - [1]: the estimation of the power consumption of 'A'
       - [2]: the estimation of the power consumption of 'B'
    """

    (rapl, cycleA, cycleB) = getPowerVersus (path, nameA, coreA, nameB, coreB)
    consoA = getPowerAloneZ (path, nameA, coreA) - residu
    consoB = getPowerAloneZ (path, nameB, coreB) - residu

    ratioA = consoA / (consoA + consoB)
    ratioB = consoB / (consoA + consoB)

    return (rapl, rapl * ratioA, rapl * ratioB)


def analyseCustomCheating (machine, HT):
    """
    Generate the plot of scaphandre results for the machine 'machine', with or without hyperthreading ('HT')
    """

    residu = computeResidualConsumption (machine, HT)

    plt.clf ()
    (directory, cores) = resDirectory (machine, HT)
    cores = int (cores / 2)
    names = []
    allX = {}
    allY = {}

    mx = -1000
    mi = 1000
    for zA in range (1, cores + 1):
        for zB in range (1, cores + 1):
            curr = str (zA) + "_v_" + str (zB)

            allX [curr] = []
            allY [curr] = []
            for nameA in PG :
                try:
                    aloneA = getPowerAloneZ (directory, nameA, zA)
                    for nameB in PG :
                        aloneB = getPowerAloneZ (directory, nameB, zB)
                        try :
                            (rapl, cA, cB) = getPowerVersusCustomCheating (directory, nameA, zA, nameB, zB, residu)
                            allY [curr].append (cA / cB * 100 - 100)

                            vA = aloneA - residu
                            vB = aloneB - residu

                            allX [curr].append (vA / vB * 100 - 100)
                        except Exception as e:

                            #raise e
                            pass
                except Exception as e:
                    #raise e
                    pass

            if len (allX [curr]) != 0:
                print ("Cheating ", curr)
                print ("Distance ideal ", computeDistToOpt (allX[curr], allY[curr]))

    for x in allX :
        if (len (allX [x]) != 0):
            plt.scatter (allX [x], allY[x], label=x, s=0.1)
            mx = max (mx, max (max (allX [x]), max (allY[x])))
            mi = min (mi, min (min (allX [x]), min (allY[x])))

        red = [x for x in range (int (mi), int (mx))]
    plt.plot (red, red, color="red", linewidth=0.1)
    plt.legend ()
    plt.suptitle ("ALL")
    # plt.show ()
    plt.savefig (".build/ALL_cheating.png", dpi=300)

