#!/usr/bin/env python3
#
#
import os
from utils import common
from utils import scaphandre
from utils import powerapi
from utils import custom
from matplotlib import pyplot as plt

if __name__ == "__main__":
    try :
        os.mkdir (".build")
    except Exception:
        pass

    # custom.analyseAlone ("big-intel", False)
    # custom.analyseAlone ("ptero", False)

    # custom.analyseAlone ("ptero", False)
    # custom.analyseAlone ("ptero-3Ghz", False)
    # custom.analyseAlone ("ptero-2Ghz", False)

    #
    # powerapi.plotSingleTraces ("big-intel", True, "matrixprod", 16, "int64", 16)
    # powerapi.plotSingleTraces ("big-intel", True, "int64", 16, "matrixprod", 16)

    # powerapi.analysePowerAPI ("ptero", False)
    # powerapi.analysePowerAPI ("ptero", True)
    # powerapi.analysePowerAPI ("big-intel", True)
    # powerapi.analysePowerAPI ("big-intel", False)
    #
    # custom.plotSingleTracesFile ("micro_no_HT/big-intel/result/queens-4/energy.csv")
    # custom.plotSingleTracesFile ("micro_no_HT/big-intel/result/queens-v-float64-4_4/energy.csv")
    # powerapi.plotSingleTraces ("big-intel", False, "matrixprod", 16, "float64", 16)
    #powerapi.plotSingleTraces ("big-intel", False, "float64", 16, "matrixprod", 16)

    #powerapi.analysePowerAPI ("ptero", False)
    #powerapi.plotSingleTraces ("big-intel", False, "int64", 16, "matrixprod", 16)
