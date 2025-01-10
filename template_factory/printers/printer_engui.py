from __future__ import print_function
from __future__ import absolute_import

""" Template Factory: engui printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import BASE_TYPE, BIT, ANALOG, ENUM, BITMASK



def printer():
    return (ENGUI.name(), ENGUI)




class ENGUI(PRINTER):
    def __init__(self):
        super(ENGUI, self).__init__()
        self._iformatstring = "engui {cmd} \"{pvname}\" '${{DEVICE}}:{pvname}'	|| return 1 2>/dev/null || exit 1\n"
        self._oformatstring = "engui {cmd} \"{pvname}\" '${{DEVICE}}:{pvname}' '${{DEVICE}}:{pvname}'	|| return 1 2>/dev/null || exit 1\n"


    @staticmethod
    def name():
        return "ENGUI"


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        super(ENGUI, self).header(header_if_def, output, **keyword_params)

        self._append("""#FILENAME [PLCF#INSTALLATION_SLOT]-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP].scl
#!/bin/bash

export engui_no_pipes=1

engui opi_begin || return 1 2>/dev/null || exit 1

""", output)

        return self


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        for src in if_def.interfaces():
            if isinstance(src, BASE_TYPE):
                if src.is_status():
                    self._body_status(src, output)
                elif src.is_command() or src.is_parameter():
                    self._body_command(src, output)


    #
    # FOOTER
    #
    def footer(self, footer_if_def, output, **keyword_params):
        super(ENGUI, self).footer(footer_if_def, output, **keyword_params)

        self._append("""
engui opi_end
""", output)

        return self


    def _iformat(self, cmd, var, output):
        self._append(self._iformatstring.format(cmd = cmd, pvname = var.name()), output)


    def _oformat(self, cmd, var, output):
        self._append(self._oformatstring.format(cmd = cmd, pvname = var.name()), output)


    def _body_status(self, var, output):
        if isinstance(var, BIT) or isinstance(var, ANALOG) or isinstance(var, ENUM):
            self._iformat("add_textupdate", var, output)
        else:
            print("Skipping {pvname} of type {pvtype}\n".format(pvname = var.name(), pvtype = var.pv_type()))


    def _body_command(self, var, output):
        if isinstance(var, ANALOG):
            self._oformat("add_textinput", var, output)
        elif isinstance(var, ENUM):
            self._oformat("add_combo", var, output)
        elif isinstance(var, BIT):
            self._oformat("add_button", var, output)
        else:
            print("Skipping {pvname} of type {pvtype}\n".format(pvname = var.name(), pvtype = var.pv_type()))
