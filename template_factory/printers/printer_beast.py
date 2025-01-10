from __future__ import absolute_import

""" Template Factory: BeastFactory printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2019, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import ALARM



def printer():
    return [ (BEAST.name(), BEAST),
             (BEAST_TEMPLATE.name(), BEAST_TEMPLATE) ]




class BEAST_BASE(PRINTER):
    def __init__(self):
        super(BEAST_BASE, self).__init__(comments = False, preserve_empty_lines = False, show_origin = False)


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        super(BEAST_BASE, self).header(header_if_def, output, **keyword_params)
        self.add_filename_header(output, extension = self._extension())



class BEAST(BEAST_BASE):
    def __init__(self):
        super(BEAST, self).__init__()


    @staticmethod
    def name():
        return "BEAST"


    def _extension(self):
        return "alarms"


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        printed = False
        try:
            device = keyword_params["DEVICE"].name()
        except KeyError:
            device = "Unknown device"

        inst_slot = self.inst_slot(if_def)
        for var in if_def.alarms():
            if not printed:
                printed = True
                self._append("""
{separator}
# {device} #
{separator}
""".format(separator = "#" * (4 + len(device)),
           device    = device), output)

            self._append("""pv("{pv}")
\tdescription("{desc}")""".format(pv        = self.create_pv_name(inst_slot, var),
                                  desc      = var.get_parameter("PV_DESC", "")), output)
            if var.get_parameter("ALARM_IS_ANNUNCIATING", False):
                self._append("\tannunciating(True)", output)
            if var.get_parameter("ALARM_IS_LATCHING", False):
                self._append("\tlatching(True)", output)



class BEAST_TEMPLATE(BEAST_BASE):
    def __init__(self):
        super(BEAST_TEMPLATE,  self).__init__()
        self._devtypes = []


    @staticmethod
    def name():
        return "BEAST-TEMPLATE"


    def _extension(self):
        return "alarms-template"


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        device = keyword_params.get("DEVICE", None)

        if device is not None:
            device_type = device.deviceType()
            if device_type in self._devtypes:
                return

            self._devtypes.append(device_type)
        else:
            device_type = "Unknown device type"

        printed = False

        for var in if_def.alarms():
            if not printed:
                printed = True
                self._append("""
{separator}
# {devtype} #
{separator}
""".format(separator = "#" * (4 + len(device_type)),
           devtype   = device_type), output)

            self._append("""pv("{pv_name}")
\tdescription("{desc}")""".format(pv_name   = var.pv_name(),
                                  desc      = var.get_parameter("PV_DESC", "")), output)
