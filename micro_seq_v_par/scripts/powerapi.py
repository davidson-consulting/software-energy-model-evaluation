import time
import os
import subprocess
import pathlib
import shutil

RES_DIR = "results"
REPEAT = 10

def export_results(directory):
    print(shutil.copytree("/tmp/sensor_output", f"{directory}/output"))
    shutil.rmtree("/tmp/sensor_output")
    pathlib.Path(f"/tmp/sensor_output").mkdir(exist_ok=True)
    subprocess.run(["sudo", "chmod", "777", "/tmp/sensor_output/"])



def run_in_parallel(pg1_name, pg1_nb_ops, pg2_name, pg2_nb_ops, cores):
    subprocess.Popen(["docker", "compose", "up", "-V", "-d", "mongo"])
    time.sleep(5)
    #subprocess.run(["bash", "-c", "docker compose exec mongo mongosh powerapi --eval 'db.sensor.drop()'"])
    subprocess.Popen(["docker", "compose", "up", "-V", "-d", "power-api-sensor"])
    time.sleep(2)

    processes = []

    for _ in range(cores):
        processes.append(subprocess.Popen(["cgexec", "-g", "perf_event:pg1", "stress-ng", "-c", "1", "--cpu-method", pg1_name, "--cpu-ops", str(pg1_nb_ops)]))
        processes.append(subprocess.Popen(["cgexec", "-g", "perf_event:pg2", "stress-ng", "-c", "1", "--cpu-method", pg2_name, "--cpu-ops", str(pg2_nb_ops)]))
     
    for process in processes:
        process.wait()

    subprocess.run(["docker", "compose", "stop", "power-api-sensor"])
    time.sleep(1)
    subprocess.run(["docker", "compose", "up", "-V", "power-api-formula"])
    subprocess.run(["docker", "compose", "down", "-v"])
    #time.sleep(5)
    #subprocess.run(["bash", "-c", "docker volume rm -f $(docker volume ls -q)"])

def run(pg_name, pg_nb_ops, cores):
    subprocess.run(["docker", "compose", "up", "-V", "-d", "mongo"])
    time.sleep(5)
    #subprocess.run(["bash", "-c", "docker compose exec mongo mongosh powerapi --eval 'db.sensor.drop()'"])
    subprocess.run(["docker", "compose", "up", "-V", "-d", "power-api-sensor"])
    time.sleep(2)

    processes = []
    for _ in range(cores):
        processes.append(subprocess.Popen(["cgexec", "-g", "perf_event:pg", "stress-ng",  "-c", "1", "--cpu-method", pg_name, "--cpu-ops", str(pg_nb_ops)]))
    
    for process in processes:
        process.wait()

    subprocess.run(["docker", "compose", "stop", "power-api-sensor"])
    time.sleep(1)
    subprocess.run(["docker", "compose", "up", "-V", "power-api-formula"])
    subprocess.run(["docker", "compose", "down", "-v"])
    #time.sleep(5)
    #subprocess.run(["bash", "-c", "docker volume rm -f $(docker volume ls -q)"])



if __name__ == "__main__":
    pg = {
            'ackermann': 50001, 
            'float64': 54546, 
            'matrixprod': 66666, 
            'callfunc': 81081081, 
            'int64': 54546, 
            'decimal64': 50001, 
            'jmp': 54546, 
            'queens': 54546, 
            'fibonacci': 46152, 
            'double': 50001, 
            'int64float': 54546, 
            'int64double': 54546
    }
   
    pathlib.Path("results").mkdir(exist_ok=True)

    for i in range(REPEAT):
        pg_names = list(pg.keys())
        for _ in range(len(pg_names)):
            pg1_name = pg_names.pop()
            for pg2_name in pg_names:
                pathlib.Path(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}").mkdir(exist_ok=True, parents=True)
                for c in [1, 3, 6]:
                    pathlib.Path(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}/{c}").mkdir(exist_ok=True, parents=True)
                    print(f"RUN {pg1_name} vs {pg2_name} FOR {c} CORES") 

                    pathlib.Path(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}/{c}/parallel").mkdir(exist_ok=True, parents=True)
                    run_in_parallel(pg1_name, pg[pg1_name], pg2_name, pg[pg2_name], c)
                    time.sleep(5)
                    export_results(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}/{c}/parallel")
     
                    pathlib.Path(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}/{c}/sequential/pg1").mkdir(parents=True, exist_ok=True)
                    pathlib.Path(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}/{c}/sequential/pg2").mkdir(parents=True, exist_ok=True)

                    run(pg1_name, pg[pg1_name], c)
                    time.sleep(5)
                    export_results(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}/{c}/sequential/pg1")

                    run(pg2_name, pg[pg2_name], c)
                    time.sleep(5)
                    export_results(f"{RES_DIR}/{i}/{pg1_name}_vs_{pg2_name}/{c}/sequential/pg2")
