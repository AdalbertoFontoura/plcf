""" PLC Factory: Global variables """
############### USING GLOBAL VARIABLES IS HIGLY DEPRECATED !
__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"

import datetime

# the command line that is used to run this instance
cmdline = None

# plcfactory branch
branch = None

# plcfactory commit id
commit_id = None

# plfactory git url
origin = None

# raw timestamp
raw_timestamp = datetime.datetime.now()

# String timestamp for names of output files
timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

# the CCDB backend
ccdb = None

# the root installation slot
root_installation_slot = 'TBD:Ctrl-PLC-001'

# the name of the E3 module
e3_modulename = 'tbd_ctrl_plc_001'

# the name of the E3 snippet
e3_snippet = 'tbd_ctrl_plc_001'

# the modversion of the PLC module/IOC (can remain None)
modversion = None

# the default modversion of the PLC module/IOC
default_modversion = None
