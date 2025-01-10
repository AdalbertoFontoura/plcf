""" Template Factory: Device list printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2018, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER



def printer():
    return (DEVLIST.name(), DEVLIST)




class DEVLIST(PRINTER):
    def __init__(self):
        super(DEVLIST, self).__init__(comments = False, preserve_empty_lines = False, show_origin = False)


    @staticmethod
    def name():
        return "DEVICE-LIST"


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        super(DEVLIST, self).header(header_if_def, output, **keyword_params)
        self.add_filename_header(output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        self._any_body(output, **keyword_params)


    def _any_body(self, output, **keyword_params):
        self._append(self.raw_inst_slot(), output)
