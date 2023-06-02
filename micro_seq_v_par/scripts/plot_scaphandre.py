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

def avg_distance(values_seq, values_parallel):
    nb_runs = min(len(values_seq), len(values_parallel))

    distances = []
    for run in range(nb_runs):
        points = list(zip(values_seq[run], values_parallel[run]))
        idealmin = np.asarray((-100, -100))
        idealmax = np.asarray((100, 100))
        
        list_distances = []
        for point in points:
            list_distances.append(np.abs(np.cross(idealmax - idealmin, idealmax - point)) / np.linalg.norm(idealmax - idealmin))

        #return sum(list_distances) / len(list_distances)
        distances.append(np.mean(list_distances))
    return distances

def table(xps, diffs_sequential, diffs_parallel):
    print("DIFFERENCES IN SEQUENTIAL")
    print(tabulate({
                    "XP": xps,
                    "MEAN": np.mean(diffs_sequential, axis=0),
                    "MEDIAN": np.median(diffs_sequential, axis=0),
                    "STD": np.std(diffs_sequential, axis=0),
                    }, headers="keys"))

    print("DIFFERENCES IN PARALLEL")
    print(tabulate({
                    "XP": xps,
                    "MEAN": np.mean(diffs_parallel, axis=0),
                    "MEDIAN": np.median(diffs_parallel, axis=0),
                    "STD": np.std(diffs_parallel, axis=0),
                    }, headers="keys"))

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
    
def main(args):
    path = args.path
    cores = args.cores

    xps = []
    diff_sequential_accross_run = []
    diff_parallel_accross_run = []
    for run in [f.path for f in os.scandir(path) if f.is_dir()]:
        xps = [f.path for f in os.scandir(run) if f.is_dir()]

        diffs_sequential = []
        diffs_parallel = []
        for xp in xps:
            (diff_sequential, diff_parallel) = fetch_results(xp, cores)
            diffs_sequential.append(diff_sequential)
            diffs_parallel.append(diff_parallel)
        
        diff_sequential_accross_run.append(diffs_sequential)
        diff_parallel_accross_run.append(diffs_parallel)

    diff_sequential_accross_run = np.array(diff_sequential_accross_run)
    diff_parallel_accross_run = np.array(diff_parallel_accross_run)
    xps = [x.split("/")[-1] for x in xps]

    #table(xps, diff_sequential_accross_run, diff_parallel_accross_run)
    #plot(diff_sequential_accross_run, diff_parallel_accross_run)
    summary(diff_sequential_accross_run, diff_parallel_accross_run)
    #print_tikx(diff_sequential_accross_run, diff_parallel_accross_run)
    print(np.mean(avg_distance(diff_sequential_accross_run, diff_parallel_accross_run)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("cores")
    args = parser.parse_args()
    main(args)
