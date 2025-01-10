from __future__ import print_function
from __future__ import absolute_import

""" SiemensDiagnostics : Entry point """

__author__     = "Miklos Boros"
__copyright__  = "Copyright 2017-2019, European Spallation Source, Lund"
__credits__    = [ "Krisztian Loki",
                   "Miklos Boros",
                   "Francois Bellorini"
                ]
__license__    = "GPLv3"
__maintainer__ = "Miklos Boros"
__email__      = "miklos.boros@esss.se; borosmiklos@gmail.com"
__status__     = "Production"
__env__        = "Python version 2.7"

# Python libraries
import argparse
import os
import sys

_NoExternal      = "ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False';"
_ExternalRead    = "ExternalAccessible := 'True'; ExternalVisible := 'False'; ExternalWritable := 'False';"
NoExternal       = "{ " + _NoExternal + " }"
ExternalRead     = "{ " + _ExternalRead + " }"



class Diagnostics(object):
    DEV_STATE_OK           =  1
    DEV_STATE_FAULT        =  2
    DEV_STATE_LOST_CON     =  3
    DEV_STATE_DISABLED     =  4
    DEV_STATE_WAS_FAULT    = 12
    DEV_STATE_WAS_LOST     = 13
    DEV_STATE_WAS_DISABLED = 14
    LAST_DEVICE            = -1
    MAX_IO_SYSTEM          =  5


    def __init__(self, MAX_IO_DEVICES = 1, MAX_LOCAL_MODULES = 30, MAX_MODULES_IN_IO_DEVICE = 30, Skip_Startup_OB = False):
        self._MAX_IO_DEVICES           = MAX_IO_DEVICES
        self._MAX_LOCAL_MODULES        = MAX_LOCAL_MODULES
        self._MAX_MODULES_IN_IO_DEVICE = MAX_MODULES_IN_IO_DEVICE
        self._Skip_Startup_OB          = Skip_Startup_OB


    def __DiagnosticsData(self, TIAVersion, ExternalSourceFile):
        #DiagnosticsData global DB
        ExternalSourceFile.append("TYPE \"typeModul\"");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   STRUCT");
        ExternalSourceFile.append("      slotLaddr : HW_IO;   // Hardware ID of  module");
        ExternalSourceFile.append("      slotErrorState : Bool;   // error state of module");
        ExternalSourceFile.append("   END_STRUCT;");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_TYPE");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("TYPE \"typeDevice\"");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   STRUCT");
        ExternalSourceFile.append("      laddr : HW_DEVICE;   // Logical address of a device or slave (system constant in HW configuration)");
        ExternalSourceFile.append("      \"name\" : String[50];   // Device name");
        ExternalSourceFile.append("      errorState : USInt;   // Status of the device 1=ok!, 2=faulty, 3=lost connection, 4=disabled, 12= was faulty, 13=was lost, 14=was disabled");
        ExternalSourceFile.append("      error : Bool;   // Signalizes an error in the device/slave");
        ExternalSourceFile.append("      nextDevice : Int;   // device number of next device");
        ExternalSourceFile.append("      actualConfiguredModules : Int;   // Actual number of configured modules in the device");
        ExternalSourceFile.append("      slot : Array[0.."+str(self._MAX_MODULES_IN_IO_DEVICE)+"] of \"typeModul\";   // slot informations");
        ExternalSourceFile.append("   END_STRUCT;");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_TYPE");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("TYPE \"typeIoSystem\"");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   STRUCT");
        ExternalSourceFile.append("      ioSystemId : UInt;   // ID of  IO System");
        ExternalSourceFile.append("      ioSystemError : Bool;   // TRUE: if an error is occured in the assigned IO System");
        ExternalSourceFile.append("      firstDevice : Int := 0;   // device number (index) of first device in IO System");
        ExternalSourceFile.append("      lastDevice : Int := 0;   // device number (index) of last device IO System");
        ExternalSourceFile.append("      actualConfiguredDevices : Int := 0;   // Actual number of configured devices in the IO System");
        ExternalSourceFile.append("      device : Array[1.."+str(self._MAX_IO_DEVICES)+"] of \"typeDevice\";   // List of all devices in the IO System");
        ExternalSourceFile.append("   END_STRUCT;");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_TYPE");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("TYPE \"typePlc\"");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   STRUCT");
        ExternalSourceFile.append("      actualConfiguredCentralModules : Int;   // Actual number of configured local modules");
        ExternalSourceFile.append("      errorState : Bool;   // Status of the device 1=ok!, 2=faulty, 3=lost connection, 4=disabled, 12= was faulty, 13=was lost, 14=was disabled");
        ExternalSourceFile.append("      slot : Array[1.."+str(self._MAX_LOCAL_MODULES)+"] of \"typeModul\";   // slot informations");
        ExternalSourceFile.append("   END_STRUCT;");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_TYPE");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("DATA_BLOCK \"DiagnosticsData\"");
        ExternalSourceFile.append("TITLE = Diagosis data DB");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("AUTHOR : SIEMENS");
        ExternalSourceFile.append("FAMILY : Diagnose");
        ExternalSourceFile.append("NAME : '10'");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("NON_RETAIN");
        ExternalSourceFile.append("//The global data block contains the data structure of the IO system, the control, the devices with the modules and an error buffer.");
        ExternalSourceFile.append("   VAR ");
        ExternalSourceFile.append("      plc " + ExternalRead + " : \"typePlc\";   // diagnosis information PLC");
        ExternalSourceFile.append("      ioSystem " + ExternalRead + " : Array[1.."+str(self.MAX_IO_SYSTEM)+"] of \"typeIoSystem\";   // diagnosis information IO systems");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_DATA_BLOCK");
        ExternalSourceFile.append("");


    def __DiagStartupIoSystem(self, TIAVersion, ExternalSourceFile):
        #DiagStartupIoSystem FB
        ExternalSourceFile.append("FUNCTION_BLOCK \"DiagStartupIoSystem\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   VAR_INPUT DB_SPECIFIC");
        ExternalSourceFile.append("      ioSystemHwId " + ExternalRead + " : HW_IOSYSTEM;   // This ID is representing the IO System (PN or DP), find the ID in the system constants");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_OUTPUT ");
        ExternalSourceFile.append("      status " + ExternalRead + " : Int;   // The return value of system function, where the last error occured");
        ExternalSourceFile.append("      instructionError " + ExternalRead + " : Int;   // Indicates in which system function the error occured: 1= DeviceStates PN , 2=GetName PN, 3=ModuleStates PN,  4=DeviceStates DP, 5= GetName DP. 6= ModuleStates DP");
        ExternalSourceFile.append("      errorIndex " + ExternalRead + " : Int;   // The last index of the respective loop, if an error occures");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_IN_OUT ");
        ExternalSourceFile.append("      ioSystem : \"typeIoSystem\";   // The diagnostics structure for one IO System");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR ");
        ExternalSourceFile.append("      statActualConfiguredDevices " + ExternalRead + " : Int := 0;   // Actual number of devices in the PN IO System");
        ExternalSourceFile.append("      statGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'; " + _ExternalRead + "} : GEOADDR;   // Slot information");
        ExternalSourceFile.append("      statGeoLaddr " + NoExternal + " : HW_ANY;   // GEO2LOG hardware identifier");
        ExternalSourceFile.append("      statConfiguredDevices " + ExternalRead + " : Array[0..1023] of Bool;   // Temporary storage of the return of \"DeviceStates\", to combine the states of the devices with numbers and names");
        ExternalSourceFile.append("      statExistingDevices " + ExternalRead + " : Array[0..1023] of Bool;   // Temporary storage of the return of \"DeviceStates\", to combine the states of the devices with numbers and names");
        ExternalSourceFile.append("      statFaultyDevices " + ExternalRead + " : Array[0..1023] of Bool;   // Temporary storage of the return of \"DeviceStates\", to combine the states of the divices with numbers and names");
        ExternalSourceFile.append("      statDisabledDevices " + ExternalRead + " : Array[0..1023] of Bool;   // Storage of the status of all devices in the PN IO System --> State: Disabled");
        ExternalSourceFile.append("      statProblemDevices " + ExternalRead + " : Array[0..1023] of Bool;   // Storage of the status of all devices in the PN IO System --> State: Problem");
        ExternalSourceFile.append("      statDeviceModuleStates " + ExternalRead + " : Array[0..127] of Bool;   // Storage of the status of all modules in the PN Devices --> State: Problem");
        ExternalSourceFile.append("      instGetNameDevices {OriginalPartName := 'FB_806_S71500'; LibVersion := '1.3'; " + _ExternalRead + "} : Get_Name;   // Instance of system function \"GetName\"");
        ExternalSourceFile.append("      statInitString " + ExternalRead + " : String;   // Used to initialize the temporary string to convert into STRING[50]");
        ExternalSourceFile.append("      statFirstDevice " + ExternalRead + " : UInt;   // Station number of the first device of the list");
        ExternalSourceFile.append("      statFirstDeviceFlag " + NoExternal + " : Bool := TRUE;   // Help tag for the first device in the linked list");
        ExternalSourceFile.append("      statLastDevice " + ExternalRead + " : UInt;   // Station number of the last device of the list");
        ExternalSourceFile.append("      statLinkedListPointer " + ExternalRead + " : Int;   // The actual index pointer of the linked list (Actual pointer = Station number of the device)");
        ExternalSourceFile.append("      statFirstRun " + NoExternal + " : Bool := TRUE;   // Signalizes the first run");
        ExternalSourceFile.append("      statResetStatesOld " + ExternalRead + " : Bool;   // Detect a rising edge at ResetStates");
        ExternalSourceFile.append("      statMaxDevices " + ExternalRead + " : Int;");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_TEMP ");
        ExternalSourceFile.append("      tempIndex : Int;   // index configured devices");
        ExternalSourceFile.append("      tempSlotIndex : Int;   // Loop index");
        ExternalSourceFile.append("      tempModuleNum : Int;   // index module number");
        ExternalSourceFile.append("      tempRetValGeo : Int;   // GEO2LOG error information");
        ExternalSourceFile.append("      tempRetValDeviceStates : Int;   // DeviceStates error information");
        ExternalSourceFile.append("      tempRetValModuleStates : Int;   // Return value system function ModuleStates");
        ExternalSourceFile.append("      tempStringConvert : String;   // Store the device names temporary here, to convert them into STRING[50]");
        ExternalSourceFile.append("      tempLastDevice : UInt;   // Temporary storage of the actual index, if it is the last device --> store it in static");
        ExternalSourceFile.append("      tempIoSystemError : Bool;");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR CONSTANT ");
        ExternalSourceFile.append("      STATE_CONFIGURED : USInt := 1;   // Used for instruction DeviceStates, read out all configured devices");
        ExternalSourceFile.append("      STATE_FAULTY : USInt := 2;   // Used for instruction DeviceStates, read out all faulty devices");
        ExternalSourceFile.append("      STATE_DISABLED : USInt := 3;   // Used for instruction DeviceStates, read out all disabled devices");
        ExternalSourceFile.append("      STATE_EXIST : USInt := 4;   // Used for instruction DeviceStates, read out all devices not reachable");
        ExternalSourceFile.append("      STATE_PROBLEM : USInt := 5;   // Used for instruction DeviceStates, read out all devices with several problems");
        ExternalSourceFile.append("      DEVICE_SLAVE : USInt := 2;   // GEO2LOG structure: HW type = 2");
        ExternalSourceFile.append("      MODULE_OF_DEVICE : USInt := 4;   // GEO2LOG structure: HW type = 4");
        ExternalSourceFile.append("      IO_SYSTEM_AREA : USInt := 1;   // GEO2LOG structure: Area = 1");
        ExternalSourceFile.append("      DP_SYSTEM_AREA : USInt := 2;   // GEO2LOG structure: Area = 2");
        ExternalSourceFile.append("      ERR_DEV_STATE_DEVICES : USInt := 1;   // Identifies the instruction behind the error code of output \"Status\" --> DeviceStates PN (Configured, faulty, existing)");
        ExternalSourceFile.append("      ERR_GET_NAME_DEVICES : USInt := 2;   // Identifies the instruction behind the error code of output \"Status\" -->  GetName of devices PN");
        ExternalSourceFile.append("      ERR_MOD_STAT_DEVICES : USInt := 3;   // Identifies the instruction behind the error code of output \"Status\" --> ModuleStates PN");
        ExternalSourceFile.append("      ERR_DEV_STAT_PN : USInt := 1;   // Value for output instruction error, DeviceStates PN devices");
        ExternalSourceFile.append("      ERR_MOD_STAT_PN : USInt := 4;   // Value for output instruction error, ModuleStates PN devices");
        ExternalSourceFile.append("      MAX_SLAVES_DP : Int := 127;");
        ExternalSourceFile.append("      MAX_SLAVES_PN : Int := 127;");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Determine hardware identifier and module states from ");
        ExternalSourceFile.append("	//               PN or DP IO system");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// The startup will be executed only once --> initialize the first run");
        ExternalSourceFile.append("	// indicator.");
        ExternalSourceFile.append("	#statFirstDeviceFlag := TRUE;");
        ExternalSourceFile.append("	#statFirstRun := TRUE;");
        ExternalSourceFile.append("	#statActualConfiguredDevices := 0;");
        ExternalSourceFile.append("	#statFirstDevice := 1;");
        ExternalSourceFile.append("	#statLastDevice := 1;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// CONFIGURED DEVICES");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// Find out how much devices are configured in the IO System --> PROFINET IO");
        ExternalSourceFile.append("	// This number is the maximum number of devices, which will be checked in the");
        ExternalSourceFile.append("	// following programm");
        ExternalSourceFile.append("	#tempRetValDeviceStates := DeviceStates(LADDR := #ioSystemHwId,");
        ExternalSourceFile.append("	                                        MODE := #STATE_CONFIGURED,");
        ExternalSourceFile.append("	                                        STATE := #statConfiguredDevices);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Check if the block call was successful");
        ExternalSourceFile.append("	IF (#tempRetValDeviceStates <> 0)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    // Error handling");
        ExternalSourceFile.append("	    #status := #tempRetValDeviceStates;");
        ExternalSourceFile.append("	    #instructionError := #ERR_DEV_STATE_DEVICES;");
        ExternalSourceFile.append("	    // Call ok --> store the actual number of configured devices    ");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	    ;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// EXISTING DEVICES");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	#tempRetValDeviceStates := DeviceStates(LADDR := #ioSystemHwId,");
        ExternalSourceFile.append("	                                        MODE := #STATE_EXIST,");
        ExternalSourceFile.append("	                                        STATE := #statExistingDevices);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Check if the block call was successful");
        ExternalSourceFile.append("	IF (#tempRetValDeviceStates <> 0)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    // Error handling");
        ExternalSourceFile.append("	    #status := #tempRetValDeviceStates;");
        ExternalSourceFile.append("	    #instructionError := #ERR_DEV_STATE_DEVICES;");
        ExternalSourceFile.append("	    // Call ok --> store the actual number of configured devices    ");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	    ;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// FAULTY DEVICES");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	#tempRetValDeviceStates := DeviceStates(LADDR := #ioSystemHwId,");
        ExternalSourceFile.append("	                                        MODE := #STATE_FAULTY,");
        ExternalSourceFile.append("	                                        STATE := #statFaultyDevices);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Check if the block call was successful");
        ExternalSourceFile.append("	IF (#tempRetValDeviceStates <> 0)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    // Error handling");
        ExternalSourceFile.append("	    #status := #tempRetValDeviceStates;");
        ExternalSourceFile.append("	    #instructionError := #ERR_DEV_STATE_DEVICES;");
        ExternalSourceFile.append("	    // Call ok --> store the actual number of configured devices    ");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	    ;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Find out the number of the assigned IO system, to define if it is");
        ExternalSourceFile.append("	// a PN or DP Network");
        ExternalSourceFile.append("	#tempRetValGeo := LOG2GEO(LADDR := #ioSystemHwId,");
        ExternalSourceFile.append("	                          GEOADDR := #statGeoAddr);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// set IO system ID");
        ExternalSourceFile.append("	#ioSystem.ioSystemId := #statGeoAddr.IOSYSTEM;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Inilize the structure for system function GEO2LOG");
        ExternalSourceFile.append("	#statGeoAddr.HWTYPE := #DEVICE_SLAVE;   // Hardware type 2: IO device");
        ExternalSourceFile.append("	// Predefine the type OF IO system. Either Profinet IO or Profibus DP");
        ExternalSourceFile.append("	IF ((#statGeoAddr.IOSYSTEM >= 100)");
        ExternalSourceFile.append("	    AND (#statGeoAddr.IOSYSTEM <= 115))");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    #statGeoAddr.AREA := #IO_SYSTEM_AREA;   // Area ID 1: PROFINET IO");
        ExternalSourceFile.append("	    #statMaxDevices := #MAX_SLAVES_PN;");
        ExternalSourceFile.append("	ELSIF ((#statGeoAddr.IOSYSTEM >= 1)");
        ExternalSourceFile.append("	    AND (#statGeoAddr.IOSYSTEM <= 32))");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    #statGeoAddr.AREA := #DP_SYSTEM_AREA;   // Area ID 1: Profibus DP");
        ExternalSourceFile.append("	    #statMaxDevices := #MAX_SLAVES_DP;");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	    ;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Go trough all devices and get the status of the configured");
        ExternalSourceFile.append("	FOR #tempIndex := 1 TO #statMaxDevices DO");
        ExternalSourceFile.append("	    // The devices are configured --> Read out the logical address and the");
        ExternalSourceFile.append("	    // device name");
        ExternalSourceFile.append("	    IF (#statConfiguredDevices[#tempIndex] = TRUE)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        // Increment the actual configured devices, store the state and");
        ExternalSourceFile.append("	        // HW_ID as an numerical value (UINT)");
        ExternalSourceFile.append("	        #statActualConfiguredDevices := #statActualConfiguredDevices + 1;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        // Store the first configured device for the linked list");
        ExternalSourceFile.append("	        IF (#statFirstDeviceFlag = TRUE)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #statFirstDevice := INT_TO_UINT(#tempIndex);");
        ExternalSourceFile.append("	            #ioSystem.firstDevice := UINT_TO_INT(#statFirstDevice);");
        ExternalSourceFile.append("	            #statFirstDeviceFlag := FALSE;");
        ExternalSourceFile.append("	            #tempLastDevice := INT_TO_UINT(#tempIndex);");
        ExternalSourceFile.append("	            // It is not the first bit --> Store the actual index as \"next device\"");
        ExternalSourceFile.append("	            // in the further one!");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            #ioSystem.device[#tempLastDevice].nextDevice := #tempIndex;");
        ExternalSourceFile.append("	            #tempLastDevice := INT_TO_UINT(#tempIndex);");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        // Store the index of the last device for the exit condition of the");
        ExternalSourceFile.append("	        // followiing instructions");
        ExternalSourceFile.append("	        #statLastDevice := #tempLastDevice;");
        ExternalSourceFile.append("	        #ioSystem.lastDevice := UINT_TO_INT(#statLastDevice);");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        // Station number ");
        ExternalSourceFile.append("	        #statGeoAddr.STATION := INT_TO_UINT(#tempIndex);");
        ExternalSourceFile.append("	        // read LADDR from devices");
        ExternalSourceFile.append("	        #tempRetValGeo := GEO2LOG(GEOADDR := #statGeoAddr,");
        ExternalSourceFile.append("	                                  LADDR => #statGeoLaddr);");
        ExternalSourceFile.append("	        // Everything is ok!");
        ExternalSourceFile.append("	        IF (#tempRetValGeo = 0)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            // store LADDR from devices in diagnostic data block");
        ExternalSourceFile.append("	            #ioSystem.device[#tempIndex].laddr := #statGeoLaddr;");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	            // Store the device name, if the device is existing");
        ExternalSourceFile.append("	            // Get name is an acyclic instruction. In the startup OB, the");
        ExternalSourceFile.append("	            // instruction has to be repeated until it is done or error");
        ExternalSourceFile.append("	            REPEAT");
        ExternalSourceFile.append("	                // Get device name of each decive in PN System");
        ExternalSourceFile.append("	                #instGetNameDevices(LADDR := #ioSystemHwId,");
        ExternalSourceFile.append("	                                    STATION_NR := #statGeoAddr.STATION,");
        ExternalSourceFile.append("	                                    DATA := #tempStringConvert);");
        ExternalSourceFile.append("	                ");
        ExternalSourceFile.append("	            UNTIL (#instGetNameDevices.DONE = TRUE)");
        ExternalSourceFile.append("	                OR (#instGetNameDevices.ERROR = TRUE)");
        ExternalSourceFile.append("	            END_REPEAT;");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	            IF (#instGetNameDevices.ERROR = TRUE)");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                // Error handling");
        ExternalSourceFile.append("	                #status := WORD_TO_INT(#instGetNameDevices.STATUS);");
        ExternalSourceFile.append("	                #instructionError := #ERR_GET_NAME_DEVICES;");
        ExternalSourceFile.append("	                #errorIndex := #tempIndex;");
        ExternalSourceFile.append("	                ");
        ExternalSourceFile.append("	                // Everything is ok --> Convert the String[254] into String[50]    ");
        ExternalSourceFile.append("	            ELSIF (#instGetNameDevices.DONE = TRUE)");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                // Cut all characters more than 50 to reduce the string length");
        ExternalSourceFile.append("	                #ioSystem.device[#tempIndex].name := DELETE(IN := #tempStringConvert,");
        ExternalSourceFile.append("	                                                            L := 204,");
        ExternalSourceFile.append("	                                                            P := 50);");
        ExternalSourceFile.append("	                ");
        ExternalSourceFile.append("	                // Initialize the temporary string before next loop");
        ExternalSourceFile.append("	                #tempStringConvert := #statInitString;");
        ExternalSourceFile.append("	            ELSE");
        ExternalSourceFile.append("	                ;");
        ExternalSourceFile.append("	            END_IF;");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            // If the return value ist not = 0 --> the device/system/module is");
        ExternalSourceFile.append("	            // not configured --> No error handling");
        ExternalSourceFile.append("	            // set LADDR from devices to 0 in diagnostic data block");
        ExternalSourceFile.append("	            #ioSystem.device[#tempIndex].laddr := 0;");
        ExternalSourceFile.append("	            #ioSystem.device[#tempIndex].name := '';");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        // Check if the configured devices are faulty or lost once through");
        ExternalSourceFile.append("	        // the startup!");
        ExternalSourceFile.append("	        IF (#statExistingDevices[#tempIndex] = TRUE)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            IF (#statFaultyDevices[#tempIndex] = TRUE)");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                ");
        ExternalSourceFile.append("	                #ioSystem.device[#tempIndex].errorState := "+str(self.DEV_STATE_FAULT)+";");
        ExternalSourceFile.append("	                #ioSystem.device[#tempIndex].error := TRUE;");
        ExternalSourceFile.append("	                ");
        ExternalSourceFile.append("	                // The device is not faulty and does exist --> set state ok!    ");
        ExternalSourceFile.append("	            ELSE");
        ExternalSourceFile.append("	                #ioSystem.device[#tempIndex].errorState := "+str(self.DEV_STATE_OK)+";");
        ExternalSourceFile.append("	                #ioSystem.device[#tempIndex].error := FALSE;");
        ExternalSourceFile.append("	            END_IF;");
        ExternalSourceFile.append("	            // The connection to the device is lost at the moment    ");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            #ioSystem.device[#tempIndex].errorState := "+str(self.DEV_STATE_LOST_CON)+";");
        ExternalSourceFile.append("	            #ioSystem.device[#tempIndex].error := TRUE;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        // No device is configured   ");
        ExternalSourceFile.append("	    ELSE");
        ExternalSourceFile.append("	        ;");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	END_FOR;");
        ExternalSourceFile.append("	// Store the actual configured devices in the diagnostics structure");
        ExternalSourceFile.append("	#ioSystem.actualConfiguredDevices := #statActualConfiguredDevices;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Mark parameter \"Next Device\" of the last device in the list");
        ExternalSourceFile.append("	// --> \"Next Device\" = negative --> Last device in the list");
        ExternalSourceFile.append("	#ioSystem.device[#statLastDevice].nextDevice := "+str(self.LAST_DEVICE)+";");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// Go through the devices until the last device is reached");
        ExternalSourceFile.append("	// If there are gaps between the device-list, jump over and have a look on");
        ExternalSourceFile.append("	// the \"NextDevice\" parameter");
        ExternalSourceFile.append("	REPEAT");
        ExternalSourceFile.append("	    IF (#statFirstRun = TRUE)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        // The index of the linked list is representing the station number.");
        ExternalSourceFile.append("	        #statGeoAddr.STATION := #statFirstDevice;");
        ExternalSourceFile.append("	        // Initialize the pointer for the first run ");
        ExternalSourceFile.append("	        #statLinkedListPointer := UINT_TO_INT(#statFirstDevice);");
        ExternalSourceFile.append("	        // Reset the flag, which signalizes the first run.");
        ExternalSourceFile.append("	        #statFirstRun := FALSE;");
        ExternalSourceFile.append("	    ELSE");
        ExternalSourceFile.append("	        // The index of the linked list is representing the station number.");
        ExternalSourceFile.append("	        #statGeoAddr.STATION := INT_TO_UINT(#statLinkedListPointer);");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    // Get the logical address of all modules and store the actual number of");
        ExternalSourceFile.append("	    // modules from each device");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    // Inilize the structure for system function GEO2LOG");
        ExternalSourceFile.append("	    #statGeoAddr.HWTYPE := #MODULE_OF_DEVICE;   // Hardware type 4: Module");
        ExternalSourceFile.append("	    FOR #tempModuleNum := 0 TO "+str(self._MAX_MODULES_IN_IO_DEVICE)+" DO");
        ExternalSourceFile.append("	        // Slot number");
        ExternalSourceFile.append("	        #statGeoAddr.SLOT := INT_TO_UINT(#tempModuleNum);");
        ExternalSourceFile.append("	        // read LADDR from modules");
        ExternalSourceFile.append("	        #tempRetValGeo := GEO2LOG(GEOADDR := #statGeoAddr,");
        ExternalSourceFile.append("	                                  LADDR => #statGeoLaddr);");
        ExternalSourceFile.append("	        // check Retval");
        ExternalSourceFile.append("	        IF (#tempRetValGeo = 0)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            // store LADDR from modules in diagnostic data block");
        ExternalSourceFile.append("	            #ioSystem.device[#statLinkedListPointer].slot[#tempModuleNum].slotLaddr := #statGeoLaddr;");
        ExternalSourceFile.append("	            #ioSystem.device[#statLinkedListPointer].actualConfiguredModules := #ioSystem.device[#statLinkedListPointer].actualConfiguredModules + 1;");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            // If the return value ist not = 0 --> the device/system/module is");
        ExternalSourceFile.append("	            // not configured --> No error handling");
        ExternalSourceFile.append("	            // set LADDR from modules to 0 in diagnostic data block");
        ExternalSourceFile.append("	            #ioSystem.device[#statLinkedListPointer].slot[#tempModuleNum].slotLaddr := 0;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	    END_FOR;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    // Check modules of faulty Devices");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    // Check the state of the configured devices");
        ExternalSourceFile.append("	    IF (#ioSystem.device[#statLinkedListPointer].errorState = "+str(self.DEV_STATE_FAULT)+")");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        // The device is reachable, but faulty because of an error in a");
        ExternalSourceFile.append("	        // subordinated system --> check the modules");
        ExternalSourceFile.append("	        #tempRetValModuleStates := ModuleStates(LADDR := #ioSystem.device[#statLinkedListPointer].laddr,");
        ExternalSourceFile.append("	                                                MODE := #STATE_PROBLEM,");
        ExternalSourceFile.append("	                                                STATE := #statDeviceModuleStates);");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        IF (#tempRetValModuleStates <> 0)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            // Error hanlding");
        ExternalSourceFile.append("	            #status := #tempRetValModuleStates;");
        ExternalSourceFile.append("	            #instructionError := #ERR_MOD_STAT_DEVICES;");
        ExternalSourceFile.append("	            #errorIndex := UINT_TO_INT(#statFirstDevice);");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            // Store the state of the different module in the diag DB");
        ExternalSourceFile.append("	            FOR #tempSlotIndex := 0 TO #ioSystem.device[#statFirstDevice].actualConfiguredModules DO");
        ExternalSourceFile.append("	                IF (#statDeviceModuleStates[#tempSlotIndex + 1] = TRUE)");
        ExternalSourceFile.append("	                THEN");
        ExternalSourceFile.append("	                    #ioSystem.device[#statLinkedListPointer].slot[#tempSlotIndex].slotErrorState := TRUE;");
        ExternalSourceFile.append("	                ELSE");
        ExternalSourceFile.append("	                    #ioSystem.device[#statLinkedListPointer].slot[#tempSlotIndex].slotErrorState := FALSE;");
        ExternalSourceFile.append("	                END_IF;");
        ExternalSourceFile.append("	            END_FOR;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	    ELSIF (#ioSystem.device[#statLinkedListPointer].errorState = "+str(self.DEV_STATE_LOST_CON)+")");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        FOR #tempSlotIndex := 0 TO #ioSystem.device[#statLinkedListPointer].actualConfiguredModules DO");
        ExternalSourceFile.append("	            IF (#ioSystem.device[#statLinkedListPointer].slot[#tempSlotIndex].slotLaddr <> 0)");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                #ioSystem.device[#statLinkedListPointer].slot[#tempSlotIndex].slotErrorState := TRUE;");
        ExternalSourceFile.append("	            END_IF;");
        ExternalSourceFile.append("	        END_FOR;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	    ELSE");
        ExternalSourceFile.append("	        ; // no faulty device --> nothing to do!");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    // Initialize the pointer for the next run");
        ExternalSourceFile.append("	    #statLinkedListPointer := #ioSystem.device[#statLinkedListPointer].nextDevice;");
        ExternalSourceFile.append("	    // If the last device is reached, reset the bit for the first run");
        ExternalSourceFile.append("	    //#FirstRun := TRUE;");
        ExternalSourceFile.append("	    // Checking the modules is done, the last device is reached");
        ExternalSourceFile.append("	UNTIL (#statLinkedListPointer < 0)");
        ExternalSourceFile.append("	END_REPEAT;");
        ExternalSourceFile.append("	// Reset the condition for the first run.");
        ExternalSourceFile.append("	#statFirstRun := TRUE;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_FUNCTION_BLOCK");
        ExternalSourceFile.append("");


    def __DiagStartupIoSystem_iDB(self, TIAVersion, ExternalSourceFile):
        #DiagStartupIoSystem_iDB instance DB
        ExternalSourceFile.append("DATA_BLOCK \"DiagStartupIoSystem_iDB\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("NON_RETAIN");
        ExternalSourceFile.append("\"DiagStartupIoSystem\"");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_DATA_BLOCK");
        ExternalSourceFile.append("");


    def __DiagStartupPlc(self, TIAVersion, ExternalSourceFile):
        #DiagStartupPlc FB
        ExternalSourceFile.append("FUNCTION_BLOCK \"DiagStartupPlc\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   VAR_OUTPUT ");
        ExternalSourceFile.append("      status " + ExternalRead + " : Int;   // The return value of system function, where the last error occured");
        ExternalSourceFile.append("      instructionError " + ExternalRead + " : Int;   // Indicates in which system function the error occured: 1= DeviceStates PN , 2=GetName PN, 3=ModuleStates PN,  4=DeviceStates DP, 5= GetName DP. 6= ModuleStates DP");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_IN_OUT ");
        ExternalSourceFile.append("      plc " + ExternalRead + " : \"typePlc\";   // The diagnostics structure for one PLC");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR ");
        ExternalSourceFile.append("      statGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'; " + _NoExternal + "} : GEOADDR;   // Slot information");
        ExternalSourceFile.append("      statGeoLaddr " + NoExternal + " : HW_ANY;   // GEO2LOG hardware identifier");
        ExternalSourceFile.append("      statActualCentralModules " + ExternalRead + " : USInt := 0;   // Actual number of modules in the central station (PLC)");
        ExternalSourceFile.append("      statPlcModuleStates " + ExternalRead + " : Array[0..127] of Bool;   // Storage of the status of all modules in the PLC central station --> State: Problem");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_TEMP ");
        ExternalSourceFile.append("      tempModuleNum : Int;   // index module number");
        ExternalSourceFile.append("      tempRetValGeo : Int;   // GEO2LOG error information");
        ExternalSourceFile.append("      tempRetValModuleStates : Int;   // Return value system function ModuleStates");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR CONSTANT ");
        ExternalSourceFile.append("      MODULE_OF_PLC : USInt := 4;   // GEO2LOG structure: HW type = 4");
        ExternalSourceFile.append("      CPU : USInt := 0;   // GEO2LOG structure: Area = 0");
        ExternalSourceFile.append("      CENTRAL_SYSTEM : USInt := 0;   // GEO2LOG structure: IO System = 0");
        ExternalSourceFile.append("      CENTRAL_STATION : USInt;   // GEO2LOG structure: Station = 0");
        ExternalSourceFile.append("      HW_ID_PLC_MODULES : HW_DEVICE := 32;   // HW ID of the PLC, which is needed for getting the module states --> fix value");
        ExternalSourceFile.append("      STATE_PROBLEM : USInt := 5;   // Used for instruction DeviceStates, read out all devices with several problems");
        ExternalSourceFile.append("      ERR_MOD_STAT_CENTRAL : USInt := 3;   // Value for output instruction error, ModuleStates local modules");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Determine hardware identifier and module states from local");
        ExternalSourceFile.append("	//               modules");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// Determine hardware identifier from LOCAL MODULES");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	#statGeoAddr.HWTYPE := #MODULE_OF_PLC;      // Hardware type 4: module");
        ExternalSourceFile.append("	#statGeoAddr.AREA := #CPU;                  // Area ID 0: CPU");
        ExternalSourceFile.append("	#statGeoAddr.IOSYSTEM := #CENTRAL_SYSTEM;   // PROFINET IO system");
        ExternalSourceFile.append("	                                            // (0 = central unit in the rack)");
        ExternalSourceFile.append("	#statGeoAddr.STATION := #CENTRAL_STATION;   // Number of the rack");
        ExternalSourceFile.append("	                                            // if area identifier");
        ExternalSourceFile.append("	                                            //  AREA = 0 (central module).");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	FOR #tempModuleNum := 1 TO "+str(self._MAX_LOCAL_MODULES)+" DO");
        ExternalSourceFile.append("	  // Slot number");
        ExternalSourceFile.append("	  #statGeoAddr.SLOT := INT_TO_UINT(#tempModuleNum);");
        ExternalSourceFile.append("	  // read LADDR from local modules");
        ExternalSourceFile.append("	  #tempRetValGeo := GEO2LOG(GEOADDR := #statGeoAddr,");
        ExternalSourceFile.append("	                            LADDR => #statGeoLaddr);");
        ExternalSourceFile.append("	  // check Retval");
        ExternalSourceFile.append("	  IF (#tempRetValGeo = 0)");
        ExternalSourceFile.append("	  THEN");
        ExternalSourceFile.append("	    // store LADDR from local modules in diagnostic data block");
        ExternalSourceFile.append("	    #plc.slot[#tempModuleNum].slotLaddr := #statGeoLaddr;");
        ExternalSourceFile.append("	    #statActualCentralModules := #statActualCentralModules + 1;");
        ExternalSourceFile.append("	  ELSE");
        ExternalSourceFile.append("	    // If the return value ist not = 0 --> the device/system/module is not");
        ExternalSourceFile.append("	    // configured --> No error handling");
        ExternalSourceFile.append("	    // set LADDR from local modules to 0 in diagnostic data block");
        ExternalSourceFile.append("	    #plc.slot[#tempModuleNum].slotLaddr := 0;");
        ExternalSourceFile.append("	  END_IF;");
        ExternalSourceFile.append("	  // Store the actual configured devices in the diagnostics DB");
        ExternalSourceFile.append("	  #plc.actualConfiguredCentralModules := #statActualCentralModules;");
        ExternalSourceFile.append("	END_FOR;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// Check module states from LOCAL MODULES");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// Check if central module are available - at least one module is always");
        ExternalSourceFile.append("	// configured, the PLC itself");
        ExternalSourceFile.append("	IF (#plc.actualConfiguredCentralModules > 1)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	  // Check the status of the local modules");
        ExternalSourceFile.append("	  #tempRetValModuleStates := ModuleStates(LADDR := #HW_ID_PLC_MODULES,");
        ExternalSourceFile.append("	                                          MODE := #STATE_PROBLEM,");
        ExternalSourceFile.append("	                                          STATE := #statPlcModuleStates);");
        ExternalSourceFile.append("	  ");
        ExternalSourceFile.append("	  // Check if the block call was successful");
        ExternalSourceFile.append("	  IF (#tempRetValModuleStates <> 0)");
        ExternalSourceFile.append("	  THEN");
        ExternalSourceFile.append("	    // Error handling");
        ExternalSourceFile.append("	    #status := #tempRetValModuleStates;");
        ExternalSourceFile.append("	    #instructionError := #ERR_MOD_STAT_CENTRAL;");
        ExternalSourceFile.append("	  ELSE");
        ExternalSourceFile.append("	    ; // Everything is ok!");
        ExternalSourceFile.append("	  END_IF;");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	  ; // There are no central module configured");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// The error LED of the PLC is flashing --> Set error state of the PLC");
        ExternalSourceFile.append("	#plc.errorState := TRUE;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// set module states from LOCAL MODULES");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	// If the first bit in the array is true, at least one module is faulty");
        ExternalSourceFile.append("	IF (#statPlcModuleStates[0] = TRUE)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	  // Check which of the modules are faulty");
        ExternalSourceFile.append("	  // PLC modules array starts at index 2 for the first local module");
        ExternalSourceFile.append("	  FOR #tempModuleNum := 2 TO #plc.actualConfiguredCentralModules + 1 DO");
        ExternalSourceFile.append("	    IF (#statPlcModuleStates[#tempModuleNum] = TRUE)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	      #plc.slot[#tempModuleNum - 1].slotErrorState := TRUE;");
        ExternalSourceFile.append("	    ELSE");
        ExternalSourceFile.append("	      #plc.slot[#tempModuleNum - 1].slotErrorState := FALSE;");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	  END_FOR;");
        ExternalSourceFile.append("	  ");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	  // Everything is ok!");
        ExternalSourceFile.append("	  FOR #tempModuleNum := 1 TO #plc.actualConfiguredCentralModules DO");
        ExternalSourceFile.append("	    #plc.slot[#tempModuleNum].slotErrorState := FALSE;");
        ExternalSourceFile.append("	  END_FOR;");
        ExternalSourceFile.append("	  ");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_FUNCTION_BLOCK");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");


    def __DiagStartupPlc_iDB(self, TIAVersion, ExternalSourceFile):
        #DiagStartupPlc_iDB instance DB
        ExternalSourceFile.append("DATA_BLOCK \"DiagStartupPlc_iDB\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("NON_RETAIN");
        ExternalSourceFile.append("\"DiagStartupPlc\"");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_DATA_BLOCK");
        ExternalSourceFile.append("");


    def __DiagnosticError(self, TIAVersion, ExternalSourceFile):
        #DiagnosticError FB
        ExternalSourceFile.append("FUNCTION \"DiagnosticError\" : Void");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   VAR_INPUT ");
        ExternalSourceFile.append("      ioState : Word;   // IO state of the HW object");
        ExternalSourceFile.append("      laddr : HW_ANY;   // Hardware identifier");
        ExternalSourceFile.append("      channel : UInt;   // Channel number");
        ExternalSourceFile.append("      multiError : Bool;   // =true if more than one error is present");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_IN_OUT ");
        ExternalSourceFile.append("      plc : \"typePlc\";   // The diagnostics structure for one PLC");
        ExternalSourceFile.append("      ioSystem : Array[1.."+str(self.MAX_IO_SYSTEM)+"] of \"typeIoSystem\";   // The diagnostics structure for one IO System");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_TEMP ");
        ExternalSourceFile.append("      tempGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'} : GEOADDR;   // Geographical address of the disturbed Module / Device");
        ExternalSourceFile.append("      tempIoSystemIndex : Int;   // Index for IO System");
        ExternalSourceFile.append("      index : Int;   // index system");
        ExternalSourceFile.append("      tempRetVal : Int;   // Return value of LOG2GEO");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR CONSTANT ");
        ExternalSourceFile.append("      GOOD : Word := 16#0001;   // Status of the hardware object: Bit 0: Good");
        ExternalSourceFile.append("      AREA_CENTRAL : UInt := 0;   // Area ID for PLC");
        ExternalSourceFile.append("      AREA_PROFINET : UInt := 1;   // Area ID for PROFINET IO");
        ExternalSourceFile.append("      AREA_PROFIBUS : UInt := 2;   // Area ID for PROFIBUS DP");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Evaluate Diagnostic interrupt OB information for PLC and");
        ExternalSourceFile.append("	//               devices");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29-08-2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// determine geographic address of faulty device");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	#tempRetVal := LOG2GEO(LADDR := #laddr,");
        ExternalSourceFile.append("	                       GEOADDR := #tempGeoAddr);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// evaluate diagnosis information for devices in an IO system");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	IF (#tempGeoAddr.AREA = #AREA_PROFINET)");
        ExternalSourceFile.append("	    OR (#tempGeoAddr.AREA = #AREA_PROFIBUS)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    // determine index for IO system");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    FOR #index := 1 TO "+str(self.MAX_IO_SYSTEM)+" DO");
        ExternalSourceFile.append("	        IF (\"DiagnosticsData\".ioSystem[#index].ioSystemId = #tempGeoAddr.IOSYSTEM)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #tempIoSystemIndex := #index;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	    END_FOR;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    IF (#tempIoSystemIndex <= "+str(self.MAX_IO_SYSTEM)+")");
        ExternalSourceFile.append("	        AND (#tempGeoAddr.STATION <= "+str(self._MAX_MODULES_IN_IO_DEVICE)+")");
        ExternalSourceFile.append("	        AND (#tempGeoAddr.SLOT <= "+str(self._MAX_MODULES_IN_IO_DEVICE)+")");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        // evaluate diagnosis information IO system");
        ExternalSourceFile.append("	        IF (#ioState = #GOOD)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].error := FALSE;");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempGeoAddr.SLOT].slotErrorState := FALSE;");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	            IF (#ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState = "+str(self.DEV_STATE_FAULT)+")");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_WAS_FAULT)+";");
        ExternalSourceFile.append("	            ELSIF (#ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState = "+str(self.DEV_STATE_LOST_CON)+")");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_WAS_LOST)+";");
        ExternalSourceFile.append("	            ELSE");
        ExternalSourceFile.append("	                #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_OK)+";");
        ExternalSourceFile.append("	            END_IF;");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].error := TRUE;");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_FAULT)+";");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempGeoAddr.SLOT].slotErrorState := TRUE;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    // evaluate diagnosis information for PLC");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	ELSIF (#tempGeoAddr.AREA = #AREA_CENTRAL)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    IF (#tempGeoAddr.SLOT <= "+str(self._MAX_LOCAL_MODULES)+")");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        // evaluate diagnosis information PLC");
        ExternalSourceFile.append("	        IF (#ioState = #GOOD)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #plc.slot[#tempGeoAddr.SLOT].slotErrorState := FALSE;");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            #plc.slot[#tempGeoAddr.SLOT].slotErrorState := TRUE;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	    ;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_FUNCTION");
        ExternalSourceFile.append("");


    def __PullOrPlugModules(self, TIAVersion, ExternalSourceFile):
        #PullOrPlugModules FB
        ExternalSourceFile.append("FUNCTION \"PullOrPlugModules\" : Void");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   VAR_INPUT ");
        ExternalSourceFile.append("      laddr : HW_IO;   // Hardware identifier");
        ExternalSourceFile.append("      eventClass : Byte;   // 16#38/39: module inserted, removed");
        ExternalSourceFile.append("      faultId : Byte;   // Fault identifier");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_IN_OUT ");
        ExternalSourceFile.append("      plc : \"typePlc\";   // The diagnostics structure for one PLC");
        ExternalSourceFile.append("      ioSystem : Array[1.."+str(self.MAX_IO_SYSTEM)+"] of \"typeIoSystem\";   // The diagnostics structure for one IO System");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_TEMP ");
        ExternalSourceFile.append("      tempIoSystemIndex : Int;   // Index for IO System");
        ExternalSourceFile.append("      index : Int;   // index system");
        ExternalSourceFile.append("      tempGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'} : GEOADDR;   // Geographical address of the disturbed Module / Device");
        ExternalSourceFile.append("      tempRetVal : Int;   // Return value of LOG2GEO");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR CONSTANT ");
        ExternalSourceFile.append("      AREA_CENTRAL : UInt := 0;   // Area ID for PLC");
        ExternalSourceFile.append("      AREA_PROFINET : UInt := 1;   // Area ID for PROFINET IO");
        ExternalSourceFile.append("      AREA_PROFIBUS : UInt := 2;   // Area ID for PROFIBUS DP");
        ExternalSourceFile.append("      MODULE_PLUGGED : Byte := 16#38;   // (Sub)module plugged");
        ExternalSourceFile.append("      MODULE_PULLED : Byte := 16#39;   // (Sub)module pulled or not responding");
        ExternalSourceFile.append("      MODULE_MATCHES : Byte := 16#54;   // IO submodule inserted and matches configured submodule");
        ExternalSourceFile.append("      MODULE_OK : Byte := 16#61;   // Module inserted, module type OK");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Evaluate Pull/plug interrupt OB information for PLC and");
        ExternalSourceFile.append("	//               devices");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// determine geographic address of faulty device");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	#tempRetVal := LOG2GEO(LADDR := #laddr,");
        ExternalSourceFile.append("	                       GEOADDR := #tempGeoAddr);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// evaluate diagnosis information for devices in an IO system");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	IF (#tempGeoAddr.AREA = #AREA_PROFINET)");
        ExternalSourceFile.append("	    OR (#tempGeoAddr.AREA = #AREA_PROFIBUS)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    // determine index for IO system");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    FOR #index := 1 TO "+str(self.MAX_IO_SYSTEM)+" DO");
        ExternalSourceFile.append("	        IF (#ioSystem[#index].ioSystemId = #tempGeoAddr.IOSYSTEM)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #tempIoSystemIndex := #index;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	    END_FOR;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    IF (#tempIoSystemIndex <= "+str(self.MAX_IO_SYSTEM)+")");
        ExternalSourceFile.append("	        AND (#tempGeoAddr.STATION <= "+str(self._MAX_MODULES_IN_IO_DEVICE)+")");
        ExternalSourceFile.append("	        AND (#tempGeoAddr.SLOT <= "+str(self._MAX_MODULES_IN_IO_DEVICE)+")");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        // check modules plugged");
        ExternalSourceFile.append("	        IF (#eventClass = #MODULE_PLUGGED)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            // reset error state only if the correct module is inserted");
        ExternalSourceFile.append("	            IF (#faultId = #MODULE_MATCHES)");
        ExternalSourceFile.append("	                OR (#faultId = #MODULE_OK)");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].error := FALSE;");
        ExternalSourceFile.append("	                #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempGeoAddr.SLOT].slotErrorState := FALSE;");
        ExternalSourceFile.append("	                ");
        ExternalSourceFile.append("	                IF (#ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState = "+str(self.DEV_STATE_FAULT)+")");
        ExternalSourceFile.append("	                THEN");
        ExternalSourceFile.append("	                    #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_WAS_FAULT)+";");
        ExternalSourceFile.append("	                ELSIF (#ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState = "+str(self.DEV_STATE_LOST_CON)+")");
        ExternalSourceFile.append("	                THEN");
        ExternalSourceFile.append("	                    #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_WAS_LOST)+";");
        ExternalSourceFile.append("	                ELSE");
        ExternalSourceFile.append("	                    #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_OK)+";");
        ExternalSourceFile.append("	                END_IF;");
        ExternalSourceFile.append("	            END_IF;");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	            // check modules pulled  ");
        ExternalSourceFile.append("	        ELSIF (#eventClass = #MODULE_PULLED)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].error := TRUE;");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_FAULT)+";");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	            #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempGeoAddr.SLOT].slotErrorState := TRUE;");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            ;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	    // evaluate diagnosis information for PLC");
        ExternalSourceFile.append("	    //=============================================================================");
        ExternalSourceFile.append("	ELSIF (#tempGeoAddr.AREA = #AREA_CENTRAL)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    IF (#tempGeoAddr.SLOT <= "+str(self._MAX_LOCAL_MODULES)+")");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	        IF (#eventClass = #MODULE_PLUGGED)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            IF (#faultId = #MODULE_MATCHES)");
        ExternalSourceFile.append("	                OR (#faultId = #MODULE_OK)");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	                #plc.slot[#tempGeoAddr.SLOT].slotErrorState := FALSE;");
        ExternalSourceFile.append("	            END_IF;");
        ExternalSourceFile.append("	            ");
        ExternalSourceFile.append("	        ELSIF (#eventClass = #MODULE_PULLED)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #plc.slot[#tempGeoAddr.SLOT].slotErrorState := TRUE;");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	            ;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	    ;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_FUNCTION");
        ExternalSourceFile.append("");


    def __RackOrStationFailure(self, TIAVersion, ExternalSourceFile):
        #RackOrStationFaliure FB
        ExternalSourceFile.append("FUNCTION \"RackOrStationFaliure\" : Void");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   VAR_INPUT ");
        if TIAVersion == 13:
            ExternalSourceFile.append("      laddr : HW_IO;   // Hardware identifier")
        else:
            ExternalSourceFile.append("      laddr : HW_DEVICE;   // Hardware identifier")
        ExternalSourceFile.append("      eventClass : Byte;   // Event class");
        ExternalSourceFile.append("      faultId : Byte;   // Fault identifier");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_IN_OUT ");
        ExternalSourceFile.append("      plc : \"typePlc\";   // The diagnostics structure for one PLC");
        ExternalSourceFile.append("      ioSystem : Array[1.."+str(self.MAX_IO_SYSTEM)+"] of \"typeIoSystem\";   // The diagnostics structure for one IO System");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_TEMP ");
        ExternalSourceFile.append("      index : Int;   // index system");
        ExternalSourceFile.append("      tempSlotIndex : Int;   // Loop index");
        ExternalSourceFile.append("      tempIoSystemIndex : Int;   // Index for IO System");
        ExternalSourceFile.append("      tempGeoAddr {OriginalPartName := 'GEOADDR'; LibVersion := '1.0'} : GEOADDR;   // Geographical address of the disturbed Module / Device");
        ExternalSourceFile.append("      tempRetVal : Int;   // Return value of LOG2GEO");
        ExternalSourceFile.append("      tempRetValModuleStates : Int;   // Return value system function ModuleStates");
        ExternalSourceFile.append("      tempDeviceModuleStates : Array[0..127] of Bool;   // Storage of the status of all modules in the PN Devices --> State: Problem");
        ExternalSourceFile.append("      tempLaddr : HW_DEVICE;   // logical address of the disturbed Module / Device");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR CONSTANT ");
        ExternalSourceFile.append("      AREA_CENTRAL : UInt := 0;   // Area ID for PLC");
        ExternalSourceFile.append("      AREA_PROFINET : UInt := 1;   // Area ID for PROFINET IO");
        ExternalSourceFile.append("      AREA_PROFIBUS : UInt := 2;   // Area ID for PROFIBUS DP");
        ExternalSourceFile.append("      SLAVE_DEVICE_RET : Byte := 16#38;   // return of a DP slave / IO device");
        ExternalSourceFile.append("      SLAVE_DEVICE_FAIL : Byte := 16#39;   // Failure of a DP slave / IO device");
        ExternalSourceFile.append("      DP_SLAVE_FAIL_RET : Byte := 16#C4;   // Failure/return of a DP slave");
        ExternalSourceFile.append("      IO_DEVICE_FAIL_RET : Byte := 16#CB;   // Failure/return of a PROFINET IO device");
        ExternalSourceFile.append("      STATE_PROBLEM : USInt := 5;   // Used for instruction DeviceStates, read out all devices with several problems");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Evaluate Rack/Station interrupt OB information for PLC and");
        ExternalSourceFile.append("	//               devices");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// determine geographic address of faulty device");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	#tempRetVal := LOG2GEO(LADDR := #laddr,");
        ExternalSourceFile.append("	                       GEOADDR := #tempGeoAddr);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// evaluate diagnosis information for devices in an IO system");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	IF (#tempGeoAddr.AREA = #AREA_PROFINET)");
        ExternalSourceFile.append("	  OR (#tempGeoAddr.AREA = #AREA_PROFIBUS)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	  ");
        ExternalSourceFile.append("	  //===========================================================================");
        ExternalSourceFile.append("	  // determine index for IO system");
        ExternalSourceFile.append("	  //===========================================================================");
        ExternalSourceFile.append("	  FOR #index := 1 TO "+str(self.MAX_IO_SYSTEM)+" DO");
        ExternalSourceFile.append("	    IF (#ioSystem[#index].ioSystemId = #tempGeoAddr.IOSYSTEM)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	      #tempIoSystemIndex := #index;");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	  END_FOR;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	  IF (#tempIoSystemIndex <= "+str(self.MAX_IO_SYSTEM)+")");
        ExternalSourceFile.append("	    AND (#tempGeoAddr.STATION <= "+str(self._MAX_MODULES_IN_IO_DEVICE)+")");
        ExternalSourceFile.append("	    AND (#tempGeoAddr.SLOT <= "+str(self._MAX_MODULES_IN_IO_DEVICE)+")");
        ExternalSourceFile.append("	  THEN");
        ExternalSourceFile.append("	    // check DP slave or IO device return ");
        ExternalSourceFile.append("	    IF (#eventClass = #SLAVE_DEVICE_RET)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	      // reset error state only if the slave or device state is OK");
        ExternalSourceFile.append("	      IF (#faultId = #DP_SLAVE_FAIL_RET)");
        ExternalSourceFile.append("	        OR (#faultId = #IO_DEVICE_FAIL_RET)");
        ExternalSourceFile.append("	      THEN");
        ExternalSourceFile.append("	        #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].error := FALSE;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        FOR #tempSlotIndex := 0 TO #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].actualConfiguredModules DO");
        ExternalSourceFile.append("	          #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempSlotIndex].slotErrorState := FALSE;");
        ExternalSourceFile.append("	        END_FOR;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        IF (#ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState = "+str(self.DEV_STATE_FAULT)+")");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	          #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_WAS_FAULT)+";");
        ExternalSourceFile.append("	        ELSIF (#ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState = "+str(self.DEV_STATE_LOST_CON)+")");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	          #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_WAS_LOST)+";");
        ExternalSourceFile.append("	        ELSE");
        ExternalSourceFile.append("	          #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_OK)+";");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	      ELSE");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        // The device is reachable, but faulty because of an error in a");
        ExternalSourceFile.append("	        // subordinated system --> check the modules");
        ExternalSourceFile.append("	        #tempRetVal := GEO2LOG(LADDR => #tempLaddr,");
        ExternalSourceFile.append("	                               GEOADDR := #tempGeoAddr);");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        #tempRetValModuleStates := ModuleStates(LADDR := #tempLaddr,");
        ExternalSourceFile.append("	                                                MODE := #STATE_PROBLEM,");
        ExternalSourceFile.append("	                                                STATE := #tempDeviceModuleStates);");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        IF (#tempRetValModuleStates = 0)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	          // Store the state of the different module in the diag DB");
        ExternalSourceFile.append("	          FOR #tempSlotIndex := 0 TO #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].actualConfiguredModules DO");
        ExternalSourceFile.append("	            IF (#tempDeviceModuleStates[#tempSlotIndex + 1] = TRUE)");
        ExternalSourceFile.append("	            THEN");
        ExternalSourceFile.append("	              #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempSlotIndex].slotErrorState := TRUE;");
        ExternalSourceFile.append("	            ELSE");
        ExternalSourceFile.append("	              #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempSlotIndex].slotErrorState := FALSE;");
        ExternalSourceFile.append("	            END_IF;");
        ExternalSourceFile.append("	          END_FOR;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	        #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_FAULT)+";");
        ExternalSourceFile.append("	        ");
        ExternalSourceFile.append("	      END_IF;");
        ExternalSourceFile.append("	      ");
        ExternalSourceFile.append("	      // check DP slave or IO device failure ");
        ExternalSourceFile.append("	    ELSIF (#eventClass = #SLAVE_DEVICE_FAIL)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	      #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].error := TRUE;");
        ExternalSourceFile.append("	      #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].errorState := "+str(self.DEV_STATE_LOST_CON)+";");
        ExternalSourceFile.append("	      ");
        ExternalSourceFile.append("	      FOR #tempSlotIndex := 0 TO #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].actualConfiguredModules DO");
        ExternalSourceFile.append("	        IF #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempSlotIndex].slotLaddr <> 0");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	          #ioSystem[#tempIoSystemIndex].device[#tempGeoAddr.STATION].slot[#tempSlotIndex].slotErrorState := TRUE;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	      END_FOR;");
        ExternalSourceFile.append("	      ");
        ExternalSourceFile.append("	    ELSE");
        ExternalSourceFile.append("	      ;");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	  END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//evaluate diagnosis information for PLC");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	ELSIF (#tempGeoAddr.AREA = #AREA_CENTRAL)");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	  ");
        ExternalSourceFile.append("	  IF (#tempGeoAddr.SLOT <= "+str(self._MAX_LOCAL_MODULES)+")");
        ExternalSourceFile.append("	  THEN");
        ExternalSourceFile.append("	    // check DP slave or IO device return ");
        ExternalSourceFile.append("	    IF (#eventClass = #SLAVE_DEVICE_RET)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	      IF (#faultId = #DP_SLAVE_FAIL_RET)");
        ExternalSourceFile.append("	        OR (#faultId = #IO_DEVICE_FAIL_RET)");
        ExternalSourceFile.append("	      THEN");
        ExternalSourceFile.append("	        #plc.slot[#tempGeoAddr.SLOT].slotErrorState := FALSE;");
        ExternalSourceFile.append("	      END_IF;");
        ExternalSourceFile.append("	      ");
        ExternalSourceFile.append("	      // check DP slave or IO device failure ");
        ExternalSourceFile.append("	    ELSIF (#eventClass = #SLAVE_DEVICE_FAIL)");
        ExternalSourceFile.append("	    THEN");
        ExternalSourceFile.append("	      #plc.slot[#tempGeoAddr.SLOT].slotErrorState := TRUE;");
        ExternalSourceFile.append("	    ELSE");
        ExternalSourceFile.append("	      ;");
        ExternalSourceFile.append("	    END_IF;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	  END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	  ;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_FUNCTION");
        ExternalSourceFile.append("");


    def __Diagnostics(self, TIAVersion, ExternalSourceFile):
        #Diagnostics FB
        ExternalSourceFile.append("FUNCTION_BLOCK \"Diagnostics\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("   VAR_IN_OUT ");
        ExternalSourceFile.append("      plc " + ExternalRead + " : \"typePlc\";   // The diagnostics structure for one PLC");
        ExternalSourceFile.append("      ioSystem " + ExternalRead + " : Array[1.."+str(self.MAX_IO_SYSTEM)+"] of \"typeIoSystem\";   // The diagnostics structure for one IO System");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR ");
        ExternalSourceFile.append("      statIoSystemIndex " + ExternalRead + " : Int;   // Index for IO System");
        ExternalSourceFile.append("      statSlotIndex " + ExternalRead + " : Int;   // Index for Slot");
        ExternalSourceFile.append("      statDeviceIndex " + ExternalRead + " : Int;   // Index for Device");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR_TEMP ");
        ExternalSourceFile.append("      retValLed : Int;");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("   VAR CONSTANT ");
        ExternalSourceFile.append("      ERROR_LED : UInt := 2;   // Identification number of the ERROR LED");
        ExternalSourceFile.append("      ERROR_LED_ON : UInt := 4;   // LED status Color 1 flashing");
        ExternalSourceFile.append("   END_VAR");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Basic diagnostic function that has to be called in every cycle");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// check error active");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	#retValLed := LED(LADDR := \"Local~Common\", LED := #ERROR_LED);");
        ExternalSourceFile.append("	IF #retValLed = #ERROR_LED_ON");
        ExternalSourceFile.append("	THEN");
        ExternalSourceFile.append("	    #plc.errorState := TRUE;");
        ExternalSourceFile.append("	ELSE");
        ExternalSourceFile.append("	    #plc.errorState := FALSE;");
        ExternalSourceFile.append("	END_IF;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	// check error in IO systems active");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	FOR #statIoSystemIndex := 1 TO "+str(self.MAX_IO_SYSTEM)+" DO");
        ExternalSourceFile.append("	    #ioSystem[#statIoSystemIndex].ioSystemError := FALSE;");
        ExternalSourceFile.append("	    ");
        ExternalSourceFile.append("	    FOR #statDeviceIndex := 1 TO "+str(self._MAX_IO_DEVICES)+" DO");
        ExternalSourceFile.append("	        IF (#ioSystem[#statIoSystemIndex].device[#statDeviceIndex].error = TRUE)");
        ExternalSourceFile.append("	        THEN");
        ExternalSourceFile.append("	            #ioSystem[#statIoSystemIndex].ioSystemError := TRUE;");
        ExternalSourceFile.append("	        END_IF;");
        ExternalSourceFile.append("	    END_FOR;");
        ExternalSourceFile.append("	END_FOR;");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_FUNCTION_BLOCK");
        ExternalSourceFile.append("");


    def __Diagnostics_iDB(self, TIAVersion, ExternalSourceFile):
        #Diagnostics_iDB instance DB
        ExternalSourceFile.append("DATA_BLOCK \"Diagnostics_iDB\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("NON_RETAIN");
        ExternalSourceFile.append("\"Diagnostics\"");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("END_DATA_BLOCK");
        ExternalSourceFile.append("");


    def __CyclicDiagnostics(self,  TIAVersion, ExternalSourceFile):
        #CyclicDiagnostics program cycle OB
        ExternalSourceFile.append("ORGANIZATION_BLOCK \"CyclicDiagnostics\"");
        ExternalSourceFile.append("TITLE = \"Main Program Sweep (Cycle)\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Main Cycle OB for diagnostics ");
        ExternalSourceFile.append("	//               OB type: Program cycle");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29-08-2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	\"Diagnostics_iDB\"(plc:=\"DiagnosticsData\".plc,");
        ExternalSourceFile.append("	                  ioSystem:=\"DiagnosticsData\".ioSystem);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_ORGANIZATION_BLOCK");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("");


    def __Diagnostic_error_interrupt(self, TIAVersion, ExternalSourceFile):
        #Diagnostic error interrupt OB
        ExternalSourceFile.append("ORGANIZATION_BLOCK \"Diagnostic error interrupt\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Diagnostics Error Interrupt OB");
        ExternalSourceFile.append("	//               OB type: Diagnostic Interrupt");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29-08-2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	\"DiagnosticError\"(ioState:=#IO_State,");
        ExternalSourceFile.append("	                  laddr:=#LADDR,");
        ExternalSourceFile.append("	                  channel:=#Channel,");
        ExternalSourceFile.append("	                  multiError:=#MultiError,");
        ExternalSourceFile.append("	                  plc:=\"DiagnosticsData\".plc,");
        ExternalSourceFile.append("	                  ioSystem:=\"DiagnosticsData\".ioSystem);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_ORGANIZATION_BLOCK");
        ExternalSourceFile.append("");


    def __Pull_or_plug_of_modules(self, TIAVersion, ExternalSourceFile):
        #Pull or plug of modules OB
        ExternalSourceFile.append("ORGANIZATION_BLOCK \"Pull or plug of modules\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Pull or Plug of mudules OB");
        ExternalSourceFile.append("	//               OB type: Pull or Plug of devices");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29-08-2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	\"PullOrPlugModules\"(laddr:=#LADDR,");
        ExternalSourceFile.append("	                    eventClass:=#Event_Class,");
        ExternalSourceFile.append("	                    faultId:=#Fault_ID,");
        ExternalSourceFile.append("	                    plc:=\"DiagnosticsData\".plc,");
        ExternalSourceFile.append("	                    ioSystem:=\"DiagnosticsData\".ioSystem);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_ORGANIZATION_BLOCK");
        ExternalSourceFile.append("");


    def __Rack_of_station_failure(self, TIAVersion, ExternalSourceFile):
        #Rack or station failure OB
        ExternalSourceFile.append("ORGANIZATION_BLOCK \"Rack or station failure\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality: Rack or Station faliure OB");
        ExternalSourceFile.append("	//               OB type: Rack or station failure");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code");
        ExternalSourceFile.append("	//        DON'T CHANGE THIS BLOCK MANUALY. Any changes will be overwritten in the next code generation.");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29-08-2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	\"RackOrStationFaliure\"(laddr:=#LADDR,");
        ExternalSourceFile.append("	                       eventClass:=#Event_Class,");
        ExternalSourceFile.append("	                       faultId:=#Fault_ID,");
        ExternalSourceFile.append("	                       plc:=\"DiagnosticsData\".plc,");
        ExternalSourceFile.append("	                       ioSystem:=\"DiagnosticsData\".ioSystem);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_ORGANIZATION_BLOCK");
        ExternalSourceFile.append("");


    def __Startup(self, TIAVersion, ExternalSourceFile):
        #Startup Complete Restart OB
        ExternalSourceFile.append("ORGANIZATION_BLOCK \"Startup\"");
        ExternalSourceFile.append("TITLE = \"Complete Restart\"");
        ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }");
        ExternalSourceFile.append("VERSION : 0.1");
        ExternalSourceFile.append("");
        ExternalSourceFile.append("BEGIN");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	//Author: SIEMENS, Owner: Miklos Boros");
        ExternalSourceFile.append("	//        email: borosmiklos@gmail.com; miklos.boros@esss.se");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Functionality:");
        ExternalSourceFile.append("	//        This OB is a Startup OB, it will be called after OB100 and before the main cycle.");
        ExternalSourceFile.append("	// ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Please Note:");
        ExternalSourceFile.append("	//        This block is part of the generated ESS Standard Code however you should use ");
        ExternalSourceFile.append("	//        the proper ioSystem ID from the ");
        ExternalSourceFile.append("	//");
        ExternalSourceFile.append("	//Change log table:");
        ExternalSourceFile.append("	//Version  Date         Expert in charge      Changes applied");
        ExternalSourceFile.append("	//01.00.00 29.08.2017   ESS/ICS               First released version for PLCFactory ");
        ExternalSourceFile.append("	//02.00.00 09-04-2018   ESS/ICS               Major bug fix for PN/DP devices");
        ExternalSourceFile.append("	//=============================================================================");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//Initialize the Main PLC Diagnostic");
        ExternalSourceFile.append("	\"DiagStartupPlc_iDB\"(plc:=\"DiagnosticsData\".plc);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	//Put your current IO device configuration here. HW identifiers are in the PLC Tags/System constants!");
        ExternalSourceFile.append("	//Initialize IOSystem1");
        ExternalSourceFile.append("	//\"DiagStartupIoSystem_iDB\"(ioSystemHwId:=268,");
        ExternalSourceFile.append("	//                          ioSystem:=\"DiagnosticsData\".ioSystem[1]);");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("	");
        ExternalSourceFile.append("END_ORGANIZATION_BLOCK");
        ExternalSourceFile.append("");


    def _WriteDiagnostics(self, TIAVersion, ExternalSourceFile):
        self.__DiagnosticsData(TIAVersion, ExternalSourceFile)
        self.__DiagStartupIoSystem(TIAVersion, ExternalSourceFile)
        self.__DiagStartupIoSystem_iDB(TIAVersion, ExternalSourceFile)
        self.__DiagStartupPlc(TIAVersion, ExternalSourceFile)
        self.__DiagStartupPlc_iDB(TIAVersion, ExternalSourceFile)
        self.__DiagnosticError(TIAVersion, ExternalSourceFile)
        self.__PullOrPlugModules(TIAVersion, ExternalSourceFile)
        self.__RackOrStationFailure(TIAVersion, ExternalSourceFile)
        self.__Diagnostics(TIAVersion, ExternalSourceFile)
        self.__Diagnostics_iDB(TIAVersion, ExternalSourceFile)
        self.__CyclicDiagnostics(TIAVersion, ExternalSourceFile)
        self.__Diagnostic_error_interrupt(TIAVersion, ExternalSourceFile)
        self.__Pull_or_plug_of_modules(TIAVersion, ExternalSourceFile)
        self.__Rack_of_station_failure(TIAVersion, ExternalSourceFile)
        if not self._Skip_Startup_OB:
            self.__Startup(TIAVersion, ExternalSourceFile)


    @staticmethod
    def WriteDiagnostics(TIAVersion, ExternalSourceFile, ifa):
        diag = Diagnostics(MAX_IO_DEVICES = ifa.MAX_IO_DEVICES, MAX_LOCAL_MODULES = ifa.MAX_LOCAL_MODULES, MAX_MODULES_IN_IO_DEVICE = ifa.MAX_MODULES_IN_IO_DEVICE)
        diag._WriteDiagnostics(TIAVersion, ExternalSourceFile)


    @staticmethod
    def process(TIAVersion, OutputDir = ".", MAX_IO_DEVICES = 1, MAX_LOCAL_MODULES = 30, MAX_MODULES_IN_IO_DEVICE = 30, Skip_Startup_OB = False):
        #Write the output to file
        externalPath = os.path.join(OutputDir, "PLCFactory_diagnostics_source_TIAv{tiaversion}.scl".format(tiaversion = TIAVersion))
        ExternalSourceFile = []
        with open(externalPath, 'wb') as externalScl:
            diag = Diagnostics(MAX_IO_DEVICES = MAX_IO_DEVICES, MAX_LOCAL_MODULES = MAX_LOCAL_MODULES, MAX_MODULES_IN_IO_DEVICE = MAX_MODULES_IN_IO_DEVICE, Skip_Startup_OB = Skip_Startup_OB)
            diag._WriteDiagnostics(TIAVersion, ExternalSourceFile)
            for line in ExternalSourceFile:
                externalScl.write((line + '\r\n').encode())


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
                        '--tia-version',
                        dest    = "TIAVersion",
                        help    = 'The TIA Portal version to use. The default is TIAv14',
                        metavar = 'TIA-Portal-version',
                        default = 'TIAv14',
                        type    = str
                       )
    parser.add_argument(
                        '--max-io-devices',
                        dest    = "MAX_IO_DEVICES",
                        default = 1
                       )
    parser.add_argument(
                        '--max-local-modules',
                        dest    = "MAX_LOCAL_MODULES",
                        default = 30
                       )
    parser.add_argument(
                        '--max-modules-in-io-device',
                        dest    = "MAX_MODULES_IN_IO_DEVICE",
                        default = 30
                       )
    parser.add_argument(
                        '--skip-startup-ob',
                        dest    = "Skip_Startup_OB",
                        help    = "Do not generate Startup OB; useful if you don't want to overwrite your changes",
                        action  = 'store_true'
                       )

    def consolidate_tia_version(tia_version):
        if tia_version is not None and isinstance(tia_version, str):
            tia13 = set({"13", "v13", "tia13", "tiav13"})
            tia14 = set({"14", "v14", "tia14", "tiav14"})
            tia15 = set({"15", "v15", "tia15", "tiav15"})
            tia17 = set({"17", "v17", "tia17", "tiav17"})
            tia18 = set({"18", "v18", "tia18", "tiav18"})

            tia_version = tia_version.lower()
            if tia_version in tia13:
                tia_version = 13
            elif tia_version in tia14:
                tia_version = 14
            elif tia_version in tia15:
                tia_version = 15
            elif tia_version in tia17:
                tia_version = 17            
            elif tia_version in tia18:
                tia_version = 18
            else:
                raise RuntimeError(1, "Invalid TIA version: " + tia_version)

        return tia_version

    args = parser.parse_args(argv)
    Diagnostics.process(consolidate_tia_version(args.TIAVersion), MAX_IO_DEVICES = args.MAX_IO_DEVICES, MAX_LOCAL_MODULES = args.MAX_LOCAL_MODULES, MAX_MODULES_IN_IO_DEVICE = args.MAX_MODULES_IN_IO_DEVICE, Skip_Startup_OB = args.Skip_Startup_OB)



if __name__ == "__main__":
    main(sys.argv[1:])
