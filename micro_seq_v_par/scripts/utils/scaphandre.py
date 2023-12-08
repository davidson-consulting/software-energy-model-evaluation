#!/usr/bin/env python3

from utils.common import *
from utils.custom import *
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

import traceback


def readMaxes (ener, nb):
    maxes = [0 for i in range (nb)]
    res = [(0, 0, 0) for i in range (nb)]
    currentMinIndex = 0

    for i in range (len (ener["FULL"])) :
        f = float (ener ["FULL"][i])
        A = float (ener ["PG1"][i])
        B = float (ener ["PG2"][i])
        if (A + B > maxes [currentMinIndex]):
            res [currentMinIndex] = (f, A, B)
            maxes [currentMinIndex] = A + B
            currentMinIndex = maxes.index (min (maxes))
    return res

def getPowerVersusScaphandre (path, nameA, coreA, nameB, coreB):
    """
    returns:
       - [0]: the rapl max power consumption of the machine when running 'A' and 'B' at the same time
       - [1]: the estimation of the power consumption of 'A'
       - [2]: the estimation of the power consumption of 'B'
    """

    ener = read (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/scaphandre.csv")
    try :
        res = readMaxes (ener, 5)
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
    except Exception as e:
        raise e
        # print (path + "/result/" + nameA + "-v-" + nameB + "-" + str (coreA) + "_" + str (coreB) + "/scaphandre.csv")
        # traceback.print_exc ()

def analyseScapandre (machine, HT, machineNoCap = ""):
    """
    Generate the plot of scaphandre results for the machine 'machine', with or without hyperthreading ('HT')
    """

    residuA = computeResidualConsumption (machine, HT)


    #plt.clf ()
    (directory, cores) = resDirectory (machine, HT)

    machineB = machineNoCap
    if (machineB == ""):
        machineB = machine
    (directoryB, cores) = resDirectory (machineB, HT)
    residuB = computeResidualConsumption (machineB, HT)

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
            curr = str (zA) + "_v_" + str (zB)
            allX [curr] = []
            allY [curr] = []

            errors [curr] = 0
            errorsNB [curr] = 0
            maxError [curr] = 0

            for nameA in PG :
                try:
                    aloneA = getPowerAloneZ (directory, nameA, zA)
                    for nameB in PG :
                        aloneB = getPowerAloneZ (directoryB, nameB, zB)

                        try :
                            (both, ratio, values) = getPowerVersusScaphandre (directory, nameA, zA, nameB, zB)

                            vA = aloneA - residuA
                            vB = aloneB - residuA

                            for i in range (len (ratio)):
                                allY [curr].append (ratio[i])
                                allX [curr].append (vA / vB * 100 - 100)

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
                                # if (errorA > 4 and nameA != nameB):
                                #     print (nameA, " ", nameB, " ", errorA)

                                errorsNB [curr] += 2


                        except Exception as e:
                            #print (e)
                            pass
                except Exception as e:
                    #print (e)
                    pass

            # if (errorsNB [curr] != 0) :
            #     print (curr, " ", errors [curr] / errorsNB [curr], " ", errorsNB [curr], " ", maxError [curr])

            # if len (allX [curr]) != 0:
            #     print ("Scaphandre ", curr)
            #     print ("Distance ideal ", computeDistToOpt (allX[curr], allY[curr]))


    allNb = sum (errorsNB.values ())
    allErrors = sum (errors.values ())
    maxError = max (maxError.values ())
    print ("FINAL : ", allErrors / allNb, " ", maxError)


    for x in allX :
            if (len (allX [x]) != 0):
                print (x)
                for i in range (len (allX[x])):
                    print (f"({allX [x][i]},{allY [x][i]})")
                print ("")
                print ("")
                print ("===")

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
    plt.savefig (".build/ALL_scaph" + str (HT) + ".png", dpi=300)
