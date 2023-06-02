import ast
import json 
import sys
from matplotlib import pyplot as plt
import operator

def sequential(directory, pg):
    consumption = {}
    pids = []
    with open(f"{directory}/sequential/{pg}_pids") as f:
        pids = ast.literal_eval(f.read())
        consumption = dict.fromkeys(pids, [])

    data = []
    with open(f"{directory}/sequential/results_{pg}.json") as f:
        data = json.load(f)

    for report in data:
        for consumer in report['consumers']:
            if str(consumer['pid']) in pids:
                consumption[str(consumer['pid'])].append(int(consumer['consumption']))

    for pid, conso in consumption.items():
        plt.plot([x for x in range(len(conso))], conso, label=pid)
    plt.legend()
    plt.show()
    plt.clf()

def parallel(directory, summed=False):
    consumption = {'pg1': {}, 'pg2': {}}
    with open(f"{directory}/parallel/pg1_pids") as f:
        pids = ast.literal_eval(f.read())
        consumption['pg1'] = dict.fromkeys(pids, [])

    with open(f"{directory}/parallel/pg2_pids") as f:
        pids = ast.literal_eval(f.read())
        consumption['pg2'] = dict.fromkeys(pids, [])

    data = []
    with open(f"{directory}/parallel/results_pg1.json") as f:
        data = json.load(f)

    for report in data:
        for consumer in report['consumers']:
            if str(consumer['pid']) in consumption['pg1'].keys():
                consumption['pg1'][str(consumer['pid'])].append(int(consumer['consumption']))
            elif str(consumer['pid']) in consumption['pg2'].keys():
                consumption['pg2'][str(consumer['pid'])].append(int(consumer['consumption']))

    for pg, pids in consumption.items():
        if summed:
            conso_s = list(map(operator.add, consumption[pg].values()))
            plt.plot([x for x in range(len(conso_s))], conso_s, label=pg)
        else:
            for pid, conso in consumption[pg].items():
                plt.plot([x for x in range(len(conso))], conso, label=f"{pg}-{pid}")
    plt.legend()
    plt.show()
    plt.clf()

if len(sys.argv) < 2:
    print("Usage: plot.py directory")
    sys.exit(1)

directory = sys.argv[1]

sequential(directory, "pg1")
sequential(directory, "pg2")
parallel(directory, summed=True)
