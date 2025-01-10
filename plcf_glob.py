""" PLC Factory: Global variables """

__author__     = "Gregor Ulm"
__copyright__  = "Copyright 2016, European Spallation Source, Lund"
__license__    = "GPLv3"

# the command line that is used to run this instance
cmdline = None

# plcfactory branch
branch = None

# plcfactory commit id
commit_id = None

# plfactory git url
origin = None

# raw timestamp
raw_timestamp = None

# String timestamp for names of output files
timestamp = None

# the CCDB backend
ccdb = None

# the root installation slot
root_installation_slot = None

# the name of the E3 module
e3_modulename = None

# the name of the E3 snippet
e3_snippet = None

# the modversion of the PLC module/IOC (can remain None)
modversion = None

# the default modversion of the PLC module/IOC
default_modversion = None
