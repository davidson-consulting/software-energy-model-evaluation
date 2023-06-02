import argparse
import os
from matplotlib import pyplot as plt
import numpy as np
from tabulate import tabulate

def fetch_results(directory, cores):
    diff_sequential = 0
    diff_parallel = 0

    seq1 = 0
    seq2 = 0
    with open(f"{directory}/{cores}/sequential/pg1", "r") as f:
        seq1 = int(float(f.read()))
    with open(f"{directory}/{cores}/sequential/pg2", "r") as f:
        seq2 = int(float(f.read()))
    diff_sequential = (seq1 - seq2) / seq1 * 100

    para1 = 0
    para2 = 0
    with open(f"{directory}/{cores}/parallel/pg1", "r") as f:
        para1 = int(float(f.read()))
    with open(f"{directory}/{cores}/parallel/pg2", "r") as f:
        para2 = int(float(f.read()))
    diff_parallel = (para1 - para2) / para1 * 100


    return (diff_sequential, diff_parallel)
    
def incoherences(data):
    incoherences = 0
    for s1 in data.keys():
        for s2 in data[s1].keys():
            if s1 == s2:
                continue
            for s3 in data[s2].keys():
                if s3 == s1 or s3 == s2:
                    continue
                if data[s1][s2] > 1 and data[s2][s3] > 1 and data[s1][s3] < -1:
                        print(f"INCOHERENCE: {s1} > {s2} ({data[s1][s2]}) ; {s2} > {s3} ({data[s2][s3]}) but {s1} < {s3} ({data[s1][s3]})")
                        incoherences += 1
                if data[s1][s2] < -1 and data[s2][s3] < -1 and data[s1][s3] > 1:
                        print(f"INCOHERENCE: {s1} < {s2} ({data[s1][s2]}) ; {s2} < {s3} ({data[s2][s3]}) but {s1} > {s3} ({data[s1][s3]})")
                        incoherences += 1
    return incoherences
        

def main(args):
    path = args.path
    cores = args.cores

    xps = []
    nb_incoherences = []
    for run in [f.path for f in os.scandir(path) if f.is_dir()]:
        print(f"RUN {run.split('/')[-1]}")
        xps = [f.path for f in os.scandir(run) if f.is_dir()]

        data = {}
        for xp in xps:
            (pg1, pg2) = xp.split("/")[-1].split("_vs_")
            (diff_sequential, diff_parallel) = fetch_results(xp, cores)
            
            if pg1 not in data.keys():
                data[pg1] = {}

            if pg2 not in data.keys():
                data[pg2] = {}

            data[pg1][pg2] = diff_parallel
            data[pg2][pg1] = diff_parallel * -1

        nb_incoherences.append(incoherences(data))
    print(nb_incoherences)
    print(np.mean(nb_incoherences))
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("cores")
    args = parser.parse_args()
    main(args)
