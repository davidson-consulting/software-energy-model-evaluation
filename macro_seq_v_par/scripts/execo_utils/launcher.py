from execo import *
from execo_g5k import *
import yaml
import logging
import sys
import os
import time
import json

images = {
    "ubuntu-22.04" : "http://cloud-images.ubuntu.com/releases/22.04/release-20230210/ubuntu-22.04-server-cloudimg-amd64.img"
}

oses = {
    "ubuntu-20.04" : "ubuntu20.04",
    "ubuntu-22.04" : "ubuntu22.04"
}

# ***********************************************
# This class is responsible to node connection, and VM creations
# It possesses nodes, and VMs connections
# ***********************************************
class ExecoClient :

    # *****************************
    # @params:
    #    - nodes: the list of host nodes (execo nodes)
    # @info: this constructor should only be called from self.fromG5K, or self.fromIps
    # *****************************
    def __init__ (self, nodes) :
        self._hnodes = nodes
        self._monitorCmd = None    
        self._ports = {}
        self._vmInfos = {}
        self._vmDef = {}
        self._vmConnect = {}
    
    # *****************************
    # Create an execo client from ips 
    # @params:
    #   - ips: the list of node ips
    #   - user: the user of those machines
    # *****************************
    @classmethod
    def fromIps (cls, ips = ["127.0.0.1"], user = "root", keyfile = os.path.expanduser ('~') + "/.ssh/id_rsa") :
        nodes = []
        for ip in ips :
            nodes = nodes + [Host (ip, user=user, keyfile=keyfile)]

        return cls (nodes)


    # *****************************
    # Configure the nodes to be able to run the VMs, and monitor
    # *****************************
    def configureNodes (self, withInstall = True, withDownload = True) :
        if (withInstall) : 
            self.launchAndWaitCmd (self._hnodes, "sudo apt-get update")
            self.launchAndWaitCmd (self._hnodes, "sudo apt-get install -y stress cgroup-tools apt-transport-https ca-certificates curl gnupg lsb-release")
            self.launchAndWaitCmd (self._hnodes, "sudo apt-get update")
            self.launchAndWaitCmd (self._hnodes, "sudo apt-get install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virtinst virt-manager nfs-common libguestfs-tools default-jre ruby dnsmasq-utils php-cli php-xml gnupg genisoimage")
            self.launchAndWaitCmd (self._hnodes, "mkdir -p test")
            self.uploadFiles (self._hnodes, ["../../libs/dio.deb"], "./test")
            self.launchAndWaitCmd (self._hnodes, "dpkg -i test/dio.deb")
            self.uploadFiles (self._hnodes, ["../../libs/anon.deb"], "./test")
            self.launchAndWaitCmd (self._hnodes, "dpkg -i test/anon.deb")
            self.uploadFiles (self._hnodes, ["../../libs/keys/"], "./test")

            
        if (withDownload) :
            self.launchAndWaitCmd (self._hnodes, "mkdir -p .qcow2")
            self.downloadImages (self._hnodes, images, ".qcow2")

    def configureVMs(self):
        vms = list(self._vmConnect.values())
        logger.info(f"LIST OF VM AT CONFIG TIME {vms}")

        self.uploadFiles (vms, ["../../libs/anon.deb"], "./")
        self.launchAndWaitCmd (vms, "sudo apt-get update")
        self.launchAndWaitCmd (vms, "sudo apt-get install -y stress apt-transport-https ca-certificates curl gnupg cgroup-tools lsb-release libpfm4")
        self.launchAndWaitCmd (vms, "sudo apt-get install -y ./anon.deb")
        self.launchAndWaitCmd (vms, "sudo cgcreate -g cpu:test.slice")
        self.launchAndWaitCmd (vms, "sudo cgcreate -g cpu:test.slice/test")

    # ================================================================================
    # ================================================================================
    # =========================           MONITOR            =========================
    # ================================================================================
    # ================================================================================


    # ***************************
    # Start the dio monitor service (to boot VMs)
    # ***************************
    def startDioMonitor (self) :
        self.launchCmd (self._hnodes, "sudo systemctl start dio-monitor")
        logger.info ("Dio monitor started on " + str (self._hnodes))

    # ***************************
    # Kill the running dio monitors on each nodes
    # ***************************
    def killDioMonitor (self):        
        self.launchCmd (self._hnodes, "sudo systemctl stop dio-monitor")
        logger.info ("Dio monitor killed on " + str (self._hnodes))

    # ***************************
    # Start the anon service on the hosts
    # ***************************
    def startAnon (self):
        self.launchCmd (self._hnodes, "sudo systemctl start anon_service.service")
        time.sleep (2)


    # ***************************
    # Kill the anon service on the hosts
    # ***************************
    def killAnon (self):
        self.launchCmd (self._hnodes, "sudo systemctl stop anon_service.service")


    def startAnonVM (self):
        vms = list(self._vmConnect.values())
        self.launchCmd (vms, "sudo systemctl start anon_service.service")
        time.sleep (2)
        logger.info ("anon service started on " + str (vms))

    # ***************************
    # Upload the configuration file of anon
    # @params:
    #     - config: the configuration of anon
    # ***************************
    def uploadAnonConfiguration (self, config):
        configFile = self.createAnonConfigFile (config)
        sliceConfig = self.createSliceConfigFile (config["slices"])
        with open ("/tmp/anon_sensor_config.toml", "w") as fp :
            fp.write (configFile)

        with open ("/tmp/anon_cgroup_config", "w") as fp:
            fp.write (sliceConfig)

        self.uploadFiles (self._hnodes, ["/tmp/anon_sensor_config.toml"], "/tmp/sensor_config.toml")
        self.uploadFiles (self._hnodes, ["/tmp/anon_cgroup_config"], "/tmp/cgroup_config")
        self.launchAndWaitCmd(self._hnodes, "sudo cp /tmp/sensor_config.toml /etc/anon/config.toml")
        self.launchAndWaitCmd(self._hnodes, "sudo cp /tmp/cgroup_config /etc/anon/cgroups")

        logger.info ("Uploaded anon config files")


    def uploadAnonConfigurationVM (self, config):
        configFile = self.createAnonConfigFile (config, withEnergy = False)
        sliceConfig = self.createSliceConfigFile (config ["slices"])
        with open ("/tmp/anon_sensor_config.toml", "w") as fp :
            fp.write (configFile)

        with open ("/tmp/anon_cgroup_config", "w") as fp:
            fp.write (sliceConfig)

        vms = list(self._vmConnect.values())
        self.uploadFiles (vms, ["/tmp/anon_sensor_config.toml"], "/tmp/sensor_config.toml")
        self.uploadFiles (vms, ["/tmp/anon_cgroup_config"], "/tmp/cgroup_config")
        self.launchAndWaitCmd(vms, "sudo cp /tmp/sensor_config.toml /etc/anon/config.toml")
        self.launchAndWaitCmd(vms, "sudo cp /tmp/cgroup_config /etc/anon/cgroups")

        logger.info ("Uploaded anon config files in VMs")


    # ***************************
    # @returns: the configuration for the sensor into a toml string
    # ***************************
    def createAnonConfigFile (self, config, withEnergy = True) :
        print (config)
        s = ""
        s = s + "[sensor]\n"
        s = s + "freq = " + str (config ["freq"] if ("freq" in config) else 1) + "\n"
        s = s + "log-lvl = \"info\"\n"
        s = s + "log-path = \"/etc/anon/service.log\"\n"
        s = s + 'core = "dumper"'
        s = s + "output-dir = \"/etc/anon/results\"\n"
        s = s + "delete-res = true\n"
        if ("perf-counters" in config):
            s = s + 'perf-counters = ' + str (config ["perf-counters"])
        else :
            s = s + '["PERF_COUNT_HW_CPU_CYCLES", "PERF_COUNT_HW_INSTRUCTIONS", "PERF_COUNT_HW_BRANCH_INSTRUCTIONS", "PERF_COUNT_HW_BRANCH_MISSES"]\n\n'
        s = s + "mount-tmp = true\n\n"

        if (withEnergy) :
            s = s + "[cpu]\n"
            s = s + "name = \"rapl\"\n\n"
            s = s + "[ram]\n"
            s = s + "name = \"rapl\""
            s = s + "\n\n"

        return s

    # ***************************
    # @returns: the content of the cgroups file
    # ***************************
    def createSliceConfigFile (self, slices) :
        res = ""
        for i in slices : 
            res = res + str (i) + "\n"
        return res

    # ***************************
    # download the csv files of the bpf sensors
    # ***************************
    def downloadAnonResultsVM (self, outputDir = "/tmp/"):
        def _downloadAnonResultsVM(self, node, outputDir, extra_name=""):
            final = {}
            path = outputDir + str (node.address) + (f"/{extra_name}" if extra_name != "" else "")
            if not(os.path.exists(path) and os.path.isdir(path)):
                os.mkdir (path)

            self.downloadFiles ([node], ["/etc/anon/results/cgroups.csv"], path)
            logger.info(f"SensorAnonVM results downloaded in directory {path}")
            final[str (node.address) + "_trace"] =  outputDir + str (node.address) + "/cgroups.csv"
            return final

        final = {}
        for name, node in self._vmConnect.items():
            logger.info(f"WILL DOWNLOAD FOR VM {node}")
            final = final | _downloadAnonResultsVM(self, node, outputDir, extra_name=name)

        return final


    # ***************************
    # download the csv files of anon top
    # ***************************
    def downloadAnonResults (self, outputDir = "/tmp/"):
        def _downloadAnonResults (self, node, outputDir) :
            final = {}
            path = outputDir + str (node.address)
            if not (os.path.exists (path) and os.path.isdir (path)):
                os.mkdir (path)

            self.downloadFiles ([node], ["/etc/anon/results/cgroups.csv"], path)
            self.downloadFiles ([node], ["/etc/anon/results/energy.csv"], path)
            logger.info (f"Anon results downloaded in directory {path}")
            final [str (node.address) + "_anon"] = outputDir + str (node.address)
            return final

        final = {}
        for node in self._hnodes :
            logger.info (f"Download anon result for {node}")
            final = final | _downloadAnonResults (self, node, outputDir)

        return final

    
    # ***************************
    # Kill the running services
    # ***************************
    def kill (self):
        self.killDioMonitor ()        
        
    # ================================================================================
    # ================================================================================
    # =========================         CLIENT UTILS         =========================
    # ================================================================================
    # ================================================================================

    # **********************************
    # Start a VM with a given configuration, does not wait vm start
    # @params:
    #    - vmInfo: the information about the VM in dico format
    #    - keyFile: the pub key (actual content of the key)
    #    - loadBalancer: the load balancer that chooses the node on which run the VM (None means always the first node)
    # @returns: the command used to create the VM
    # @example:
    # =======================
    # client = ExecoClient.fromG5K ()
    # client.configureNodes ()
    # client.startMonitor ()
    # 
    # pubkey = ".ssh/id_rsa.pub"
    # prvKey = ".ssh/id_rsa"
    # cmd = client.startVM ({"name" : "v0", "vcpus" : 4, "memory" : 4096, "disk" : 10000, "frequency" : 800}, pubKey, prvKey, loadBalancer = BestFit ())
    # 
    # =======================
    # **********************************
    def startVM (self, vmInfo, pubKey = "../../libs/keys/key.pub", loadBalancer = None):
        node = None
        if (loadBalancer == None):
            node = self._hnodes[0]
        else :
            node = loadBalancer.select (self._hnodes, self._vmInfos, self._vmDef, vmInfo)

        pubKeyContent = ""
        with open (pubKey, "r") as fp:
            pubKeyContent = fp.read ()[0:-1]
        
        configFile = self.createVMConfigFile (vmInfo, pubKeyContent)
        with open ("/tmp/{0}_config.toml".format(vmInfo["name"]), "w") as fp :
            fp.write (configFile)

        self.uploadFiles ([node], ["/tmp/{0}_config.toml".format (vmInfo["name"])], "./test") 
        cmd = self.launchCmd ([node], "dio-client --provision ./test/{0}_config.toml".format (vmInfo["name"]))
        self._vmInfos[vmInfo["name"]] = node
        self._vmDef [vmInfo["name"]] = vmInfo

        return cmd

        
    # **********************************
    # Open a port to connect to the VM via nat
    # @params:
    #    - vmInfo: the information about the VM
    # @returns: a VM host connected to the VM
    # **********************************
    def connectVM (self, vmInfo, prvKey = "../../libs/keys/key") :
        node = self._vmInfos [vmInfo["name"]]
        port = self.createUnusedPort (node)
        cmd = self.launchCmd ([node], "dio-client --nat " + str (vmInfo["name"]) + " --host {0} --guest 22".format (port))
        cmd.wait ()
        
        time.sleep (1)
        while True : 
            vm = Host (node.address, user="alice", keyfile=prvKey, port=port)
            cmd = self.launchCmd ([vm], "echo \"Hello\"", user="alice")
            status = cmd.wait ()
            if status.ok :
                self._vmConnect[vmInfo["name"]] = vm
                return vm
            else :
                time.sleep (1)
    
    # **********************************
    # Open a NAT port to access the VM from the external network
    # @params:
    #   - vmName: the name of the vm to access by NAT
    #   - port: the port redirection
    # @returns: the NAT port
    # **********************************
    def openVMPort (self, vmName, port, outPort = None) : 
        node = self._vmInfos[vmName]
        if (outPort == None) : 
            outPort = self.createUnusedPort (node)

        cmd = self.launchCmd ([node], "dio-client --nat " + str (vmName) + " --host {0} --guest {1}".format (outPort, port))
        cmd.wait ()
        return outPort
    
    # **********************************
    # Get an unused port on the node node
    # @params:
    #    - node: the node on which the port will be opened
    # **********************************
    def createUnusedPort (self, node):
        port = 3030
        if (node in self._ports):
            port = self._ports[node]
            self._ports[node] = port + 1
        else : 
            self._ports[node] = port + 1
        return port

    # **********************************
    # Kill all the running VMs
    # **********************************
    def killAllVMs (self) :
        for v in self._vmInfos :
            self.launchAndWaitCmd ([self._vmInfos[v]], "dio-client --kill " + str (v))
            self.launchAndWaitCmd ([self._vmInfos[v]], "virsh destroy " + str (v))
            self.launchAndWaitCmd ([self._vmInfos[v]], "virsh undefine " + str (v))


    # ************************
    # Bare metal access for bare metal tests
    # ************************
    def connectBare (self):
        return self._hnodes[0]
    
    # **********************************
    # Create a file containing the toml configuration of a VM
    # @params:
    #    - vmInfo: the dico containing the information about the VM
    #    - pubKey: the content of the pub key
    # @returns: the content of the configuration file
    # **********************************
    def createVMConfigFile (self, vmInfo, pubKey) :
        global oses
        s = "[vm]\n"
        s = s + "name = \"{0}\"\n".format (vmInfo ["name"])
        s = s + "image = \"/root/.qcow2/{0}.qcow2\"\n".format (vmInfo["image"])
        s = s + "os = \"{0}\"\n".format (oses[vmInfo["image"]])
        s = s + "user = \"alice\"\n"
        s = s + "ssh_key = \"{0}\"\n".format (pubKey)
        s = s + "vcpus = {0}\n".format (vmInfo["vcpus"])
        s = s + "memory = {0}\n".format (vmInfo["memory"])
        s = s + "disk = {0}\n".format (vmInfo["disk"])
        if ("freq" in vmInfo) :
            s = s + "freq = {0}\n".format (vmInfo["freq"])
        if ("pins" in vmInfo) :
            s = s + 'pins = "{0}"\n'.format (vmInfo["pins"])
        return s

    # ================================================================================
    # ================================================================================
    # =========================        COMMAND UTILS         =========================
    # ================================================================================
    # ================================================================================    

    # ************************************
    # Run a bash command on remote nodes, and waits its completion
    # @params:
    #   - nodes: the list of nodes
    #   - cmd: the command to run
    #   - user: the user that runs the command
    # ************************************
    def launchAndWaitCmd (self, nodes, cmd, user = "root") :
        conn_params = {'user': user}
        cmd_run = Remote (cmd, nodes, conn_params)
        logger.info ("Launch " + cmd + " on " + str (nodes) + " " + str (conn_params))
        cmd_run.start ()
        status = cmd_run.wait ()
        logger.info ("Done")
        
    # ************************************
    # Run a bash command on remote nodes, but do not wait its completion
    # @params:
    #   - nodes: the list of nodes
    #   - cmd: the command to run
    #   - user: the user that runs the command
    # ************************************
    def launchCmd (self, nodes, cmd, user = "root") :
        conn_params = {'user': user}
        cmd_run = Remote (cmd, nodes, conn_params)
        logger.info ("Launch " + cmd + " on " + str (nodes) + " " + str (conn_params))
        cmd_run.start ()
        return cmd_run

    # ************************************
    # Kill commands before their completion
    # @params:
    #    - cmds: the list of command to kill
    # ************************************
    def killCmds (self, cmds):
        for c in cmds:
            c.kill ()
    
    # ************************************
    # Wait the completion of commands (do not restart failing commands)
    # @params:
    #    - cmds: the list of command to wait
    # ************************************
    def waitCmds (self, cmds) :
        for c in cmds :
            c.wait ()    
    
    # ************************************
    # Wait the completion of commands, and restart them if they failed for some reason
    # @params:
    #    - cmds: the list of command to wait
    # ************************************
    def waitAndForceCmds (self, cmds) : 
        while True :
            restart = []
            for c in cmds :
                status = c.wait (timeout = get_seconds (0.1))
                if not status.ok :
                    logger.info ("Command failed, restarting : " +  str (c))
                    c.reset ()
                    c.start ()
                    restart = restart + [c]
                elif not status.finished_ok :
                    restart = restart + [c]
                else :
                    logger.info ("Command finished " + str (c))
            if restart != []:
                cmds = restart
            else :
                break

    # ************************************
    # Download image files on remote nodes
    # @params:
    #   - nodes: the list of nodes
    #   - images: the list of images to download (wget)
    #   - user: the user that will download the images
    # ************************************            
    def downloadImages (self, nodes, images, user = "root") :    
        for i in images :
            cmd = "wget " + images [i] + " -O .qcow2/" + i + ".qcow2"
            self.launchAndWaitCmd (nodes, cmd)

        logger.info ("Done")

    # ****************************
    # Upload files located on localhost to remote nodes
    # @params:
    #    - nodes: the list of nodes
    #    - files: the list of files to upload
    #    - directory: where to put the files
    #    - user: the user on the remote nodes
    # ****************************
    def uploadFiles (self, nodes, files, directory,  user = "root") :
        conn_params = {'user': user}
        cmd_run = Put (nodes, files, directory, connection_params=conn_params)
        logger.info ("Upload files on " + str (nodes) + ":" + str (files))
        cmd_run.run ()
        cmd_run.wait ()
        logger.info ("Done")


    # ****************************
    # Download files located on remote nodes to localhost
    # @params:
    #    - nodes: the list of nodes
    #    - files: the list of files to download
    #    - directory: where to put the files
    #    - user: the user on the remote nodes
    # ****************************
    def downloadFiles (self, nodes, files, directory, user = "root") :
        conn_params = {'user': user}
        cmd_run = Get (nodes, files, directory, connection_params=conn_params)
        logger.info (f"Download files on {nodes} {files}")
        cmd_run.run ()
        cmd_run.wait ()
        logger.info ("Done")        
