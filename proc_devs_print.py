import json
import sys

from template_factory.printers.printer_iff import PRINTER, TemplatePrinterException
from tf_ifdef import IfDefSyntaxError, SOURCE, BLOCK, BASE_TYPE, BIT, TIME


class IFF(PRINTER):
    def __init__(self):
        super(IFF, self).__init__(comments=True, preserve_empty_lines=False, show_origin=False)

    def comment(self):
        return "//"

    @staticmethod
    def name():
        return "IFA"

    def header(self, data, output, **keyword_params):
        super(IFF, self).header(data, output, **keyword_params).add_filename_header(output, extension="ifa")

        self.get_offsets()

        plc_type = keyword_params.get("PLC_TYPE", None)
        if plc_type not in ["SIEMENS", "BECKHOFF"]:
            raise TemplatePrinterException(f"Unknown PLC type: {plc_type}")

        plcpulse = data["PROJ"]["HW"].get("PLCF#PLC-EPICS-COMMS: PLCPulse", "Pulse_200ms")
        if plc_type == "SIEMENS":
            try:
                interface_id = int(data["PROJ"]["HW"].get("PLCF#PLC-EPICS-COMMS: InterfaceID", None))
            except (TypeError, ValueError):
                raise TemplatePrinterException("Missing/invalid 'PLC-EPICS-COMMS: InterfaceID'")
        else:
            interface_id = ""

        output.write(f"""HASH
#HASH
PLC
LabS-ICS-Cryo-PLC-163
PLC_TYPE
{plc_type}
MAX_IO_DEVICES
{data["PROJ"]["HW"]["PLCF#PLC-DIAG:Max-IO-Devices"]}
MAX_LOCAL_MODULES
{data["PROJ"]["HW"]["PLCF#PLC-DIAG:Max-Local-Modules"]}
MAX_MODULES_IN_IO_DEVICE
{data["PROJ"]["HW"]["PLCF#PLC-DIAG:Max-Modules-In-IO-Device"]}
INTERFACE_ID
{interface_id}
DIAG_CONNECTION_ID
{data["PROJ"]["HW"]["PLCF#PLC-EPICS-COMMS: DiagConnectionID"]}
S7_CONNECTION_ID
{data["PROJ"]["HW"]["PLCF#PLC-EPICS-COMMS: S7ConnectionID"]}
MODBUS_CONNECTION_ID
{data["PROJ"]["HW"]["PLCF#PLC-EPICS-COMMS: MBConnectionID"]}
DIAG_PORT
{data["PROJ"]["HW"]["PLCF#PLC-EPICS-COMMS: DiagPort"]}
S7_PORT
{data["PROJ"]["HW"]["PLCF#PLC-EPICS-COMMS: S7Port"]}
MODBUS_PORT
{data["PROJ"]["HW"]["PLCF#PLC-EPICS-COMMS: MBPort"]}
PLC_PULSE
{plcpulse}
GATEWAY_DATABLOCK
""")

        self.advance_offsets_after_header(True)

    def footer(self, data, output, **keyword_params):
        super(IFF, self).footer(data, output, **keyword_params)
        output.write(f"""TOTALEPICSTOPLCLENGTH
{self._epics_to_plc_offset - self.EPICSToPLCDataBlockStartOffset}
TOTALPLCTOEPICSLENGTH
{self._plc_to_epics_offset - self.PLCToEPICSDataBlockStartOffset}
""")


def read_json(file_path):
    """Reads JSON file and returns its data as a Python dictionary."""
    with open(file_path, 'r') as f:
        return json.load(f)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python printer_iff.py <input_json_file> <output_ifa_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Read input JSON file
    try:
        data = read_json(input_file)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

    # Generate .ifa file
    try:
        printer = IFF()
        with open(output_file, 'w') as out:
            printer.header(data, out, PLC_TYPE="SIEMENS")  # Example: PLC_TYPE can be adjusted
            printer.footer(data, out)
        print(f"Successfully generated IFA file: {output_file}")
    except Exception as e:
        print(f"Error generating IFA file: {e}")
        sys.exit(1)
