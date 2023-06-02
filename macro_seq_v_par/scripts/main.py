#!/usr/bin/env python3


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

def parseArguments ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ("scenario", help="the scenario file")
    parser.add_argument ("ip", help="the ip of the machine to use")
    
    return parser.parse_args ()

# Run a scenario  and store the result in the database
def main (args) :
    client = launcher.ExecoClient.fromIps (ips = [args.ip], user="root")
    client.configureNodes (withInstall = True, withDownload = False)

    scenar = scenario.Scenario (args.scenario, client, database.DatabaseClient ())
    scenar.setup (loadBalancer = None)
    scenar.provision()
    scenar.run ()
    scenar.store ()

    client.kill ()

    
if __name__ == "__main__" :
    main (parseArguments ())
