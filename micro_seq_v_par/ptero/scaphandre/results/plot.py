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

def table(xps, diffs_sequential, diffs_parallel):
    print("DIFFERENCES IN SEQUENTIAL")
    print(tabulate({
                    "XP": xps,
                    "MIN": np.min(diffs_sequential, axis=0),
                    "MAX": np.max(diffs_sequential, axis=0),
                    "MEAN": np.mean(diffs_sequential, axis=0),
                    "MEDIAN": np.median(diffs_sequential, axis=0),
                    "STD": np.std(diffs_sequential, axis=0),
                    }, headers="keys"))

    print("DIFFERENCES IN PARALLEL")
    print(tabulate({
                    "XP": xps,
                    "MIN": np.min(diffs_parallel, axis=0),
                    "MAX": np.max(diffs_parallel, axis=0),
                    "MEAN": np.mean(diffs_parallel, axis=0),
                    "MEDIAN": np.median(diffs_parallel, axis=0),
                    "STD": np.std(diffs_parallel, axis=0),
                    }, headers="keys"))

def plot(diffs_sequential, diffs_parallel):
    x = np.mean(diffs_sequential, axis=0)
    y = np.mean(diffs_parallel, axis=0)
    #xerror = [x - diffs_sequential.min(axis=0), diffs_sequential.max(axis=0) - x]
    #yerror = [y - diffs_parallel.min(axis=0), diffs_parallel.max(axis=0) - y]
    xerror = [x - np.sort(diffs_sequential, axis=0)[1], np.sort(diffs_sequential, axis=0)[-2] - x]
    yerror = [y - np.sort(diffs_parallel, axis=0)[1], np.sort(diffs_parallel, axis=0)[-2] - y]
    plt.scatter(x, y)
    plt.errorbar(x, y, ls="none",
                 xerr=xerror,
                 yerr=yerror)
    plt.show()

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
    for i in range(len(diffs_sequential)):
        points = list(zip(diffs_sequential[i], diffs_parallel[i]))
        incoherences = 0
        for point in points:
            if (point[0] < 0 and point[1] > 0) or (point[0] > 0 and point[1] < 0):
                incoherences += 1
        print(incoherences)
    
def main(args):
    run = args.run
    cores = args.cores

    xps = []
    diff_sequential_accross_run = []
    diff_parallel_accross_run = []
    for run in range(1, 9):
        xps = [f.path for f in os.scandir(f"./{run}") if f.is_dir()]

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

    table(xps, diff_sequential_accross_run, diff_parallel_accross_run)
    plot(diff_sequential_accross_run, diff_parallel_accross_run)
    summary(diff_sequential_accross_run, diff_parallel_accross_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("cores")
    args = parser.parse_args()
    main(args)
