from __future__ import division
from __future__ import absolute_import

""" Template Factory: IFF printer class """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


#TODO:
# DOCUMENT, DOCUMENT, DOCUMENT
# Modified if_def._artifact.is_perdevtype() to self._device.deviceType() != 'PLC'
# Alfio Rizzo - Fri Feb 14 12:06:26 PM CET 2025

from . import PRINTER, TemplatePrinterException
from tf_ifdef import IfDefSyntaxError, SOURCE, BLOCK, BASE_TYPE, BIT, TIME


def printer():
    return (IFF.name(), IFF)



_iff_template = """VARIABLE
{name}
EPICS
{epics}
TYPE
{type}
ARRAY_INDEX
{array_index}
BIT_NUMBER
{bit_number}
"""

_iff_time_template = """{base}EGU
{egu}
"""

_iff_nogw_template = """{base}NO_GATEWAY
True
"""



#
# InterFaceFactory output
#
class IFF(PRINTER):
    def __init__(self):
        super(IFF, self).__init__(comments = True, preserve_empty_lines = False, show_origin = False)


    def comment(self):
        return "//"


    @staticmethod
    def name():
        return "IFA"


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        #
        # No need to initialize counters to 10, IFA does not need it
        #
        super(IFF, self).header(header_if_def, output, **keyword_params).add_filename_header(output, extension = "ifa")

        self.get_offsets()

        plc_type = keyword_params.get("PLC_TYPE", None)
        if plc_type != "SIEMENS" and plc_type != "BECKHOFF":
            raise TemplatePrinterException("Unknown PLC type: {}".format(plc_type))

        plcpulse = self.get_property("PLC-EPICS-COMMS: PLCPulse", "Pulse_200ms")
        if plc_type == "SIEMENS":
            try:
                interface_id = int(self.get_property("PLC-EPICS-COMMS: InterfaceID", None))
            except (TypeError, ValueError) as e:
                raise TemplatePrinterException("Missing/invalid 'PLC-EPICS-COMMS: InterfaceID'")
        else:
            interface_id = ""

        self._append("""HASH
#HASH
PLC
{inst_slot}
PLC_TYPE
{plc_type}
MAX_IO_DEVICES
{max_io_devices}
MAX_LOCAL_MODULES
{max_local_modules}
MAX_MODULES_IN_IO_DEVICE
{max_modules_in_io_device}
INTERFACE_ID
{interfaceid}
DIAG_CONNECTION_ID
{diagconnectionid}
S7_CONNECTION_ID
{s7connectionid}
MODBUS_CONNECTION_ID
{mbconnectionid}
DIAG_PORT
{diagport}
S7_PORT
{s7port}
MODBUS_PORT
{mbport}
PLC_PULSE
{plcpulse}
GATEWAY_DATABLOCK
{gateway_datablock}
""".format(inst_slot                = self.raw_inst_slot(),
           plc_type                 = plc_type,
           max_io_devices           = self.get_property("PLC-DIAG:Max-IO-Devices", 20),
           max_local_modules        = self.get_property("PLC-DIAG:Max-Local-Modules", 60),
           max_modules_in_io_device = self.get_property("PLC-DIAG:Max-Modules-In-IO-Device", 60),
           interfaceid              = interface_id,
           diagconnectionid         = self.get_property("PLC-EPICS-COMMS: DiagConnectionID", 254),
           s7connectionid           = self.plcf("PLC-EPICS-COMMS: S7ConnectionID"),
           mbconnectionid           = self.plcf("PLC-EPICS-COMMS: MBConnectionID"),
           diagport                 = self.get_property("PLC-EPICS-COMMS: DiagPort", 2001),
           s7port                   = self.plcf("PLC-EPICS-COMMS: S7Port"),
           mbport                   = self.plcf("PLC-EPICS-COMMS: MBPort"),
           plcpulse                 = plcpulse,
           gateway_datablock        = self.get_property("PLC-EPICS-COMMS: GatewayDatablock", "")), output)

        self.advance_offsets_after_header(True)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        self._append("""DEVICE
{inst_slot}
DEVICE_TYPE
{type}
DATABLOCK
{datablock}
EPICSTOPLCLENGTH
{epicstoplclength}
PLCTOEPICSLENGTH
{plctoepicslength}
EPICSTOPLCDATABLOCKOFFSET
{epicstoplcdatablockoffset}
PLCTOEPICSDATABLOCKOFFSET
{plctoepicsdatablockoffset}
""".format(inst_slot                 = self.raw_inst_slot(),
           type                      = self._device.deviceType() if self._device.deviceType() != 'PLC' else "{}_as_{}".format(self._device.deviceType(), self._device.name()),
           datablock                 = if_def.datablock_name(),
           epicstoplcdatablockoffset = self._epics_to_plc_offset,
           plctoepicsdatablockoffset = self._plc_to_epics_offset,
           epicstoplclength          = if_def.to_plc_words_length(),
           plctoepicslength          = if_def.from_plc_words_length()), output)

        self.advance_offsets_after_body(True)

        for src in if_def.interfaces():
            if isinstance(src, BLOCK):
                self._body_block(src, output)
            elif isinstance(src, BASE_TYPE):
                self._body_var(src, output)
            elif isinstance(src, SOURCE):
                self._body_source(src, output)


    def _body_block(self, block, output):
        self._append((block.source(), "BLOCK\n{block_type}\n".format(block_type = block.type())), output)


    def _body_var(self, var, output):
        self._append((var.source(), self._body_format_var(var)), output)


    def _body_source(self, var, output):
        self._append(var, output)


    def _body_format_var(self, var):
        if var.is_overlapped():
            return ""

        if var.offset() % 2:
            if not isinstance(var, BIT):
                bit_number = 8
            else:
                bit_number = 8 + var.bit_number()
        else:
            bit_number = var.bit_number()

        ifa = _iff_template.format(name        = var.name(),
                                   epics       = var.pv_name(),
                                   type        = var.plc_type() if var.dimension() == 1 else "{}[{}]".format(var.plc_type(), var.dimension()),
                                   array_index = str(var.offset() // 2),
                                   bit_number  = bit_number)

        if not var.get_parameter('USE_GATEWAY_DB', True):
            ifa = _iff_nogw_template.format(base = ifa)

        if isinstance(var, TIME):
            egu = var.get_pv_field("EGU").lower()
            if egu not in ["ms", "s", "m", "h"]:
                if egu == "msec":
                    egu = "ms"
                elif egu == "sec":
                    egu = "s"
                elif egu == "min":
                    egu = "m";
                else:
                    raise IfDefSyntaxError("Unknown time unit: " + egu)

            ifa = _iff_time_template.format(base = ifa,
                                            egu  = egu)

        return ifa


    #
    # FOOTER
    #
    def footer(self, footer_if_def, output, **keyword_params):
        super(IFF, self).footer(footer_if_def, output, **keyword_params)

        self._append("""TOTALEPICSTOPLCLENGTH
{totalepicstoplclength}
TOTALPLCTOEPICSLENGTH
{totalplctoepicslength}
""".format(totalepicstoplclength = self._epics_to_plc_offset - self.EPICSToPLCDataBlockStartOffset,
           totalplctoepicslength = self._plc_to_epics_offset - self.PLCToEPICSDataBlockStartOffset), output)
