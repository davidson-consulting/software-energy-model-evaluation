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

def print_avg_distance(values_seq, values_parallel):
    points = list(zip(values_seq, values_parallel))
    idealmin = np.asarray((-100, -100))
    idealmax = np.asarray((100, 100))
    
    list_distances = []
    for point in points:
        list_distances.append(np.abs(np.cross(idealmax - idealmin, idealmax - point)) / np.linalg.norm(idealmax - idealmin))

    #return sum(list_distances) / len(list_distances)
    return np.mean(list_distances)

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 models.py CORES")
        sys.exit(1)

    c = int(sys.argv[1])
    runs = [ f.path for f in os.scandir("results") if f.is_dir() ]

    diff_sequential_accross_run = []
    diff_parallel_accross_run = []
    for run in runs:
        experiments = [ f.path for f in os.scandir(run) if f.is_dir() ]

        diffs_parallel = []
        diffs_sequential = []
        tab = []
        for experiment in experiments:
            try:
                (pg1, pg2) = experiment[2:].split("_vs_")
                row = [pg1, pg2]
                # PARALLEL
                systemParallel = sum(read_energy(f"{experiment}/{c}/parallel/output/sensor-global/").values())
                pg1Parallel = sum(read_energy(f"{experiment}/{c}/parallel/output/sensor-/pg1").values())
                pg2Parallel = sum(read_energy(f"{experiment}/{c}/parallel/output/sensor-/pg2").values())
                
                row.append(systemParallel)
                row.append(pg1Parallel)
                row.append(pg2Parallel)
                
                diffs_parallel.append((pg1Parallel - pg2Parallel) / pg1Parallel * 100)

                # SEQUENTIAL
                pg1Sequential = sum(read_energy(f"{experiment}/{c}/sequential/pg1/output/sensor-rapl").values())
                pg2Sequential = sum(read_energy(f"{experiment}/{c}/sequential/pg2/output/sensor-rapl").values())
                
                row.append(pg1Sequential)
                row.append(pg2Sequential)

                diffs_sequential.append((pg1Sequential - pg2Sequential) / pg2Sequential * 100)

                tab.append(row)
            except:
                print("NOT FOUND: {experiment}")
                continue
        diff_sequential_accross_run.append(diffs_sequential)
        diff_parallel_accross_run.append(diffs_parallel)
        
    diff_sequential_accross_run = np.array(diff_sequential_accross_run)
    diff_parallel_accross_run = np.array(diff_parallel_accross_run)

    plot(diff_sequential_accross_run, diff_parallel_accross_run)

    
