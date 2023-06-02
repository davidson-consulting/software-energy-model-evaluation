import argparse
import os
from matplotlib import pyplot as plt
import numpy as np
from tabulate import tabulate

def fetch_results(directory, cores):
    seq1 = 0
    seq2 = 0
    with open(f"{directory}/{cores}/sequential/pg1", "r") as f:
        seq1 = int(float(f.read()) * 10**-7)
    with open(f"{directory}/{cores}/sequential/pg2", "r") as f:
        seq2 = int(float(f.read()) * 10**-7)

    para1 = 0
    para2 = 0
    with open(f"{directory}/{cores}/parallel/pg1", "r") as f:
        para1 = int(float(f.read()) * 10**-7)
    with open(f"{directory}/{cores}/parallel/pg2", "r") as f:
        para2 = int(float(f.read()) * 10**-7)

    return (seq1, para1, seq2, para2)
    
def variability(data):    
    i = 1
    ytick = "ytick={"
    yticklabels = "yticklabels={"
    for s in data.keys():
        ytick += f"{i},"
        i += 1
        
        yticklabels += f"{s},"
    
    print("\\begin{tikzpicture}")
    print("\\begin{axis}")
    print("\t[")
    print(f"\t{ytick},")
    print(f"\t{yticklabels},")
    print("\t]")

    for s in data.keys():
        sequential = np.array(data[s]["sequential"])
        print("\\addplot+[")
        print("boxplot prepared={")
        print(f"\tmedian={np.median(sequential)},")
        print(f"\tupper quartile={np.percentile(sequential, 75)},")
        print(f"\tlower quartile={np.percentile(sequential, 25)},")
        print(f"\tupper whisker={sequential.max()},")
        print(f"\tlower whisker={sequential.min()},")
        print("},")
        print("] coordinates {};")
    print("\\end{axis}")

    i = 1
    ytick = "ytick={"
    yticklabels = "yticklabels={"
    for s in data.keys():
        ytick += f"{i},"
        i += 1
        
        yticklabels += f"{s},"

    print("\\begin{axis}")
    print("\t[")
    print(f"\t{ytick},")
    print(f"\t{yticklabels},")
    print("\t]")
    for s in data.keys():
        parallel = np.array(data[s]["parallel"])
        print("\\addplot+[")
        print("boxplot prepared={")
        print(f"\tmedian={np.median(parallel)},")
        print(f"\tupper quartile={np.percentile(parallel, 75)},")
        print(f"\tlower quartile={np.percentile(parallel, 25)},")
        print(f"\tupper whisker={parallel.max()},")
        print(f"\tlower whisker={parallel.min()},")
        print("},")
        print("] coordinates {};")
    print("\\end{axis}")
    print("\\end{tikzpicture}")

def main(args):
    path = args.path
    cores = args.cores

    xps = []
    data = {}
    for run in [f.path for f in os.scandir(path) if f.is_dir()]:
        print(f"\n\nRUN {run.split('/')[-1]}")
        xps = [f.path for f in os.scandir(run) if f.is_dir()]

        for xp in xps:
            (pg1, pg2) = xp.split("/")[-1].split("_vs_")
            (seq1, para1, seq2, para2) = fetch_results(xp, cores)
            
            if pg1 not in data.keys():
                data[pg1] = {
                    "parallel": [],
                    "sequential": []
                }

            if pg2 not in data.keys():
                data[pg2] = {
                    "parallel": [],
                    "sequential": []
                }

            data[pg1]["sequential"].append(seq1)
            data[pg1]["parallel"].append(para1)
            data[pg2]["sequential"].append(seq2)
            data[pg2]["parallel"].append(para2)

        
    variability(data)
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("cores")
    args = parser.parse_args()
    main(args)
