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


def plotSingleTracesFile (source):
    # (path, cores) = resDirectory (machine, HT)

    ener = read (source)
    times = [float (i) for i in ener ["timestamp"]]
    rapl = [float (i) for i in ener ["RAPL"]]
    glob = [float (i) for i in ener ["glob"]]
    pg1 = [float (i) for i in ener ["PG1"]]
    pg2 = [float (i) for i in ener ["PG2"]]

    times, rapl, glob, pg1, pg2 = (list(t) for t in zip(*sorted(zip(times, rapl, glob, pg1, pg2))))

    # plt.clf ()

    plt.plot (rapl, label="rapl")
    plt.plot (glob, label="glob")
    plt.plot (pg1, label="PG1")
    plt.plot (pg2, label="PG2")


    print (pg1, " ", pg2)

    plt.legend ()
    plt.show ()
    plt.savefig (f".build/{nameA}-v-{nameB}-{coreA}_{coreB}_powerapi.png", dpi = 300)


def plotSingleTraces (machine, HT, nameA, coreA, nameB, coreB):
    (path, cores) = resDirectory (machine, HT)

    ener = read (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/powerapi.csv")
    times = [float (i) for i in ener ["timestamp"]]
    rapl = [float (i) for i in ener ["RAPL"]]
    glob = [float (i) for i in ener ["glob"]]
    pg1 = [float (i) for i in ener ["PG1"]]
    pg2 = [float (i) for i in ener ["PG2"]]

    times, rapl, glob, pg1, pg2 = (list(t) for t in zip(*sorted(zip(times, rapl, glob, pg1, pg2))))

    plt.clf ()

    rapl_ = [rapl [i] + rapl [i + 1] for i in range (0, len (rapl) - 1, 2)]
    glob_ = [glob [i] + glob [i + 1] for i in range (0, len (glob) - 1, 2)]

    pg1_ = [pg1 [i] + pg1 [i + 1] for i in range (0, len (pg1) - 1, 2)]
    pg2_ = [pg2 [i] + pg2 [i + 1] for i in range (0, len (pg2) - 1, 2)]

    print (pg1)
    print (pg1_)
    plt.plot (rapl_, label="rapl")
    plt.plot (glob_, label="glob")
    plt.plot (pg1_, label=nameA)
    plt.plot (pg2_, label=nameB)

    print ("rapl")
    for i in range (len (rapl_)) :
        print (f"({i}, {rapl_[i]})")

    print ("glob")
    for i in range (len (glob_)) :
        print (f"({i}, {glob_[i]})")

    print (nameA)
    for i in range (len (pg1_)) :
        print (f"({i}, {pg1_[i]})")

    print ("===")
    print (nameB)
    for i in range (len (pg2_)) :
        print (f"({i}, {pg2_[i]})")

    plt.legend ()
    plt.show ()
    plt.savefig (f".build/{nameA}-v-{nameB}-{coreA}_{coreB}_powerapi.png", dpi = 300)

def readMaxes (ener, nb):
    maxes = [0 for i in range (nb)]
    res = [(0, 0, 0) for i in range (nb)]
    currentMinIndex = 0

    for i in range (len (ener["RAPL"])) :
        f = float (ener ["RAPL"][i])
        A = float (ener ["PG1"][i])
        B = float (ener ["PG2"][i])
        if (A+B > maxes [currentMinIndex]):
            res [currentMinIndex] = (f, A, B)
            maxes [currentMinIndex] = A+B
            currentMinIndex = maxes.index (min (maxes))

    l = 0
    for i in range (len (maxes)):
        if maxes [i] == 0:
            break;
        l += 1

    return res[:l]

def getPowerVersusPowerAPI (path, nameA, coreA, nameB, coreB):
    """
    returns:
       - [0]: the rapl max power consumption of the machine when running 'A' and 'B' at the same time
       - [1]: the estimation of the power consumption of 'A'
       - [2]: the estimation of the power consumption of 'B'
    """

    ener = read (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/powerapi.csv")
    res = readMaxes (ener, 10)
    values = []
    ratio = []
    for measure in res :
        if (measure [1] != 0 and measure [2] != 0):
            ratio.append (measure [1] / measure [2] * 100 - 100)
            values.append ((measure [1], measure [2]))

    (ratio, values) = removeExtremes (ratio, values)

    if (np.var (ratio) < 1):
        return (max (res[0]), [ratio[0]], [values[0]])
    else :
        return (max (res[0]), ratio, values)

def analysePowerAPI (machine, HT):
    """
    Generate the plot of powerapi results for the machine 'machine', with or without hyperthreading ('HT')
    """

    residu = computeResidualConsumption (machine, HT)
    plt.clf ()
    (directory, cores) = resDirectory (machine, HT)
    cores = int (cores / 2)
    names = []
    allX = {}
    allY = {}

    errors = {}
    errorsNB = {}
    maxError = {}

    mx = -1000
    mi = 1000
    for zA in range (1, cores + 1):
        for zB in range (1, cores + 1):
            if (zA == zB):
                continue
            curr = str (zA) + "_v_" + str (zB)
            allX [curr] = []
            allY [curr] = []
            errors [curr] = 0
            errorsNB [curr] = 0
            maxError [curr] = 0
            for nameA in PG :
                try :
                    aloneA = getPowerAloneZ (directory, nameA, zA)
                    for nameB in PG :
                        try :
                            aloneB = getPowerAloneZ (directory, nameB, zB)
                            (both, ratio, values) = getPowerVersusPowerAPI (directory, nameA, zA, nameB, zB)

                            vA = aloneA #- residu
                            vB = aloneB #- residu

                            expected = vA / vB * 100 - 100
                            if (expected > 40):
                                print (nameA, " ", nameB)

                            for i in range (len (ratio)) :
                                allY [curr].append (ratio [i])
                                allX [curr].append (expected)


                            for i in range (len (values)):
                                ceA = values [i][0]
                                ceB = values [i][1]

                                vAR = vA / (vA + vB)
                                vBR = vB / (vA + vB)

                                ceAR = ceA / (ceA + ceB)
                                ceBR = ceB / (ceA + ceB)

                                errorA = abs (vAR - ceAR) * 100
                                errorB = abs (vBR - ceBR) * 100


                                errors [curr] += errorA
                                errors [curr] += errorB
                                maxError [curr] = max (maxError [curr], max (errorA, errorB))
                                errorsNB[curr] += 2

                        except Exception as e:
                            # print (e)
                            pass
                except Exception as e:
                    #print (e)
                    pass

            if (errorsNB [curr] != 0) :
                print (curr, " ", errors [curr] / errorsNB [curr], " ", errorsNB [curr], " ", maxError [curr])
                
                # if len (allX [curr]) != 0:
            #     print ("PowerApi", curr)
            #     print ("Distance ideal ", computeDistToOpt (allX[curr], allY[curr]))


    allNb = sum (errorsNB.values ())
    allErrors = sum (errors.values ())
    maxError = max (maxError.values ())
    print ("FINAL : ", allErrors / allNb, " ", maxError)

    # for x in allX :
    #         if (len (allX [x]) != 0):
    #             print (x)
    #             for i in range (len (allX[x])):
    #                 print (f"({allX [x][i]},{allY [x][i]})")
    #             print ("")
    #             print ("")
    #             print ("===")

    for x in allX :
        if (len (allX [x]) != 0):
            plt.scatter (allX [x], allY[x], label=x, s=0.5)
            mx = max (mx, max (max (allX [x]), max (allY[x])))
            mi = min (mi, min (min (allX [x]), min (allY[x])))

    red = [x for x in range (int (mi), int (mx))]
    plt.plot (red, red, color="red", linewidth=0.1)
    plt.legend ()
    plt.suptitle ("ALL")
    plt.show ()
    plt.savefig (f".build/ALL_powerapi_{HT}.png", dpi=300)
