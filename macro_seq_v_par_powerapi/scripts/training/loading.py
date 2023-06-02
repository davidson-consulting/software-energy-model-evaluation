#!/usr/bin/env python3

import csv
import matplotlib.pylab as plt
import os
import argparse
import numpy
from scipy.signal import lfilter


def readCsv (filename, split=';') :
    #
    # Read a csv file, and return the header and each rows
    # @params:
    #    - filename: a csv file
    #
    #
    with open (filename, "r") as fp :
        reader = csv.reader (fp)
        head = next (reader)
        rows = []
        for row in reader :
            rows.append (row)
        return (head, rows)

def parseEnergyCsv (anon):
    #
    # Parse an energy csv file
    # @returns: the consumption in watt (one point per second), and the speeds of the CPU cores in hz
    #
    (head, rows) = readCsv (anon)
    nb_cores = len (head) - 4
    energy = []
    speeds = []
    for row in rows :
        val = float (row[1].strip ())
        energy.append (val)
        speeds.append ([])
        for i in range (nb_cores) :
            speeds [-1].append (int (row [i + 4]))

    watts = [energy [0]]
    for i in range (1, len (energy)) :
        watts.append (energy [i] - energy [i - 1])

    return (watts, speeds)

def parsePerfCountersCsv (anon, including = "", exluding = "#SYSTEM") :
    #
    # Parse a perf counter csv file
    # @params:
    #    - filtering: only get the line where filtering is contained in the cgroup name
    #    - exluding: get the lines where exluding is no contained in the cgroup name
    #
    # @returns: The sum of performance counter (one point per second)
    #
    (head, rows) = readCsv (anon)
    result = {}
    for row in rows :
        if including in row [1] and exluding not in row [1]:
            time = int (float (row [0].strip ()))
            for i in range (2, len (head)) :
                if head [i] in result :
                    if (time in result [head [i]]):
                        result [head [i]][time] += float (row [i].strip ())
                    else :
                        result [head [i]][time] = float (row [i].strip ())
                else :
                    result [head [i]] = {time : float (row [i].strip ())}

    RR = {}
    for i in result :
        lists = sorted(result [i].items()) # sorted by key, return a list of tuples
        x_2, y_2 = zip(*lists)
        RR [i] = y_2


    return RR
