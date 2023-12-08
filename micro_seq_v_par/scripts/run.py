import time
import os
import subprocess
import pathlib
import shutil
import json
import argparse
import csv

PG = {
    'ackermann': int (16667 * 3),
    'float64': int (18182 * 3),
    'matrixprod': int (22222 * 3),
    'rand': int (16000 * 3),
    'int64': int (18182 * 3),
    'decimal64': int (16667 * 3),
    'jmp': int (18182 * 3),
    'queens': int (18182 * 3),
    'fibonacci': int (15384 * 3),
    'double': int (16667 * 3),
    'int64float': int (18182 * 3),
    'int64double': int (18182 * 3)
}

configAnon = """
[sensor]
freq = 1
log-lvl = "none"
log-path = "/etc/anon/service.log" # file where logs are written, empty for stdout
core = "dumper"
perf-counters = ["PERF_COUNT_HW_CPU_CYCLES", "PERF_COUNT_HW_INSTRUCTIONS", "PERF_COUNT_SW_CPU_CLOCK", "PERF_COUNT_HW_BRANCH_MISSES"]
output-dir = "/etc/anon/results"
mount-tmpfs = false

[cpu]
name = "rapl"
"""

cgroupAnon = """
custom.slice/*
anon.slice/*
"""

def read (filename):
    rows = {}
    with open (filename, 'r') as fp:
        reader = csv.reader (fp)
        head = next (reader)

        for row in reader:
            current = row
            for h in range (len (head)) :
                if not head [h] in rows :
                    rows [head[h]] = []
                rows [head[h]].append (current [h])

    return rows

def getInstant (ener, instant):
    for i in range (len (ener["timestamp"])):
        if (float (ener ["timestamp"][i]) == instant):
            return float (ener ["power"][i])
        elif float (ener ["timestamp"][i]) >= instant:
            return 0
    return 0

def getInstantList (eners, instant):
    result = 0
    for i in eners :
        result += getInstant (i, instant)
    return result

def read_powerapi_results (pgname, coreA, coreB):
    try:
        os.mkdir (pgname)
    except:
        pass
    
    rapl = read ("/tmp/sensor_output/sensor-rapl/PowerReport.csv")
    globl = read ("/tmp/sensor_output/sensor-global/PowerReport.csv")
    pg1 = [read (f"/tmp/sensor_output/sensor-/pg1_c{i}/PowerReport.csv") for i in range (coreA)]
    pg2 = [read (f"/tmp/sensor_output/sensor-/pg2_c{i + coreA}/PowerReport.csv") for i in range (coreB)]
    
    with open (pgname + "/powerapi.csv", "w") as out :
        out.write ("timestamp;RAPL;glob;PG1;PG2\n")
        for i in range (len (rapl ["timestamp"])):
            instant = float (rapl ["timestamp"][i])
            r = rapl ["power"][i]
            gl = getInstant (globl, instant)
            p1 = getInstantList (pg1, instant)
            p2 = getInstantList (pg2, instant)

            out.write (f"{instant};{r};{gl};{p1};{p2}\n")
            
def read_scaph_results(pids1, pids2, pgname):
    with open("/tmp/results.json", "r") as f:
        with open (pgname + "/scaphandre.csv", "w") as out:
            out.write ("FULL;PG1;PG2\n")
            results = json.load(f)
            for result in results:
                pg1 = 0
                pg2 = 0
                for consumer in result["consumers"]:
                    if str(consumer["pid"]) in pids1:
                        pg1 += consumer["consumption"] / 1000000
                    elif str(consumer["pid"]) in pids2:
                        pg2 += consumer["consumption"] / 1000000
                full = result ["host"]["consumption"] / 1000000
                out.write (str (full) + ";" + str (pg1) + ";" + str (pg2) + "\n")

def save_anon_result(pgname):
    try:
        os.mkdir (pgname)
    except:
        pass

    with open (pgname + "/cgroups.csv", "w") as fp:
        with open ("/etc/anon/results/cgroups.csv") as fr:
            fp.write (fr.read ())

    with open (pgname + "/energy.csv", "w") as fp:
        with open ("/etc/anon/results/energy.csv") as fr:
            fp.write (fr.read ())


def get_pids_in_cgroup(cgroup, i, nb):
    r = []
    for z in range (i, i + nb):
        with open(f"{cgroup}/c{z}/cgroup.procs", "r") as f:
            r = r + f.read().split("\n")[:-1]
    return r

def runEmpty ():
    try:
        os.mkdir ("result/")
    except:
        pass

    subprocess.Popen (["cgcreate", "-g", "cpu,memory:custom.slice/pg1"]).wait ()
    with open ("/etc/anon/config.toml", "w") as f:
        f.write (configAnon)

    with open ("/etc/anon/cgroups", "w") as f:
        f.write (cgroupAnon)

    scaphandre = subprocess.Popen(["scaphandre", "json", "--max-top-consumers", "15", "-t", "60", "-s", "1", "-f", "/tmp/results.json"])
    anon = subprocess.Popen(["anon_service"])
    time.sleep (40)
    scaphandre.kill()
    anon.kill ()
    save_anon_result ("result/empty")

    try :
        read_scaph_results ([], [], "result/empty")
    except Exception as e:
        print (e)
        pass
    

def runAloneCapped (start, cores, cap = 10):
    try:
        os.mkdir ("result/")
    except:
        pass

    subprocess.Popen (["cgcreate", "-g", "cpuset,cpu,memory:custom.slice/pg1"]).wait ()
    for i in range (cores):
        subprocess.Popen (["cgcreate", "-g", f"cpuset,cpu,memory:custom.slice/pg1/c{i}"]).wait ()
        subprocess.Popen (["/bin/bash", "set_cpu.sh", "pg1", str(i)]).wait ()
        subprocess.Popen (["/bin/bash", "cap.sh", str (i), str (cap * 1000)]).wait ()
        
    with open ("/etc/anon/config.toml", "w") as f:
        f.write (configAnon)

    with open ("/etc/anon/cgroups", "w") as f:
        f.write (cgroupAnon)

    for pg1 in PG:
        for it in range (start, cores + 1) :        
            
            anon = subprocess.Popen(["anon_service"])
            time.sleep (1)

            pg = []
            for i in range (it):
                pg.append (subprocess.Popen (["cgexec", "-g", f"cpu:custom.slice/pg1/c{i}", "stress-ng.exe", "-c", "1", "--cpu-method", pg1, "-t", "20"]))

            for p in pg :
                p.wait ()

            time.sleep (4)

            anon.kill ()
            save_anon_result ("result/" + pg1 + "-" + str (it))


    subprocess.Popen (["cgdelete", "-g", "cpu,memory:custom.slice/pg1"]).wait ()

    
def runAlone (start, cores):
    try:
        os.mkdir ("result/")
    except:
        pass

    subprocess.Popen (["cgcreate", "-g", "cpuset,cpu,memory:custom.slice/pg1"]).wait ()
    with open ("/etc/anon/config.toml", "w") as f:
        f.write (configAnon)

    with open ("/etc/anon/cgroups", "w") as f:
        f.write (cgroupAnon)

    for pg1 in PG:
        for it in range (start, cores + 1) :

            #scaphandre = subprocess.Popen(["scaphandre", "json", "--max-top-consumers", str (cores), "-t", "60", "-s", "1", "-f", "/tmp/results.json"])
            anon = subprocess.Popen(["anon_service"])
            time.sleep (1)

            pg = []
            for i in range (it):
                pg.append (subprocess.Popen (["cgexec", "-g", "cpu:custom.slice/pg1", "stress-ng.exe", "-c", "1", "--cpu-method", pg1, "-t", "20"]))

            time.sleep (1)
            # pids_pg1 = get_pids_in_cgroup("/sys/fs/cgroup/custom.slice/pg1")
            # print (pids_pg1)

            for p in pg :
                p.wait ()

            time.sleep (4)

            # scaphandre.kill()
            anon.kill ()
            save_anon_result ("result/" + pg1 + "-" + str (it))

            # try :
            #     read_scaph_results (pids_pg1, [], "result/" + pg1 + "-" + str (it))
            # except Exception as e:
            #     print (e)
            #     pass

    subprocess.Popen (["cgdelete", "-g", "cpuset,cpu,memory:custom.slice/pg1"]).wait ()


def runVersusPowerAPI (coreA, coreB, cap=100):
    for i in range (coreB):
        subprocess.Popen (["cgcreate", "-g", f"cpuset,cpu,perf_event:pg2_c{coreA + i}"]).wait ()
        subprocess.Popen (["/bin/bash", "set_cpu_v1.sh", "pg2", f"{coreA + i}"]).wait ()
    
    for i in range (coreA):
        subprocess.Popen (["cgcreate", "-g", f"cpuset,cpu,perf_event:pg1_c{i}"]).wait ()
        subprocess.Popen (["/bin/bash", "set_cpu_v1.sh", "pg1", f"{i}"]).wait ()
        if (cap < 100):
            subprocess.Popen (["/bin/bash", "cap_v1.sh", str (i), str (cap * 1000)]).wait ()

    
    for pg2 in PG :
        for pg1 in PG:
            print (pg1, " v ", pg2, " ", coreA, " v ", coreB)
            powerapi = subprocess.Popen(["bash", "launch.sh"])
            powerapi.wait ()
            time.sleep (4)

            pg = []
            for i in range (coreA):
                pg.append (subprocess.Popen (["cgexec", "-g", f"cpu,cpuset,perf_event:pg1_c{i}", "stress-ng.exe", "-c", "1", "--cpu-method", pg1, "-t", "30"]))

            for i in range (coreB):
                pg.append (subprocess.Popen (["cgexec", "-g", f"cpu,cpuset,perf_event:pg2_c{i + coreA}", "stress-ng.exe", "-c", "1", "--cpu-method", pg2, "-t", "30"]))

            for p in pg :
                p.wait ()

            time.sleep (10)
            powerapi = subprocess.Popen (["bash", "kill.sh"])
            powerapi.wait ()
            
            try :                
                read_powerapi_results ("result/" + pg1 + "-v-" + pg2 + "-" + str (coreA) + "_" + str (coreB), coreA, coreB)
            except Exception as e:
                print (e)
                pass


def runVersus (coreA, coreB, cap = 100):
    subprocess.Popen (["cgcreate", "-g", "cpuset,cpu,memory:custom.slice/pg1"]).wait ()
    subprocess.Popen (["cgcreate", "-g", "cpuset,cpu,memory:custom.slice/pg2"]).wait ()

    for i in range (coreB):
        subprocess.Popen (["cgcreate", "-g", f"cpuset,cpu,memory:custom.slice/pg2/c{coreA + i}"]).wait ()
        subprocess.Popen (["/bin/bash", "set_cpu.sh", "pg2", f"{coreA + i}"]).wait ()
    
    for i in range (coreA):
        subprocess.Popen (["cgcreate", "-g", f"cpuset,cpu,memory:custom.slice/pg1/c{i}"]).wait ()
        subprocess.Popen (["/bin/bash", "set_cpu.sh", "pg1", f"{i}"]).wait ()
        if (cap < 100):
            subprocess.Popen (["/bin/bash", "cap.sh", str (i), str (cap * 1000)]).wait ()
    
    with open ("/etc/anon/config.toml", "w") as f:
        f.write (configAnon)

    with open ("/etc/anon/cgroups", "w") as f:
        f.write (cgroupAnon)

    for pg2 in PG :
        for pg1 in PG:                
            print (pg1, " v ", pg2, " ", coreA, " v ", coreB)
            scaphandre = subprocess.Popen(["scaphandre", "json", "--max-top-consumers", str (coreA + coreB), "-t", "60", "-s", "1", "-f", "/tmp/results.json"])
            anon = subprocess.Popen(["anon_service"])
            time.sleep (1)

            pg = []
            for i in range (coreA):
                pg.append (subprocess.Popen (["cgexec", "-g", f"cpu:custom.slice/pg1/c{i}", "stress-ng.exe", "-c", "1", "--cpu-method", pg1, "-t", "30"]))

            for i in range (coreB):
                pg.append (subprocess.Popen (["cgexec", "-g", f"cpu:custom.slice/pg2/c{i + coreA}", "stress-ng.exe", "-c", "1", "--cpu-method", pg2, "-t", "30"]))

            time.sleep (1)
            pids_pg1 = get_pids_in_cgroup("/sys/fs/cgroup/custom.slice/pg1", 0, coreA)
            pids_pg2 = get_pids_in_cgroup("/sys/fs/cgroup/custom.slice/pg2", coreA, coreB)
            print (pids_pg1)
            print (pids_pg2)

            for p in pg :
                p.wait ()

            time.sleep (4)

            scaphandre.kill()
            anon.kill ()

            save_anon_result ("result/" + pg1 + "-v-" + pg2 + "-" + str (coreA) + "_" + str (coreB))

            try :
                read_scaph_results (pids_pg1, pids_pg2, "result/" + pg1 + "-v-" + pg2 + "-" + str (coreA) + "_" + str (coreB))
            except Exception as e:
                print (e)
                pass

    subprocess.Popen (["cgdelete", "-g", "cpuset,cpu,memory:custom.slice/pg1"]).wait ()
    subprocess.Popen (["cgdelete", "-g", "cpu,memory:custom.slice/pg2"]).wait ()

if __name__ == "__main__" :
    try:
        os.mkdir ("result/")
    except:
        pass
    
    # runEmpty ()
    # result = runAloneCapped (3, 6, cap=50)
    # runVersus (1, 3, cap = 50)
    # runVersus (2, 3, cap = 50)
    # runVersus (3, 3, cap = 50)
    # runVersus (3, 6, cap = 50)
    # runVersus (6, 6, cap = 50)
    
    # # result = runVersus (4, 4)

    runVersusPowerAPI (1, 3, cap=50)
    runVersusPowerAPI (2, 3, cap=50)
    runVersusPowerAPI (3, 3, cap=50)
    
    # # runVersusPowerAPI (1, 4)
    # # runVersusPowerAPI (1, 6)

    # runVersusPowerAPI (2, 2)
    # runVersusPowerAPI (2, 3)
    # runVersusPowerAPI (2, 4)
    # runVersusPowerAPI (2, 6)

    # runVersusPowerAPI (3, 3)
    # runVersusPowerAPI (3, 4)
    # runVersusPowerAPI (3, 6)

    # runVersusPowerAPI (4, 4)
    # runVersusPowerAPI (4, 6)

    # runVersusPowerAPI (6, 6)

