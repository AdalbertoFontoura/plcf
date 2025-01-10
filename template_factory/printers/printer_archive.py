""" Template Factory: ARCHIVE printer class """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"


#TODO:
# DOCUMENT, DOCUMENT, DOCUMENT


from . import PRINTER
from tf_ifdef import IfDefSyntaxError, PV


def printer():
    return (ARCHIVE.name(), ARCHIVE)



#
# AA output
#
class ARCHIVE(PRINTER):
    def __init__(self):
        super(ARCHIVE, self).__init__()


    @staticmethod
    def name():
        return "ARCHIVE"


    @staticmethod
    def combinable():
        return True


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        #
        # No need to initialize anything
        #
        super(ARCHIVE, self).header(header_if_def, output, **keyword_params).add_filename_header(output, extension = "archive")
        if keyword_params.get("PLC_TYPE", False):
            self._append("#" * 60, output)
            self._append("## {root_inst_slot}".format(root_inst_slot = self.root_inst_slot()), output)
            def archive(var, desc):
                self._append("""# {desc}
{root_inst_slot}:{var}""".format(desc           = desc,
                                 root_inst_slot = self.root_inst_slot(),
                                 var            = var), output)

            archive("ModVersionR", "The module version")
            archive("ModbusConnectedR", "Modbus connection state")
            archive("S7ConnectedR", "S7 connection state")
            archive("PLCAddr-RB", "Address of the PLC")
            archive("ConnectedR", "Global connection state")
            archive("PLCHashCorrectR", "Hash correctness state")
            archive("AliveR", "PLC liveliness")
            archive("CommsHashToPLC", "IOC Hash")
            archive("CommsHashFromPLCR", "PLC Hash")
            archive("PayloadSizeR", "Configured payload size")
            archive("PayloadSizeFromPLCR", "Payload size configured on the PLC")
            archive("PayloadSizeCorrectR", "Payload size configuration correctness state")



    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        inst_slot = self.inst_slot(if_def)
        separator = False
        for var in if_def.interfaces():
            if isinstance(var, PV) and var.get_parameter("ARCHIVE", False):
                if not separator:
                    self._append("#" * 60, output)
                    self._append("## {inst_slot}".format(inst_slot = inst_slot), output)
                    separator = True
                desc = self._get_desc(var)
                if desc:
                    self._append("# {}".format(desc), output)
                self._append("{pv}{policy}".format(pv     = var.fqpn(),
                                                   policy = self._archive(var)), output)


    def _archive(self, var):
        arch = var.get_parameter("ARCHIVE")
        if isinstance(arch, bool):
            return ""
        if not (isinstance(arch, str) or isinstance(arch, int) or isinstance(arch, float)):
            raise IfDefSyntaxError("Invalid ARCHIVE specification: {} {}".format(arch, type(arch)))

        return arch


    def _get_desc(self, var):
        desc = var.get_parameter("ARCH_DESC", None)
        if not desc:
            desc = var.get_parameter("ARCHIVE_DESC", None)
            if not desc:
                desc = var.get_parameter("PV_DESC", None)

        return desc
