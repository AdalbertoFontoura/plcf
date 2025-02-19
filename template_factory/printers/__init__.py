from __future__ import print_function
from __future__ import absolute_import

# Copied func_param_msg from tf_idef.py
# Alfio Rizzo - Fri Feb 14 12:06:26 PM CET 2025

import glob
import importlib
import os.path

try:
    from plcf_ext import PLCFExtException
except ImportError:
    class PLCFExtException(Exception):
        pass


try:
    from plcf import PLCFNoPropertyException
except ImportError:
    class PLCFNoPropertyException(Exception):
        pass


try:
    isinstance("unicode", unicode)
except NameError:
    unicode = str



class TemplatePrinterException(Exception):
    args_format = """
{}
"""

    def __init__(self, *args, **keyword_params):
        super(TemplatePrinterException, self).__init__(*args)
        self.keyword_params = keyword_params


    def __repr__(self):
        try:
            return """at line {linenum}:
{line}{args}""".format(linenum = self.keyword_params["IFDEF_SOURCE"].sourcenum(),
                       line    = self.keyword_params["IFDEF_SOURCE"].source(),
                       args    = self.args_format.format(self.args[0]) if self.args[0] else "")
        except KeyError:
            return """{args}""".format(args    = self.args_format.format(self.args[0]) if self.args[0] else "")


    def __str__(self):
        return repr(self)


# copied from tf_ifdef.py
def func_param_msg(param, ptype, atype = None):
    if atype is None:
        return "'{param}' must be of type {type}!".format(param = param, type = ptype)
    return "'{param}' must be of type {type} (not it is {atype})!".format(param = param, type = ptype, atype = atype)


def get_printer(printer):
    for (n, c) in _available_printers:
        if n is not None and n == printer:
            return c()

    return None


def available_printers():
    printers = []
    for (n, c) in _available_printers:
        printers.append(n)

    return printers


def is_combinable(printer):
    return printer in _combinable_printers




from tf_ifdef import IF_DEF, SOURCE, PRINTER_METADATA

#
# PRINTER
#
class PRINTER(object):
    def __init__(self, comments = False, preserve_empty_lines = False, show_origin = False):
        super(PRINTER, self).__init__()
        assert isinstance(comments,             bool),    func_param_msg("comments",             "bool")
        assert isinstance(preserve_empty_lines, bool),    func_param_msg("preserve_empty_lines", "bool")
        assert isinstance(show_origin,          bool),    func_param_msg("show_origin",          "bool")

        self._output         = None
        self._comments       = comments
        self._preserve_empty = preserve_empty_lines
        self._show_origin    = show_origin
        self._output_dir     = "."
        self._helpers        = None
        self._root_inst_slot = None

        self._device         = None
        self._if_def         = None
        self._plcf           = None
        self.__append        = self.__append_simple


    def _check_if_list(self, output):
        assert isinstance(output, list),    func_param_msg("output", "list")


    def _parse_keyword_args(self, keyword_params):
        self._device = keyword_params.get("DEVICE", None)
        self._plcf   = keyword_params.get("PLCF", None)
        if self._plcf is not None:
            self.__append = self.__append_with_cplcf
        else:
            self.__append = self.__append_simple


    def __reset_body(self):
        # Cache ROOT_INSTALLATION_SLOT and INSTALLATION_SLOT
        self.__cached_root_inst_slot = self.__get_root_inst_slot("ROOT_INSTALLATION_SLOT")
        self.__cached_inst_slot = self.__get_inst_slot("INSTALLATION_SLOT", self._if_def)


    def _reset_body(self):
        self.__reset_body()


    def get_endianness(self):
        endianness = self.get_property("PLC-EPICS-COMMS:Endianness", None)
        if endianness == 'BigEndian':
            self._endianness = "BE"
        elif endianness == 'LittleEndian':
            self._endianness = 'LE'
        else:
            raise TemplatePrinterException("Unknown PLC endianness specification: '{}'".format(endianness))


    def get_offsets(self):
        try:
            self.EPICSToPLCDataBlockStartOffset = int(self.get_property("EPICSToPLCDataBlockStartOffset", None))
        except (TypeError, ValueError):
            raise TemplatePrinterException("Invalid EPICSToPLCDataBlockStartOffset property: {}".format(self.get_property("EPICSToPLCDataBlockStartOffset", None)))

        try:
            self.PLCToEPICSDataBlockStartOffset = int(self.get_property("PLCToEPICSDataBlockStartOffset", None))
        except (TypeError, ValueError):
            raise TemplatePrinterException("Invalid PLCToEPICSDataBlockStartOffset property: {}".format(self.get_property("PLCToEPICSDataBlockStartOffset", None)))

        self._plc_to_epics_offset = self.PLCToEPICSDataBlockStartOffset
        self._epics_to_plc_offset = self.EPICSToPLCDataBlockStartOffset


    def advance_offsets_after_header(self, ifa = False):
        # S7 offsets are in bytes (but for IFA it is in words)
        self._plc_to_epics_offset += 10 * (1 if ifa else 2)
        # while modbus offsets are in (16 bit) words
        self._epics_to_plc_offset += 10


    def advance_offsets_after_body(self, ifa = False):
        # S7 offsets are in bytes (but for IFA it is in words)
        self._plc_to_epics_offset += (1 if ifa else 2) * int(self._if_def.from_plc_words_length())
        # while modbus offsets are in (16 bit) words
        self._epics_to_plc_offset += int(self._if_def.to_plc_words_length())


    def expand(self, string):
        """
        Expand string as a PLCF# expression
        """
        if string and self._plcf:
            return self._plcf.process(string)

        return string


    def plcf(self, plcf_expr):
        """
        Return a PLCF# expression with plcf_expr. Will be processed/expanded if possible
        """
        assert isinstance(plcf_expr, str),    func_param_msg("plcf_expr", "str")

        plcf_expr = "[PLCF#{plcf}]".format(plcf = plcf_expr)
        return self.expand(plcf_expr)


    def get_property(self, prop_name, default):
        """
        Returns the value of property 'prop_name' or default if not found or not set

        Raises TemplatePrinterException if there is no PLCF instance
        """
        if self._plcf:
            try:
                prop_value = self._plcf.getProperty(prop_name)
                return default if prop_value is None else prop_value
            except PLCFNoPropertyException:
                return default

        raise TemplatePrinterException("No PLCF instance provided")


    def __get_inst_slot(self, default_slot, if_def):
        if if_def is not None:
            return if_def.inst_slot()

        return self.plcf(default_slot)


    def inst_slot(self, if_def = None):
        # Use the cached INSTALLATION_SLOT if if_def is provided
        if if_def:
            return self.__cached_inst_slot
        else:
            return self.__get_inst_slot("INSTALLATION_SLOT", None)


    def raw_inst_slot(self, if_def = None):
        return self.__get_inst_slot("RAW_INSTALLATION_SLOT", if_def)


    def create_pv_name(self, slot, property_part = None):
        if property_part is None:
            property_part = slot
            slot = self.__cached_inst_slot

        # if property_part is not a string then assume it is a BASE_TYPE
        if not isinstance(property_part, str):
            property_part = property_part.pv_name()

        if slot.startswith('[PLCF#'):
            slot = slot[6:-1]

        try:
            return self.plcf('ext.check_pv_length("{slot}"+":{property}")'.format(slot = slot, property = property_part))
        except PLCFExtException as e:
            raise TemplatePrinterException(e)


    def __get_root_inst_slot(self, default_slot):
        if self._root_inst_slot is None:
            return self.plcf(default_slot)
        else:
            return self._root_inst_slot


    def root_inst_slot(self):
        return self.__cached_root_inst_slot


    def raw_root_inst_slot(self):
        return self.__get_root_inst_slot("RAW_ROOT_INSTALLATION_SLOT")


    def template(self):
        return self.plcf("TEMPLATE")


    def timestamp(self):
        return self.plcf("TIMESTAMP")


    def filename(self, inst_slot = None, template = True, extension = 'txt', custom = None):
        if custom:
            return custom
        
        if inst_slot is None:
            inst_slot = self.raw_root_inst_slot()
        
        if template is True:
            template = "-{}".format(self.template())
        elif template:
            template = "-{}".format(template)
        else:
            template = ""


        return "{inst_slot}{template}-{timestamp}.{ext}".format(inst_slot = inst_slot,
                                                                template  = template,
                                                                timestamp = self.timestamp(),
                                                                ext       = extension)


    def add_filename_header(self, output, inst_slot = None, template = True, extension = 'txt', custom = None):
        self._append("#FILENAME {}".format(self.filename(inst_slot, template, extension, custom)), output)


    def comment(self):
        return ""


    def origin(self):
        return "<<<--- "


    def empty_line(self):
        return "\n"


    @staticmethod
    def name():
        """Return the *globally unique* name of the printer."""
        return ""


    @staticmethod
    def combinable():
        """Return if the printer can be used with DEFs and ordinary templates.

           A printer is combinable if the result can be the combination of processing DEFs
           and ordinary templates. Most printers are non-combinable.

        """
        return False


    def write(self, fname, output):
        self._check_if_list(output)

        gen_fname = "{basename}_TEMPLATE_{printer}.txt"
        with open(gen_fname.format(basename = os.path.splitext(os.path.basename(fname))[0], printer = self.name()), "w") as f:
            for line in output:
                if line is not None:
                    print(line.rstrip(), file = f)


    def needs_ifdef(self):
        # Check if _any_body() is overridden
        return "_any_body" not in self.__class__.__dict__


    def header(self, header_if_def, output, **keyword_params):
        self._check_if_list(output)
        self._output_dir     = keyword_params.get("OUTPUT_DIR", ".")
        self._helpers        = keyword_params.get("HELPERS", None)
        self._root_inst_slot = keyword_params.get("ROOT_INSTALLATION_SLOT", None)
        self._root_device    = keyword_params.get("ROOT_DEVICE", None)

        self._parse_keyword_args(keyword_params)
        self._device = self._root_device
        self._header_if_def = header_if_def

        self._reset_body()

        return self


    def body(self, if_def, output, **keyword_params):
        self._check_if_list(output)

        self._parse_keyword_args(keyword_params)

        self._if_def = if_def

        self._reset_body()

        if isinstance(if_def, IF_DEF):
            self._ifdef_body(if_def, output, **keyword_params)
        else:
            self._any_body(output, **keyword_params)

        self._if_def = None


    def _ifdef_body(self, if_def, output, **keyword_params):
        pass


    def _any_body(self, output, **keyword_params):
        pass


    def footer(self, footer_if_def, output, **keyword_params):
        self._check_if_list(output)

        self._parse_keyword_args(keyword_params)

        self._footer_if_def = footer_if_def

        self._reset_body()

        return self


    def __append_simple(self, output, stuff):
        if isinstance(stuff, str) or isinstance(stuff, unicode):
            output.append(stuff)
        else:
            output.extend(stuff)


    def __append_with_cplcf(self, output, stuff):
        if isinstance(stuff, str) or isinstance(stuff, unicode):
            output.append(self._plcf.processLine(stuff))
        else:
            output.extend(self._plcf.process(stuff))


    def _append_origin(self, origin, output):
        if self._show_origin and origin.strip() != "":
            self.__append(output, map(lambda x: self.comment() + self.origin() + x, origin.splitlines()))


    def _append_source(self, source, output):
        if isinstance(source, PRINTER_METADATA) and source.get(self.name()) is not None:
            self._append_origin(source.source(), output)
            self._append(str(source.get(self.name())), output)
            return

        if source.is_comment():
            if self._comments:
                if source.source().strip() != "":
                    self.__append(output, self.comment() + source.source())
                elif self._preserve_empty:
                    self.__append(output, self.empty_line())
        else:
            self._append_origin(source.source(), output)


    def _append(self, gen, output = None):
        if output is None:
            output = self._output

        if output is None:
            return

        if isinstance(gen, SOURCE):
            return self._append_source(gen, output)

        # the generic format is ("input", "result")
        # but lets support "result" only formats too
        if not isinstance(gen, tuple):
            from_inp = ""
            result = gen
        else:
            (from_inp, result) = gen

        if from_inp is None:
            from_inp = ""

        self._append_origin(from_inp, output)
        if isinstance(result, str) and result != "":
            self.__append(output, result.splitlines(True))
        elif isinstance(result, list):
            self.__append(output, result)
        else:
            raise TemplatePrinterException("Unknown type to _append: {}, {}".format(result, type(result)))

        return gen


    def call(self, var, func):
        return self._append(getattr(var, func + self.__class__.__name__)())




_available_printers  = []
_combinable_printers = set()
for printer in glob.iglob(os.path.dirname(__file__) + "/printer_*.py"):
    mod = os.path.splitext(os.path.basename(printer))[0]
    importlib.import_module(__name__ + "." + mod)

    try:
        prn_tpl = eval(mod + ".printer()")
        if type(prn_tpl) is list:
            _available_printers.extend(prn_tpl)
            for (n, c) in prn_tpl:
                if c.combinable():
                    _combinable_printers.add(n)
        else:
            _available_printers.append(prn_tpl)
            if prn_tpl[1].combinable():
                _combinable_printers.add(prn_tpl[0])
    except NotImplementedError:
        pass

    del mod
    del printer


del glob
del importlib
