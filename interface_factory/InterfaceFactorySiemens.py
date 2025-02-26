from __future__ import print_function
from __future__ import absolute_import

""" InterfaceFactory : Entry point """

__author__     = "Miklos Boros"
__copyright__  = "Copyright 2017-2020, European Spallation Source, Lund"
__credits__    = [ "Krisztian Loki"
				, "Miklos Boros"
				, "Francois Bellorini"
				]
__license__    = "GPLv3"
__maintainer__ = "Miklos Boros"
__email__      = "miklos.boros@esss.se; borosmiklos@gmail.com"
__status__     = "Production"
__env__        = "Python version 2.7"

# Python libraries
import os
import sys

# IFA modules
from . import IFA



#Global variables
ifa       = None
verify    = False
CommsTest = False
ExternalSourceFile = []

_NoExternal      = "ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False';"
_ExternalRead    = "ExternalAccessible := 'True'; ExternalVisible := 'False'; ExternalWritable := 'False';"
#_NoExternal      = "S7_HMI_Accessible := 'False'; S7_HMI_Visible := 'False';"
NoExternal       = "{ " + _NoExternal + " }"
ExternalRead     = "{ " + _ExternalRead + " }"

DeviceTypeList = []

DevTypeHeader = []
DevTypeVAR_INPUT = []
DevTypeVAR_INOUT = []
DevTypeVAR_OUTPUT = []
DevTypeDB_SPEC = []
DevTypeVAR_TEMP = []
DevTypeBODY_HEADER = []
DevTypeBODY_CODE = []
DevTypeBODY_CODE_ARRAY = []
DevTypeBODY_END = []

EPICS_PLC_TesterDB = []

EPICS_device_calls_test_body = []
EPICS_device_calls_test_header = []

DeviceInstance = []

EndString = ""
EndString2 = ""
IsDouble = False

MaxStatusReg = 0
MaxCommandReg = 0



def CloseLastVariable():
	global DevTypeBODY_CODE
	global EndString
	global EndString2
	global IsDouble

	if IsDouble:
		if EndString != "":
			DevTypeBODY_CODE.append("       " + EndString)
			EndString = ""
		if EndString2 != "":
			DevTypeBODY_CODE.append("       " + EndString2)
			EndString2 = ""
	else:
		if EndString != "":
			DevTypeBODY_CODE.append("       " + EndString)
			EndString = ""


def ClearCmd(body, clear_cmd):
	if not isinstance(clear_cmd, list):
		clear_cmd = [ clear_cmd ]
	if CommsTest:
		body.append("       IF (NOT \"Utilities\".TestInProgress) THEN")
		for l in clear_cmd:
			body.append(l.format("	"))
		body.append("       END_IF;")
	else:
		for l in clear_cmd:
			body.append(l.format(""))


def IsInGatewayDatablock(variable):
	try:
		if ifa.GATEWAY_DATABLOCK is None or variable.properties["NO_GATEWAY"]:
			return False
	except KeyError:
		# ifa.GATEWAY_DATABLOCK always exists but variable.properties["NO_GATEWAY"] does not
		#  so if we get a KeyError it means that 'ifa.GATEWAY_DATABLOCK is not None' AND there is no 'NO_GATEWAY'
		# which means that this variable is definitely in a a gateway datablock
		pass

	return True


def GetPLCVariableName(variable, in_array = None):
	# InArrayName should be passed as in_array; when copying from "remote" arrays into local arrays GetPLCVariableName() MUST NOT return the gateway datablock prefix
	plc_var = variable.name()
	if in_array is None and IsInGatewayDatablock(variable):
		return '{}."{}"'.format(ifa.GATEWAY_DATABLOCK, plc_var)
	else:
		return '#"{}"'.format(plc_var)


def AddBOOL(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== BOOL TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyWord := W#0;")
		if ActVariableBitNumber < 8:
			DevTypeBODY_CODE.append("       #MyBoolsinWord[" + str((int(ActVariableBitNumber)+8)) + "] := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWord;"
		else:
			DevTypeBODY_CODE.append("       #MyBoolsinWord[" + str((int(ActVariableBitNumber)-8)) + "] := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWord;"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyWord := \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"];")
			if variable.is_command():
				clear_cmd = "       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"] := 0;"
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
		if ActVariableBitNumber < 8:
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyBoolsinWord[" + str((int(ActVariableBitNumber)+8)) + "];    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = ""
		else:
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyBoolsinWord[" + str((int(ActVariableBitNumber)-8)) + "];    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = ""
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddBYTE(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== BYTE TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyWord := W#0;")
		if ActVariableBitNumber == 0:
			DevTypeBODY_CODE.append("       #MyBytesinWord[0] := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWord;"
		else:
			DevTypeBODY_CODE.append("       #MyBytesinWord[1] := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWord;"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyWord := \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"];")
			if variable.is_command():
				clear_cmd = "       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"] := 0;"
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
		if ActVariableBitNumber == 0:
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyBytesinWord[1];    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = ""
		else:
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyBytesinWord[0];    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = ""
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddINT(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== INT TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyInt := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
		if ActVariableBitNumber == 0:
			IsDouble = False
			EndString = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWordinInt;"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyWordinInt := \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"];")
			if variable.is_command():
				clear_cmd = "       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"] := 0;"
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyInt;    //EPICSName: "+ActVariableEPICSName)
			IsDouble = False
			EndString = ""
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddWORD(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== WORD TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyWord := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
		if ActVariableBitNumber == 0:
			IsDouble = False
			EndString = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWord;"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"];    //EPICSName: "+ActVariableEPICSName)
			if variable.is_command():
				clear_cmd = "        {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"] := 0;"
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
			IsDouble = False
			EndString = ""
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddDINT(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== DINT TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyDInt := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
		if ActVariableBitNumber == 0:
			IsDouble = True
			EndString  = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWordsinDint[0];"
			EndString2 = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex+1) +"] := #MyWordsinDint[1];"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyDInt	:= 0;")
			DevTypeBODY_CODE.append("       #MyWordsinDint[0]	:= \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"];")
			DevTypeBODY_CODE.append("       #MyWordsinDint[1]	:= \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex+1) +"];")
			if variable.is_command():
				clear_cmd = ["       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"] := 0;",
				             "       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex+1) +"] := 0;"]
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyDInt;    //EPICSName: "+ActVariableEPICSName)
			IsDouble = True
			EndString = ""
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddDWORD(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== DWORD TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyDWord := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
		if ActVariableBitNumber == 0:
			IsDouble = True
			EndString  = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWordsinDWord[0];"
			EndString2 = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex+1) +"] := #MyWordsinDWord[1];"
	elif variable.is_input():
		raise IFA.FatalException("DWORD is not supported for ModbusTCP")
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddREAL(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== REAL TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyReal := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
		if ActVariableBitNumber == 0:
			IsDouble = True
			EndString  = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWordsinReal[0];"
			EndString2 = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex+1) +"] := #MyWordsinReal[1];"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyReal	:= 0.0;")
			DevTypeBODY_CODE.append("       #MyWordsinReal[0]	:= \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"];")
			DevTypeBODY_CODE.append("       #MyWordsinReal[1]	:= \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex+1) +"];")
			if variable.is_command():
				clear_cmd = ["       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"] := 0;",
				             "       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex+1) +"] := 0;"]
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyReal;    //EPICSName: "+ActVariableEPICSName)
			IsDouble = True
			EndString = ""
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddTIME(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== TIME TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyTime := "+ ActVariablePLCName +";    //EPICSName: "+ActVariableEPICSName)
		if ActVariableBitNumber == 0:
			IsDouble = True
			EndString  = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex) +"] := #MyWordsinTime[0];"
			EndString2 = "\"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + "+str(ActVariableArrayIndex+1) +"] := #MyWordsinTime[1];"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       #MyTime	:= T#0" + variable.properties["EGU"] + ";")
			DevTypeBODY_CODE.append("       #MyWordsinTime[0]	:= \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"];")
			DevTypeBODY_CODE.append("       #MyWordsinTime[1]	:= \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex+1) +"];")
			if variable.is_command():
				clear_cmd = ["       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex) +"] := 0;",
				             "       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + "+str(ActVariableArrayIndex+1) +"] := 0;"]
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyTime;    //EPICSName: "+ActVariableEPICSName)
			IsDouble = True
			EndString = ""
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def AddSTRING(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== STRING TYPE ========
	ActVariablePLCName    = GetPLCVariableName(variable, InArrayName)
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])
	ActStringLength       = variable.dimension() // 2 + (variable.dimension() % 2)

	if variable.is_output():
		if InArrayName is not None:
			raise IFA.FatalException("'Hybrid' PLC STRING arrays are not supported: " + InArrayName)
			# The fact that ActVariablePLCName is IN_OUT (because of the TESTER) triggers an error because ActVariablePLCName is not specified in EPICS_device_calls
			DevTypeBODY_CODE_ARRAY.append("              "+ ActVariablePLCName +" := "+InArrayName+"["+str(InArrayNum)+"];")
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			# This clearing is also essential to have a terminating zero in place in case the string is shorter than the allowed maximum
			DevTypeBODY_CODE.append("       // Clear the buffer of any residual data, but skip the first word as that is the actual and maximum length")
			DevTypeBODY_CODE.append("       FOR #i:=1 TO 20 DO")
			DevTypeBODY_CODE.append("            #MyWordsinString[#i] := 0;")
			DevTypeBODY_CODE.append("       END_FOR;")
			DevTypeBODY_CODE.append("       #MyString := " + ActVariablePLCName + ";  //EPICSName: " + ActVariableEPICSName)
			if ActStringLength > 1:
				DevTypeBODY_CODE.append("       FOR #i:=0 TO " + str(ActStringLength - 2) + " DO")
				DevTypeBODY_CODE.append("            \"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + " + str(ActVariableArrayIndex) + " + #i] := #MyWordsinString[#i + 1];")
				DevTypeBODY_CODE.append("       END_FOR;")
			DevTypeBODY_CODE.append("       // Terminate C-string")
			if variable.dimension() % 2:
				DevTypeBODY_CODE.append("       \"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + " + str(ActVariableArrayIndex) + " + " + str(ActStringLength - 1) + "] := 0;")
			else:
				DevTypeBODY_CODE.append("       \"PLCToEPICS\".\"Word\"[#PLCToEPICSDataBlockOffset + " + str(ActVariableArrayIndex) + " + " + str(ActStringLength - 1) + "] := #MyWordsinString[" + str(ActStringLength) + "] & 16#FF00;")
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			if ActStringLength > 0:
				DevTypeBODY_CODE.append("       #i := 0;")
				DevTypeBODY_CODE.append("       WHILE TRUE DO")
				DevTypeBODY_CODE.append("            IF #i = 20 THEN")
				DevTypeBODY_CODE.append("                 #i := 39;")
				DevTypeBODY_CODE.append("                 EXIT;")
				DevTypeBODY_CODE.append("            END_IF;")
				DevTypeBODY_CODE.append("            #MyWordsinString[#i + 1] := \"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + " + str(ActVariableArrayIndex) + " + #i];")
				DevTypeBODY_CODE.append("            //Check if there is a terminating zero and store the string length in bytes")
				DevTypeBODY_CODE.append("            IF (#MyWordsinString[#i + 1] & 16#FF00) = 0 THEN")
				DevTypeBODY_CODE.append("                 #i := #i * 2;")
				DevTypeBODY_CODE.append("                 EXIT;")
				DevTypeBODY_CODE.append("            ELSIF (#MyWordsinString[#i + 1] & 16#00FF) = 0 THEN")
				DevTypeBODY_CODE.append("                 #i := #i * 2 + 1;")
				DevTypeBODY_CODE.append("                 EXIT;")
				DevTypeBODY_CODE.append("            END_IF;")
				DevTypeBODY_CODE.append("            #i := #i + 1;")
				DevTypeBODY_CODE.append("       END_WHILE;")
			DevTypeBODY_CODE.append("       // Set the length of #MyString")
			DevTypeBODY_CODE.append("       #MyWordsinString[0] := (#MyWordsinString[0] & 16#FF00) OR #i;")
			if variable.is_command():
				clear_cmd = "       {}\"EPICSToPLC\".\"Word\"[#EPICSToPLCDataBlockOffset + " + str(ActVariableArrayIndex) + "] := 0;"
				ClearCmd(DevTypeBODY_CODE, clear_cmd)
			DevTypeBODY_CODE.append("       "+ ActVariablePLCName +" := #MyString;    //EPICSName: "+ActVariableEPICSName)
	else:
		raise IFA.FatalException("Neither input nor output: {}".format(variable))

	return (InArrayNum, StartingRegister)


def WriteDevType():

	global DevTypeHeader
	global DevTypeVAR_INPUT
	global DevTypeVAR_OUTPUT
	global DevTypeVAR_INOUT
	global DevTypeDB_SPEC
	global DevTypeVAR_TEMP
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global DevTypeBODY_END
	global ExternalSourceFile

	global MaxStatusReg
	global MaxCommandReg

	ExternalSourceFile.extend(DevTypeHeader)

	ExternalSourceFile.append("   VAR_INPUT")
	ExternalSourceFile.extend(DevTypeVAR_INPUT)
	ExternalSourceFile.append("   EPICSToPLCLength " + NoExternal + " : Int;   // Length of device command register array (in words)")
	ExternalSourceFile.append("   EPICSToPLCDataBlockOffset " + NoExternal + " : Int;   // Offset in EPICS->PLC comms block where this device data resides (in words)")
	ExternalSourceFile.append("   PLCToEPICSLength " + NoExternal + " : Int;   // Length of device status register array (in words)")
	ExternalSourceFile.append("   PLCToEPICSDataBlockOffset " + NoExternal + " : Int;   // Offset in PLC->EPICS comms block where this device data resides (in words)")
	ExternalSourceFile.append("   END_VAR")

	ExternalSourceFile.append("   VAR_OUTPUT")
	ExternalSourceFile.extend(DevTypeVAR_OUTPUT)
	ExternalSourceFile.append("      DEVICE_PARAM_OK " + NoExternal + " : Bool;")
	ExternalSourceFile.append("   END_VAR")

	ExternalSourceFile.append("   VAR_IN_OUT")
	ExternalSourceFile.extend(DevTypeVAR_INOUT)
	ExternalSourceFile.append("   END_VAR")

	ExternalSourceFile.extend(DevTypeDB_SPEC)

	ExternalSourceFile.extend(DevTypeVAR_TEMP)

	ExternalSourceFile.extend(DevTypeBODY_HEADER)

	if DevTypeBODY_CODE_ARRAY != []:
		ExternalSourceFile.append("        IF \"Utilities\".TestInProgress = FALSE THEN")
	ExternalSourceFile.extend(DevTypeBODY_CODE_ARRAY)
	if DevTypeBODY_CODE_ARRAY != []:
		ExternalSourceFile.append("        END_IF;")

	ExternalSourceFile.extend(DevTypeBODY_CODE)

	ExternalSourceFile.extend(DevTypeBODY_END)

	DevTypeHeader = []
	DevTypeVAR_INPUT = []
	DevTypeVAR_INOUT = []
	DevTypeVAR_OUTPUT = []
	DevTypeDB_SPEC = []
	DevTypeVAR_TEMP = []
	DevTypeBODY_HEADER = []
	DevTypeBODY_CODE = []
	DevTypeBODY_CODE_ARRAY = []
	DevTypeBODY_END = []

def WriteEPICS_PLC_TesterDB():

	global EPICS_PLC_TesterDB
	global ExternalSourceFile

	ExternalSourceFile.append("DATA_BLOCK \"EPICS_PLC_Tester\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("   STRUCT")
	ExternalSourceFile.append("      HeartBeat " + NoExternal + " : Bool;")

	ExternalSourceFile.extend(EPICS_PLC_TesterDB)

	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("END_DATA_BLOCK")

	EPICS_PLC_TesterDB = []


def WriteDeviceInstances():

	global DeviceInstance
	global ExternalSourceFile

	ExternalSourceFile.extend(DeviceInstance)

	DeviceInstance = []

def WriteEPICS_Debugger(for_standard = False):

	global ExternalSourceFile

	ExternalSourceFile.append("DATA_BLOCK \"EPICS_DebuggerResult\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      EPICS_Debugger_UtilitiesCall : String;   // PLCFactory Utilities call status")
	ExternalSourceFile.append("      EPICS_Debugger_DeviceCalls : String;   // PLCFactory DeviceCalls status")
	ExternalSourceFile.append("      EPICS_Debugger_IOCHash : String;   // EPICS IOC Hash vs. PLCFactory Hash")
	ExternalSourceFile.append("      EPICS_Debugger_ModBusHeartBeat : String;   // EPICS IOC Modbus (IOC->PLC) communication status")
	ExternalSourceFile.append("      EPICS_Debugger_S7Connection : String;   // EPICS IOC S7 TCP (PLC->IOC) communication status")
	ExternalSourceFile.append("      EPICS_Debugger_EPICS_GeneralState : String;   // Main status of the EPICS IOC communication")
	ExternalSourceFile.append("      EPICS_S7Port : Int;   // Actual TCP port that has been opened by the PLC")
	ExternalSourceFile.append("      EPICS_ModbusPort : Int;   // Actual ModBusTCP port that has been opened by the PLC")
	ExternalSourceFile.append("      EPICS_PLC_EthernetInterface : UInt;   // The currently used HW Identifer of the Ethernet Port on the PLC dedicated to EPICS")
	ExternalSourceFile.append("      EPICS_PayloadSize_InBytes : UInt;   // The currently configured payload size in bytes")
	ExternalSourceFile.append("      EPICS_PLC_Hash : DInt;   // The PLC Hash")
	ExternalSourceFile.append("      EPICS_PLCFactory_Version : String;   // The PLCFactory version that was used to generate the PLC code")
	ExternalSourceFile.append("      EPICS_CommunicationOK : Bool;   // Overall EPICS communication is OK")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("FUNCTION_BLOCK \"EPICS_DebuggerFB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      CheckUtilitiesTON {OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'; ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : TON_TIME;")
	ExternalSourceFile.append("      UtilSquareErrorTON { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;")
	ExternalSourceFile.append("      CheckUtilitiesTON2 {OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'; ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : TON_TIME;")
	ExternalSourceFile.append("      UtilSquareErrorTON2 { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;")
	ExternalSourceFile.append("      ModBus_TON {OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'; ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : TON_TIME;")
	ExternalSourceFile.append("      ModBus_wordsave { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Word;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("   VAR DB_SPECIFIC")
	ExternalSourceFile.append("      Helper_String { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : String;")
	ExternalSourceFile.append("      Helper_String_Array { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} AT Helper_String : Struct")
	ExternalSourceFile.append("         String_Maximal { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Byte;")
	ExternalSourceFile.append("         String_Actual { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Byte;")
	ExternalSourceFile.append("         StringValueArray { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Array[0..15] of Byte;")
	ExternalSourceFile.append("      END_STRUCT;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      S7ConnTON {OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'; ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : TON_TIME;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP ")
	ExternalSourceFile.append("      AllOK { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;")
	ExternalSourceFile.append("      i : Int;")
	ExternalSourceFile.append("      ModBusOK : Bool;")
	ExternalSourceFile.append("      S7OK : Bool;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2020 by European Spallation Source, Lund")
	ExternalSourceFile.append("	//This block was generated by PLCFactory")
	ExternalSourceFile.append("	//Description: This FB checks the EPICS configuration and outputs the result into EPICS_DebuggerResult.")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//DO NOT Modify this block!!!")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//AllOK will be evaluated in this code and passed to the EPICS_CommunicationOK signal that can be used by the PLC logic")
	ExternalSourceFile.append("	#AllOK := TRUE;")

	ExternalSourceFile.append("")
	ExternalSourceFile.append("	#CheckUtilitiesTON(IN:=\"Utilities\".Square_100ms,")
	ExternalSourceFile.append("	                   PT:=T#200ms,")
	ExternalSourceFile.append("	                   Q=>#UtilSquareErrorTON);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	#CheckUtilitiesTON2(IN := NOT \"Utilities\".Square_100ms,")
	ExternalSourceFile.append("	                   PT := T#200ms,")
	ExternalSourceFile.append("	                   Q => #UtilSquareErrorTON2);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	#ModBus_TON(IN := #ModBus_wordsave = \"EPICSToPLC\".\"Word\"[{}],".format(IFA.EPICSTOPLC_HEARTBEAT))
	ExternalSourceFile.append("	            PT := T#5s);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("     \"EPICS_DebuggerResult\".#EPICS_PayloadSize_InBytes := {};".format(10 if for_standard else ifa.TOTALPLCTOEPICSLENGTH * 2))
	ExternalSourceFile.append("     \"EPICS_DebuggerResult\".#EPICS_PLC_Hash := {};".format(0 if for_standard else ifa.HASH))
	ExternalSourceFile.append("     \"EPICS_DebuggerResult\".#EPICS_PLCFactory_Version := '{}';".format(ifa.commit_id if not verify else ""))
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF (\"Utilities\".AlwaysOn = FALSE) THEN")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".#EPICS_Debugger_UtilitiesCall := 'ERROR: FunctionBlock: \"_UilitiesFB\" is called with a wrong InstanceDB. Call it with the existing iDB named: \"Utilities\" AND check if the System Memory bits and the System Clock byte is enabled!';")
	ExternalSourceFile.append("         #AllOK := FALSE;")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    IF (#UtilSquareErrorTON OR #UtilSquareErrorTON2) THEN")
	ExternalSourceFile.append("	        \"EPICS_DebuggerResult\".#EPICS_Debugger_UtilitiesCall := 'ERROR: FunctionBlock: \"_UilitiesFB\" is called with a wrong InstanceDB. Call it with the existing iDB named: \"Utilities\" AND check if the System Memory bits and the System Clock byte is enabled!';")
	ExternalSourceFile.append("             #AllOK := FALSE;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        \"EPICS_DebuggerResult\".#EPICS_Debugger_UtilitiesCall := 'OK: EPICS Utilities works as expected.';")
	ExternalSourceFile.append("	        ")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	IF (\"Utilities\".EPICS_Device_calls_precessed) THEN")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".#EPICS_Debugger_DeviceCalls := 'OK: \"EPICS_device_calls\" is called as expected.';")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".#EPICS_Debugger_DeviceCalls := 'ERROR: \"EPICS_device_calls\" is not called in OB1!';")
	ExternalSourceFile.append("         #AllOK := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	IF ((\"EPICSToPLC\".\"Word\"[{e2ph1}] = \"PLCToEPICS\".\"Word\"[{p2eh1}]) AND (\"EPICSToPLC\".\"Word\"[{e2ph2}] = \"PLCToEPICS\".\"Word\"[{p2eh2}])) THEN".format(e2ph1 = IFA.EPICSTOPLC_HASH,
e2ph2 = IFA.EPICSTOPLC_HASH + 1,
p2eh1 = IFA.PLCTOEPICS_HASH,
p2eh2 = IFA.PLCTOEPICS_HASH + 1))
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".#EPICS_Debugger_IOCHash := 'OK: IOC and PLC hash are equal.';")
	ExternalSourceFile.append("	ELSE    ")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".#EPICS_Debugger_IOCHash := 'ERROR: IOC and PLC hash are NOT equal!';")
	ExternalSourceFile.append("         #AllOK := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF (#ModBus_TON.Q) THEN")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".#EPICS_Debugger_ModBusHeartBeat := 'ERROR: The IOC is not sending any HeartBeat via ModBus!';")
	ExternalSourceFile.append("         #AllOK := FALSE;")
	ExternalSourceFile.append("	    #ModBusOK := FALSE;")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".#EPICS_Debugger_ModBusHeartBeat := 'OK: ModBus HeartBeat is received as expected.';")
	ExternalSourceFile.append("	    #ModBusOK := TRUE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	#S7ConnTON(IN := NOT \"_CommsPLC_EPICS_DB\".SendDone, PT := T#3s);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF (\"_CommsPLC_EPICS_DB\".BytesToSend > 0) THEN")
	ExternalSourceFile.append("	    ")
	ExternalSourceFile.append("	    IF (#S7ConnTON.Q) THEN")
	ExternalSourceFile.append("	        \"EPICS_DebuggerResult\".EPICS_Debugger_S7Connection := 'ERROR: EPICS S7 connection can not send Status variables!';")
	ExternalSourceFile.append("	        #S7OK := FALSE;")
	ExternalSourceFile.append("             #AllOK := FALSE;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        \"EPICS_DebuggerResult\".EPICS_Debugger_S7Connection := 'OK: EPICS S7 works as expected.';")
	ExternalSourceFile.append("	        #S7OK := TRUE;")
	ExternalSourceFile.append("	        ")
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	ELSE")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".EPICS_Debugger_S7Connection := 'OK: EPICS S7 disabled, there is no Status variable to send.';")
	ExternalSourceFile.append("	    #S7OK := TRUE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF (#ModBusOK AND #S7OK) THEN")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".EPICS_Debugger_EPICS_GeneralState := 'OK. EPICS IOC communication is ONLINE.';")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF (#ModBusOK AND NOT #S7OK) THEN")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".EPICS_Debugger_EPICS_GeneralState := 'ERROR. ModBus seems to be working but S7 TCP is blocked. Try to check your PLC router IP.';")
	ExternalSourceFile.append("         #AllOK := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF (NOT #ModBusOK AND #S7OK) THEN")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".EPICS_Debugger_EPICS_GeneralState := 'ERROR. ModBus seems to be offline. Waiting for IOC to finish connecting to the PLC.';")
	ExternalSourceFile.append("         #AllOK := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF ( NOT #ModBusOK AND NOT #S7OK) THEN")
	ExternalSourceFile.append("	    \"EPICS_DebuggerResult\".EPICS_Debugger_EPICS_GeneralState := 'ERROR. Both ModBus and S7 TCP seems to be offline. Check if your IOC is running and if it is connected to the right PLC interface. Your HardwareID comes from CCDB!';")
	ExternalSourceFile.append("         #AllOK := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	\"EPICS_DebuggerResult\".EPICS_ModbusPort := \"_CommsPLC_EPICS_DB\".MBPort;")
	ExternalSourceFile.append("	\"EPICS_DebuggerResult\".EPICS_S7Port := \"_CommsPLC_EPICS_DB\".S7Port;")
	ExternalSourceFile.append("	\"EPICS_DebuggerResult\".EPICS_PLC_EthernetInterface :=  \"_CommsPLC_EPICS_DB\".InterfaceID;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	#ModBus_wordsave := \"EPICSToPLC\".\"Word\"[{}];".format(IFA.EPICSTOPLC_HEARTBEAT))
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Put the Overall result to the Globl DB")
	ExternalSourceFile.append("	\"EPICS_DebuggerResult\".EPICS_CommunicationOK := #AllOK;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"EPICS_DebuggerFB_iDB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"EPICS_DebuggerFB\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("ORGANIZATION_BLOCK \"EPICS_DebuggerOB\"")
	ExternalSourceFile.append("TITLE = \"Main Program Sweep (Cycle)\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2020 by European Spallation Source, Lund")
	ExternalSourceFile.append("	//This block was generated by PLCFactory")
	ExternalSourceFile.append("	//Description: This OB is a cyclic OB called in every PLC cycle and EPICS_DebuggerFB checks the EPICS configuration.")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//DO NOT Modify this block!!!")
	ExternalSourceFile.append("	\"EPICS_DebuggerFB_iDB\"();")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_ORGANIZATION_BLOCK")



def WriteEPICS_device_calls(EPICS_device_calls_header = None, EPICS_device_calls_body = None):

	global ExternalSourceFile

	ExternalSourceFile.append("FUNCTION \"EPICS_device_calls\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 1.0")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP")

	if EPICS_device_calls_header is not None:
		ExternalSourceFile.extend(EPICS_device_calls_header)

	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("      //Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2020 by European Spallation Source, Lund")
	ExternalSourceFile.append("      //This block was generated by PLCFactory")
	if EPICS_device_calls_body is not None:
		ExternalSourceFile.append("      //According to HASH:"+ifa.HASH)
	ExternalSourceFile.append("      //Description: Description: This function calls the devices according to the corresponding device type")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("        //DO NOT Modify the following line!!!")
	ExternalSourceFile.append("        \"Utilities\".TestInProgress := FALSE;")
	ExternalSourceFile.append("        \"Utilities\".EPICS_Device_calls_precessed := TRUE;")
	ExternalSourceFile.append("")

	if EPICS_device_calls_body is not None:
		ExternalSourceFile.extend(EPICS_device_calls_body)

	ExternalSourceFile.append("END_FUNCTION")


def WriteEPICS_device_calls_test():

	global ExternalSourceFile
	global EPICS_device_calls_test_body
	global EPICS_device_calls_test_header

	ExternalSourceFile.append("FUNCTION \"EPICS_device_calls_test\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 1.0")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_TEMP")

	ExternalSourceFile.extend(EPICS_device_calls_test_header)

	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("      //Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2020 by European Spallation Source, Lund")
	ExternalSourceFile.append("      //This block was generated by PLCFactory")
	ExternalSourceFile.append("      //According to HASH:"+ifa.HASH)
	ExternalSourceFile.append("      //Description: Description: This function calls the devices according to the corresponding device type")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("      //DO NOT Modify the following line!!!")
	ExternalSourceFile.append("      \"Utilities\".TestInProgress := TRUE;")
	ExternalSourceFile.append("      \"Utilities\".EPICS_Device_calls_precessed := TRUE;")
	ExternalSourceFile.append("")

	ExternalSourceFile.extend(EPICS_device_calls_test_body)

	ExternalSourceFile.append("END_FUNCTION")

	EPICS_device_calls_test_body = []
	EPICS_device_calls_test_header = []


def WriteUtilitiesCode(TIAVersion):

	global ExternalSourceFile

	ExternalSourceFile.append("FUNCTION_BLOCK \"_UtilitiesFB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      CPUSytemMemoryBits " + NoExternal + " : Byte;   // Address of system memory byte")
	ExternalSourceFile.append("      CPUClockMemoryBits " + NoExternal + " : Byte;   // Address of clock memory byte")
	ExternalSourceFile.append("      StartupDelaySP " + NoExternal + " : Time;   // Delay before startup delay bit turned on")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      AlwaysOn " + NoExternal + " : Bool;   // Bit always TRUE")
	ExternalSourceFile.append("      AlwaysTrue " + NoExternal + " : Bool;   // Bit always TRUE")
	ExternalSourceFile.append("      AlwaysOff " + NoExternal + " : Bool;   // Bit always FALSE")
	ExternalSourceFile.append("      AlwaysFalse " + NoExternal + " : Bool;   // Bit always FALSE")
	ExternalSourceFile.append("      FirstScan " + NoExternal + " : Bool;   // Bit TRUE for only the first scan of the PLC")
	ExternalSourceFile.append("      StartupDelayDn " + NoExternal + " : Bool;   // Bit initially FALSE, turning TRUE after preset delay")
	if TIAVersion == 13:
		ExternalSourceFile.append("      StartupDelayTmr {OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'} : TON_TIME;")
	else:
		ExternalSourceFile.append("      StartupDelayTmr { "+ _NoExternal +" OriginalPartName := 'IEC_TIMER'; LibVersion := '1.0'} : IEC_TIMER;")
	ExternalSourceFile.append("      Square_100ms " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (100 ms frequency)")
	ExternalSourceFile.append("      Square_100msONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_100ms " + NoExternal + " : Bool;   // Bit TRUE every 100 ms for one PLC scan")
	ExternalSourceFile.append("      Square_200ms " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (200 ms frequency)")
	ExternalSourceFile.append("      Square_200msONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_200ms " + NoExternal + " : Bool;   // Bit TRUE every 200 ms for one PLC scan")
	ExternalSourceFile.append("      Square_400ms " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (400 ms frequency)")
	ExternalSourceFile.append("      Square_400msONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_400ms " + NoExternal + " : Bool;   // Bit TRUE every 400 ms for one PLC scan")
	ExternalSourceFile.append("      Square_500ms " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (500 ms frequency)")
	ExternalSourceFile.append("      Square_500msONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_500ms " + NoExternal + " : Bool;   // Bit TRUE every 500 ms for one PLC scan")
	ExternalSourceFile.append("      Square_800ms " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (800 ms frequency)")
	ExternalSourceFile.append("      Square_800msONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_800ms " + NoExternal + " : Bool;   // Bit TRUE every 800 ms for one PLC scan")
	ExternalSourceFile.append("      Square_1s " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (1 s frequency)")
	ExternalSourceFile.append("      Square_1sONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_1s " + NoExternal + " : Bool;   // Bit TRUE every 1 s for one PLC scan")
	ExternalSourceFile.append("      Square_1600ms " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (1600 ms frequency)")
	ExternalSourceFile.append("      Square_1600msONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_1600ms " + NoExternal + " : Bool;   // Bit TRUE every 1600 ms for one PLC scan")
	ExternalSourceFile.append("      Square_2s " + NoExternal + " : Bool;   // Bit FALSE/TRUE based on square wave (2 s frequency)")
	ExternalSourceFile.append("      Square_2sONS " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      Pulse_2s " + NoExternal + " : Bool;   // Bit TRUE every 2 s for one PLC scan")
	ExternalSourceFile.append("      TestInProgress " + NoExternal + " : Bool;   // Indicates which caller FC is used")
	ExternalSourceFile.append("      EPICS_Device_calls_precessed " + NoExternal + " : Bool;   // Indicates which caller FC is used")
	ExternalSourceFile.append("      EPICSParametersStatus " + NoExternal + " : Word;   // 0=Never Uploaded 1=Uploading... 2=Uploaded")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("   VAR RETAIN")
	ExternalSourceFile.append("      ParameterFreeze " + NoExternal + " : Bool;   // If True, the Handlers doesn't take new parameters from EPICS")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//This block provides standard \"Utilities\" tags that can be used in the rest OF the PLC code such")
	ExternalSourceFile.append("	//as:")
	ExternalSourceFile.append("	//* Always On")
	ExternalSourceFile.append("	//* Always Off")
	ExternalSourceFile.append("	//* Startup Delay")
	ExternalSourceFile.append("	//* Pulses (different frequences)")
	ExternalSourceFile.append("	//* etc.")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//When using This block in your program, name the instance DB \"Utilities\" AND THEN you will be able TO use tags like \"Utilities.AlwaysOn\" in the rest OF your program.")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//This block relies On information provided BY the CPU. This needs TO be enabled in the CPU hardware configuration under System AND Clock Memory.")
	ExternalSourceFile.append("	//Enable both functions AND pick memory bytes you'd like TO use (defauls are %MB1 AND %MB0 respectively).")
	ExternalSourceFile.append("	//THEN connect the selected Byte TO the inputs OF This block.")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE for only the first scan of the PLC")
	ExternalSourceFile.append("	#FirstScan := #CPUSytemMemoryBits.%X0;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit always TRUE")
	ExternalSourceFile.append("	#AlwaysOn := #CPUSytemMemoryBits.%X2;")
	ExternalSourceFile.append("	#AlwaysTrue := #CPUSytemMemoryBits.%X2;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit always FALSE")
	ExternalSourceFile.append("	#AlwaysOff := #CPUSytemMemoryBits.%X3;")
	ExternalSourceFile.append("	#AlwaysFalse := #CPUSytemMemoryBits.%X3;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit initially FALSE, turning TRUE after preset delay")
	if TIAVersion == 13:
		ExternalSourceFile.append("	#StartupDelayTmr(IN := #AlwaysTrue,")
		ExternalSourceFile.append("	                 PT := #StartupDelaySP,")
		ExternalSourceFile.append("	                 Q => #StartupDelayDn);")
	else:
		ExternalSourceFile.append("	#StartupDelayTmr.TON(IN := #AlwaysTrue,")
		ExternalSourceFile.append("	                     PT := #StartupDelaySP,")
		ExternalSourceFile.append("	                     Q => #StartupDelayDn);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 100 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_100ms := #CPUClockMemoryBits.%X0;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_100ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_100msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_100ms);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 200 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_200ms := #CPUClockMemoryBits.%X1;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_200ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_200msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_200ms);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 400 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_400ms := #CPUClockMemoryBits.%X2;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_400ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_400msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_400ms);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 500 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_500ms := #CPUClockMemoryBits.%X3;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_500ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_500msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_500ms);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 800 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_800ms := #CPUClockMemoryBits.%X4;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_800ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_800msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_800ms);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 1 s FOR one PLC scan")
	ExternalSourceFile.append("	#Square_1s := #CPUClockMemoryBits.%X5;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_1s,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_1sONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_1s);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 1600 ms FOR one PLC scan")
	ExternalSourceFile.append("	#Square_1600ms := #CPUClockMemoryBits.%X6;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_1600ms,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_1600msONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_1600ms);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Bit TRUE every 2s FOR one PLC scan")
	ExternalSourceFile.append("	#Square_2s := #CPUClockMemoryBits.%X7;")
	ExternalSourceFile.append("	\"UTIL_P_TRIG\"(\"i_Input Bit\" := #Square_2s,")
	ExternalSourceFile.append("	              \"iq_Trigger Bit\" := #Square_2sONS,")
	ExternalSourceFile.append("	              \"iq_Pulse Bit\" := #Pulse_2s);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"Utilities\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"_UtilitiesFB\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("   ParameterFreeze := true;")
	ExternalSourceFile.append("END_DATA_BLOCK")


def WriteStandardPLCCode(TIAVersion):

	global ExternalSourceFile

	ExternalSourceFile.append("FUNCTION \"UTIL_P_TRIG\" : Void")
	ExternalSourceFile.append("TITLE = Positive Edge Detection Pulse")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      \"i_Input Bit\" : Bool;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_IN_OUT ")
	ExternalSourceFile.append("      \"iq_Trigger Bit\" : Bool;")
	ExternalSourceFile.append("      \"iq_Pulse Bit\" : Bool;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//Prositive edge generator for SCL")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	IF #\"i_Input Bit\" AND #\"iq_Trigger Bit\"")
	ExternalSourceFile.append("	THEN")
	ExternalSourceFile.append("	    #\"iq_Pulse Bit\" := FALSE;")
	ExternalSourceFile.append("	ELSIF #\"i_Input Bit\"")
	ExternalSourceFile.append("	    THEN")
	ExternalSourceFile.append("	        #\"iq_Pulse Bit\" := TRUE;")
	ExternalSourceFile.append("	        #\"iq_Trigger Bit\" := TRUE;")
	ExternalSourceFile.append("	    ELSE")
	ExternalSourceFile.append("	        #\"iq_Pulse Bit\" := FALSE;")
	ExternalSourceFile.append("	        #\"iq_Trigger Bit\" := FALSE;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("END_FUNCTION")

	WriteUtilitiesCode(TIAVersion)

	ExternalSourceFile.append("DATA_BLOCK \"EPICSToPLC\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("//########## EPICS->PLC datablock ##########")
	ExternalSourceFile.append("   STRUCT")
	ExternalSourceFile.append("      \"Word\" " + NoExternal + " : Array[0.."+str(ifa.TOTALEPICSTOPLCLENGTH -1)+"] of Word;")
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"PLCToEPICS\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("//########## PLC->EPICS datablock ##########")
	ExternalSourceFile.append("   STRUCT")
	ExternalSourceFile.append("      \"Word\" " + NoExternal + " : Array[0.."+str(ifa.TOTALPLCTOEPICSLENGTH -1)+"] of Word;")
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	ExternalSourceFile.append("FUNCTION_BLOCK \"_CommsPLC_EPICS\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_INPUT ")
	ExternalSourceFile.append("      Enable " + NoExternal + " : Bool;   // Enable all comms")
	ExternalSourceFile.append("      SendTrigger " + NoExternal + " : Bool;   // Trigger for PLC->EPICS data send (should be quick and cyclic)")
	ExternalSourceFile.append("      BytesToSend " + NoExternal + " : Int;   // Number of bytes for PLC->EPICS data send")
	ExternalSourceFile.append("      InterfaceID " + NoExternal + " : HW_ANY;   // Hardware identifier of Ethernet port to be used (see under device configuration)")
	ExternalSourceFile.append("      S7ConnectionID " + NoExternal + " : Int := 256;   // Connection ID for EPICS s7plc driver connection")
	ExternalSourceFile.append("      MBConnectionID " + NoExternal + " : Int := 255;   // Connection ID for EPICS modbus driver connection")
	ExternalSourceFile.append("      S7Port " + NoExternal + " : Int := 2000;   // PLC port for EPICS s7plc driver connection")
	ExternalSourceFile.append("      MBPort " + NoExternal + " : Int := 502;   // PLC port for EPICS modbus driver connection")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_OUTPUT ")
	ExternalSourceFile.append("      SendDone " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      SendBusy " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      SendError " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      SendStatus " + NoExternal + " : Word;")
	ExternalSourceFile.append("      RcvNewDataReady " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      RcvDataRead " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      RcvError " + NoExternal + " : Bool;")
	ExternalSourceFile.append("      RcvStatus " + NoExternal + " : Word;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR_IN_OUT ")
	ExternalSourceFile.append("      PLCToEPICSData : Variant;   // Pointer to PLC->EPICS data exchange block (header of the array of words)")
	ExternalSourceFile.append("      EPICSToPLCData : Variant;   // Pointer to EPICS->PLC data exchange block (header of the array of words)")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("   VAR ")
	ExternalSourceFile.append("      SendConnData { " + _NoExternal + " OriginalPartName := 'TCON_IP_v4'; LibVersion := '1.0'} : TCON_IP_v4;   // Connection parameters")
	ExternalSourceFile.append("      RcvConnData { " + _NoExternal + " OriginalPartName := 'TCON_IP_v4'; LibVersion := '1.0'} : TCON_IP_v4;   // Connection parameters")
	ExternalSourceFile.append("      TSEND_C_DB { " + _NoExternal + " OriginalPartName := 'TSENDC'; LibVersion := '3.2'} : TSEND_C;")
	ExternalSourceFile.append("      MB_SERVER_DB { " + _NoExternal + " OriginalPartName := 'MBSERVER'; LibVersion := '4.2'} : MB_SERVER;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//This function block performs send/recieve communication between the PLC AND EPICS using:")
	ExternalSourceFile.append("	//1. Open user communication (s7plc driver in EPICS)")
	ExternalSourceFile.append("	//2. Modbus TCP (Modbus driver in EPICS)")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("	//The block is fully self-contained, i.e. you should be able TO simple insert it in your program (AND call it OF course) AND provide some inputs TO it")
	ExternalSourceFile.append("	//")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Set up connections (Ethernet port ID)")
	ExternalSourceFile.append("	#SendConnData.InterfaceId := #InterfaceID;")
	ExternalSourceFile.append("	#RcvConnData.InterfaceId := #InterfaceID;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Set up connections (Connection ID) (separate connections for s7 and Modbus)")
	ExternalSourceFile.append("	#SendConnData.ID := INT_TO_WORD(IN:= #S7ConnectionID);")
	ExternalSourceFile.append("	#RcvConnData.ID := INT_TO_WORD(IN := #MBConnectionID);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Set up connections (Connection type)")
	ExternalSourceFile.append("	#SendConnData.ConnectionType := 11;")
	ExternalSourceFile.append("	#RcvConnData.ConnectionType := 11;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Set up connections (Active connection establishment)")
	ExternalSourceFile.append("	IF NOT #SendConnData.ActiveEstablished THEN")
	ExternalSourceFile.append("	    #RcvConnData.ActiveEstablished := false;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//Set up connections (Local port)")
	ExternalSourceFile.append("	#SendConnData.LocalPort := INT_TO_UINT(IN:= #S7Port);")
	ExternalSourceFile.append("	#RcvConnData.LocalPort := INT_TO_UINT(IN := #MBPort);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//PLC -> EPICS communication. Data is sent using open user communication (s7plc driver in EPICS)")
	ExternalSourceFile.append("	#TSEND_C_DB(REQ:=#SendTrigger,")
	ExternalSourceFile.append("	            CONT:=TRUE,")
	ExternalSourceFile.append("	            LEN:=INT_TO_UINT(IN:=#BytesToSend),")
	ExternalSourceFile.append("	            DONE=>#SendDone,")
	ExternalSourceFile.append("	            BUSY=>#SendBusy,")
	ExternalSourceFile.append("	            ERROR=>#SendError,")
	ExternalSourceFile.append("	            STATUS=>#SendStatus,")
	ExternalSourceFile.append("	            CONNECT:=#SendConnData,")
	ExternalSourceFile.append("	            DATA:=#PLCToEPICSData);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	//EPICS <- EPICS communication. Data is received using modbus server on the PLC (modbus driver in EPICS)")
	ExternalSourceFile.append("	#MB_SERVER_DB(DISCONNECT:=NOT #Enable,")
	ExternalSourceFile.append("	              NDR=>#RcvNewDataReady,")
	ExternalSourceFile.append("	              DR=>#RcvDataRead,")
	ExternalSourceFile.append("	              ERROR=>#RcvError,")
	ExternalSourceFile.append("	              STATUS=>#RcvStatus,")
	ExternalSourceFile.append("	              MB_HOLD_REG:=#EPICSToPLCData,")
	ExternalSourceFile.append("	              CONNECT:=#RcvConnData);")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_FUNCTION_BLOCK")

	ExternalSourceFile.append("DATA_BLOCK \"_CommsPLC_EPICS_DB\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("\"_CommsPLC_EPICS\"")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")

	WriteEPICS_device_calls()

	ExternalSourceFile.append("FUNCTION \"_CommsEPICS\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//Heartbeat PLC->EPICS")
	ExternalSourceFile.append("	IF \"Utilities\".Pulse_1s THEN")
	ExternalSourceFile.append("	    \"PLCToEPICS\".\"Word\"[{hb}] := \"PLCToEPICS\".\"Word\"[{hb}] + 1;".format(hb = IFA.PLCTOEPICS_HEARTBEAT))
	ExternalSourceFile.append("	    IF \"PLCToEPICS\".\"Word\"[{}] >= 32000 THEN".format(IFA.PLCTOEPICS_HEARTBEAT))
	ExternalSourceFile.append("	        \"PLCToEPICS\".\"Word\"[{}] := 0;".format(IFA.PLCTOEPICS_HEARTBEAT))
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	// Call the comms block to provide PLC<->EPICS comms")
	ExternalSourceFile.append("	\"_CommsPLC_EPICS_DB\"(Enable := \"Utilities\".AlwaysOn,")
	ExternalSourceFile.append("	                     SendTrigger := \"Utilities\"." + ifa.PLC_PULSE + ",")
	ExternalSourceFile.append("	                     BytesToSend := 10,")
	ExternalSourceFile.append("	                     InterfaceID := "+ifa.INTERFACE_ID+",")
	ExternalSourceFile.append("	                     S7ConnectionID := "+ifa.S7_CONNECTION_ID+",")
	ExternalSourceFile.append("	                     MBConnectionID := "+ifa.MODBUS_CONNECTION_ID+",")
	ExternalSourceFile.append("	                     S7Port         := "+str(ifa.S7_PORT)+",")
	ExternalSourceFile.append("	                     MBPort         := "+str(ifa.MODBUS_PORT)+",")
	ExternalSourceFile.append("	                     PLCToEPICSData := \"PLCToEPICS\".\"Word\",")
	ExternalSourceFile.append("	                     EPICSToPLCData := \"EPICSToPLC\".\"Word\");")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_FUNCTION")

	WriteEPICS_Debugger(True)

	ExternalSourceFile.append("FUNCTION \"_Comms\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//This is an aggregator function, it will call all the other comms functions required:")
	ExternalSourceFile.append("	//1. PLC/EPICS")
	ExternalSourceFile.append("	//2. Any other comms")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	\"_CommsEPICS\"();")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_FUNCTION")


def WriteCommsEpicsAndDbs():

	global ExternalSourceFile

	ExternalSourceFile.append("DATA_BLOCK \"EPICSToPLC\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("//########## EPICS->PLC datablock ##########")
	ExternalSourceFile.append("   STRUCT")
	ExternalSourceFile.append("      \"Word\" " + NoExternal + " : Array[0.."+str(ifa.TOTALEPICSTOPLCLENGTH -1)+"] of Word;")
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")
	ExternalSourceFile.append("")

	ExternalSourceFile.append("DATA_BLOCK \"PLCToEPICS\"")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'FALSE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("NON_RETAIN")
	ExternalSourceFile.append("//########## PLC->EPICS datablock ##########")
	ExternalSourceFile.append("   STRUCT")
	ExternalSourceFile.append("      \"Word\" " + NoExternal + " : Array[0.."+str(ifa.TOTALPLCTOEPICSLENGTH -1)+"] of Word;")
	ExternalSourceFile.append("   END_STRUCT;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_DATA_BLOCK")
	ExternalSourceFile.append("")


	ExternalSourceFile.append("FUNCTION \"_CommsEPICS\" : Void")
	ExternalSourceFile.append("{ S7_Optimized_Access := 'TRUE' }")
	ExternalSourceFile.append("VERSION : 0.1")
	ExternalSourceFile.append("   VAR_TEMP")
	ExternalSourceFile.append("      PLC_Hash : DInt;")
	ExternalSourceFile.append("   END_VAR")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("BEGIN")
	ExternalSourceFile.append("	//Heartbeat PLC->EPICS")
	ExternalSourceFile.append("	IF \"Utilities\".Pulse_1s THEN")
	ExternalSourceFile.append("	    \"PLCToEPICS\".\"Word\"[{hb}] := \"PLCToEPICS\".\"Word\"[{hb}] + 1;".format(hb = IFA.PLCTOEPICS_HEARTBEAT))
	ExternalSourceFile.append("	    IF \"PLCToEPICS\".\"Word\"[{}] >= 32000 THEN".format(IFA.PLCTOEPICS_HEARTBEAT))
	ExternalSourceFile.append("	        \"PLCToEPICS\".\"Word\"[{}] := 0;".format(IFA.PLCTOEPICS_HEARTBEAT))
	ExternalSourceFile.append("	    END_IF;")
	ExternalSourceFile.append("	END_IF;")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	// PLC Factory commit ID: {}".format(ifa.commit_id if not verify else ""))
	ExternalSourceFile.append("	// PLC Hash (Generated by PLC Factory)")
	ExternalSourceFile.append("	#PLC_Hash := DINT#"+ifa.HASH+";")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	// Send the PLC Hash to the EPICS IOC")
	ExternalSourceFile.append("	\"PLCToEPICS\".\"Word\"[{}] := DINT_TO_WORD(#PLC_Hash);".format(IFA.PLCTOEPICS_HASH + 1))
	ExternalSourceFile.append("	\"PLCToEPICS\".\"Word\"[{}] := DINT_TO_WORD(SHR(IN := #PLC_Hash, N := 16));".format(IFA.PLCTOEPICS_HASH))
	ExternalSourceFile.append("")
	ExternalSourceFile.append("	// Send the PLC parameter upload status to the EPICS IOC")
	ExternalSourceFile.append("	\"PLCToEPICS\".\"Word\"[{}] := \"EPICSToPLC\".\"Word\"[{}];".format(IFA.PLCTOEPICS_UPLOADSTAT, IFA.EPICSTOPLC_UPLOADSTAT))
	ExternalSourceFile.append("     \"Utilities\".EPICSParametersStatus := \"EPICSToPLC\".\"Word\"[{}];".format(IFA.EPICSTOPLC_UPLOADSTAT))

	ExternalSourceFile.append("")
	ExternalSourceFile.append("	// Put the PLC Hash into the Modbus map")
	ExternalSourceFile.append("	\"EPICSToPLC\".\"Word\"[{}] := DINT_TO_WORD(#PLC_Hash);".format(IFA.EPICSTOPLC_READ_HASH + 1))
	ExternalSourceFile.append("	\"EPICSToPLC\".\"Word\"[{}] := DINT_TO_WORD(SHR(IN := #PLC_Hash, N := 16));".format(IFA.EPICSTOPLC_READ_HASH))
	ExternalSourceFile.append("")

	ExternalSourceFile.append("")
	ExternalSourceFile.append("	// Put the payload size (in bytes) into the Modbus map")
	ExternalSourceFile.append("	\"EPICSToPLC\".\"Word\"[{}] := {};".format(IFA.EPICSTOPLC_READ_PAYLOAD_SIZE, ifa.TOTALPLCTOEPICSLENGTH * 2))
	ExternalSourceFile.append("")

	ExternalSourceFile.append("	// Call the comms block to provide PLC<->EPICS comms")
	ExternalSourceFile.append("	\"_CommsPLC_EPICS_DB\"(Enable         := \"Utilities\".AlwaysOn,")
	ExternalSourceFile.append("	                     SendTrigger    := \"Utilities\"." + ifa.PLC_PULSE + ",")
	ExternalSourceFile.append("	                     BytesToSend    := "+str(ifa.TOTALPLCTOEPICSLENGTH * 2)+",")
	ExternalSourceFile.append("	                     InterfaceID    := "+ifa.INTERFACE_ID+",")
	ExternalSourceFile.append("	                     S7ConnectionID := "+ifa.S7_CONNECTION_ID+",")
	ExternalSourceFile.append("	                     MBConnectionID := "+ifa.MODBUS_CONNECTION_ID+",")
	ExternalSourceFile.append("	                     S7Port         := "+str(ifa.S7_PORT)+",")
	ExternalSourceFile.append("	                     MBPort         := "+str(ifa.MODBUS_PORT)+",")
	ExternalSourceFile.append("	                     PLCToEPICSData := \"PLCToEPICS\".\"Word\",")
	ExternalSourceFile.append("	                     EPICSToPLCData := \"EPICSToPLC\".\"Word\");")
	ExternalSourceFile.append("")
	ExternalSourceFile.append("END_FUNCTION")

ReservedChars = { ':', '/', '\\', '?', '*', '[', ']', '.', '-', '+', '=', '{', '}' }

def QuoteVariableName(TIAVersion, variableName):
    if TIAVersion >= 14 or not set(variableName).isdisjoint(ReservedChars):
        return '"{}"'.format(variableName)

    return variableName


def ProcessIFADevTypes(OutputDir, TIAVersion, CommsTest, timestamp):

	#Process IFA devices
	print("Processing .ifa file...")

	ProcessedDeviceNum = 0

	global ExternalSourceFile
	global DeviceTypeList
	DeviceTypeList = []

	global DevTypeHeader
	global DevTypeVAR_INPUT
	global DevTypeVAR_INOUT
	global DevTypeVAR_OUTPUT
	global DevTypeDB_SPEC
	global DevTypeVAR_TEMP
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global DevTypeBODY_END

	global EPICS_PLC_TesterDB
	global DeviceInstance


	global EndString
	global EndString2
	global IsDouble

	StartingRegister = -1

	ActVariablePLCName = ""
	ActVariableEPICSName = ""
	ActVariableType = ""
	LastVariableType = ""
	ActVariableArrayIndex = 0
	ActVariableBitNumber = 0
	EndString = ""
	EndString2 = ""
	EndDeviceString = ""
	IsDouble = False
	NewDeviceType = False
	EPICS_device_calls_body   = []
	EPICS_device_calls_header = []

	global MaxStatusReg;
	global MaxCommandReg;
	MaxStatusReg = 0;
	MaxCommandReg = 0;

	InArrayName = None
	InArrayGatewayDatablock = True
	InArrayStartIdx  = None
	InArrayNum  = None

	WriteUtilitiesCode(TIAVersion)

	for device in ifa.Devices:
		ProcessedDeviceNum = ProcessedDeviceNum + 1

		ActualDeviceName = device.properties["DEVICE"]
		ActualDeviceType = device.properties["DEVICE_TYPE"]
		ActualDataBlock  = '"{}"'.format(device.properties["DATABLOCK"])
		PLCTOEPICSLENGTH = device.properties["PLCTOEPICSLENGTH"]
		EPICSTOPLCLENGTH = device.properties["EPICSTOPLCLENGTH"]
		EPICSTOPLCDATABLOCKOFFSET = device.properties["EPICSTOPLCDATABLOCKOFFSET"]
		PLCTOEPICSDATABLOCKOFFSET = device.properties["PLCTOEPICSDATABLOCKOFFSET"]
		Text = "Device: "+ ActualDeviceName + " Type: "+ ActualDeviceType
		print("    ", "-" * len(Text), sep='')
		print("    ", Text, sep='')
		print("    ", "-" * len(Text), sep='')

		#Device Instance
		DeviceInstance.append("")
		DeviceInstance.append("DATA_BLOCK " + ActualDataBlock)
		DeviceInstance.append("{ S7_Optimized_Access := 'TRUE' }")
		DeviceInstance.append("VERSION : 1.0")
		DeviceInstance.append("NON_RETAIN")
		DeviceInstance.append("\"DEVTYPE_"+ActualDeviceType+"\"")
		DeviceInstance.append("BEGIN")
		DeviceInstance.append("END_DATA_BLOCK")
		DeviceInstance.append("")

		EPICS_device_calls_header.append("      \""+ActualDeviceName+"\" : Bool;   // HASH codes are OK")
		EPICS_device_calls_test_header.append("      \""+ActualDeviceName+"\" : Bool;   // HASH codes are OK")

		EPICS_device_calls_body.append("")
		EPICS_device_calls_body.append("        //********************************************")
		EPICS_device_calls_body.append("        // Device name: "+ActualDeviceName)
		EPICS_device_calls_body.append("        // Device type: "+ActualDeviceType)
		EPICS_device_calls_body.append("        //********************************************")
		EPICS_device_calls_body.append("")
		EPICS_device_calls_body.append("      "+ActualDataBlock+" (EPICSToPLCLength:="+EPICSTOPLCLENGTH+",")
		EPICS_device_calls_body.append("      EPICSToPLCDataBlockOffset:="+EPICSTOPLCDATABLOCKOFFSET+",")
		EPICS_device_calls_body.append("      PLCToEPICSLength:="+PLCTOEPICSLENGTH+",")
		EPICS_device_calls_body.append("      PLCToEPICSDataBlockOffset:="+PLCTOEPICSDATABLOCKOFFSET+");")

		EndDeviceString = ActualDeviceName
		EPICS_device_calls_test_body.append("")
		EPICS_device_calls_test_body.append("      //********************************************")
		EPICS_device_calls_test_body.append("      // Device name: "+ActualDeviceName)
		EPICS_device_calls_test_body.append("      // Device type: "+ActualDeviceType)
		EPICS_device_calls_test_body.append("      //********************************************")
		EPICS_device_calls_test_body.append("")
		EPICS_device_calls_test_body.append("      "+ActualDataBlock+" (EPICSToPLCLength:="+EPICSTOPLCLENGTH+",")
		EPICS_device_calls_test_body.append("      EPICSToPLCDataBlockOffset:="+EPICSTOPLCDATABLOCKOFFSET+",")
		EPICS_device_calls_test_body.append("      PLCToEPICSLength:="+PLCTOEPICSLENGTH+",")
		EPICS_device_calls_test_body.append("      PLCToEPICSDataBlockOffset:="+PLCTOEPICSDATABLOCKOFFSET+",")

		#Check if DeviceType is already generated
		if ActualDeviceType not in DeviceTypeList:
			MaxStatusReg = 0;
			MaxCommandReg = 0;

			NewDeviceType = True
			DeviceTypeList.append(ActualDeviceType)
			print("    ->  New device type found. [", ActualDeviceType, "] Creating source code...", sep='')
			DevTypeHeader.append("FUNCTION_BLOCK \"" + "DEVTYPE_" + ActualDeviceType+ "\"")
			DevTypeHeader.append("{ S7_Optimized_Access := 'TRUE' }")
			DevTypeHeader.append("VERSION : 1.0")

			DevTypeDB_SPEC.append("   Var DB_SPECIFIC")
			DevTypeDB_SPEC.append("      MyWord " + NoExternal + " : Word;")
			DevTypeDB_SPEC.append("      MyBytesinWord " + NoExternal + " AT MyWord : Array[0..1] of Byte;")
			DevTypeDB_SPEC.append("      MyBoolsinWord " + NoExternal + " AT MyWord : Array[0..15] of Bool;")
			DevTypeDB_SPEC.append("      MyDInt " + NoExternal + " : DInt;")
			DevTypeDB_SPEC.append("      MyWordsinDint " + NoExternal + " AT MyDInt : Array[0..1] of Word;")
			DevTypeDB_SPEC.append("      MyReal " + NoExternal + " : Real;")
			DevTypeDB_SPEC.append("      MyWordsinReal " + NoExternal + " AT MyReal : Array[0..1] of Word;")
			DevTypeDB_SPEC.append("      MyInt " + NoExternal + " : Int;")
			DevTypeDB_SPEC.append("      MyWordinInt " + NoExternal + " AT MyInt : Word;")
			DevTypeDB_SPEC.append("      MyDWord " + NoExternal + " : DWord;")
			DevTypeDB_SPEC.append("      MyWordsinDWord " + NoExternal + " AT MyDWord : Array[0..1] of Word;")
			DevTypeDB_SPEC.append("      MyTime " + NoExternal + " : Time;")
			DevTypeDB_SPEC.append("      MyWordsinTime " + NoExternal + " AT MyTime : Array[0..1] of Word;")
			DevTypeDB_SPEC.append("      MyString " + NoExternal + " : String[40];")
			DevTypeDB_SPEC.append("      MyWordsinString " + NoExternal + " AT MyString : Array[0..20] of Word;")
			DevTypeDB_SPEC.append("   END_VAR")

			DevTypeVAR_TEMP.append("   VAR_TEMP")
			DevTypeVAR_TEMP.append("      HashModbus : DInt;")
			DevTypeVAR_TEMP.append("      HashIFA : DInt;")
			DevTypeVAR_TEMP.append("      HashTIAMap : DInt;")
			DevTypeVAR_TEMP.append("      i : Int;")
			DevTypeVAR_TEMP.append("   END_VAR")

			DevTypeBODY_HEADER.append("    //Author: Miklos Boros (miklos.boros@esss.se), Copyrigth 2017-2020 by European Spallation Source, Lund")
			DevTypeBODY_HEADER.append("    //This block was generated by PLCFactory, please don't change it MANUALLY!")
			if not verify:
				DevTypeBODY_HEADER.append("    //Input File Name: " + os.path.basename(ifa.IfaPath))
				DevTypeBODY_HEADER.append("    //Generated: "+ timestamp)
			DevTypeBODY_HEADER.append("    //According to HASH: "+ifa.HASH)
			DevTypeBODY_HEADER.append("    //Device type: "+ActualDeviceType)
			DevTypeBODY_HEADER.append("    //Description: This function does the variable mapping for a device. All device-variable will be linked to an interface variable defined in this block.")
			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("    //********************************************")
			DevTypeBODY_HEADER.append("    //****************HASH check******************")
			DevTypeBODY_HEADER.append("    //********************************************")
			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("    #MyWordsinDint[0] := \"EPICSToPLC\".\"Word\"[{}];".format(IFA.EPICSTOPLC_HASH))
			DevTypeBODY_HEADER.append("    #MyWordsinDint[1] := \"EPICSToPLC\".\"Word\"[{}];".format(IFA.EPICSTOPLC_HASH + 1))
			DevTypeBODY_HEADER.append("    #HashModbus := #MyDInt; //Hash from EPICS/ModbusTCP")
			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("    #HashIFA := " + ifa.HASH + "; //Hash from Interface Factory as a constant")
			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("    #MyWordsinDint[0] := \"PLCToEPICS\".\"Word\"[{}];".format(IFA.PLCTOEPICS_HASH))
			DevTypeBODY_HEADER.append("    #MyWordsinDint[1] := \"PLCToEPICS\".\"Word\"[{}];".format(IFA.PLCTOEPICS_HASH + 1))
			DevTypeBODY_HEADER.append("    #HashTIAMap := #MyDInt; //Hash from PLCFactory TIA Map")
			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("    IF ((#HashIFA = #HashModbus) AND (#HashModbus = #HashTIAMap)) THEN //Check CRCs")
			DevTypeBODY_HEADER.append("        #DEVICE_PARAM_OK := TRUE;")

			DevTypeBODY_END.append("    Else")
			DevTypeBODY_END.append("       #DEVICE_PARAM_OK := FALSE; //Invalid Hash")
			DevTypeBODY_END.append("    END_IF;")
			DevTypeBODY_END.append("END_FUNCTION_BLOCK")

		else:
			NewDeviceType = False


		for line in device.comments:
			DevTypeBODY_CODE.append("       " + line)

		for item in device:
			if item.is_wrapper_array():
				if item.is_start():
					InArrayName = GetPLCVariableName(item)
					InArrayNum = item.start_idx()
					InArrayStartIdx = item.start_idx()
					InArrayGatewayDatablock = IsInGatewayDatablock(item)
				else:
					if not InArrayGatewayDatablock:
						DevTypeVAR_INPUT.append("      " + QuoteVariableName(TIAVersion, item.name()) + " " + NoExternal + " : Array["+str(InArrayStartIdx)+".."+ str(InArrayNum-1) +"] of "+ ActVariableType+";   //EPICS Status variables defined in an array")
					InArrayName = None
					InArrayNum  = None
					InArrayGatewayDatablock = True

			elif item.is_block():
				CloseLastVariable()
				StartingRegister = -1
				if item.is_status():
					DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("    //*************STATUS VARIABLES***************")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("")
				elif item.is_command():
					DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("    //*************COMMAND VARIABLES**************")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("")
				elif item.is_parameter():
					DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("    //************PARAMETER VARIABLES*************")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("")
				elif item.is_general_input():
					DevTypeBODY_CODE.append("")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("    //**********GENERAL INPUT VARIABLES***********")
					DevTypeBODY_CODE.append("    //********************************************")
					DevTypeBODY_CODE.append("")
				else:
					raise IFA.FatalException("Unknown block type: {}".format(item.name()))


			elif item.is_variable():
				ActVariablePLCName    = item.properties["VARIABLE"]
				ActVariableEPICSName  = item.properties["EPICS"]
				ActVariableType       = item.properties["TYPE"]
				ActVariableArrayIndex = int(item.properties["ARRAY_INDEX"])
				ActVariableBitNumber  = int(item.properties["BIT_NUMBER"])
				TIAVariablePLCName    = QuoteVariableName(TIAVersion, ActVariablePLCName)

				#Close the last variable if there is a new variable
				if 	LastVariableType != ActVariableType:
					LastVariableType = ActVariableType
					CloseLastVariable()

				if not IsInGatewayDatablock(item):
					if item.is_status():
						if InArrayName is not None:
							DevTypeVAR_INOUT.append("      \"" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS Status variable in an array: "+ActVariableEPICSName)
							EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS Status variable: "+ActVariableEPICSName)
							EPICS_device_calls_test_body.append("                                 "+TIAVariablePLCName+" := \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
						else:
							DevTypeVAR_INPUT.append("      \"" + ActVariablePLCName + "\" " + ExternalRead + " : "+ ActVariableType+";   //EPICS Status variable: "+ActVariableEPICSName)
							EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS Status variable: "+ActVariableEPICSName)
							EPICS_device_calls_test_body.append("                                 "+TIAVariablePLCName+" := \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
					elif item.is_command():
						DevTypeVAR_OUTPUT.append("      \"" + ActVariablePLCName + "\" " + ExternalRead + " : "+ ActVariableType+";   //EPICS Command variable: "+ActVariableEPICSName)
						EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS Command variable: "+ActVariableEPICSName)
						EPICS_device_calls_test_body.append("                                 "+TIAVariablePLCName+" => \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
					elif item.is_parameter():
						DevTypeVAR_OUTPUT.append("      \"" + ActVariablePLCName + "\" " + ExternalRead + " : "+ ActVariableType+";   //EPICS Parameter variable: "+ActVariableEPICSName)
						EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS Parameter variable: "+ActVariableEPICSName)
						EPICS_device_calls_test_body.append("                                 "+TIAVariablePLCName+" => \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
					elif item.is_general_input():
						DevTypeVAR_OUTPUT.append("      \"" + ActVariablePLCName + "\" " + ExternalRead + " : "+ ActVariableType+";   //EPICS General input variable: "+ActVariableEPICSName)
						EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS General input variable: "+ActVariableEPICSName)
						EPICS_device_calls_test_body.append("                                 "+TIAVariablePLCName+" => \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")
					else:
						raise IFA.FatalException("Unknown variable flavor: {}".format(item.name()))

				elif item.is_output() and InArrayName is not None:
					# (local) Arrays need to be declared even if using gateway mode
					DevTypeVAR_INOUT.append("      \"" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS Status variable in an array: "+ActVariableEPICSName)
					EPICS_PLC_TesterDB.append("      \"" + ActualDeviceName+"_" + ActVariablePLCName + "\" " + NoExternal + " : "+ ActVariableType+";   //EPICS Status variable: "+ActVariableEPICSName)
					EPICS_device_calls_test_body.append("                                 "+TIAVariablePLCName+" := \"EPICS_PLC_Tester\".#\""+ ActualDeviceName+"_" + ActVariablePLCName + "\",")

				#SUPPORTED TYPES
				#PLC_types = {'BOOL', 'BYTE', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'TIME' }

				#====== BOOL TYPE ========
				if ActVariableType == "BOOL":
					InArrayNum, StartingRegister = AddBOOL(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== BYTE TYPE ========
				elif ActVariableType == "BYTE" or ActVariableType == "USINT" or ActVariableType == "SINT":
					InArrayNum, StartingRegister = AddBYTE(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== INT TYPE ========
				elif ActVariableType == "INT":
					InArrayNum, StartingRegister = AddINT(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== WORD TYPE ========
				elif ActVariableType == "WORD" or ActVariableType == "UINT":
					InArrayNum, StartingRegister = AddWORD(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== DINT TYPE ========
				elif ActVariableType == "DINT":
					InArrayNum, StartingRegister = AddDINT(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== DWORD TYPE ========
				elif ActVariableType == "DWORD" or ActVariableType == "UDINT":
					InArrayNum, StartingRegister = AddDWORD(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== REAL TYPE ========
				elif ActVariableType == "REAL":
					InArrayNum, StartingRegister = AddREAL(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== TIME TYPE ========
				elif ActVariableType == "TIME":
					InArrayNum, StartingRegister = AddTIME(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== STRING TYPE ========
				elif ActVariableType == "STRING":
					InArrayNum, StartingRegister = AddSTRING(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#=== not supported TYPE ===
				else:
					raise IFA.FatalException("Unsupported variable type", ActVariableType)
				#==========================
				if item.is_output():
					if ActVariableArrayIndex >= MaxStatusReg:
						if IsDouble:
							MaxStatusReg = ActVariableArrayIndex + 1
						else:
							MaxStatusReg = ActVariableArrayIndex

				elif item.is_input():
					if ActVariableArrayIndex >= MaxCommandReg:
						if IsDouble:
							MaxCommandReg = ActVariableArrayIndex + 1
						else:
							MaxCommandReg = ActVariableArrayIndex

				else:
					raise IFA.FatalException("Neither input nor output", item)

		# Processed all items in a device, let's close the last variable
		CloseLastVariable()

		# Device is done, let's do some housekeeping
		if EndDeviceString != "":
			EPICS_device_calls_test_body.append("                                 DEVICE_PARAM_OK=>#\""+EndDeviceString+"\");")
			EndDeviceString = ""
		if NewDeviceType == True:
			WriteDevType()
		else:
			DevTypeHeader = []
			DevTypeVAR_INPUT = []
			DevTypeVAR_INOUT = []
			DevTypeVAR_OUTPUT = []
			DevTypeDB_SPEC = []
			DevTypeVAR_TEMP = []
			DevTypeBODY_HEADER = []
			DevTypeBODY_CODE = []
			DevTypeBODY_CODE_ARRAY = []
			DevTypeBODY_END = []

	#Constuct the output source file
	WriteDeviceInstances()
	if CommsTest:
		WriteEPICS_PLC_TesterDB()
	WriteEPICS_device_calls(EPICS_device_calls_header, EPICS_device_calls_body)
	WriteEPICS_Debugger()
	if CommsTest:
		WriteEPICS_device_calls_test()

	print("\nTotal", str(ProcessedDeviceNum), "device(s) processed.")
	print("Total", str(len(DeviceTypeList)), "device type(s) generated.\n")


def consolidate_tia_version(tia_version):
    if tia_version is not None and isinstance(tia_version, str):
        tia13   = set({"13",   "v13",   "tia13",   "tiav13"})
        tia14   = set({"14",   "v14",   "tia14",   "tiav14"})
        tia15   = set({"15",   "v15",   "tia15",   "tiav15"})
        tia15_1 = set({"15.1", "v15.1", "tia15.1", "tiav15.1"})
        tia17 = set({"17", "v17", "tia17", "tiav17"})
        tia18 = set({"18", "v18", "tia18", "tiav18"})

        if tia_version in tia13:
            tia_version = 13
        elif tia_version in tia14:
            tia_version = 14
        elif tia_version in tia15:
            tia_version = 15
        elif tia_version in tia15_1:
            tia_version = 15.1
        elif tia_version in tia17:
            tia_version = 17
        elif tia_version in tia18:
            tia_version = 18
        else:
            raise IFA.FatalException("Unsupported TIA version: " + tia_version)

    return tia_version


def produce(OutputDir, _ifa, **kwargs):
	global ifa
	global verify
	global CommsTest

	print("""
*******************************************
*                                         *
*   Generating Siemens PLC source code    *
*                                         *
*******************************************
""")

	generated_files = dict()

	ifa = _ifa

	#=============Call main functions=============
	global ExternalSourceFile
	ExternalSourceFile = []

	TIAVersion = kwargs.get('TIAVersion', 14)
	TIAVersion = consolidate_tia_version(TIAVersion)
	onlydiag   = kwargs.get('onlydiag', False)
	nodiag     = kwargs.get('nodiag', False)
	Direct     = kwargs.get('direct', False)
	CommsTest  = kwargs.get('commstest', False)
	verify     = kwargs.get('verify', False)
	timestamp  = kwargs.get('timestamp', None) 
	ifa.commit_id  = kwargs.get('commit_id', "")
	if Direct:
		raise IFA.FatalException("Direct mode is only supported in the InterfaceFactoryLegacySiemens module")

	if CommsTest and ifa.GATEWAY_DATABLOCK is not None:
		raise IFA.FatalException("Testing is not (yet?) supported with 'gateway-mode'")

	if ifa.GATEWAY_DATABLOCK is not None:
		ifa.GATEWAY_DATABLOCK = '.'.join(map(lambda x: '"{}"'.format(x), ifa.GATEWAY_DATABLOCK.split('.')))

	if not onlydiag:
		#WriteStandardPLCCode
		WriteStandardPLCCode(TIAVersion)

		if verify:
			standardPath = os.path.join(OutputDir, "PLCFactory_external_source_standard_TIAv{tiaversion}_{timestamp}.scl".format(tiaversion = TIAVersion, timestamp = timestamp))
		else:
			standardPath = os.path.join(OutputDir, "PLCFactory_external_source_standard_TIAv{tiaversion}.scl".format(tiaversion = TIAVersion))
		with open(standardPath, 'wb') as standardScl:
			for line in ExternalSourceFile:
				standardScl.write((line + '\r\n').encode())

		generated_files["STANDARD_SCL"] = standardPath

		ExternalSourceFile = []

		#Process devices/device types
		ProcessIFADevTypes(OutputDir, TIAVersion, CommsTest, timestamp)

	if not nodiag or onlydiag:
		#WriteDiagnostics
		from .SiemensDiagnostics import Diagnostics
		Diagnostics.WriteDiagnostics(TIAVersion, ExternalSourceFile, ifa)
	else:
		print("NOTE:\nSkipping diagnostics")

	if not onlydiag:
		#Generating _CommsPLC_EPICS and global communication DBs
		WriteCommsEpicsAndDbs()

	#Write the output fo file
	if verify:
		externalPath = os.path.join(OutputDir, "PLCFactory_external_source_TIAv{tiaversion}_{timestamp}.scl".format(tiaversion = TIAVersion, timestamp = timestamp))
	else:
		externalPath = os.path.join(OutputDir, "PLCFactory_external_source_TIAv{tiaversion}.scl".format(tiaversion = TIAVersion))
	with open(externalPath, 'wb') as externalScl:
		for line in ExternalSourceFile:
			externalScl.write((line + '\r\n').encode())

	if onlydiag:
		print("NOTE:\nOnly diagnostics code is generated")

	generated_files["PROJECT_SCL"] = externalPath

	
	return generated_files


def main(argv):
	os.system('clear')

	print("  _____       _             __                 ______         _                   ")
	print(" |_   _|     | |           / _|               |  ____|       | |                  ")
	print("   | |  _ __ | |_ ___ _ __| |_ __ _  ___ ___  | |__ __ _  ___| |_ ___  _ __ _   _ ")
	print("   | | | '_ \| __/ _ \ '__|  _/ _` |/ __/ _ \ |  __/ _` |/ __| __/ _ \| '__| | | |")
	print("  _| |_| | | | ||  __/ |  | || (_| | (_|  __/ | | | (_| | (__| || (_) | |  | |_| |")
	print(" |_____|_| |_|\__\___|_|  |_| \__,_|\___\___| |_|  \__,_|\___|\__\___/|_|   \__, |")
	print("                                                                             __/ |")
	print(" Copyright 2017-2020, European Spallation Source, Lund                      |___/ \n")


	print("InterfaceFactory can't be run in standalone mode! Use PLCFactory instead.")
	print()
	print()

if __name__ == "__main__":
	main(sys.argv[1:])
