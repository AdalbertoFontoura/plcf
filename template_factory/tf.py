from __future__ import print_function
from __future__ import absolute_import

""" Template Factory:  """

__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


from tf_ifdef import IF_DEF
from printers import get_printer, available_printers, is_combinable, TemplatePrinterException

def parseDef(def_file, **kwargs):
    assert isinstance(def_file, str)

    return IF_DEF.parse(def_file, **kwargs)




if __name__ == "__main__":
    pass
