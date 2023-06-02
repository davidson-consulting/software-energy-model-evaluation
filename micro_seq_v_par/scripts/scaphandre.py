import time
import os
import subprocess
import pathlib
import shutil
import json 
import argparse
#from vjoule_api_py.vjoule_api import *

REPEAT = 10
PG = {
            'ackermann': 16667, 
            'float64': 18182, 
            'matrixprod': 22222, 
            'rand': 16000, 
            'int64': 18182, 
            'decimal64': 16667, 
            'jmp': 18182, 
            'queens': 18182, 
            'fibonacci': 15384, 
            'double': 16667, 
            'int64float': 18182, 
            'int64double': 18182
}

def get_pids_in_cgroup(cgroup):
    with open(f"{cgroup}/cgroup.procs", "r") as f:
        return f.read().split("\n")[:-1]

def export_results(pids, directory, file):
    print("exporting results for pids : ", pids)
    power_host = 0
    power = 0
    expected_read = len(pids)
    with open("/tmp/results.json", "r") as f:
        results = json.load(f)
        for result in results:
            save_host_power = False
            for consumer in result["consumers"]:
                if str(consumer["pid"]) in pids:
                    power += consumer["consumption"]
                    expected_read -= 1
                    save_host_power = True
            if save_host_power:
                power_host += result["host"]["consumption"]

    if expected_read > 0:
        print("SOME PIDS MISSED")

    with open(f"{directory}/{file}", "w+") as f:
        f.write(str(power))

    with open(f"{directory}/{file}_host", "w+") as f:
        f.write(str(power_host))

    shutil.copyfile("/tmp/results.json", f"{directory}/results_{file}.json")

def run_in_parallel(pg1_name, pg1_nb_ops, pg2_name, pg2_nb_ops, cores):
    if os.path.isfile("/tmp/results.json"):
        os.remove("/tmp/results.json")
    scaphandre = subprocess.Popen(["scaphandre", "json", "--max-top-consumers", "15", "-t", "60", "-s", "0", "-n", "100000000", "-f", "/tmp/results.json"])
    time.sleep(1)

    processes = []

    for _ in range(cores):
        processes.append(subprocess.Popen(["cgexec", "-g", "cpu:/pg1", "stress-ng", "-c", "1", "--cpu-method", pg1_name, "--cpu-ops", str(pg1_nb_ops)]))
        processes.append(subprocess.Popen(["cgexec", "-g", "cpu:/pg2", "stress-ng", "-c", "1", "--cpu-method", pg2_name, "--cpu-ops", str(pg2_nb_ops)]))

    time.sleep(1)

    pids_pg1 = get_pids_in_cgroup("/sys/fs/cgroup/pg1")
    pids_pg2 = get_pids_in_cgroup("/sys/fs/cgroup/pg2")
     
    for process in processes:
        process.wait()

    time.sleep(1)
    scaphandre.kill()

    return (pids_pg1, pids_pg2)

def run(pg_name, pg_nb_ops, cores):
    if os.path.isfile("/tmp/results.json"):
        os.remove("/tmp/results.json")
    scaphandre = subprocess.Popen(["scaphandre", "json", "--max-top-consumers", "15", "-t", "60", "-s", "0", "-n", "100000000", "-f", "/tmp/results.json"])
    #subprocess.Popen(["systemctl", "start", "vjoule_service"])
    time.sleep(1)
    #vjoule = subprocess.Popen(["vjoule", "top", "-o", "/tmp/vjoule.csv"])

    processes = []
    for _ in range(cores):
        processes.append(subprocess.Popen(["cgexec", "-g", "cpu:/pg1", "stress-ng",  "-c", "1", "--cpu-method", pg_name, "--cpu-ops", str(pg_nb_ops)]))

    time.sleep(1)

    pids_pg1 = get_pids_in_cgroup("/sys/fs/cgroup/pg1")
    
    for process in processes:
        process.wait()
   
    time.sleep(1)
    scaphandre.kill()
    #vjoule.kill()

    return pids_pg1

def main_run_one(args):
    pg1_name = args.pg

    api = VJouleAPI ()

    for i in range(REPEAT):
        pathlib.Path(f"results/{i}").mkdir(parents=True, exist_ok=True)
        for c in [1, 3, 6]:
            pathlib.Path(f"results/{i}/{c}").mkdir(parents=True, exist_ok=True)
            print(f"RUN {pg1_name} FOR {c} CORES") 

            m_beg = api.getCurrentMachineConsumption ()
            pids = run(pg1_name, PG[pg1_name] * args.time_factor, c)
            m_end = api.getCurrentMachineConsumption ()
            m_diff = m_end - m_beg
            print("RAPL :")
            print(m_diff)
            export_results(pids, f"results/{i}/{c}/pg")
            shutil.copyfile("/tmp/vjoule.csv", f"results/{i}/{c}/vjoule.csv") 


def _run(pg1_name, pg2_name, result_dir, time_factor=1):
    for c in [1, 3, 6]:
        pathlib.Path(f"{result_dir}/{pg1_name}_vs_{pg2_name}/{c}").mkdir(parents=True, exist_ok=True)
        print(f"RUN {pg1_name} vs {pg2_name} FOR {c} CORES") 

        xp_ok = False

        pathlib.Path(f"{result_dir}/{pg1_name}_vs_{pg2_name}/{c}/parallel").mkdir(parents=True, exist_ok=True)
        
        while not xp_ok:
            try:
                (pids_pg1, pids_pg2) = run_in_parallel(pg1_name, PG[pg1_name] * time_factor, pg2_name, PG[pg2_name] * time_factor, c)
                export_results(pids_pg1, f"{result_dir}/{pg1_name}_vs_{pg2_name}/{c}/parallel/", "pg1")
                export_results(pids_pg2, f"{result_dir}/{pg1_name}_vs_{pg2_name}/{c}/parallel/", "pg2")
                xp_ok = True
            except e:
                print(e)
                continue

        pathlib.Path(f"{result_dir}/{pg1_name}_vs_{pg2_name}/{c}/sequential").mkdir(parents=True, exist_ok=True)

        xp_ok = False

        while not xp_ok:
            try:
                pids = run(pg1_name, PG[pg1_name] * time_factor, c)
                export_results(pids, f"{result_dir}/{pg1_name}_vs_{pg2_name}/{c}/sequential/", "pg1")
                xp_ok = True
            except e:
                print(e)
                continue
        
        xp_ok = False

        while not xp_ok:
            try:
                pids = run(pg2_name, PG[pg2_name] * time_factor, c)
                export_results(pids, f"{result_dir}/{pg1_name}_vs_{pg2_name}/{c}/sequential/", "pg2")
                xp_ok = True
            except e:
                print(e)
                continue

def main_run(args):
    pg1_name = args.pg1
    pg2_name = args.pg2

    subprocess.run(["cgcreate", "-g", "cpu:/pg1"])
    subprocess.run(["cgcreate", "-g", "cpu:/pg2"])

    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path(f"results/{pg1_name}_vs_{pg2_name}").mkdir(parents=True, exist_ok=True)
    _run(pg1_name, pg2_name, "results")

def main_all(args): 
    subprocess.run(["cgcreate", "-g", "cpu:/pg1"])
    subprocess.run(["cgcreate", "-g", "cpu:/pg2"])

    pathlib.Path("results").mkdir(exist_ok=True)

    for i in range(REPEAT):
        pg_names = list(PG.keys())
        for _ in range(len(pg_names)):
            pg1_name = pg_names.pop()
            for pg2_name in pg_names:
                pathlib.Path(f"results/{i}/{pg1_name}_vs_{pg2_name}").mkdir(parents=True, exist_ok=True)
                _run(pg1_name, pg2_name, f"results/{i}", time_factor=args.time_factor)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--time_factor", type=int, default=1)
    subparsers = parser.add_subparsers()

    parser_all = subparsers.add_parser("all")
    parser_all.set_defaults(func=main_all)

    parser_run = subparsers.add_parser("run")
    parser_run.set_defaults(func=main_run)
    parser_run.add_argument("pg1")
    parser_run.add_argument("pg2")

    parser_run_1 = subparsers.add_parser("run-one")
    parser_run_1.set_defaults(func=main_run_one)
    parser_run_1.add_argument("pg")

    args = parser.parse_args()
    args.func(args)
