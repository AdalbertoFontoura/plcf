from __future__ import absolute_import

""" Template Factory: Autosave req file printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import BASE_TYPE


def printer():
    return [ (AUTOSAVE.name(), AUTOSAVE), (AUTOSAVE_TEST.name(), AUTOSAVE_TEST) ]




class AUTOSAVE(PRINTER):
    def __init__(self):
        super(AUTOSAVE, self).__init__(comments = False, preserve_empty_lines = False, show_origin = False)


    @staticmethod
    def name():
        return "AUTOSAVE"


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        super(AUTOSAVE, self).header(header_if_def, output, **keyword_params).add_filename_header(output, extension = "req")

        return self


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        self._output = output

        inst_slot = self.inst_slot(if_def)
        for src in if_def.interfaces():
            if isinstance(src, BASE_TYPE) and src.is_parameter():
                self._append("{}.VAL".format(src.fqpn()))



class AUTOSAVE_TEST(PRINTER):
    def __init__(self):
        super(AUTOSAVE_TEST, self).__init__(comments = False, preserve_empty_lines = False, show_origin = False)


    @staticmethod
    def name():
        return "AUTOSAVE-TEST"


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        super(AUTOSAVE_TEST, self).header(header_if_def, output, **keyword_params).add_filename_header(output, custom = "{inst_slot}-[PLCF#TEMPLATE]-[PLCF#TIMESTAMP]-test.req".format(inst_slot = self.raw_inst_slot()))

        self._append("{root_inst_slot}:UploadStat-RB.VAL".format(root_inst_slot = self.root_inst_slot()), output)

        return self


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        self._output = output

        inst_slot = self.inst_slot(if_def)
        for src in if_def.interfaces():
            if isinstance(src, BASE_TYPE) and src.is_status():
                self._append("{}.VAL".format(src.fqpn()))
