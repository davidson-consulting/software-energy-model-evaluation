import time
import os
import subprocess
import pathlib
import shutil
import json 

REPEAT = 10

def get_pids_in_cgroup(cgroup):
    with open(f"{cgroup}/cgroup.procs", "r") as f:
        return f.read().split("\n")[:-1]

def export_results(pids, file):
    print("exporting results for pids : ", pids)
    power = 0
    with open("/tmp/results.json", "r") as f:
        results = json.load(f)
        for result in results:
            for consumer in result["consumers"]:
                if str(consumer["pid"]) in pids:
                    power += consumer["consumption"]

    with open(file, "w+") as f:
        f.write(str(power))

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
    time.sleep(1)

    processes = []
    for _ in range(cores):
        processes.append(subprocess.Popen(["cgexec", "-g", "cpu:/pg1", "stress-ng",  "-c", "1", "--cpu-method", pg_name, "--cpu-ops", str(pg_nb_ops)]))

    time.sleep(1)

    pids_pg1 = get_pids_in_cgroup("/sys/fs/cgroup/pg1")
    
    for process in processes:
        process.wait()
   
    time.sleep(1)
    scaphandre.kill()

    return pids_pg1

if __name__ == "__main__":
    pg = {
            'ackermann': 16667, 
            'float64': 18182, 
            'matrixprod': 22222, 
            'callfunc': 27027027, 
            'int64': 18182, 
            'decimal64': 16667, 
            'jmp': 18182, 
            'queens': 18182, 
            'fibonacci': 15384, 
            'double': 16667, 
            'int64float': 18182, 
            'int64double': 18182
    }
  
    subprocess.run(["cgcreate", "-g", "cpu:/pg1"])
    subprocess.run(["cgcreate", "-g", "cpu:/pg2"])

    pathlib.Path("results").mkdir(exist_ok=True)

    for i in range(1, REPEAT):
        pg_names = list(pg.keys())
        for _ in range(len(pg_names)):
            pg1_name = pg_names.pop()
            for pg2_name in pg_names:
                pathlib.Path(f"results/{i}/{pg1_name}_vs_{pg2_name}").mkdir(parents=True, exist_ok=True)
                for c in [1, 3, 6]:
                    pathlib.Path(f"results/{i}/{pg1_name}_vs_{pg2_name}/{c}").mkdir(parents=True, exist_ok=True)
                    print(f"RUN {pg1_name} vs {pg2_name} FOR {c} CORES") 

                    xp_ok = False

                    pathlib.Path(f"results/{i}/{pg1_name}_vs_{pg2_name}/{c}/parallel").mkdir(parents=True, exist_ok=True)
                    
                    while not xp_ok:
                        try:
                            (pids_pg1, pids_pg2) = run_in_parallel(pg1_name, pg[pg1_name], pg2_name, pg[pg2_name], c)
                            export_results(pids_pg1, f"results/{i}/{pg1_name}_vs_{pg2_name}/{c}/parallel/pg1")
                            export_results(pids_pg2, f"results/{i}/{pg1_name}_vs_{pg2_name}/{c}/parallel/pg2")
                            xp_ok = True
                        except:
                            continue
     
                    pathlib.Path(f"results/{i}/{pg1_name}_vs_{pg2_name}/{c}/sequential").mkdir(parents=True, exist_ok=True)

                    xp_ok = False

                    while not xp_ok:
                        try:
                            pids = run(pg1_name, pg[pg1_name], c)
                            export_results(pids, f"results/{i}/{pg1_name}_vs_{pg2_name}/{c}/sequential/pg1")
                            xp_ok = True
                        except:
                            continue
                    
                    xp_ok = False

                    while not xp_ok:
                        try:
                            pids = run(pg2_name, pg[pg2_name], c)
                            export_results(pids, f"results/{i}/{pg1_name}_vs_{pg2_name}/{c}/sequential/pg2")
                            xp_ok = True
                        except:
                            continue
