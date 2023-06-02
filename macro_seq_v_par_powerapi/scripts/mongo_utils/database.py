from pymongo import MongoClient
from datetime import datetime
import pymongo
import hashlib
import yaml

# *************************************
# Class used to store results, and retreive old results
# *************************************
class DatabaseClient :

    # *************************************
    # Connect to the mongo db database
    # @params:
    #    - username: the name of the user (can be empty)
    #    - password: the password of the user (not empty if user is not empty)
    #    - addr: the address of the mongo database
    # *************************************
    def __init__ (self, username = "", password = "", addr = "localhost") :
        if (username != "") :            
            self._connection_string = "mongodb://{0}:{1}@{2}".format (username, password, addr)
        else :
            self._connection_string = "mongodb://{0}".format(addr)
        
        self._client = MongoClient (self._connection_string)
        self._base = self._client["dio-monitor"]

    # ****************************************
    # Insert a line of result in the tests database
    # 
    # @params:
    #   - scenario: the scenario in yaml format (used to create a uniq identifier, where equivalent scenarios should have the same identifier)
    #   - results: the results of the execution of the scenario, in string format
    #
    #******************************************
    def insertResult (self, scenario, results) :
        collection = self._base["tests"]
        
        m = hashlib.md5 ()
        s_scenar = yaml.dump (scenario)
        m.update (s_scenar.encode ())
        _id = m.hexdigest ()

        old_results = collection.find ({"_id" : _id})
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S.%f")
        values = [{"timestamp" : current_time, "data" : results}]

        replace = False
        for oitem in old_results :
            values = oitem["values"] + values
            replace = True

        item = {
            "_id" : _id,
            "values" : values
        }

        if (replace) :            
            collection.replace_one ({"_id" : _id}, item)
        else :
            collection.insert_one (item)
    
        
    # ****************************************
    # Get the list of results associated to a scenario
    # @params:
    #    - scenario: the scenario to search in yamkl format
    # @returns: the list of results, i.e. list of string, that can be parsed to json
    # ****************************************
    def getResult (self, scenario) :
        collection = self._base["tests"]
        m = hashlib.md5 ()
        s_scenar = yaml.dump (scenario)
        m.update (s_scenar.encode ())
        _id = m.hexdigest ()

        old_results = collection.find ({"_id" : _id})
        for oitem in old_results : # for loop, but there is 1 or 0 element
            return oitem["values"]

        return []


