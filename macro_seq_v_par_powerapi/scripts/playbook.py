#!/usr/bin/env python3

import os
from mongo_utils import database
from execo_utils import launcher
from execo_utils import scenario
from execo import *
from execo_g5k import *
import logging
import yaml
import time
import argparse
import subprocess
import shutil
from distutils.dir_util import copy_tree

def parseArguments ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ("playbook", help="the playbook file")
    parser.add_argument ("out", help="output directory")
    parser.add_argument ("ip", help="the ip of the machine to use")

    return parser.parse_args ()

# Run a scenario  and store the result in the database
def main (args) :
    ran = {}
    with open (args.playbook, 'r') as fp :
        content = yaml.load (fp, Loader=yaml.FullLoader)
        for test in content ["tests"]:

            client = launcher.ExecoClient.fromIps (ips = [args.ip], user="root")
            client.configureNodes (withInstall = True, withDownload = False)

            path = os.path.join (os.path.dirname (args.playbook), test)
            print ("Running test : ", path)

            name = os.path.splitext (test)[0]
            if (name in ran) :
                ran [name] += 1
            else :
                ran [name] = 1

            res_dir = os.path.join (args.out, os.path.splitext (test)[0] + "/" + str (ran [name]))
            print (res_dir)
            try :
                os.makedirs (res_dir)
            except :
                pass

            try :
                shutil.rmtree (os.path.join ("/tmp/", args.ip))
            except:
                pass

            scenar = scenario.Scenario (path, client, database.DatabaseClient ())
            scenar.setup (loadBalancer = None)
            scenar.provision()
            scenar.run ()
            scenar.store ()

            copy_tree(os.path.join ("/tmp/", args.ip), res_dir)

            client.kill ()
            sleep (5)

if __name__ == "__main__" :
    main (parseArguments ())
