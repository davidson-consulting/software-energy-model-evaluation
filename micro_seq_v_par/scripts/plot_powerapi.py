import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
import sys
from tabulate import tabulate

def read_energy(directory):
    values = {}
    with open(f"{directory}/PowerReport.csv", "r") as f:
        rows = f.read().split("\n")[1:-1]
        for row in rows:
            data = row.split(",")
            values[data[0]] = (float(data[3]))
        return values

def avg_distance(values_seq, values_parallel):
    nb_runs = min(len(values_seq), len(values_parallel))

    distances = []
    for run in range(nb_runs):
        points = list(zip(values_seq[run], values_parallel[run]))
        idealmin = np.asarray((-100, -100))
        idealmax = np.asarray((100, 100))
        
        list_distances = []
        for point in points:
            print(point)
            list_distances.append(np.abs(np.cross(idealmax - idealmin, idealmax - point)) / np.linalg.norm(idealmax - idealmin))

        #return sum(list_distances) / len(list_distances)
        distances.append(np.mean(list_distances))
    return distances

def summary(diffs_sequential, diffs_parallel):
    # AVG Distance with idea value
    idealmin = np.asarray((-100, -100))
    idealmax = np.asarray((100, 100))

    for i in range(len(diffs_sequential)):
        points = list(zip(diffs_sequential[i], diffs_parallel[i]))
        list_distances = []
        for point in points:
            list_distances.append(np.abs(np.cross(idealmax - idealmin, idealmax - point)) / np.linalg.norm(idealmax - idealmin))

        print("Distance moyenne run ", np.mean(list_distances))


    # Nb of incoherences
    incoherences = []
    for i in range(len(diffs_sequential)):
        points = list(zip(diffs_sequential[i], diffs_parallel[i]))
        incoherences.append(0)
        for point in points:
            if (point[0] < 0 and point[1] > 0) or (point[0] > 0 and point[1] < 0):
                incoherences[i] += 1
    print(np.mean(incoherences))


def plot(diffs_sequential, diffs_parallel):
    x = np.mean(diffs_sequential, axis=0)
    y = np.mean(diffs_parallel, axis=0)
    xerror = [x - diffs_sequential.min(axis=0), diffs_sequential.max(axis=0) - x]
    yerror = [y - diffs_parallel.min(axis=0), diffs_parallel.max(axis=0) - y]
    #xerror = [x - np.quantile(diffs_sequential, 0.05, axis=0), np.quantile(diffs_sequential, 0.95, axis=0) - x]
    #yerror = [y - np.quantile(diffs_parallel, 0.05, axis=0), np.quantile(diffs_parallel, 0.95, axis=0) - y]
    plt.scatter(x, y)
    plt.errorbar(x, y, ls="none",
                 xerr=xerror,
                 yerr=yerror)
    plt.show()

def print_tikx(diffs_sequential, diffs_parallel):
    x = np.mean(diffs_sequential, axis=0)
    y = np.mean(diffs_parallel, axis=0)
    for z in zip(x, y):
        print(f"({z[0]:.5f}, {z[1]:.5f})")

def main(args):
    path = args.path
    c = args.cores

    diff_sequential_accross_run = []
    diff_parallel_accross_run = []
    for run in [f.path for f in os.scandir(path) if f.is_dir()]:
        experiments = [ f.path for f in os.scandir(run) if f.is_dir() ]

        diffs_parallel = []
        diffs_sequential = []
        tab = []
        for experiment in experiments:
            #try:
                (pg1, pg2) = experiment[2:].split("_vs_")
                row = [pg1, pg2]
                # PARALLEL
                systemParallel = sum(read_energy(f"{experiment}/{c}/parallel/output/cpu-global/").values())
                pg1Parallel = sum(read_energy(f"{experiment}/{c}/parallel/output/cpu-/pg1").values())
                pg2Parallel = sum(read_energy(f"{experiment}/{c}/parallel/output/cpu-/pg2").values())
                
                row.append(systemParallel)
                row.append(pg1Parallel)
                row.append(pg2Parallel)
                                
                diffs_parallel.append((pg1Parallel - pg2Parallel) / pg1Parallel * 100)
                print(f"{experiment} - {(pg1Parallel - pg2Parallel) / pg1Parallel * 100}")
                # SEQUENTIAL
                pg1Sequential = sum(read_energy(f"{experiment}/{c}/sequential/pg1/output/cpu-rapl").values())
                pg2Sequential = sum(read_energy(f"{experiment}/{c}/sequential/pg2/output/cpu-rapl").values())
                
                row.append(pg1Sequential)
                row.append(pg2Sequential)

                diffs_sequential.append((pg1Sequential - pg2Sequential) / pg2Sequential * 100)

                tab.append(row)
            #except:
            #    print(f"NOT FOUND: {experiment}")
            #    continue
        diff_sequential_accross_run.append(diffs_sequential)
        diff_parallel_accross_run.append(diffs_parallel)
        
    diff_sequential_accross_run = np.array(diff_sequential_accross_run)
    diff_parallel_accross_run = np.array(diff_parallel_accross_run)

    #print_tikx(diff_sequential_accross_run, diff_parallel_accross_run)
    #plot(diff_sequential_accross_run, diff_parallel_accross_run)
    print(np.mean(avg_distance(diff_sequential_accross_run, diff_parallel_accross_run)))
    summary(diff_sequential_accross_run, diff_parallel_accross_run)

 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("cores")
    args = parser.parse_args()
    main(args)
