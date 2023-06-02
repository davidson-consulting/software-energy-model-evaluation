import yaml

from execo import *
from execo_g5k import *
import logging
import sys
import os
import time
from os import walk
import os

# ***********************************************
# This class is responsible for executing a scenario and retrieving the csv results (using dumping_formula)
# ***********************************************
class Scenario :

    # ***********************************************
    # @params:
    #    - scenar: the scenario path
    #    - execoClient: the client (already configured) that will start the VMs
    # ***********************************************
    def __init__ (self, scenar, execoClient, mongoClient) :
        self._client = execoClient
        self._mongo = mongoClient
        self._scenar = scenar
        self._vms = {}
        self._bare = None
        self._toInstall = []
        self._toRun = {}
        self._running = {}
        self._output = {}
        self._vmNames = {}
        self._vmUsers = {}
        self._hostSensorConfig = {}
        self._vmSensorConfig = {}
        
        self._readScenario ()
    
    # ***********************************************
    # Start the VMs involved in the scenario
    # Wait until all the VMs are correctly configured
    # ***********************************************

    def setup(self, loadBalancer = None):
        time.sleep (2)
        
        cmds = {}        
        for v in self._toInstall :
            cmds[v[0]["name"]] = self._client.startVM (v[0], loadBalancer = loadBalancer)

        for v in self._toInstall :
            cmds [v[0]["name"]].wait ()
            vm = self._client.connectVM (v[0])
            self._vms [v[0]["name"]] = (vm, v[1])
            self._vmNames [vm] = v[0]["name"]
            self._vmUsers [vm] = "vagrant"

        if (self._bare != None) :
            vm = self._client.connectBare ()
            self._vmNames[vm] = "bare"
            self._vms["bare"] = (vm, self._bare)
            self._vmUsers [vm] = "root"


        self._client.configureVMCgroups ()
        self._client.configureVMs()
        self._client.uploadAnonConfigurationVM (self._vmSensorConfig)
                
    # ***********************************************
    # Setup all VMs, installing evaluation environment
    # ***********************************************
    def provision (self):       
        self._installTests ()
        self._configureRun ()
                
    # ***********************************************
    # Install the test on the VMs before running them
    # This is a part of the configuration
    # ***********************************************
    def _installTests (self) :
        cmds = []
        part2 = []

        # Install the tests inside the VMs
        for v in self._vms :  
            vm = self._vms[v][0]
            test = self._vms[v][1]            
            if (test["type"] == "phoronix") :
                cmds = cmds + [self._installPhoronix (vm)] # Just install phoronix, second step will install the proper test
                part2 = part2 + [self._vms[v]] # Phoronix needs a second step
            elif (test ["type"] == "custom") :
                cmds = cmds + [self._installCustomTest (vm, test)]
            elif (test ["type"] == "stress") :
                cmds = cmds + [self._installStressTest (vm)]
            else :
                logger.error ("Unknown test type : " + str (test["type"]) + " for VM " + str (v))

        self._client.waitAndForceCmds (cmds)

        # Some tests needs a second step to be properly installed (e.g. phoronix)
        cmds = []
        for p in part2 :
            cmds = cmds + [self._installPhoronixTest (p[0], p[1])]
            
        self._client.waitAndForceCmds (cmds)

        for p in part2 :
            self._finalizePhoronixTest (p [0])


    # ***********************************************
    # Configure the set that will be used to determine when to start and stop tests
    # ***********************************************
    def _configureRun (self) : 
        for v in self._vms :
            vm = self._vms[v][0]
            test = self._vms[v][1]            
            if (test["start"] in self._toRun) : 
                self._toRun [test["start"]] = self._toRun[test["start"]] + [(test, vm)]
            else :
                self._toRun[test["start"]] = [(test, vm)]

            if ("end" in test) : 
                if (test["end"] in self._toRun) : 
                    self._toRun [test["end"]] = self._toRun[test["end"]] + [(test, vm)]
                else :
                    self._toRun[test["end"]] = [(test, vm)]

        

    # ***********************************************
    # Install phoronix on the VM "vm"
    # @warning: does not wait the end of the install command
    # @params:
    #    - vm: the VM Host
    # @returns: the install command to wait
    # ***********************************************
    def _installPhoronix (self, vm) :
        # Phoronix is installed by a deb file
        self._client.uploadFiles ([vm], ["../../libs/phoronix/phoronix.deb"], ".", user = self._vmUsers[vm])

        # # There is a directory containing config information that must be updated
        self._client.launchAndWaitCmd ([vm], "mkdir -p /home/vagrant/.phoronix-test-suite", user=self._vmUsers[vm]);
        self._client.launchAndWaitCmd ([vm], "sudo mkdir -p /root/.phoronix-test-suite", user=self._vmUsers[vm]);

        # put the config file in that directory
        self._client.uploadFiles ([vm], ["../../libs/phoronix/user-config.xml"], ".phoronix-test-suite/", user = self._vmUsers[vm])
        self._client.launchAndWaitCmd ([vm], "sudo cp /home/vagrant/.phoronix-test-suite/user-config.xml /root/.phoronix-test-suite/", user=self._vmUsers[vm]);
        self._client.launchAndWaitCmd ([vm], "sudo cp /home/vagrant/.phoronix-test-suite/user-config.xml /etc/phoronix-test-suite.xml", user=self._vmUsers[vm]);

        # Install the dependency of phoronix, and then phoronix, and configure it
        cmd = self._client.launchCmd ([vm], 'sudo apt update ; sudo apt install -y php-cli php-xml openjdk-11-jdk mesa-utils vulkan-tools apt-file unzip ; sudo apt --fix-broken install -y ; sudo dpkg -i phoronix.deb ; echo -e "y\\nn" | sudo phoronix-test-suite ; echo -e "y\\nn" | phoronix-test-suite', user=self._vmUsers [vm])
        
        return cmd

    # ***********************************************
    # Install the phoronix test "test" on the VM "vm"
    # @assume: phoronix is installed and configured on the VM
    # @warning: does not wait the end of the installation command
    # @params:
    #    - vm: the VM host
    #    - test: the dictionnary containing the name of the test to execute (e.g. {"name" : "compress-7zip"})
    # @returns: the install command to wait
    # ***********************************************
    def _installPhoronixTest (self, vm, test) :
        # install the test
        return self._client.launchCmd ([vm], "sudo phoronix-test-suite install " + str (test["name"]) + ' ; echo -e "n\\ny" | sudo phoronix-test-suite batch-setup')        


    def _finalizePhoronixTest (self, vm):
        self._client.uploadFiles ([vm], ["../../libs/phoronix/user-config-no-conn.xml"], ".", user = self._vmUsers [vm])
        self._client.launchAndWaitCmd ([vm], "sudo cp user-config-no-conn.xml /home/vagrant/.phoronix-test-suite/user-config.xml", user=self._vmUsers[vm])
        self._client.launchAndWaitCmd ([vm], "sudo cp user-config-no-conn.xml /root/.phoronix-test-suite/user-config.xml", user = self._vmUsers[vm])
        self._client.launchAndWaitCmd ([vm], "sudo cp user-config-no-conn.xml /etc/phoronix-test-suite.xml", user = self._vmUsers[vm])
        self._client.launchAndWaitCmd ([vm], "sudo phoronix-test-suite make-download-cache", user = self._vmUsers[vm])


    # ***********************************************
    # Install a custom test in the VM
    # @warning: does not wait the end of the install command
    # @params:
    #    - vm: the VM Host
    #    - test: the dictionnary containing the name of the custom test to install
    # @returns: the install command to wait
    # ***********************************************
    def _installCustomTest (self, vm, test) :
        files = {}
        rootPath = "../utils/" + str (test["name"]);
        for (d, d2, filenames) in walk (rootPath) : # Create a dictionnary containing the tree definition of the directory containing the test
            p = os.path.relpath (d, rootPath)
            fis = []
            for f in filenames :
                fis = fis + [str (d) + "/" + f]
            files[p] = fis

        rootPath = test["name"]
        for p in files : # Upload all the files of the test
            self._client.launchAndWaitCmd ([vm], "mkdir -p " + rootPath + "/" + p, user = self._vmUsers[vm])
            self._client.uploadFiles ([vm], files[p], rootPath + "/" + p, user = self._vmUsers[vm])

        # Some test have dependencies, so the install script is there to install them
        return self._client.launchCmd ([vm], "cd " + rootPath + "; ./install.sh", user = self._vmUsers[vm])    

    # ***********************************************
    # Install the stress test in the VM
    # @warning: does not wait the end of the install command
    # @params:
    #    - vm: the VM Host
    # @returns: the install command to wait
    # ***********************************************
    def _installStressTest (self, vm):
        print (vm)
        return self._client.launchCmd ([vm], "sudo apt update ; sudo apt install -y stress", user=self._vmUsers[vm])
    
    # ***********************************************
    # Start the scenario (launch the benchmark at the correct moment)
    # Wait until the scenario is finished
    # Retreive the log files of the monitors
    # ***********************************************
    def run (self):
        self._client.startPowerapi ()
        self._client.startAnonVM ()

        instants = list (self._toRun.keys ())
        instants = sorted (instants)

        logger.info ("Starting benchmark")

        print (instants)
        for i in range (len (instants)) :
            logger.info ("Running test at instant : " + str (instants[i]))
            self._runTests (instants [i], self._toRun [instants [i]])
            if (i != len (instants) - 1) :
                toSleep = instants [i + 1] - instants [i]
                logger.info ("Sleeping : " + str (toSleep))
                time.sleep (toSleep)

        # Wait the tests that are not killed 
        for t in self._running:
            self._running [t].wait ()
            self._output [self._vmNames[t]] = self._running[t].processes[0].stdout
            
        time.sleep (30)
        logger.info ("Benchmark finished")        
    
    # ***********************************************
    # Run or end the test in "tests"
    # @info: populate the set "self._running"
    # @params:
    #     - instant: the current instant of the test running
    #     - tests: the tests to run or kill    
    # ***********************************************    
    def _runTests (self, instant, tests) :
        for t in tests :
            if (instant == t[0]["start"]) :
                self._startTest (t[1], t[0])
            else :
                if ("end" in t[0]) : 
                    if (instant == t[0]["end"]) :
                        self._killTest (t[1])

    # ***********************************************
    # Start the test "test" on the vm "vm"
    # @info: populate the set "self._running"
    # @params:
    #    - vm: the vm Host
    #    - test: the test to launch
    # ***********************************************
    def _startTest (self, vm, test):
        if (test["type"] == "phoronix") :
            nbRun = test["nb-run"]
            self._running [vm] = self._client.launchCmd ([vm], 'sudo FORCE_TIMES_TO_RUN=' + str (nbRun) + ' cgexec -g cpu:test.slice/test phoronix-test-suite batch-run ' + test["name"], user=self._vmUsers[vm])
        elif (test["type"] == "stress") :
            self._running [vm] = self._client.launchCmd ([vm], "sudo cgexec -g cpu:test.slice/test stress -c " + str (test["nb-cpus"]), user=self._vmUsers[vm])
        else :
            rootPath = test["name"]
            self._running[vm] = self._client.launchCmd ([vm], "cd " + rootPath + " ; ./launch.sh " + test["params"])
            
    # ***********************************************
    # Kill the test that is currently running in the VM "vm"
    # @info: update the set "self._running"
    # @params:
    #    - vm: the vm Host
    # ***********************************************    
    def _killTest (self, vm) :
        if (vm in self._running) :
            logger.info ("Ending the test on " + str (vm))
            self._client.killCmds ([self._running [vm]])
            self._output[self._vmNames[vm]] = self._running[vm].processes[0].stdout


    # ***********************************************
    # Store the result of the scenario in the mongodb database
    # ***********************************************
    def store (self):
        self._client.killPowerapi ()
        logs = self._client.downloadPowerapiResults ()
        logs = logs | self._client.downloadAnonResultsVM ()

        self._client.killAllVMs ()

        resultPage = {}
        #resultPage ["monitors"] = self._readMonitorLogs (logs)
        resultPage ["vms"] = self._output
        placement = self._client._vmInfos;
        resultPage ["placement"] = {name : placement[name].address for name in placement}
        
        # with open (self._scenar, 'r') as fp :
        #     content = yaml.load (fp, Loader=yaml.FullLoader)
        #     resultPage ["scenario"] = content
        #     with open (self._scenar + ".report.yaml", "w") as fp2:
        #         fp2.write (yaml.dump (resultPage))
                
        #     self._mongo.insertResult (s, resultPage)
                    
    # ***********************************************
    # Read the monitor logs
    # @params:
    #    - logs: the list of log files ({node_address : path_to_file})
    # @returns: {node_address : file_content}
    # ***********************************************
    def _readMonitorLogs (self, logs):
        result = {}
        for i in logs :
            with open (logs[i], "r") as fp : 
                result [i] = fp.read ()
        return result

    # ***********************************************
    # Read the scenario file
    # ***********************************************
    def _readScenario (self) :
        with open (self._scenar, 'r') as fp :
            print (fp)
            content = yaml.load (fp, Loader=yaml.FullLoader)
            if ("vms" in content) : 
                for vi in content["vms"] :
                    for j in range (int (vi["instances"])) :
                        vm = {"name" : vi["name"] + str (j),
                              "image" : vi["image"],
                              "vcpus" : int (vi["vcpus"]),
                              "memory" : int (vi["memory"]),
                              "disk" : int (vi["disk"])}
                        if ("freq" in vi) :
                            vm ["freq"] = int (vi["freq"])
                        if ("pins" in vi):
                            vm ["pins"] = vi["pins"]
                        bench = vi["test"]
                        self._toInstall = self._toInstall + [(vm, bench)]
            if "bare" in content : 
                self._bare = content["bare"]["test"]

            self._vmSensorConfig = content ["vm-sensor-config"]
            self._hostSensorConfig = content ["host-sensor-config"]
