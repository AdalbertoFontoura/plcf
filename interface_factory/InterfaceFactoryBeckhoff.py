from __future__ import print_function
from __future__ import absolute_import

""" InterfaceFactory : Entry point """

__author__     = "Miklos Boros"
__copyright__  = "Copyright 2017-2018, European Spallation Source, Lund"
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
import datetime
import os
import errno
import sys
import time
import shutil

# IFA modules
from . import IFA

# PLC Factory modules
import helpers
import plcf_glob as glob

#Global variables
ifa     = None
verify  = False
basedir = None

FC_EPICS_DEVICE_CALLS_HEADER = []
FC_EPICS_DEVICE_CALLS_BODY = []
FC_EPICS_DEVICE_CALLS_FOOTER = []

DevTypeHeader = []
DevTypeVAR_INPUT = []
DevTypeVAR_OUTPUT = []
DevTypeVAR_TEMP = []
DevTypeBODY_HEADER = []
DevTypeBODY_CODE = []
DevTypeBODY_FOOTER = []

EPICS_GVL = []
EPICS_GVL_DEVICES = []
FB_EPICS_S7_Comm = []
FB_Pulse = []
ST_2_UINT = []
U_DINT_UINT = []
U_REAL_UINT = []
U_TIME_UINT = []
EPICS_PLC_TesterDB = []


ActualDeviceName = ""
ActualDeviceNameWhite = ""
ActualDeviceType = ""
EPICSTOPLCLENGTH = ""
EPICSTOPLCDATABLOCKOFFSET = ""
PLCTOEPICSDATABLOCKOFFSET = ""
DeviceTypeList = []


DeviceInstance = []

EndString = ""
EndString2 = ""
IsDouble = False

MaxStatusReg = 0
MaxCommandReg = 0

TotalStatusReg = 0
TotalCommandReg = 0


Direct = False
OutputDirectory = ""

GlobalIDCounter = 0


def WriteEPICS_PLC_TesterDB():

	global EPICS_PLC_TesterDB
	global ExternalSourceFile


	ExternalSourceFile.extend(EPICS_PLC_TesterDB)


	EPICS_PLC_TesterDB = []

def Write_EPICS_device_calls():

	global OutputDirectory
	global FC_EPICS_DEVICE_CALLS_HEADER
	global FC_EPICS_DEVICE_CALLS_BODY
	global FC_EPICS_DEVICE_CALLS_FOOTER

	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","EPICS calls", "FC_EPICS_DEVICE_CALLS.TcPOU")
	with open(externalPath, 'wb') as externalScl:
		for line in FC_EPICS_DEVICE_CALLS_HEADER:
			externalScl.write((line + '\r\n').encode())

		for line in FC_EPICS_DEVICE_CALLS_BODY:
			externalScl.write((line + '\r\n').encode())


		for line in FC_EPICS_DEVICE_CALLS_FOOTER:
			externalScl.write((line + '\r\n').encode())

	FC_EPICS_DEVICE_CALLS_HEADER = []
	FC_EPICS_DEVICE_CALLS_BODY = []
	FC_EPICS_DEVICE_CALLS_FOOTER = []

def Write_EPICS_GVL():
	global EPICS_GVL
	global EPICS_GVL_DEVICES
	global TotalStatusReg
	global TotalCommandReg

	EPICS_GVL.append("	aDataS7				: ARRAY [0.."+str(TotalStatusReg-1)+"] OF UINT; 			//Array of data sent to EPICS")
	EPICS_GVL.append("	aDataModbus			AT %MW0 :ARRAY [0.."+str(TotalCommandReg-1)+"] OF UINT;		//Array of data from EPICS. Corresponds to Modbus address 12289 1-based addressing. (122988 0-based)")
	EPICS_GVL.append("	FB_EPICS_S7_Comm 	: FB_EPICS_S7_Comm;					//EPICS TCP/IP communication function block")
	EPICS_GVL.append("	EasyTester			: DINT;								//Test variable for EasyTester")
	EPICS_GVL.append("END_VAR")
	EPICS_GVL.append("]]>")
	EPICS_GVL.append("</Declaration>")
	EPICS_GVL.append("</GVL>")
	EPICS_GVL.append("</TcPlcObject>")
	EPICS_GVL.append("")

	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","ESS standard PLC code", "EPICS_GVL.TcGVL")
	with open(externalPath, 'wb') as externalScl:
		for line in EPICS_GVL:
			externalScl.write((line + '\r\n').encode())

	EPICS_GVL = []

def Write_Structs_and_Unions():

	global OutputDirectory
	global ST_2_UINT
	global U_DINT_UINT
	global U_REAL_UINT
	global U_TIME_UINT
	global GlobalIDCounter

	ST_2_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	ST_2_UINT.append("<TcPlcObject ")
	ST_2_UINT.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
	ST_2_UINT.append("<DUT ")
	GlobalIDCounter = GlobalIDCounter + 1
	ST_2_UINT.append("Name=\"ST_2_UINT\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">")
	ST_2_UINT.append("<Declaration>")
	ST_2_UINT.append("<![CDATA[")
	ST_2_UINT.append("TYPE ST_2_UINT :")
	ST_2_UINT.append("STRUCT")
	ST_2_UINT.append("	nLow	:UINT;")
	ST_2_UINT.append("	nHigh	:UINT;")
	ST_2_UINT.append("END_STRUCT")
	ST_2_UINT.append("END_TYPE")
	ST_2_UINT.append("]]>")
	ST_2_UINT.append("</Declaration>")
	ST_2_UINT.append("</DUT>")
	ST_2_UINT.append("</TcPlcObject>	")

	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","ESS standard PLC code", "ST_2_UINT.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in ST_2_UINT:
			externalScl.write((line + '\r\n').encode())

	U_DINT_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	U_DINT_UINT.append("<TcPlcObject ")
	U_DINT_UINT.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
	U_DINT_UINT.append("<DUT ")
	GlobalIDCounter = GlobalIDCounter + 1
	U_DINT_UINT.append("Name=\"U_DINT_UINTs\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">")
	U_DINT_UINT.append("<Declaration>")
	U_DINT_UINT.append("<![CDATA[")
	U_DINT_UINT.append("TYPE U_DINT_UINTs :")
	U_DINT_UINT.append("UNION")
	U_DINT_UINT.append("	stLowHigh	:ST_2_UINT;")
	U_DINT_UINT.append("	nValue		:DINT;")
	U_DINT_UINT.append("END_UNION")
	U_DINT_UINT.append("END_TYPE")
	U_DINT_UINT.append("]]>")
	U_DINT_UINT.append("</Declaration>")
	U_DINT_UINT.append("</DUT>")
	U_DINT_UINT.append("</TcPlcObject>		")

	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","ESS standard PLC code", "U_DINT_UINTs.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in U_DINT_UINT:
			externalScl.write((line + '\r\n').encode())

	U_REAL_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	U_REAL_UINT.append("<TcPlcObject ")
	U_REAL_UINT.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
	U_REAL_UINT.append("<DUT ")
	GlobalIDCounter = GlobalIDCounter + 1
	U_REAL_UINT.append("Name=\"U_REAL_UINTs\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">")
	U_REAL_UINT.append("<Declaration>")
	U_REAL_UINT.append("<![CDATA[")
	U_REAL_UINT.append("TYPE U_REAL_UINTs :")
	U_REAL_UINT.append("UNION")
	U_REAL_UINT.append("	stLowHigh	:ST_2_UINT;")
	U_REAL_UINT.append("	fValue		:REAL;")
	U_REAL_UINT.append("END_UNION")
	U_REAL_UINT.append("END_TYPE")
	U_REAL_UINT.append("]]>")
	U_REAL_UINT.append("</Declaration>")
	U_REAL_UINT.append("</DUT>")
	U_REAL_UINT.append("</TcPlcObject>")
	U_REAL_UINT.append("")

	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","ESS standard PLC code", "U_REAL_UINTs.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in U_REAL_UINT:
			externalScl.write((line + '\r\n').encode())

	U_TIME_UINT.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	U_TIME_UINT.append("<TcPlcObject Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
	U_TIME_UINT.append("<DUT ")
	GlobalIDCounter = GlobalIDCounter + 1
	U_TIME_UINT.append("Name=\"U_TIME_UINTs\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">")
	U_TIME_UINT.append("<Declaration>")
	U_TIME_UINT.append("<![CDATA[")
	U_TIME_UINT.append("TYPE U_TIME_UINTs :")
	U_TIME_UINT.append("UNION")
	U_TIME_UINT.append("	stLowHigh	:ST_2_UINT;")
	U_TIME_UINT.append("	tValue		:TIME;")
	U_TIME_UINT.append("END_UNION")
	U_TIME_UINT.append("END_TYPE")
	U_TIME_UINT.append("]]>")
	U_TIME_UINT.append("</Declaration>")
	U_TIME_UINT.append("</DUT>")
	U_TIME_UINT.append("</TcPlcObject>")


	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","ESS standard PLC code", "U_TIME_UINTs.TcDUT")
	with open(externalPath, 'wb') as externalScl:
		for line in U_TIME_UINT:
			externalScl.write((line + '\r\n').encode())

	ST_2_UINT = []
	U_DINT_UINT = []
	U_REAL_UINT = []
	U_TIME_UINT = []

def Write_FB_EPICS_S7_Comm():

	global FB_EPICS_S7_Comm
	global GlobalIDCounter

	FB_EPICS_S7_Comm.append

	FB_EPICS_S7_Comm.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	FB_EPICS_S7_Comm.append("<TcPlcObject Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.18\">")
	GlobalIDCounter = GlobalIDCounter + 1
	FB_EPICS_S7_Comm.append("  <POU Name=\"FB_EPICS_S7_Comm\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">")
	FB_EPICS_S7_Comm.append("    <Declaration><![CDATA[")
	FB_EPICS_S7_Comm.append("FUNCTION_BLOCK FB_EPICS_S7_Comm")
	FB_EPICS_S7_Comm.append("VAR_INPUT")
	FB_EPICS_S7_Comm.append("	sLocalHost		:STRING(15)	:= '';			// PLC IP. Local if empty")
	FB_EPICS_S7_Comm.append("	sRemoteHost		:STRING(15)	:= '';			// EPICS IOC. Local if empty")
	FB_EPICS_S7_Comm.append("	nS7Port			:UDINT		:= 2000;		//Server port. Leave empty for default 2000")
	FB_EPICS_S7_Comm.append("	nPLC_Hash		:DINT;					//Hash written during XML generation at PLC factory")
	FB_EPICS_S7_Comm.append("	tSendTrig		:TIME		:= T#200MS;		//Frequency of pushed data")
	FB_EPICS_S7_Comm.append("	")
	FB_EPICS_S7_Comm.append("END_VAR")
	FB_EPICS_S7_Comm.append("VAR_OUTPUT")
	FB_EPICS_S7_Comm.append("	nCase			:INT		:= 0;			//Status. 0=Init, 1=Close conn., 2=Listen, 3=Accept, 4=Send data")
	FB_EPICS_S7_Comm.append("	bConnected		:BOOL;					//TCP/IP connection accepted")
	FB_EPICS_S7_Comm.append("	bError			:BOOL;					//Error in connection")
	FB_EPICS_S7_Comm.append("END_VAR")
	FB_EPICS_S7_Comm.append("VAR")
	FB_EPICS_S7_Comm.append("	sSrvNetID		:T_AmsNetId	:= '';			// Local ID if empty")
	FB_EPICS_S7_Comm.append("	bConnectEpics		:BOOL		:= TRUE;		//Open or closes TCP/IP connection")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	fb_SocketCloseAll	:FB_SocketCloseAll;")
	FB_EPICS_S7_Comm.append("	bCloseAll		:BOOL;")
	FB_EPICS_S7_Comm.append("	bCloseAllBusy		:BOOL;")
	FB_EPICS_S7_Comm.append("	bCloseAllError		:BOOL;")
	FB_EPICS_S7_Comm.append("	nCloseAllErrID		:UDINT;")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	hServer			:T_HSERVER;")
	FB_EPICS_S7_Comm.append("	bListen			:BOOL;")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	fbServerConnection	:FB_ServerClientConnection;")
	FB_EPICS_S7_Comm.append("	bSvrConnect		:BOOL;")
	FB_EPICS_S7_Comm.append("	bSvrBusy		:BOOL;")
	FB_EPICS_S7_Comm.append("	bSvrError		:BOOL;")
	FB_EPICS_S7_Comm.append("	nSvrErrID		:UDINT;")
	FB_EPICS_S7_Comm.append("	hSocket			:T_HSOCKET;")
	FB_EPICS_S7_Comm.append("	eSvrState		:E_SocketConnectionState;")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	fb_SocketSend		:FB_SocketSend;")
	FB_EPICS_S7_Comm.append("	bSend			:BOOL;")
	FB_EPICS_S7_Comm.append("	bSendBusy		:BOOL;")
	FB_EPICS_S7_Comm.append("	bSendError		:BOOL;")
	FB_EPICS_S7_Comm.append("	nSendErrID		:UDINT;")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	f_bConnectEpics		:F_TRIG;")
	FB_EPICS_S7_Comm.append("	t_Init			:TON;")
	FB_EPICS_S7_Comm.append("	//tInitTime		:TIME:= T#3S;")
	FB_EPICS_S7_Comm.append("	t_Push			:TON;")
	FB_EPICS_S7_Comm.append("	nNumberOfErr		:INT:=0;")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	//blink & counter functions")
	FB_EPICS_S7_Comm.append("	fb_Pulse		:FB_Pulse;		//Pulse/counter function block")
	FB_EPICS_S7_Comm.append("	nCount			:UINT;")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	i			:INT:=3;		//index for filling data array loop")
	FB_EPICS_S7_Comm.append("	nPLC_HashH		:UINT;			//Least significant part of the hash")
	FB_EPICS_S7_Comm.append("	nPLC_HashL		:UINT;			//Most significant part of the hash")
	FB_EPICS_S7_Comm.append("END_VAR")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("]]>")
	FB_EPICS_S7_Comm.append("    </Declaration>")
	FB_EPICS_S7_Comm.append("    <Implementation>")
	FB_EPICS_S7_Comm.append("      <ST><![CDATA[(*")
	FB_EPICS_S7_Comm.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************")
	FB_EPICS_S7_Comm.append("TCP/IP server on Bechoff for EPICS<--Beckhoff communication flow.")
	FB_EPICS_S7_Comm.append("Modbus Server on Beckhoff for EPICS-->Beckhoff communication flow.")
	FB_EPICS_S7_Comm.append("Created by: Andres Quintanilla (andres.quintanilla@esss.se)")
	FB_EPICS_S7_Comm.append("            Miklos Boros (miklos.boros@esss.se)")
	FB_EPICS_S7_Comm.append("Date: 06/04/2018")
	FB_EPICS_S7_Comm.append("Notes: TCP/IP server pushes data to the EPICS IOC connected. Modbus connection is open for R/W.")
	FB_EPICS_S7_Comm.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.")
	FB_EPICS_S7_Comm.append("Functionality: ")
	FB_EPICS_S7_Comm.append("Step 0: Reset all flags to start sequence")
	FB_EPICS_S7_Comm.append("Step 1: Close all previous connections")
	FB_EPICS_S7_Comm.append("Step 2: Initialize TCP/Ip server Listener")
	FB_EPICS_S7_Comm.append("Step 3: Accept any incoming connection request. Matching connection is validated via the input nPLC Hash at EPICS level.")
	FB_EPICS_S7_Comm.append("Step 4: Sends data to epics constantly using input tSendTrig as frequency")
	FB_EPICS_S7_Comm.append("**********************************************************************************************************")
	FB_EPICS_S7_Comm.append("*)")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("CASE nCase OF ")
	FB_EPICS_S7_Comm.append("	0:// Reset all flags to start sequence")
	FB_EPICS_S7_Comm.append("	bCloseAll		:=FALSE;")
	FB_EPICS_S7_Comm.append("	bListen 		:=FALSE;")
	FB_EPICS_S7_Comm.append("	bSvrConnect		:=FALSE;")
	FB_EPICS_S7_Comm.append("	bSend 			:=FALSE;")
	FB_EPICS_S7_Comm.append("	t_Init.IN		:=FALSE;")
	FB_EPICS_S7_Comm.append("	t_Push.IN		:=FALSE;")
	FB_EPICS_S7_Comm.append("	nNumberOfErr		:=0;")
	FB_EPICS_S7_Comm.append("	IF bConnectEpics THEN")
	FB_EPICS_S7_Comm.append("		nCase := nCase + 1;")
	FB_EPICS_S7_Comm.append("	END_IF")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	1:// Close all previous connections")
	FB_EPICS_S7_Comm.append("	t_Init.PT	:= T#3S;")
	FB_EPICS_S7_Comm.append("	t_Init.IN	:= TRUE;")
	FB_EPICS_S7_Comm.append("	bCloseAll	:= TRUE;")
	FB_EPICS_S7_Comm.append("	IF NOT bCloseAllBusy AND T_Init.Q AND NOT bSvrBusy THEN")
	FB_EPICS_S7_Comm.append("		T_Init.IN	:= FALSE;")
	FB_EPICS_S7_Comm.append("		bCloseAll	:= FALSE;")
	FB_EPICS_S7_Comm.append("		nCase		:= nCase + 1;")
	FB_EPICS_S7_Comm.append("	END_IF")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	2:// Initialize TCP/IP server Listener")
	FB_EPICS_S7_Comm.append("	bListen	:= TRUE;")
	FB_EPICS_S7_Comm.append("	nCase	:= nCase + 1;")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	3:// Start server and wait to accept a connection")
	FB_EPICS_S7_Comm.append("	t_Init.PT	:= T#600S;")
	FB_EPICS_S7_Comm.append("	t_Init.IN	:= TRUE;")
	FB_EPICS_S7_Comm.append("	bSvrConnect	:= TRUE;")
	FB_EPICS_S7_Comm.append("	IF eSvrState = eSOCKET_CONNECTED AND NOT bSvrBusy THEN")
	FB_EPICS_S7_Comm.append("		t_Init.IN		:= FALSE;")
	FB_EPICS_S7_Comm.append("		nCase			:= nCase + 1;")
	FB_EPICS_S7_Comm.append("	END_IF")
	FB_EPICS_S7_Comm.append("	IF t_Init.Q THEN")
	FB_EPICS_S7_Comm.append("		t_Init.IN		:= FALSE;")
	FB_EPICS_S7_Comm.append("		bListen			:= FALSE;")
	FB_EPICS_S7_Comm.append("		bSvrConnect		:= FALSE;")
	FB_EPICS_S7_Comm.append("		nCase			:= 0;")
	FB_EPICS_S7_Comm.append("	END_IF")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("	4:// Push data to EPICS")
	FB_EPICS_S7_Comm.append("	t_Push.IN	:= TRUE;")
	FB_EPICS_S7_Comm.append("	bSend 		:= TRUE;")
	FB_EPICS_S7_Comm.append("	IF t_Push.Q THEN")
	FB_EPICS_S7_Comm.append("		t_Push.IN	:= FALSE;")
	FB_EPICS_S7_Comm.append("		bSend 		:= FALSE;")
	FB_EPICS_S7_Comm.append("		IF bSendError THEN")
	FB_EPICS_S7_Comm.append("			nNumberOfErr	:= nNumberOfErr + 1;	")
	FB_EPICS_S7_Comm.append("		END_IF")
	FB_EPICS_S7_Comm.append("	END_IF")
	FB_EPICS_S7_Comm.append("	IF nNumberOfErr = 20 THEN")
	FB_EPICS_S7_Comm.append("		t_Push.IN	:= FALSE;")
	FB_EPICS_S7_Comm.append("		bSend 		:= FALSE;")
	FB_EPICS_S7_Comm.append("		bListen		:= FALSE;")
	FB_EPICS_S7_Comm.append("		bSvrConnect	:= FALSE;")
	FB_EPICS_S7_Comm.append("		nNumberOfErr	:= 0;")
	FB_EPICS_S7_Comm.append("		nCase		:= 0;")
	FB_EPICS_S7_Comm.append("	END_IF")
	FB_EPICS_S7_Comm.append("END_CASE")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("//Prepares array to be sent")
	FB_EPICS_S7_Comm.append("nPLC_HashL := DINT_TO_UINT(SHR(nPLC_Hash,16));")
	FB_EPICS_S7_Comm.append("nPLC_HashH := DINT_TO_UINT(nPLC_Hash);")
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataS7[{}]:=nPLC_HashL;".format(IFA.PLCTOEPICS_HASH + 1))
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataS7[{}]:=nPLC_HashH;".format(IFA.PLCTOEPICS_HASH))
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataS7[{}]:=nCount;".format(IFA.PLCTOEPICS_HEARTBEAT))
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("// Send the PLC parameter upload status to the EPICS IOC")
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataS7[{}]:=EPICS_GVL.aDataModbus[{}];".format(IFA.PLCTOEPICS_UPLOADSTAT, IFA.EPICSTOPLC_UPLOADSTAT))
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("//Put the HASH to modbus map")
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataModbus[{}]:=nPLC_HashL;".format(IFA.EPICSTOPLC_READ_HASH + 1))
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataModbus[{}]:=nPLC_HashH;".format(IFA.EPICSTOPLC_READ_HASH))
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("// Put the payload size (in bytes) into the Modbus map")
	FB_EPICS_S7_Comm.append("EPICS_GVL.aDataModbus[{}]:={};".format(IFA.EPICSTOPLC_READ_PAYLOAD_SIZE, ifa.TOTALPLCTOEPICSLENGTH * 2))
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("//TCP IP communication function blocks")
	FB_EPICS_S7_Comm.append("F_CreateServerHnd(")
	FB_EPICS_S7_Comm.append("	sSrvNetID 	:=sSrvNetID,")
	FB_EPICS_S7_Comm.append("	sLocalHost 	:=sLocalHost,")
	FB_EPICS_S7_Comm.append("	nLocalPort	:=nS7Port,")
	FB_EPICS_S7_Comm.append("	nMode		:=LISTEN_MODE_CLOSEALL,")
	FB_EPICS_S7_Comm.append("	bEnable		:=bListen,")
	FB_EPICS_S7_Comm.append("	hServer		:=hServer);")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("fbServerConnection(")
	FB_EPICS_S7_Comm.append("	hServer	:= hServer,")
	FB_EPICS_S7_Comm.append("	eMode	:= eACCEPT_ALL,")
	FB_EPICS_S7_Comm.append("	sRemoteHost:= sRemoteHost,")
	FB_EPICS_S7_Comm.append("	nRemotePort:=nS7Port,")
	FB_EPICS_S7_Comm.append("	bEnable	:= bSvrConnect,")
	FB_EPICS_S7_Comm.append("	tReconnect	:= T#3S,")
	FB_EPICS_S7_Comm.append("	bBusy		=>bSvrBusy,")
	FB_EPICS_S7_Comm.append("	bError		=>bSvrError,")
	FB_EPICS_S7_Comm.append("	nErrID		=>nSvrErrID,")
	FB_EPICS_S7_Comm.append("	hSocket		=>hSocket,")
	FB_EPICS_S7_Comm.append("	eState		=>eSvrState);")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("fb_SocketCloseAll(")
	FB_EPICS_S7_Comm.append("	sSrvNetId:=sSrvNetID,")
	FB_EPICS_S7_Comm.append("	bExecute:=bCloseAll,")
	FB_EPICS_S7_Comm.append("	tTimeout:=T#5S,")
	FB_EPICS_S7_Comm.append("	bBusy=>bCloseAllBusy,")
	FB_EPICS_S7_Comm.append("	bError=>bCloseAllError,")
	FB_EPICS_S7_Comm.append("	nErrId=>nCloseAllErrID);")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("fb_SocketSend(")
	FB_EPICS_S7_Comm.append("	sSrvNetId:=sSrvNetID,")
	FB_EPICS_S7_Comm.append("	hSocket:=hSocket,")
	FB_EPICS_S7_Comm.append("	cbLen:=SIZEOF(EPICS_GVL.aDataS7),")
	FB_EPICS_S7_Comm.append("	pSrc:=ADR(EPICS_GVL.aDataS7),")
	FB_EPICS_S7_Comm.append("	bExecute:=bSend,")
	FB_EPICS_S7_Comm.append("	tTimeout:=T#5S,")
	FB_EPICS_S7_Comm.append("	bBusy=>bSendBusy,")
	FB_EPICS_S7_Comm.append("	bError=>bSendError,")
	FB_EPICS_S7_Comm.append("	nErrId=>nSendErrID);")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("//Counter function")
	FB_EPICS_S7_Comm.append("IF nCase = 4 THEN ")
	FB_EPICS_S7_Comm.append("	fb_Pulse.bEn := TRUE;")
	FB_EPICS_S7_Comm.append("	ELSE")
	FB_EPICS_S7_Comm.append("	fb_Pulse.bEn := FALSE;")
	FB_EPICS_S7_Comm.append("END_IF")
	FB_EPICS_S7_Comm.append("fb_Pulse(bEn:= , tTimePulse:=T#1S , bPulse=> , nCount=>nCount );")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("//Triggers")
	FB_EPICS_S7_Comm.append("f_bConnectEpics(CLK:=bConnectEpics, Q=>);")
	FB_EPICS_S7_Comm.append("IF f_bConnectEpics.Q THEN")
	FB_EPICS_S7_Comm.append("	nCase	:= 0;")
	FB_EPICS_S7_Comm.append("END_IF")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("//Timers")
	FB_EPICS_S7_Comm.append("t_Init(IN:=, PT:=);")
	FB_EPICS_S7_Comm.append("t_Push(IN:=, PT:=tSendTrig);")
	FB_EPICS_S7_Comm.append("")
	FB_EPICS_S7_Comm.append("//Outputs")
	FB_EPICS_S7_Comm.append("bConnected	:= eSvrState = eSOCKET_CONNECTED AND nCase = 4 AND NOT bSendError;")
	FB_EPICS_S7_Comm.append("bError		:= bCloseAllError OR bSvrError OR bSendError;")
	FB_EPICS_S7_Comm.append("]]>")
	FB_EPICS_S7_Comm.append("      </ST>")
	FB_EPICS_S7_Comm.append("    </Implementation>")
	FB_EPICS_S7_Comm.append("  </POU>")
	FB_EPICS_S7_Comm.append("</TcPlcObject>")

	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","ESS standard PLC code", "FB_EPICS_S7_Comm.TcPOU")
	with open(externalPath, 'wb') as externalScl:
		for line in FB_EPICS_S7_Comm:
			externalScl.write((line + '\r\n').encode())

	FB_EPICS_S7_Comm = []

def Write_FB_Pulse():
	global FB_Pulse
	global GlobalIDCounter


	FB_Pulse.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	FB_Pulse.append("<TcPlcObject ")
	FB_Pulse.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
	FB_Pulse.append("<POU ")
	GlobalIDCounter = GlobalIDCounter + 1
	FB_Pulse.append("Name=\"FB_Pulse\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">")
	FB_Pulse.append("<Declaration>")
	FB_Pulse.append("<![CDATA[")
	FB_Pulse.append("FUNCTION_BLOCK FB_Pulse			//Pulse and counter function block")
	FB_Pulse.append("VAR_INPUT")
	FB_Pulse.append("	bEn			:BOOL;")
	FB_Pulse.append("	tTimePulse	:TIME:=t#1s;")
	FB_Pulse.append("END_VAR")
	FB_Pulse.append("VAR_OUTPUT")
	FB_Pulse.append("	bPulse		:BOOL;			//Frequency of Pulse, 50/50 pulse width")
	FB_Pulse.append("	nCount		:UINT;			//Count of pulses generated. Resets at 65535")
	FB_Pulse.append("END_VAR")
	FB_Pulse.append("VAR")
	FB_Pulse.append("	T_BlinkON	:TON;			//Timer function")
	FB_Pulse.append("	T_BlinkOFF	:TOF;			//Timer function")
	FB_Pulse.append("	cCounter	:CTU;			//Counter up function")
	FB_Pulse.append("	")
	FB_Pulse.append("END_VAR")
	FB_Pulse.append("]]>")
	FB_Pulse.append("</Declaration>")
	FB_Pulse.append("<Implementation>")
	FB_Pulse.append("<ST>")
	FB_Pulse.append("<![CDATA[")
	FB_Pulse.append("(*")
	FB_Pulse.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************")
	FB_Pulse.append("Poulse generator for sending data to the IOC")
	FB_Pulse.append("Created by: Andres Quintanilla (andres.quintanilla@esss.se)")
	FB_Pulse.append("            Miklos Boros (miklos.boros@esss.se)")
	FB_Pulse.append("Date: 04/04/2018")
	FB_Pulse.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.")
	FB_Pulse.append("Versions:")
	FB_Pulse.append("Version 1: 06/04/2018. Communication stablished and stable")
	FB_Pulse.append("**********************************************************************************************************")
	FB_Pulse.append("*)")
	FB_Pulse.append("")
	FB_Pulse.append("T_BlinkON (IN:=bEn AND NOT T_BlinkOFF.Q, PT:=tTimePulse/2);")
	FB_Pulse.append("T_BlinkOFF(IN:=T_BlinkON.Q, PT:=tTimePulse/2, Q=>bPulse);")
	FB_Pulse.append("")
	FB_Pulse.append("cCounter(CU:=bPulse,")
	FB_Pulse.append("		Reset:=,")
	FB_Pulse.append("		PV:=,")
	FB_Pulse.append("		Q:=,")
	FB_Pulse.append("		CV=>nCount);")
	FB_Pulse.append("IF nCount = 65530 THEN")
	FB_Pulse.append("	cCounter.RESET := TRUE;")
	FB_Pulse.append("ELSE")
	FB_Pulse.append("	cCounter.RESET := FALSE;")
	FB_Pulse.append("END_IF")
	FB_Pulse.append("]]>")
	FB_Pulse.append("</ST>")
	FB_Pulse.append("</Implementation>")
	FB_Pulse.append("</POU>")
	FB_Pulse.append("</TcPlcObject>")

	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","ESS standard PLC code", "FB_Pulse.TcPOU")
	with open(externalPath, 'wb') as externalScl:
		for line in FB_Pulse:
			externalScl.write((line + '\r\n').encode())

	FB_Pulse = []

def Write_DevType():

	global ActualDeviceType

	global DevTypeHeader
	global DevTypeVAR_INPUT
	global DevTypeVAR_OUTPUT
	global DevTypeVAR_TEMP
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_FOOTER

	global MaxStatusReg
	global MaxCommandReg
	externalPath = os.path.join(OutputDirectory,basedir,"EPICS","EPICS types", "FB_DEVTYPE_"+helpers.sanitizeFilename(ActualDeviceType)+".TcPOU")
	with open(externalPath, 'wb') as externalScl:
		#DevTypeHeader
		for line in DevTypeHeader:
			externalScl.write((line + '\r\n').encode())
		#DevTypeVAR_INPUT
		externalScl.write(("VAR_INPUT" + '\r\n').encode())
		externalScl.write(("      nOffsetStatus	:INT;			//Offset for status variables"+ '\r\n').encode())
		externalScl.write(("	  nOffsetCmd   :INT;			//Offset for command variables"+ '\r\n').encode())
		for line in DevTypeVAR_INPUT:
			externalScl.write((line + '\r\n').encode())
		externalScl.write(("END_VAR" + '\r\n').encode())
		#DevTypeVAR_OUTPUT
		externalScl.write(("VAR_OUTPUT" + '\r\n').encode())
		for line in DevTypeVAR_OUTPUT:
			externalScl.write((line + '\r\n').encode())
		externalScl.write(("END_VAR" + '\r\n').encode())
		#DevTypeVAR_TEMP
		for line in DevTypeVAR_TEMP:
			externalScl.write((line + '\r\n').encode())
		#DevTypeBODY_HEADER
		for line in DevTypeBODY_HEADER:
			externalScl.write((line + '\r\n').encode())
		#DevTypeBODY_CODE
		for line in DevTypeBODY_CODE:
			externalScl.write((line + '\r\n').encode())
		#DevTypeBODY_FOOTER
		for line in DevTypeBODY_FOOTER:
			externalScl.write((line + '\r\n').encode())

	DevTypeHeader = []
	DevTypeVAR_INPUT = []
	DevTypeVAR_OUTPUT = []
	DevTypeVAR_TEMP = []
	DevTypeBODY_HEADER = []
	DevTypeBODY_CODE = []
	DevTypeBODY_FOOTER = []

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


def AddBOOL(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== BOOL TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
			DevTypeBODY_CODE.append("       nTempUINT." + str(ActVariableBitNumber)+ "           := "+ InArrayName + "[" +str(InArrayNum)+"];       //EPICSName: "+ActVariableEPICSName)
		else:
			DevTypeBODY_CODE.append("       nTempUINT." + str(ActVariableBitNumber)+ "           := "+ ActVariablePLCName + ";       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = "EPICS_GVL.aDataS7[nOffsetStatus + "+str(ActVariableArrayIndex) +"]    := nTempUINT;"
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       nTempUINT			:= EPICS_GVL.aDataModbus[nOffsetCmd + "+str(ActVariableArrayIndex)+"];")
		DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             :=     nTempUINT." + str(ActVariableBitNumber)+ ";       //EPICSName: "+ActVariableEPICSName)
		if variable.is_command():
			EndString = "if (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; END_IF"
		else:
			EndString = ""
		IsDouble = False

	return (InArrayNum, StartingRegister)


def AddBYTE(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== BYTE TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
			DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := BYTE_TO_UINT("+ InArrayName + "[" +str(InArrayNum)+"]);       //EPICSName: "+ActVariableEPICSName)
		else:
			DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := BYTE_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = ""
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             := UINT_TO_BYTE(EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]);       //EPICSName: "+ActVariableEPICSName)
		if variable.is_command():
			EndString = "if (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; END_IF"
		else:
			EndString = ""
		IsDouble = False

	return (InArrayNum, StartingRegister)


def AddINT(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== INT TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
			DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := INT_TO_UINT("+ InArrayName + "[" +str(InArrayNum)+"]);       //EPICSName: "+ActVariableEPICSName)
		else:
			DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := INT_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = ""
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             := UINT_TO_INT(EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]);       //EPICSName: "+ActVariableEPICSName)
		if variable.is_command():
			EndString = "if (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; END_IF"
		else:
			EndString = ""
		IsDouble = False

	return (InArrayNum, StartingRegister)

				#====== WORD TYPE ========
def AddWORD(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== WORD TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
			DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := WORD_TO_UINT("+ InArrayName + "[" +str(InArrayNum)+"]);       //EPICSName: "+ActVariableEPICSName)
		else:
			DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := WORD_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = ""
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		DevTypeBODY_CODE.append("       "+ActVariablePLCName+"             := UINT_TO_WORD(EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]);       //EPICSName: "+ActVariableEPICSName)
		if variable.is_command():
			EndString = "if (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; END_IF"
		else:
			EndString = ""
		IsDouble = False

	return (InArrayNum, StartingRegister)


def AddDINT(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== DINT TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       uDINT2UINTs.nValue :="+ ActVariablePLCName + ";")
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := uDINT2UINTs.stLowHigh.nLow;       //EPICSName: "+ActVariableEPICSName)
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := uDINT2UINTs.stLowHigh.nHigh;       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = ""
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		DevTypeBODY_CODE.append("       uUINTs2DINT.stLowHigh.nLow             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "];       //EPICSName: "+ActVariableEPICSName)
		DevTypeBODY_CODE.append("       uUINTs2DINT.stLowHigh.nHigh            := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex+1)+ "];       //EPICSName: "+ActVariableEPICSName)
		EndString =  ActVariablePLCName + "				:= uUINTs2DINT.nValue;"
		if variable.is_command():
			EndString += "\nif (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex+1)+ "]:=0; END_IF"
		IsDouble = False

	return (InArrayNum, StartingRegister)


def AddDWORD(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== DWORD TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := DWORD_TO_UINT("+ ActVariablePLCName + ");       //EPICSName: "+ActVariableEPICSName)
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := DWORD_TO_UINT(SHR("+ ActVariablePLCName + ",16));       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = ""
	elif variable.is_input():
		raise IFA.FatalException("DWORD is not supported for ModbusTCP")

	return (InArrayNum, StartingRegister)


def AddREAL(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== REAL TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       uREAL2UINTs.fValue :="+ ActVariablePLCName + ";")
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := uREAL2UINTs.stLowHigh.nLow;       //EPICSName: "+ActVariableEPICSName)
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := uREAL2UINTs.stLowHigh.nHigh;       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = ""
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		DevTypeBODY_CODE.append("       uUINTs2REAL.stLowHigh.nLow             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "];       //EPICSName: "+ActVariableEPICSName)
		DevTypeBODY_CODE.append("       uUINTs2REAL.stLowHigh.nHigh             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(int(ActVariableArrayIndex)+1)+ "];       //EPICSName: "+ActVariableEPICSName)
		EndString =  ActVariablePLCName + "				:= uUINTs2REAL.fValue;"
		if variable.is_command():
			EndString += "\nif (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex+1)+ "]:=0; END_IF"
		IsDouble = False

	return (InArrayNum, StartingRegister)


def AddTIME(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== TIME TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])

	if variable.is_output():
		if InArrayName is not None:
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
			DevTypeBODY_CODE.append("       uTIME2UINTs.tValue :="+ ActVariablePLCName + ";")
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex)+ "]           := uTIME2UINTs.stLowHigh.nLow;       //EPICSName: "+ActVariableEPICSName)
		DevTypeBODY_CODE.append("       EPICS_GVL.aDataS7[nOffsetStatus + " + str(int(ActVariableArrayIndex)+1)+ "]           := uTIME2UINTs.stLowHigh.nHigh;       //EPICSName: "+ActVariableEPICSName)
		IsDouble = False
		EndString = ""
	elif variable.is_input():
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
		DevTypeBODY_CODE.append("       uUINTs2TIME.stLowHigh.nLow             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "];       //EPICSName: "+ActVariableEPICSName)
		DevTypeBODY_CODE.append("       uUINTs2TIME.stLowHigh.nHigh             := EPICS_GVL.aDataModbus[nOffsetCmd + " + str(int(ActVariableArrayIndex)+1)+ "];       //EPICSName: "+ActVariableEPICSName)
		EndString =  ActVariablePLCName + "				:= uUINTs2TIME.tValue;"
		if variable.is_command():
			EndString += "\nif (EPICS_GVL.EasyTester <> 2) THEN EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex)+ "]:=0; EPICS_GVL.aDataModbus[nOffsetCmd + " + str(ActVariableArrayIndex+1)+ "]:=0; END_IF"
		IsDouble = False

	return (InArrayNum, StartingRegister)


def AddSTRING(variable, InArrayName, InArrayNum, StartingRegister):
	global DevTypeBODY_CODE
	global DevTypeBODY_CODE_ARRAY
	global EndString
	global EndString2
	global IsDouble

	#====== STRING TYPE ========
	ActVariablePLCName    = variable.properties["VARIABLE"]
	ActVariableEPICSName  = variable.properties["EPICS"]
	ActVariableType       = variable.properties["TYPE"]
	ActVariableArrayIndex = int(variable.properties["ARRAY_INDEX"])
	ActVariableBitNumber  = int(variable.properties["BIT_NUMBER"])
	ActStringLength       = variable.dimension()

	# 80 is the default size of a STRING
	# 255 is the size of a T_MaxString
	if ActStringLength > 80:
		raise IFA.FatalException("STRINGs longer than 80 characters are not guaranteed to work")

	if variable.is_output():
		if InArrayName is not None:
			raise IFA.FatalException("'Hybrid' PLC STRING arrays are not supported: " + InArrayName)
			InArrayNum = InArrayNum + 1
		if StartingRegister != ActVariableArrayIndex:
			CloseLastVariable()
			StartingRegister = ActVariableArrayIndex
			DevTypeBODY_CODE.append("")
#			DevTypeBODY_CODE.append("       // Clear the buffer of any residual data")
#			# Using SIZEOF() to make sure that we clear the whole string and that we have an extra '\0' character to use in the for loop below (i.e. when ActStringLength is odd)
#			DevTypeBODY_CODE.append("       MEMSET(ADR(sTempHStr), 0, SIZEOF(sTempHStr));")
#			DevTypeBODY_CODE.append("       STRNCPY(ADR(sTempHStr), ADR(" + ActVariablePLCName + "), " + str(ActStringLength) + ");")
#			# Copy the characters
#			# Have to use ActStringLength to make sure we don't overflow the allocated space in the buffer
#			DevTypeBODY_CODE.append("       FOR i:=0 TO " + str(ActStringLength - 1) + " BY 2 DO")
#			DevTypeBODY_CODE.append("            EPICS_GVL.aDataS7[nOffsetStatus + " + str(ActVariableArrayIndex) + " + i / 2] := SHL(TO_UINT(sTempHStr[i + 1]), 8) OR sTempHStr[i];       //EPICSName: "+ActVariableEPICSName)
#			DevTypeBODY_CODE.append("       END_FOR;")
#			DevTypeBODY_CODE.append("       // Alternative implementation")
			DevTypeBODY_CODE.append("       STRNCPY(ADR(EPICS_GVL.aDataS7) + SIZEOF(UINT) * (nOffsetStatus + " + str(ActVariableArrayIndex) + "), ADR(" + ActVariablePLCName + "), " + str(ActStringLength) + ");")
			IsDouble = False
			EndString = ""
	elif variable.is_input():
		raise IFA.FatalException("STRING is not supported for ModbusTCP")

	return (InArrayNum, StartingRegister)


def ProcessIFADevTypes(OutputDir):

	#Process IFA devices
	print("Processing .ifa file...")

	pulses = {
		"Pulse_100ms" : "100MS",
		"Pulse_200ms" : "200MS",
		"Pulse_400ms" : "400MS",
		"Pulse_500ms" : "500MS",
		"Pulse_800ms" : "800MS",
		"Pulse_1s" : "1000MS",
		"Pulse_1600ms" : "1600MS",
		"Pulse_2s" : "2000MS",
		}

	try:
		plc_pulse = pulses[ifa.PLC_PULSE]
	except KeyError:
		raise IFA.FatalException("Unknown PLC Pulse specification: {}".format(ifa.PLC_PULSE))

	ProcessedDeviceNum = 0

	global ActualDeviceName
	global ActualDeviceNameWhite
	global ActualDeviceType
	global EPICSTOPLCLENGTH
	global EPICSTOPLCDATABLOCKOFFSET
	global PLCTOEPICSDATABLOCKOFFSET
	global DeviceTypeList
	DeviceTypeList = []

	global DevTypeHeader
	global DevTypeVAR_INPUT
	global DevTypeVAR_OUTPUT
	global DevTypeVAR_TEMP
	global DevTypeBODY_HEADER
	global DevTypeBODY_CODE
	global DevTypeBODY_FOOTER

	global EPICS_PLC_TesterDB

	global FC_EPICS_DEVICE_CALLS_HEADER
	global FC_EPICS_DEVICE_CALLS_BODY
	global FC_EPICS_DEVICE_CALLS_FOOTER

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

	global MaxStatusReg
	global MaxCommandReg
	global TotalStatusReg
	global TotalCommandReg
	global GlobalIDCounter
	MaxStatusReg = 0
	MaxCommandReg = 0
	TotalStatusReg = 0
	TotalCommandReg = 0
	GlobalIDCounter = 0

	InArrayName = None
	InArrayNum  = None


	EPICS_GVL.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	EPICS_GVL.append("<TcPlcObject ")
	EPICS_GVL.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
	EPICS_GVL.append("<GVL ")
	GlobalIDCounter = GlobalIDCounter + 1
	EPICS_GVL.append("Name=\"EPICS_GVL\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\">")
	EPICS_GVL.append("<Declaration>")
	EPICS_GVL.append("<![CDATA[{attribute 'qualified_only'}")
	EPICS_GVL.append("VAR_GLOBAL")
	EPICS_GVL.append("(*")
	EPICS_GVL.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************")
	EPICS_GVL.append("TCP/IP server on Bechoff for EPICS<--Beckhoff communication flow.")
	EPICS_GVL.append("Modbus Server on Beckhoff for EPICS-->Beckhoff communication flow.")
	EPICS_GVL.append("//Created by: Andres Quintanilla (andres.quintanilla@esss.se)")
	EPICS_GVL.append("              Miklos Boros (miklos.boros@esss.se)")
	EPICS_GVL.append("Date: 06/04/2018")
	EPICS_GVL.append("Notes: TCP/IP server pushes data to the EPICS IOC connected. Modbus connection is open for R/W.")
	EPICS_GVL.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.")
	EPICS_GVL.append("Versions:")
	EPICS_GVL.append("Version 1: 06/04/2018. Communication stablished and stable")
	EPICS_GVL.append("**********************************************************************************************************")
	EPICS_GVL.append("*)")
	EPICS_GVL.append("")
	EPICS_GVL.append("//Global Variables used in EPICS<-->Beckhoff communication at ESS. ")

	FC_EPICS_DEVICE_CALLS_HEADER.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
	FC_EPICS_DEVICE_CALLS_HEADER.append("<TcPlcObject Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.18\">")
	GlobalIDCounter = GlobalIDCounter + 1
	FC_EPICS_DEVICE_CALLS_HEADER.append("  <POU Name=\"FC_EPICS_DEVICE_CALLS\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    <Declaration><![CDATA[")
	FC_EPICS_DEVICE_CALLS_HEADER.append("FUNCTION FC_EPICS_DEVICE_CALLS : BOOL")
	FC_EPICS_DEVICE_CALLS_HEADER.append("VAR_INPUT")
	FC_EPICS_DEVICE_CALLS_HEADER.append("	sPlcIp			:STRING(15)	:= '';			// PLC IP. Local if empty")
	FC_EPICS_DEVICE_CALLS_HEADER.append("	sEpicsIp		:STRING(15)	:= '';			// EPICS IOC IP.")
	FC_EPICS_DEVICE_CALLS_HEADER.append("END_VAR")
	FC_EPICS_DEVICE_CALLS_HEADER.append("VAR")
	FC_EPICS_DEVICE_CALLS_HEADER.append("END_VAR")
	FC_EPICS_DEVICE_CALLS_HEADER.append("]]>")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    </Declaration>")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    <Implementation>")
	FC_EPICS_DEVICE_CALLS_HEADER.append("      <ST><![CDATA[")
	FC_EPICS_DEVICE_CALLS_HEADER.append("EPICS_GVL.FB_EPICS_S7_Comm(")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    sLocalHost  := sPlcIp,")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    sRemoteHost := sEpicsIp,")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    nS7Port     := {},".format(ifa.S7_PORT))
	FC_EPICS_DEVICE_CALLS_HEADER.append("    nPLC_Hash   := {},".format(ifa.HASH))
	FC_EPICS_DEVICE_CALLS_HEADER.append("    tSendTrig   := T#{},".format(plc_pulse))
	FC_EPICS_DEVICE_CALLS_HEADER.append("    nCase=> ,")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    bConnected=> ,")
	FC_EPICS_DEVICE_CALLS_HEADER.append("    bError=> );")

	FC_EPICS_DEVICE_CALLS_FOOTER.append("]]>")
	FC_EPICS_DEVICE_CALLS_FOOTER.append("      </ST>")
	FC_EPICS_DEVICE_CALLS_FOOTER.append("    </Implementation>")
	FC_EPICS_DEVICE_CALLS_FOOTER.append("  </POU>")
	FC_EPICS_DEVICE_CALLS_FOOTER.append("</TcPlcObject>")


	TotalCommandReg = ifa.TOTALEPICSTOPLCLENGTH
	TotalStatusReg  = ifa.TOTALPLCTOEPICSLENGTH
	for device in ifa.Devices:
		ProcessedDeviceNum = ProcessedDeviceNum + 1

		ActualDeviceName = device.properties["DEVICE"]
		ActualDeviceType = device.properties["DEVICE_TYPE"]
		EPICSTOPLCLENGTH = device.properties["EPICSTOPLCLENGTH"]
		EPICSTOPLCDATABLOCKOFFSET = device.properties["EPICSTOPLCDATABLOCKOFFSET"]
		PLCTOEPICSDATABLOCKOFFSET = device.properties["PLCTOEPICSDATABLOCKOFFSET"]
		ActualDeviceNameWhite = ActualDeviceName

		Text = "Device: "+ ActualDeviceName + " Type: "+ ActualDeviceType
		print("    ", "-" * len(Text), sep='')
		print("    ", Text, sep='')
		print("    ", "-" * len(Text), sep='')

		ActualDeviceNameWhite = ActualDeviceNameWhite.replace(":","_")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace("/","")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace("\\","")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace("?","")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace("*","")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace("[","")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace("]","")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace(".","")
		ActualDeviceNameWhite = ActualDeviceNameWhite.replace("-","_")
		ActualDeviceType = ActualDeviceType.replace("-","_")
		ActualDeviceType = ActualDeviceType.replace(":","_")

		if (int(EPICSTOPLCDATABLOCKOFFSET)<12288):
			print("ERROR:")
			print("The PLCs modbus offset held by the property: PLCF#EPICSToPLCDataBlockStartOffset in CCDB is less then 12288! \n")
			print("Make sure your PLC in CCDB is PLC_BECKHOFF type instead of PLC! \n")
			print("--- %.1f seconds ---\n" % (time.time() - start_time))
			sys.exit()


		FC_EPICS_DEVICE_CALLS_BODY.append("")
		FC_EPICS_DEVICE_CALLS_BODY.append("//********************************************")
		FC_EPICS_DEVICE_CALLS_BODY.append("// Device name: "+ActualDeviceName)
		FC_EPICS_DEVICE_CALLS_BODY.append("// Device type: "+ActualDeviceType)
		FC_EPICS_DEVICE_CALLS_BODY.append("//********************************************")
		FC_EPICS_DEVICE_CALLS_BODY.append("")
		FC_EPICS_DEVICE_CALLS_BODY.append("EPICS_GVL.FB_DEV_"+ActualDeviceNameWhite+"(")
		FC_EPICS_DEVICE_CALLS_BODY.append("       nOffsetStatus:= "+str(int(PLCTOEPICSDATABLOCKOFFSET))+",")
		FC_EPICS_DEVICE_CALLS_BODY.append("       nOffsetCmd:="+str(int(EPICSTOPLCDATABLOCKOFFSET)-12288)+");")

		EPICS_GVL.append("	FB_DEV_"+ActualDeviceNameWhite+"	:FB_DEVTYPE_"+ActualDeviceType+";					//Device instance("+ActualDeviceName+")")

		#Check if DeviceType is already generated
		if ActualDeviceType not in DeviceTypeList:

			MaxStatusReg = 0
			MaxCommandReg = 0

			NewDeviceType = True
			DeviceTypeList.append(ActualDeviceType)
			print("    ->  New device type found. [", ActualDeviceType, "] Creating source code...", sep='')

			DevTypeHeader.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>")
			DevTypeHeader.append("<TcPlcObject ")
			DevTypeHeader.append("Version=\"1.1.0.1\" ProductVersion=\"3.1.4022.10\">")
			DevTypeHeader.append("<POU ")
			GlobalIDCounter = GlobalIDCounter + 1
			DevTypeHeader.append("Name=\"FB_DEVTYPE_"+ActualDeviceType+"\" Id=\"{5bb54db1-6fe3-4b17-2b0f-"+str(GlobalIDCounter).zfill(12)+"}\" SpecialFunc=\"None\">")
			DevTypeHeader.append("<Declaration>")
			DevTypeHeader.append("<![CDATA[")
			DevTypeHeader.append("FUNCTION_BLOCK FB_DEVTYPE_"+ActualDeviceType+"")

			DevTypeVAR_TEMP.append("VAR")
			DevTypeVAR_TEMP.append("	nTempUINT		:UINT;")
			DevTypeVAR_TEMP.append("	i			:INT;")
			DevTypeVAR_TEMP.append("	sTempHStr		:T_MaxString;")
			DevTypeVAR_TEMP.append("")
			DevTypeVAR_TEMP.append("	uREAL2UINTs	:U_REAL_UINTs;")
			DevTypeVAR_TEMP.append("	uUINTs2REAL	:U_REAL_UINTs;")
			DevTypeVAR_TEMP.append("	uTIME2UINTs	:U_TIME_UINTs;")
			DevTypeVAR_TEMP.append("	uUINTs2TIME	:U_TIME_UINTs;")
			DevTypeVAR_TEMP.append("	uDINT2UINTs	:U_DINT_UINTs;")
			DevTypeVAR_TEMP.append("	uUINTs2DINT	:U_DINT_UINTs;")
			DevTypeVAR_TEMP.append("	fValue: INT;")
			DevTypeVAR_TEMP.append("END_VAR")

			DevTypeBODY_HEADER.append("")
			DevTypeBODY_HEADER.append("]]>")
			DevTypeBODY_HEADER.append("</Declaration>")
			DevTypeBODY_HEADER.append("<Implementation>")
			DevTypeBODY_HEADER.append("<ST>")
			DevTypeBODY_HEADER.append("<![CDATA[")
			DevTypeBODY_HEADER.append("(*")
			DevTypeBODY_HEADER.append("**********************EPICS<-->Beckhoff integration at ESS in Lund, Sweden*******************************")
			DevTypeBODY_HEADER.append("Data types handler for TCP/IP communication EPICS<--Beckhoff at ESS. Lund, Sweden.")
			DevTypeBODY_HEADER.append("Created by: Andres Quintanilla (andres.quintanilla@esss.se)")
			DevTypeBODY_HEADER.append("            Miklos Boros (miklos.boros@esss.se)")
			DevTypeBODY_HEADER.append("Notes: Converts different types of data into UINT. Adds the converted data into the array to be sent to EPICS.")
			DevTypeBODY_HEADER.append("The first 10 spaces of the array are reserved. nOffset input is used for that. ")
			DevTypeBODY_HEADER.append("Code must not be changed manually. Code is generated and handled by PLC factory at ESS.")
			DevTypeBODY_HEADER.append("Versions:")
			DevTypeBODY_HEADER.append("Version 1: 06/04/2018. Communication stablished and stable")
			DevTypeBODY_HEADER.append("**********************************************************************************************************")
			DevTypeBODY_HEADER.append("*)")


			DevTypeBODY_FOOTER.append("")
			DevTypeBODY_FOOTER.append("]]>")
			DevTypeBODY_FOOTER.append("</ST>")
			DevTypeBODY_FOOTER.append("</Implementation>")
			DevTypeBODY_FOOTER.append("</POU>")
			DevTypeBODY_FOOTER.append("</TcPlcObject>")
		else:
			NewDeviceType = False

#		for line in device.comments:
#			DevTypeBODY_CODE.append("       " + line)

		for item in device:
			if item.is_wrapper_array():
				if item.is_start():
					InArrayName = item.name()
					InArrayNum  = 0
				else:
					DevTypeVAR_INPUT.append("      " + InArrayName + " : Array[1.."+ str(InArrayNum) +"] OF "+ ActVariableType+";   //EPICS Status variables defined in an array")
					InArrayName = None
					InArrayNum  = None

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

				#Close the last variable if there is a new variable
				if 	LastVariableType != ActVariableType:
					LastVariableType = ActVariableType
					CloseLastVariable()

				if item.is_status():
					if InArrayName is None:
						DevTypeVAR_INPUT.append("      " + ActVariablePLCName +"  :"+ ActVariableType+";        //EPICS Status variable: "+ActVariableEPICSName)

				elif item.is_command():
					DevTypeVAR_OUTPUT.append("      " + ActVariablePLCName +"  :"+ ActVariableType+";        //EPICS Command variable: "+ActVariableEPICSName)

				elif item.is_parameter():
					DevTypeVAR_OUTPUT.append("      " + ActVariablePLCName +"  :"+ ActVariableType+";        //EPICS Parameter variable: "+ActVariableEPICSName)

				elif item.is_general_input():
					DevTypeVAR_OUTPUT.append("      " + ActVariablePLCName +"  :"+ ActVariableType+";        //EPICS General input variable: "+ActVariableEPICSName)

				else:
					raise IFA.FatalException("Unknown variable flavor: {}".format(item.name()))

				#SUPPORTED TYPES
				#PLC_types = {'BOOL', 'BYTE', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'TIME' }

				#====== BOOL TYPE ========
				if ActVariableType == "BOOL":
					InArrayNum, StartingRegister = AddBOOL(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== BYTE TYPE ========
				elif ActVariableType == "BYTE":
					InArrayNum, StartingRegister = AddBYTE(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== INT TYPE ========
				elif ActVariableType == "INT":
					InArrayNum, StartingRegister = AddINT(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== WORD TYPE ========
				elif ActVariableType == "WORD":
					InArrayNum, StartingRegister = AddWORD(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== DWORD TYPE ========
				elif ActVariableType == "DWORD":
					InArrayNum, StartingRegister = AddDWORD(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== REAL TYPE ========
				elif ActVariableType == "REAL":
					InArrayNum, StartingRegister = AddREAL(item, InArrayName, InArrayNum, StartingRegister)
				#==========================
				#====== DINT TYPE ========
				elif ActVariableType == "DINT":
					InArrayNum, StartingRegister = AddDINT(item, InArrayName, InArrayNum, StartingRegister)
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
					if not Direct:
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
		if NewDeviceType == True:
			Write_DevType()
		else:
			DevTypeHeader = []
			DevTypeVAR_INPUT = []
			DevTypeVAR_OUTPUT = []
			DevTypeVAR_TEMP = []
			DevTypeBODY_HEADER = []
			DevTypeBODY_CODE = []
			DevTypeBODY_FOOTER = []

	print("\nTotal", str(ProcessedDeviceNum), "device(s) processed.")
	if not Direct:
		print("Total", str(len(DeviceTypeList)), "device type(s) generated.\n")
	else:
		print("Device types are not being generated. (Direct mode)\n")


def produce(OutputDir, _ifa, **kwargs):

	global MakeOutputFile
	global OutputDirectory
	global TotalStatusReg
	global TotalCommandReg
	global start_time
	global ifa
	global verify
	global basedir

	print("""
*******************************************
*                                         *
*   Generating Beckhoff PLC source code   *
*                                         *
*******************************************
""")

	start_time      = time.time()
	OutputDirectory = OutputDir
	verify     = kwargs.get('verify', False)

	generated_files = dict()

	ifa = _ifa

	if ifa.GATEWAY_DATABLOCK is not None:
		raise IFA.FatalException("'gateway-mode' is not supported")

	if verify:
		basedir = "BECKHOFF_{}".format(glob.timestamp)
	else:
		basedir = "BECKHOFF"
	helpers.makedirs(os.path.join(OutputDirectory, basedir, "EPICS", "EPICS types"))
	helpers.makedirs(os.path.join(OutputDirectory, basedir, "EPICS", "EPICS calls"))
	helpers.makedirs(os.path.join(OutputDirectory, basedir, "EPICS", "ESS standard PLC code"))

	#Process devices/device types
	ProcessIFADevTypes(OutputDir)

	#Generate FC_EPICS_DEVICE_CALLS.TcPOU
	Write_EPICS_device_calls()

	#Generate ST_2_UINT.TcDUT
	#Generate U_DINT_UINTs.TcDUT
	#Generate U_REAL_UINTs.TcDUT
	#Generate U_TIME_UINTs.TcDUT
	Write_Structs_and_Unions()

	#Generate FB_EPICS_S7_Comm.TcPOU
	Write_FB_EPICS_S7_Comm()

	#Generate FB_Pulse.TcPOU
	Write_FB_Pulse()

	#Generate EPICS_GVL.TcGVL
	Write_EPICS_GVL()

	if verify:
		i = 0
		def add_to_generated(directory, i, generated):
			for f in os.listdir(directory):
				f = os.path.join(directory, f)
				if not os.path.isfile(f):
					i = add_to_generated(f, i, generated)
					continue
				generated_files['BECKHOFF_{}'.format(i)] = f
				i += 1
			return i

		add_to_generated(os.path.join(OutputDirectory, basedir), 0, generated_files)
	else:
		generated_files['BECKHOFF'] = shutil.make_archive(os.path.join(OutputDirectory, "PLCFactory_external_source_Beckhoff"), 'zip', os.path.join(OutputDirectory, basedir))

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
	print(" Copyright 2017-2018, European Spallation Source, Lund                      |___/ \n")



	start_time     = time.time()

	print("InterfaceFactory can't be run in standalone mode! Use PLCFactory instead.")
	print()
	print()

if __name__ == "__main__":
	main(sys.argv[1:])
