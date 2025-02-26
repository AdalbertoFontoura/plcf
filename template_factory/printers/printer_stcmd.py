from __future__ import absolute_import

""" Template Factory: Startup Snippet printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017,2018, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER, TemplatePrinterException
from tf_ifdef import STATUS_BLOCK, BASE_TYPE



def printer():
    return [ (IOCSH.name(), IOCSH),
             (TEST_IOCSH.name(), TEST_IOCSH),
           ]




# class e3(object):
#     @staticmethod
#     def _extension():
#         return "iocsh"


#     def modulename(self):
#         return self.plcf("ext.e3_modulename()")


#     def snippet(self):
#         return self.plcf("ext.e3_snippet()")


#     def modversion(self):
#         # If there is a requested version we have to use that as MODVERSION
#         plciocversion = self.plcf("ext.modversion()")
#         if plciocversion:
#             return plciocversion

#         # This is set using a tricky epicsEnvSet
#         return "$(PLCIOCVERSION)"


#     def _modversion_macro(self):
#         return "{modulename}_VERSION".format(modulename = self.modulename())


#     def _modversion(self):
#         return "{modversion}={default}".format(modversion = self._modversion_macro(), default = self.plcf("ext.default_modversion()"))




class MACROS(object):
    def __init__(self):
        super(MACROS, self).__init__()
        self._root_macro = False
        self._macros     = []


    @staticmethod
    def macro_name(macro):
        return macro[2:-1]


    def macros(self):
        return self._macros


    def _declare_macros(self, if_def, output):
        if not self._root_macro:
            self._root_macro = True
            if self.raw_root_inst_slot()[0] == '$':
                self._macros.append(self.raw_root_inst_slot())
                self._append("""
#- @field {}
#- @type STRING
#- PLC device name
""".format(self.macro_name(self.raw_root_inst_slot())), output)

        for macro in if_def.macros():
            self._macros.append(macro)
            self._append("""
#- @field {macro}
#- @type STRING
#- {macro}
""".format(macro = self.macro_name(macro)), output)


    def _define_macros(self):
        if not self._macros:
            return ""

        return ", " + ", ".join(["{m}={v}".format(m = self.macro_name(m), v = m) for m in self._macros])




class IOCSH(MACROS, PRINTER):
    SIEMENS_PLC_PULSE = dict({"Pulse_100ms" : 100,
                              "Pulse_200ms" : 200,
                              "Pulse_400ms" : 400,
                              "Pulse_500ms" : 500,
                              "Pulse_800ms" : 800,
                              "Pulse_1s" : 1000,
                              "Pulse_1600ms" : 1600,
                              "Pulse_2s" : 200})

    def __init__(self):
        super(IOCSH, self).__init__()
        self._opc = False
        self._autosave = False


    @staticmethod
    def name():
        return "IOCSH"


    @staticmethod
    def flavor():
        return ""


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_parameters):
        snippet = keyword_parameters.get('SNIPPET', 'N/A')
        self.modulename = keyword_parameters.get('MODULE_NAME')
        self.modversion = keyword_parameters.get('MODVERSION', '$(PLCIOCVERSION)')
        default_modversion = keyword_parameters.get('DEF_MODVERSION')
        self._modversion_macro = "{modulename}_VERSION".format(modulename = self.modulename)
        self._modversion = "{modversion}={default}".format(modversion = self._modversion_macro, default = default_modversion)
        super(IOCSH, self).header(header_if_def, output, **keyword_parameters).add_filename_header(output, inst_slot = snippet, template = False if not self._autosave else "autosave", extension = 'iocsh')
        self._opc = True if "OPC" in keyword_parameters.get("PLC_TYPE", "") else False

        if not self._opc:
            self.get_endianness()
            self.get_offsets()

        self._ipaddr = keyword_parameters.get("PLC_HOSTNAME", None)
        if self._ipaddr is None:
            self._ipaddr = self.get_property("Hostname", None)
        if self._ipaddr == "":
            self._ipaddr = None

        self._recvtimeout = 3000
        plc_pulse = self.get_property("PLC-EPICS-COMMS: PLCPulse", "Pulse_200ms")
        try:
            plc_pulse = self.SIEMENS_PLC_PULSE[plc_pulse]
            self._recvtimeout = int(plc_pulse * 5)
        except KeyError:
            raise TemplatePrinterException("Cannot interpret PLCPulse property: '{}'".format(plc_pulse))

        st_cmd_header = """
#- @field IPADDR
#- @{ipaddr}
#- PLC IP address
{s7_vs_opc}
#- @field DBDIR
#- @runtime YES
#- The directory where the db files are located

#- @field MODVERSION
#- @runtime YES
#- The version of the PLC-IOC integration

#- @field {modversion}
#- @runtime YES

#- @field S7_PORT
#- @runtime YES
#- Can override S7 port with this

#- @field MB_PORT
#- @runtime YES
#- Can override Modbus port with this

""".format(ipaddr     = "type STRING" if self._ipaddr is None else "runtime YES",
           modversion = self._modversion_macro,
           s7_vs_opc  = """
#- @field RECVTIMEOUT
#- @type INTEGER
#- PLC->EPICS receive timeout (ms), should be longer than frequency of PLC SND block trigger (REQ input)
""" if not self._opc else """
#- @field PORT
#- @type INTEGER
#- PLC OPC-UA port

#- @field PUBLISHING_INTERVAL
#- @type INTEGER
#- The OPC-UA publishing interval
""")

        self._append(st_cmd_header, output)

        self._append("""#-
#- Check if MODVERSION is set
#-
#- First set PLCIOCVERSION to a safe default; the module version if it is a module else the creation date
epicsEnvSet("PLCIOCVERSION", "$({default})")
#- Now, the tricky part;
#- 1. try to set PLCIOCVERSION from a macro named PLCIOCVERSION + MODVERSION (where MODVERSION defaults to the empty string if not set)
#-    this will basically set PLCIOCVERSION to the value of PLCIOCVERSION if MODVERSION is not set or empty
#- 2. if MODVERSION _is_ set to a non empty string then PLCIOCVERSION will be set to the value of MODVERSION because
#-    the constructed macro name (from the macros PLCIOCVERSION + MODVERSION) will not exist and the value of MODVERSION will be used as a default
epicsEnvSet("PLCIOCVERSION", "$(PLCIOCVERSION$(MODVERSION=)=$(MODVERSION))")
""".format(default = self._modversion), output)

        if not self._opc:
            self.advance_offsets_after_header()


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_parameters):
        # Append macro 'declarations' to header part...
        self._declare_macros(if_def, output);

        if not self._opc and if_def._status_block() is not None:
            self.advance_offsets_after_body()


    def _dbLoadRecords(self, plc_macro, insize):
        return """#- Load plc interface database
dbLoadRecords("$(DBDIR=){modulename}.db", "{PLC_MACRO}={plcname}, MODVERSION={modversion}, S7_PORT=$(S7_PORT={s7_port}), MODBUS_PORT=$(MB_PORT={modbus_port}), PAYLOAD_SIZE={insize}{macros}")""".format(
            PLC_MACRO   = plc_macro,
            plcname     = self.raw_root_inst_slot(),
            modulename  = self.modulename,
            modversion  = self.modversion,
            s7_port     = self.plcf("PLC-EPICS-COMMS: S7Port"),
            modbus_port = self.plcf("PLC-EPICS-COMMS: MBPort"),
            insize      = insize,
            macros      = self._define_macros())


    #
    # FOOTER
    #
    def footer(self, footer_if_def, output, **keyword_parameters):
        if self._opc:
            self._opc_footer(footer_if_def, output, **keyword_parameters)
        else:
            self._s7_footer(footer_if_def, output, **keyword_parameters)

        self._append("""#- Remove PLCIOCVERSION to not pollute the environment
epicsEnvUnset("PLCIOCVERSION")""", output)

    #
    # S7 + MODBUS FOOTER
    #
    def _s7_footer(self, footer_if_def, output, **keyword_parameters):
        super(IOCSH, self).footer(footer_if_def, output, **keyword_parameters)

        insize = self._plc_to_epics_offset - self.PLCToEPICSDataBlockStartOffset

        st_cmd_footer = """
#- S7 port           : {s7drvport}
#- Input block size  : {insize} bytes
#- Output block size : 0 bytes
#- Endianness        : {endianness}
s7plcConfigure("{plcname}", {ipaddr}, $(S7_PORT={s7drvport}), {insize}, 0, {bigendian}, $(RECVTIMEOUT={recvtimeout}), 0)

#- Modbus port       : {modbusdrvport}
drvAsynIPPortConfigure("{plcname}", {ipaddr}:$(MB_PORT={modbusdrvport}), 0, 0, 1)

#- Link type         : TCP/IP (0)
#- The timeout is initialized to the (modbus) default if not specified
modbusInterposeConfig("{plcname}", 0, $(RECVTIMEOUT=0), 0)

#- Slave address     : 0
#- Function code     : 16 - Write Multiple Registers
#- Addressing        : Absolute (-1)
#- Data segment      : 20 words
drvModbusAsynConfigure("{plcname}write", "{plcname}", 0, 16, -1, 20, 0, 0, "S7-1500")

#- Slave address     : 0
#- Function code     : 3 - Read Multiple Registers
#- Addressing        : Relative ({start_offset})
#- Data segment      : 10 words
#- Polling           : 1000 msec
drvModbusAsynConfigure("{plcname}read", "{plcname}", 0, 3, {start_offset}, 10, 0, 1000, "S7-1500")

{dbloadrecords}
""".format(ipaddr        = "$(IPADDR)" if self._ipaddr is None else "$(IPADDR={})".format(self._ipaddr),
           recvtimeout   = self._recvtimeout,
           s7drvport     = self.plcf("PLC-EPICS-COMMS: S7Port"),
           modbusdrvport = self.plcf("PLC-EPICS-COMMS: MBPort"),
           insize        = insize,
           endianness    = "BigEndian" if self._endianness == "BE" else "LittleEndian",
           bigendian     = 1 if self._endianness == "BE" else 0,
           plcname       = self.raw_root_inst_slot(),
           dbloadrecords = self._dbLoadRecords("PLCNAME", insize),
           start_offset  = self.EPICSToPLCDataBlockStartOffset,
          )

        self._append(st_cmd_footer, output)


    #
    # OPC-UA FOOTER
    #
    def _opc_footer(self, footer_if_def, output, **keyword_parameters):
        super(IOCSH, self).footer(footer_if_def, output, **keyword_parameters)

        st_cmd_footer = """
#- Session name : {plcname}-session
opcuaCreateSession("{plcname}-session", "opc.tcp://$(IPADDR):$(PORT)")

#- Subscription       : {plcname}
#- Publising interval : $(PUBLISHING_INTERVAL)
opcuaCreateSubscription("{plcname}", "{plcname}-session", $(PUBLISHING_INTERVAL))

{dbloadrecords}
""".format(plcname       = self.raw_root_inst_slot(),
           dbloadrecords = self._dbLoadRecords("SUBSCRIPTION", 0)
          )

        self._append(st_cmd_footer, output)




class TEST_IOCSH(MACROS, PRINTER):
    def __init__(self):
        super(TEST_IOCSH, self).__init__()


    @staticmethod
    def name():
        return "TEST-IOCSH"


    @staticmethod
    def flavor():
        return "-test"


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_parameters):
        snippet = keyword_parameters.get('SNIPPET', 'N/A')
        modulename = keyword_parameters.get('MODULE_NAME')
        _modversion_macro = "{modulename}_VERSION".format(modulename = modulename)
        super(TEST_IOCSH, self).header(header_if_def, output, **keyword_parameters).add_filename_header(output, inst_slot = snippet, template = "test", extension = 'iocsh')

        st_cmd_header = """
#- @field MODVERSION
#- @runtime YES
#- The version of the PLC-IOC integration

#- @field {modversion}
#- @runtime YES

""".format(modversion = _modversion_macro)

        self._append(st_cmd_header, output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_parameters):
        # Append macro 'declarations' to header part...
        self._declare_macros(if_def, output);


    #
    # FOOTER
    #
    def footer(self, footer_if_def, output, **keyword_parameters):
        super(TEST_IOCSH, self).footer(footer_if_def, output, **keyword_parameters)
        modulename = keyword_parameters.get('MODULE_NAME')
        modversion = keyword_parameters.get('MODVERSION', '$(PLCIOCVERSION)')
        st_cmd_footer = """
#- Load plc interface database
dbLoadRecords("$(DBDIR=){modulename}-test.db", "MODVERSION={modversion}{macros}")
""".format(modulename = modulename,
           modversion = modversion,
           macros     = self._define_macros())

        self._append(st_cmd_footer, output)
