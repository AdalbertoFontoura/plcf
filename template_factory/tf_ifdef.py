from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

""" Template Factory: Interface Definition Classes """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"


import copy
from collections import OrderedDict
#import inspect

# FIXME: I don't think it is needed anymore
#try:
#    from plcf import PLCF
#except ImportError:
#    pass

try:
    isinstance("aladar", basestring)
except NameError:
    basestring = str



# Data types for S7 PLCs
PLC_types = { 'BOOL', 'BYTE', 'CHAR', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'SSTIME', 'TIME', 'LTIME', 'DATE', 'TIME_OF_DAY', 'STRING' }

# New data types for S7-1200/1500
PLC_types.update({ 'USINT',    # Unsigned Short  INTeger
                   'SINT',     # Signed   Short  INTeger
                   'UINT',     # Unsigned        INTeger
                   'UDINT'     # Unsigned Double INTeger
                 })


bits_in_type_map = { 'UINT8'   :  8, 'INT8'   :  8, 'UNSIGN8' :  8, 'BYTE'       :  8, 'CHAR'       :  8, 'USINT'    :  8, 'SINT'         :  8,
                     'UINT16'  : 16, 'INT16'  : 16, 'SHORT'   : 16, 'UNSIGN16'   : 16, 'WORD'       : 16, 'INT16SM'  : 16, 'BCD_UNSIGNED' : 16, 'BCD_SIGNED' : 16, 'INT'  : 16, 'UINT'  : 16,
                     'UINT32'  : 32, 'INT32'  : 32, 'LONG'    : 32, 'UNSIGN32'   : 32, 'DWORD'      : 32, 'INT32_LE' : 32, 'INT32_BE'     : 32, 'DINT'       : 32, 'TIME' : 32, 'UDINT' : 32,
                     'FLOAT32' : 32, 'REAL32' : 32, 'FLOAT'   : 32, 'FLOAT32_LE' : 32, 'FLOAT32_BE' : 32, 'REAL'     : 32,
                     'FLOAT64' : 64, 'REAL64' : 64, 'DOUBLE'  : 64, 'FLOAT64_LE' : 64, 'FLOAT64_BE' : 64 }

limits = { "u8"  : ( 0,                            int("0xFF", base = 0)),

           "i8"  : ( int("-0x80", base = 0),       int("0x7F", base = 0)),

           "u16" : ( 0,                            int("0xFFFF", base = 0)),

           "i16" : ( int("-0x8000", base = 0),     int("0x7FFF", base = 0)),

           "u32" : ( 0,                            int("0xFFFFFFFF", base = 0)),

           "i32" : ( int("-0x80000000", base = 0), int("0x7FFFFFFF", base = 0))
         }

PLC_type_limits = { 'BYTE'  : limits["u8"],
                    'CHAR'  : limits["u8"],
                    'USINT' : limits["u8"],

                    'SINT'  : limits["i8"],

                    'WORD'  : limits["u16"],
                    'UINT'  : limits["u16"],

                    'INT'   : limits["i16"],

                    'DWORD' : limits["u32"],
                    'UDINT' : limits["u32"],

                    'DINT'  : limits["i32"],
                    'TIME'  : limits["i32"]
                  }


class IfDefException(Exception):
    args_format = """
{}
"""

    def __init__(self, typemsg, *args, **keyword_params):
        self.typemsg        = typemsg
        self.args           = args
        self.keyword_params = keyword_params


    def __call__(self, *args):
        return self.__class__(self.typemsg, *(self.args + args))


    def __repr__(self):
        try:
            return """{error} in {file} at line {linenum}:
{line}{args}""".format(error   = self.typemsg,
                       file    = self.keyword_params["filename"],
                       linenum = self.keyword_params["linenum"],
                       line    = self.keyword_params["line"],
                       args    = self.args_format.format(self.args[0]) if self.args[0] else "")
        except KeyError:
            return """{error}: {args}""".format(error   = self.typemsg,
                                                args    = self.args_format.format(self.args[0]) if self.args[0] else "")


    def __str__(self):
        return repr(self)


    def type(self):
        return self.typemsg


    def add_params(self, **keyword_params):
        self.keyword_params.update(keyword_params)


class IfDefSyntaxError(IfDefException):
    def __init__(self, *args, **keyword_params):
        super(IfDefSyntaxError, self).__init__("Syntax error", *args, **keyword_params)


class IfDefInternalError(IfDefException):
    def __init__(self, *args, **keyword_params):
        super(IfDefInternalError, self).__init__("Internal error", *args, **keyword_params)


class IfDefPrematureEnd(IfDefSyntaxError):
    def __init__(self, *args, **keyword_params):
        super(IfDefPrematureEnd, self).__init__("Unexpected EOF while parsing", *args, **keyword_params)


class IfDefFeatureMissingError(IfDefSyntaxError):
    def __init__(self, feature):
        super(IfDefFeatureMissingError, self).__init__("Required feature '{}' is not supported in this version".format(feature))


class IfDefExperimentalFeatureError(IfDefSyntaxError):
    def __init__(self, feature):
        super(IfDefExperimentalFeatureError, self).__init__("Required feature '{}' is experimental in this version. Use '--enable-experimental' to enable".format(feature))


class IfDefExperimentalError(IfDefSyntaxError):
    def __init__(self, interface):
        super(IfDefExperimentalError, self).__init__("The function '{}' is experimental. Use '--enable-experimental' to enable.".format(interface))


class PVNameLengthException(IfDefException):
    def __init__(self, name, *args, **keyword_params):
        super(PVNameLengthException, self).__init__("The PV name '{pv_name}' is longer than permitted ({act_len} / {max_len})".format(pv_name = name, act_len = len(name), max_len = PV.FQPN_LEN), *args, **keyword_params)



#def ifdef_assert_instance(var, var_type, var_type_string = None):
#    frame  = inspect.currentframe()
#    oframe = frame.f_back
#    try:
#        all_vars = oframe.f_locals
#        if var_type_string is None:
#            var_type_string = str(var_type)
#        if not isinstance(all_vars[var], var_type):
#            raise IfDefInternalError("'{param}' must be of type {type}!".format(param = var, type = var_type_string))
#    finally:
#        del oframe
#        del frame




class DummyHash(object):
    def update(self, string):
        pass



class DummyPLCF(object):
    def __init__(self, presets = {}):
        self._presets = presets


    def process(self, what):
        return self._presets.get(what, what)


    def processLine(self, line):
        return line



class SOURCE(object):
    def __init__(self, source, comment = False, keyword_params = None):
        super(SOURCE, self).__init__()

        if isinstance(source, tuple):
            source, sourcenum = source
        else:
            sourcenum = -1

        assert isinstance(source,     str),  func_param_msg("source",     "string")
        assert isinstance(sourcenum,  int),  func_param_msg("sourcenum",  "integer")
        assert isinstance(comment,    bool), func_param_msg("comment",    "bool")
        assert keyword_params is None or isinstance(keyword_params, dict),   func_param_msg("keyword_params", "dict")

        self._source    = source.lstrip()
        self._sourcenum = sourcenum
        self._comment   = comment
        self._hashed    = False
        self._warnings  = None
        self._keyword_params = dict() if keyword_params is None else keyword_params


    def hash_message(self):
        return self._source.rstrip() if self._hashed else ""


    def is_comment(self):
        return self._comment


    def source(self):
        return self._source


    def sourcenum(self):
        return self._sourcenum


    def get_parameter(self, param_name, *val_if_not_found):
        if len(val_if_not_found):
            return self._keyword_params.get(param_name, val_if_not_found[0])

        return self._keyword_params[param_name]


    @staticmethod
    def __is_it_a(klass, typ):
        for t in klass.__bases__:
            print("Checking ", t.__name__, " and ", typ)
            if t.__name__ == typ:
                return True

            if SOURCE.__is_it_a(t, typ):
                return True

        return False


    def is_it_a(self, typ, explicit = False):
        if type(self).__name__ == typ:
            return True

        if explicit:
            return False

        return SOURCE.__is_it_a(type(self), typ)


    def warnings(self):
        return self._warnings


    def _add_warning(self, warn):
        if self._warnings is None:
            self._warnings = [ "At line number {lnum}:".format(lnum = self.sourcenum()), warn ]
        else:
            self._warnings.append(warn)

        return warn



class PRINTER_METADATA(SOURCE):
    def __init__(self, source, printers, metadata, hash_message = None):
        if isinstance(printers, str):
            printers = [ printers ]
        assert isinstance(printers, list), func_param_msg("printers", "list")

        super(PRINTER_METADATA, self).__init__(source)

        self._printers     = printers
        self._metadata     = metadata
        self._hash_message = hash_message


    def hash_message(self):
        if self._hash_message is None:
            return super(PRINTER_METADATA, self).hash_message()

        return self._hash_message


    def get(self, printer):
        if printer not in self._printers:
            return None

        return self._metadata



class VERBATIM(SOURCE):
    def __init__(self, source, verbatim):
        assert isinstance(source, tuple),  func_param_msg("source",   "tuple")
        assert isinstance(verbatim, str),  func_param_msg("verbatim", "string")

        super(VERBATIM, self).__init__(source)

        self._verbatim = verbatim


    def __str__(self):
        return self._verbatim



#
# Blocks
#
class fakeBLOCK(SOURCE):
    def __init__(self):
        super(fakeBLOCK, self).__init__("")

        self._ifaces = []


    def add_iface(self, var):
        if not isinstance(var, SOURCE):
            raise IfDefInternalError("Cannot add non-SOURCE({}) to preBLOCK!".format(type(var)))

        if isinstance(var, BLOCK):
            raise IfDefInternalError("Cannot add block ({}) to preBLOCK".format(var.type()))

        if isinstance(var, fakeBLOCK):
            return

        self._ifaces.append(var)


    def interfaces(self):
        return self._ifaces



class BLOCK(SOURCE):
    STATUS = "STATUS"
    CMD    = "COMMAND"
    PARAM  = "PARAMETER"
    GENERAL_INPUT  = "GENERAL_INPUT"

    def __init__(self, source, block_type, optimize):
        super(BLOCK, self).__init__(source)

        BITS.end()

        assert isinstance(block_type,    str)
        assert isinstance(optimize,      bool)

        self._block_type    = block_type
        self._ifaces        = []
# TODO: remove _block_offset and use _length instead
        self._block_offset  = 0
        self._start_offset  = 0
        self._length        = 0
        self._optimize_s7db = optimize
        self._block_printer = None


    def _is_alignment_needed(self, width):
        if not self.optimize():
            return (self._block_offset % 2) == 1
        else:
            # MODBUS cannot address the individual bytes in a WORD
            return (self.to_plc() or width > 1) and (self._block_offset % 2) == 1


    def endian_correct_epics_type(self, epics_type):
        return epics_type


    def optimize(self):
        return self._optimize_s7db


    def length(self):
        return self._length


    def start_offset(self):
        return self._start_offset


    def offset_for(self, width):
        if self._is_alignment_needed(width):
            self._block_offset += 1
        return self._block_offset


    def add_iface(self, var):
        if not isinstance(var, SOURCE):
            raise IfDefInternalError("Cannot add non-SOURCE({}) to BLOCK!".format(type(var)))

        if isinstance(var, BLOCK):
            return

        self._ifaces.append(var)


    def interfaces(self):
        return self._ifaces


    def get_overlap(self):
        return OVERLAP(self)


    def from_plc(self):
        return False


    def to_plc(self):
        return False


    def is_status_block(self):
        return isinstance(self, STATUS_BLOCK)


    def is_command_block(self):
        return isinstance(self, CMD_BLOCK)


    def is_parameter_block(self):
        return isinstance(self, PARAM_BLOCK)


    def is_general_input_block(self):
        return isinstance(self, GEN_INPUT_BLOCK)


    def type(self):
        return self._block_type


    def plc_type_to_epics_type(self, plc_type):
        try:
            return self.valid_type_pairs()[plc_type][0]
        except KeyError:
            if plc_type in PLC_types:
                raise IfDefSyntaxError("Unsupported PLC type: " + plc_type)
            else:
                raise IfDefSyntaxError("Unknown PLC type: " + plc_type)


    def pair_types(self, keyword_params):
        if keyword_params is None:
            return (None, None)

        assert isinstance(keyword_params, dict), func_param_msg("keyword_params", "dict")

        def _valid_var_types(self):
            types = []
            for k,v in self.valid_type_pairs().items():
                types += v
            return types


        for key, value in keyword_params.items():
            if key.startswith(PV.PV_PREFIX) or not key in PLC_types:
                continue

            if not value in _valid_var_types(self):
                raise IfDefSyntaxError("Unsupported type: " + value)

            plcbits   = _bits_in_type(key)
            epicsbits = _bits_in_type(value)

            if not plcbits == epicsbits:
                raise IfDefSyntaxError("Bit width must be the same: {plc} vs {epics}".format(plc = key, epics = value))

            return (key, value)

        return (None, None)


    def end(self):
        BITS.end()
        if self._block_offset % 2:
            self._block_offset += 1

        self._length = self._block_offset


    def compute_offset(self, num_bytes):
        if isinstance(num_bytes, int):
            self._block_offset += num_bytes
        else:
            raise IfDefSyntaxError("Cannot compute width, unknown type: " + str(num_bytes))


    def set_start_offset(self, offs):
        if offs % 2:
            raise IfDefInternalError("Block start offset must start on a PLC word boundary")

        self._start_offset = offs


    def set_endianness(self, endianness):
        self._endianness = endianness


    def register_printer(self, printer):
        self._block_printer = printer



class STATUS_BLOCK(BLOCK):
    TYPE = "S7PLC"


    @staticmethod
    def length_keyword():
        return "StatusWordsLength"


    @staticmethod
    def valid_type_pairs():
        return dict(BYTE   = [ "UINT8",   "UNSIGN8", "BYTE", "CHAR" ],
                    USINT  = [ "UINT8",   "UNSIGN8", "BYTE", "CHAR" ],
                    SINT   = [ "INT8" ],
                    WORD   = [ "UINT16",  "UNSIGN16", "WORD" ],
                    UINT   = [ "UINT16",  "UNSIGN16", "WORD" ],
                    INT    = [ "INT16",   "SHORT" ],
                    DWORD  = [ "UINT32",  "UNSIGN32", "DWORD" ],
                    UDINT  = [ "UINT32",  "UNSIGN32", "DWORD" ],
                    DINT   = [ "INT32",   "LONG" ],
                    REAL   = [ "FLOAT32", "REAL32",   "FLOAT" ],
                    TIME   = [ "INT32",   "LONG" ],
                    STRING = [ "STRING" ])


    @staticmethod
    def dtyp():
        return "S7plc"


    @staticmethod
    def inst_io():
        return "$(PLCNAME)"


    @staticmethod
    def basetype():
        return STATUS_BLOCK.TYPE


    def __init__(self, source, optimize):
        super(STATUS_BLOCK, self).__init__(source, BLOCK.STATUS, optimize)


    def from_plc(self):
        return True


    def inp_out(self, **keyword_params):
        return 'INP,  "{}"'.format(self._block_printer.field_inp(**keyword_params))


    def link_offset(self, var, plc_to_epics_offset, epics_to_plc_offset):
        # S7 uses byte based offsets
        return plc_to_epics_offset + var.offset()


    def pv_template(self, **keyword_params):
        return self._block_printer.inpv_template(**keyword_params)



#
# Special class to handle the similarities between CMD_BLOCK and PARAM_BLOCK
#
class MODBUS(object):
    TYPE = "MODBUS"

    _int32_types   = [ "INT32_BE",   "INT32_LE" ]
    _float32_types = [ "FLOAT32_BE", "FLOAT32_LE" ]
    _zstring_types = [ "ZSTRING_HIGH_LOW", "ZSTRING_LOW_HIGH" ]

    _endian_dependent_type_pairs = dict(
# DWORD and UDINT are unsigned types, but MODBUS does not support writing (or reading) unsigned 32bit integers
# so make it an error to use them
#                    DWORD = _int32_types,
#                    UDINT = _int32_types,
                    DINT   = _int32_types,
                    REAL   = _float32_types,
                    TIME   = _int32_types,
                    STRING = _zstring_types)


    _valid_type_pairs = dict(_endian_dependent_type_pairs,
                    BYTE  = [ "UINT16" ],
                    USINT = [ "UINT16" ],
                    SINT  = [ "INT16" ],
                    WORD  = [ "UINT16",     "BCD_UNSIGNED" ],
                    UINT  = [ "UINT16",     "BCD_UNSIGNED" ],
                    INT   = [ "INT16",      "BCD_SIGNED",  "INT16SM" ])


    _endian_specific_epics_types = [item for sublist in _endian_dependent_type_pairs.values() for item in sublist]


    @staticmethod
    def endian_dependent_type_pairs():
        return MODBUS._endian_dependent_type_pairs


    @staticmethod
    def valid_type_pairs():
        return MODBUS._valid_type_pairs


    @staticmethod
    def dtyp():
        return "asynInt32"


    @staticmethod
    def inst_io():
        return "asyn"


    @staticmethod
    def basetype():
        return MODBUS.TYPE


    def to_plc(self):
        return True


    def inp_out(self, **keyword_params):
        return 'OUT,  "{}"'.format(self._block_printer.field_out(**keyword_params))


    def endian_correct_epics_type(self, epics_type):
        if epics_type not in self._endian_specific_epics_types:
            return super(MODBUS, self).endian_correct_epics_type(epics_type)

        if epics_type in self._int32_types:
            pairs = self._int32_types
        elif epics_type in self._float32_types:
            pairs = self._float32_types
        elif epics_type in self._zstring_types:
            pairs = self._zstring_types
        else:
            raise IfDefInternalError("Cannot determine endian correct type of {}".format(epics_type))

        return pairs[0] if self._big_endian else pairs[1]


    def link_offset(self, var, plc_to_epics_offset, epics_to_plc_offset):
        # Modbus uses (16 bit) word base offsets
        return epics_to_plc_offset + var.offset() // 2


    def pv_template(self, **keyword_params):
        return self._block_printer.outpv_template(**keyword_params)


    def compile_endianness(self, endianness):
        if endianness == 'BE':
            self._big_endian = True
        elif endianness == 'LE':
            self._big_endian = False
        else:
            raise IfDefSyntaxError("Unknown endianness: {}".format(endianness))




class TOPLC_BLOCK(MODBUS, BLOCK):
    def __init__(self, source, block_typ, optimize):
        super(TOPLC_BLOCK, self).__init__(source, block_typ, optimize)


    def set_endianness(self, endianness):
        self.compile_endianness(endianness)
        super(TOPLC_BLOCK, self).set_endianness(endianness)



class CMD_BLOCK(TOPLC_BLOCK):
    @staticmethod
    def length_keyword():
        return "CommandWordsLength"


    def __init__(self, source, optimize):
        super(CMD_BLOCK, self).__init__(source, BLOCK.CMD, optimize)



class PARAM_BLOCK(TOPLC_BLOCK):
    @staticmethod
    def length_keyword():
        return "ParameterWordsLength"


    def __init__(self, source, optimize):
        super(PARAM_BLOCK, self).__init__(source, BLOCK.PARAM, optimize)



class GEN_INPUT_BLOCK(TOPLC_BLOCK):
    @staticmethod
    def length_keyword():
        return "GeneralInputWordsLength"


    def __init__(self, source, optimize):
        super(GEN_INPUT_BLOCK, self).__init__(source, BLOCK.GENERAL_INPUT, optimize)



class OVERLAP(BLOCK):
    def __init__(self, block):
        assert isinstance(block, BLOCK), func_param_msg("block", "BLOCK")

        self._block                    = block
        self._overlap_offset           = block._block_offset
        self._overlap_width            = 0
        self._overlap_alignment_needed = False

        #
        # Copy every attribute from the passed in BLOCK instance
        #
        for attr in block.__dict__:
            self.__dict__[attr] = copy.copy(block.__dict__[attr])

        #
        # Call BLOCK methods of the passed in BLOCK type instead of self
        #  but honor overriden functions
        #
        for attr in dir(block):
            val = getattr(block, attr)
            if not hasattr(val, '__call__') or attr.startswith('__') or attr in OVERLAP.__dict__:
                continue

            setattr(self, attr, val)


    def is_empty(self):
        return self._overlap_width == 0


    def add_iface(self, var):
        #
        # Overlaps have nothing to do with the PLC
        #
        pass


    def interfaces(self):
        return None


    def offset_for(self, width):
        #
        # Check for alignment errors
        #
#        if not self._block._block_offset == self._overlap_offset:
#            raise IfDefInternalError("Consistency error: block is " + str(self._block._block_offset) + " while overlap is " + str(self._overlap_offset))
        if self.is_empty():
            self._overlap_alignment_needed = self._is_alignment_needed(width)
        elif self._overlap_alignment_needed != self._is_alignment_needed(width):
            raise IfDefInternalError("Alignment mismatch during overlap")

        return self._overlap_offset


    def compute_offset(self, num_bytes):
        if self._overlap_width < num_bytes:
            self._overlap_width = num_bytes


    def get_overlap(self):
        raise IfDefSyntaxError("Cannot nest overlaps!")


    def end(self):
        self._block.compute_offset(self._overlap_width)




class IF_DEF_INTERFACE_FUNC(object):
    def __init__(self, is_hashed, var):
        super(IF_DEF_INTERFACE_FUNC, self).__init__()

        self._var    = var
        var._hashed  = is_hashed


#This only relevant for classes that do not override hash_message()
def hashed_interface(func):
    def hashed_interface_func(*args, **kwargs):
        return ifdef_interface(func)(*args, _hashed_interface = True, **kwargs)

    return hashed_interface_func


def experimental_interface(func):
    def experimental_interface_func(*args, **kwargs):
        kwargs["__EXPERIMENTAL__"] = True
        return func(*args, **kwargs)

    return experimental_interface_func


def ifdef_interface(func):
    def ifdef_interface_func(*args, **kwargs):
        if args is not None and isinstance(args, tuple) and len(args) > 0 and isinstance(args[0], IF_DEF):
            _hashed_interface       = kwargs.pop("_hashed_interface", False)
            _experimental_interface = kwargs.pop("__EXPERIMENTAL__", False)
            if _experimental_interface and not args[0]._experimental:
                raise IfDefExperimentalError(func.__name__)

            # If function has **keyword_params
            if func.__code__.co_flags & 8:
                # Expand templates
                args[0]._expand_templates(kwargs)

                def update_params(kwargs, default_params):
                    for kw in default_params:
                        if kw not in kwargs:
                            kwargs[kw] = default_params[kw]

                # Get function specific default params
                try:
                    update_params(kwargs, args[0]._defaults[func.__name__])
                except KeyError:
                    pass

                # Get global params
                if func.__name__ not in IF_DEF.IGNORE_DEFAULTS_FOR:
                    update_params(kwargs, args[0]._global_defaults)

            var = func(*args, **kwargs)

            # If the function is an alias, get the real one
            while isinstance(var, IF_DEF_INTERFACE_FUNC):
                var = var._var

            if not isinstance(var, SOURCE):
                raise IfDefInternalError("Function '{f}' not returning variable, please file a bug report".format(f = func.__name__))
            return IF_DEF_INTERFACE_FUNC(_hashed_interface, var)
        else:
            raise IfDefSyntaxError("Trying to call non-interface function '{f}'".format(f = func.__name__))

    return ifdef_interface_func



class IF_DEF(object):
    DEFAULT_INSTALLATION_SLOT = "INSTALLATION_SLOT"
    DEFAULT_DATABLOCK_NAME    = "DEV_[PLCF#{}]_iDB".format("RAW_INSTALLATION_SLOT")
    IGNORE_DEFAULTS_FOR = ["set_defaults", "clear_defaults"]


    @staticmethod
    def create_dummy_plcf():
        return DummyPLCF({ "[PLCF#{}]".format(IF_DEF.DEFAULT_INSTALLATION_SLOT) : "INST:SLOT", "[PLCF#ROOT_INSTALLATION_SLOT]" : "ROOT-INST:SLOT" })


    @staticmethod
    def parse(def_file, **keyword_params):
        # TODO: change to str once we moved to Python3
        if isinstance(def_file, basestring):
            artifact = keyword_params.get("ARTIFACT")
        else:
            artifact = def_file
            def_file = artifact.saved_as()

        keyword_params["PLCF"] = keyword_params.get("PLCF", IF_DEF.create_dummy_plcf())
        cplcf = keyword_params["PLCF"]

        with IF_DEF(**keyword_params) as if_def:
            if_def._artifact = artifact
            if_def._read_def(def_file, cplcf)

        return if_def


    def __init__(self, OPTIMIZE = False, **keyword_params):
        assert isinstance(OPTIMIZE, bool)
        super(IF_DEF, self).__init__()

        PV.init(self)

        self._pv_names  = dict()
        self._plc_names = set()
        self._templates = dict()

        cplcf = keyword_params.get("PLCF", self.create_dummy_plcf())

        self._datablock_name           = cplcf.process(IF_DEF.DEFAULT_DATABLOCK_NAME)
        self.DEFAULT_DATABLOCK_NAME    = self._datablock_name
        self._inst_slot                = cplcf.process("[PLCF#{}]".format(IF_DEF.DEFAULT_INSTALLATION_SLOT))
        self.DEFAULT_INSTALLATION_SLOT = self._inst_slot
        self._root_inst_slot           = cplcf.process("[PLCF#ROOT_INSTALLATION_SLOT]")

        self._ifaces                = []
        self._preBLOCK              = fakeBLOCK()
        self._STATUS                = None
        self._CMD                   = None
        self._PARAM                 = None
        self._GEN_INPUT             = None
        self._active_BLOCK          = None
        self._overlap               = None
        self._active                = True
        self._source                = ""
        self._to_plc_words_length   = 0
        self._from_plc_words_length = 0
        self._optimize              = OPTIMIZE
        self._plc_array             = None
        self._filename              = None
        self._artifact              = None
        self._readonly              = keyword_params.get("PLC_READONLY", False)
        self._experimental          = keyword_params.get("EXPERIMENTAL", False)
        self._quiet                 = keyword_params.get("QUIET",        False)
        self._global_defaults       = dict()
        self._defaults              = dict()
        self._macros                = list()
        self._external_validity_pvs = dict()

        self._features              = [ "STABLE-HASH", "OPC", "OPC-UA", "MULTILINE", "VALIDITY-PV", "ARRAY-START-IDX", "SELECTIVE-GATEWAY-DB" ]
        self._experimental_features = []

        if self._experimental:
            self._features.extend(self._experimental_features)

        self._interface_funcs = dict()

        self._evalEnv = dict()
        self._evalEnv['__builtins__'] = None
        self._evalEnv['True'] = True
        self._evalEnv['False'] = False
        for f in dir(self):
            val = getattr(self, f)
            if not hasattr(val, '__call__') or f.startswith('_'):
                continue

            if val.__name__ in ["ifdef_interface_func", "hashed_interface_func", "experimental_interface_func"]:
                self._interface_funcs[val] = f
                self._evalEnv[f] = val


    def __enter__(self):
        return self


    def __exit__(self, type, value, traceback):
        # Close ifdef if there was no exception
        if type is None:
            self._end()


    def _eval(self, line):
        if line.split('(')[0] not in self._evalEnv:
            raise IfDefSyntaxError("Not supported keyword")

        try:
            result = eval(line, self._evalEnv)

            if not isinstance(result, IF_DEF_INTERFACE_FUNC):
               raise IfDefSyntaxError("Missing parentheses?")
        except NameError as e:
            raise IfDefSyntaxError(e)
        except TypeError as e:
            words = e.args[0].split(' ')
            if len(words) > 1:
                first_word = words[0]
                if first_word[:-2] in self._evalEnv and words[1] == 'takes' and words[2] == 'exactly':
                    # Decrease numbers by 1 ('self' should be hidden from user)
                    words[3] = str(int(words[3]) - 1)
                    words[5] = "({}".format(int(words[5][1:]) - 1)
                    e.args = (" ".join(words),)
                    raise IfDefSyntaxError(e)
            raise


    def _status_block(self):
        return self._STATUS


    def _cmd_block(self):
        return self._CMD


    def _param_block(self):
        return self._PARAM


    def _gen_input_block(self):
        return self._GEN_INPUT


    def _active_block(self):
        if self._active_BLOCK is None:
            raise IfDefSyntaxError("Must define a block first!")

        if self._overlap is not None:
            return self._overlap

        return self._active_BLOCK


    def _active_bit_def(self):
        return BITS.get_bit_def(self._active_block())


    def _end_block(self, block):
        self._end_plc_array()

        if block is not None:
            block.end()
            if not self._quiet:
                print("{var}: {length}".format(var = block.length_keyword(), length = str(block.length() // 2)))


    def _add(self, var):
        assert isinstance(var, SOURCE), func_param_msg("var", "SOURCE")

        if isinstance(var, BASE_TYPE):
            self._check_plc_array(var.plc_type())

        if self._active_BLOCK is not None:
            if self._overlap is None:
                self._active_BLOCK.add_iface(var)
        else:
            self._preBLOCK.add_iface(var)

        self._ifaces.append(var)
        return var


    def _add_comment(self, line):
        assert isinstance(line, str), func_param_msg("line", "string")

        var   = SOURCE(line, comment = True)
        return self._add(var)


    def _add_source(self):
        return self._add(SOURCE(self._source))


    # returns the length of 'block' in (16 bit) words
    def _words_length_of(self, block):
        if block is None:
            return 0

        assert isinstance(block, BLOCK), func_param_msg("block", "BLOCK", type(block))

        return block.length() // 2


    def _exception_if_active(self):
        if self._active:
            raise IfDefSyntaxError("The interface definition is still active!")


    def _end_plc_array(self):
        if self._plc_array is not None:
            self.end_plc_array()


    def _check_plc_array(self, atype):
        if self._plc_array is None:
            return

        if self._plc_array[1] is None:
            self._plc_array = (self._plc_array[0], atype, self._plc_array[2])
            return
        elif self._plc_array[1] == atype:
            return

        raise IfDefSyntaxError("Array is already using {type}, cannot use {atype}".format(type = self._plc_array[1], atype = atype))


    def _calc_block_hash(self, hashobj, block):
        if block is None:
            return

        hashobj.update(block.hash_message())
        for var in block.interfaces():
            hashobj.update(var.hash_message())


    def _handle_extra_params(self, keyword_params):
        if self._plc_array is not None:
            if "USE_GATEWAY_DB" in keyword_params:
                raise IfDefSyntaxError("`USE_GATEWAY_DB` must be used in `define_plc_array()`")
            # Must be defined in define_plc_array() BUT we need to know this for every individual variable
            keyword_params["USE_GATEWAY_DB"] = self._plc_array[2]

        keyword_params["DATABLOCK"] = self._datablock_name

        return keyword_params


    def _expand_templates(self, keyword_params):
        if "TEMPLATE" not in keyword_params:
            return

        tname = keyword_params["TEMPLATE"]
        if tname not in self._templates:
            raise IfDefSyntaxError("No such template: " + tname)

        template = self._templates[tname]
        for tkey in template.keys():
            if tkey not in keyword_params:
                keyword_params[tkey] = template[tkey]


    def _parse(self, line, linenum):
        self._source  = (line, linenum)
        stripped_line = line.strip()

        try:
            if not isinstance(line, str) and not isinstance(line, unicode):
                raise IfDefSyntaxError("Interface definition lines must be strings!")

            if not self._active:
                raise IfDefSyntaxError("The interface definition is no longer active!")

            if stripped_line.startswith("_"):
                raise IfDefSyntaxError("Interface definition lines cannot start with '_'")

            if stripped_line.startswith("#TF#") or stripped_line.startswith("#-"):
                return

            if stripped_line.startswith("#"):
                self._add_comment(line[1:])
                return

            if stripped_line == "":
                self._add_comment(line)
                return

            self._eval(stripped_line)
        except IfDefException as e:
            e.add_params(filename = self._filename, line = stripped_line, linenum = linenum)
            raise
        except AssertionError as e:
            raise IfDefInternalError(e, filename = self._filename, line = stripped_line, linenum = linenum)
        except SyntaxError as e:
            if e.msg == "unexpected EOF while parsing":
                raise IfDefPrematureEnd()
            elif e.msg == "EOF while scanning triple-quoted string literal":
                raise IfDefPrematureEnd()
            elif e.msg == "invalid syntax" and e.lineno > 1 and len(stripped_line.splitlines()[e.lineno - 1]) == e.offset:
                raise IfDefPrematureEnd()
            raise IfDefSyntaxError(e.msg, filename = self._filename, line = stripped_line, linenum = linenum + e.lineno - 1)
        except TypeError as e:
            if "got an unexpected keyword argument" in e.message:
                raise IfDefSyntaxError(e.message, filename = self._filename, line = stripped_line, linenum = linenum)

            raise


    def _read_def(self, def_file, cplcf):
        if self._filename is not None:
            raise IfDefInternalError("Cannot parse more than one Interface Definition file")

        self._filename = def_file
        with open(def_file, 'r') as defs:
            multiline    = None
            multilinenum = 1
            linenum      = 1

            for line in defs:
                line = cplcf.processLine(line)

                try:
                    if multiline:
                        multiline += line
                        self._parse(multiline, multilinenum)
                        multiline = None
                    else:
                        self._parse(line, linenum)
                except IfDefPrematureEnd:
                    if multiline is None:
                        multiline    = line
                        multilinenum = linenum

                linenum += 1

            if multiline:
                raise IfDefPrematureEnd(def_file)


    def calculate_hash(self, hashobj):
        self._exception_if_active()

        if hashobj is None or "update" not in dir(hashobj) or not callable(hashobj.update):
            raise IfDefInternalError("Expected a hash object from the hashlib module!")

        self._calc_block_hash(hashobj, self._preBLOCK)
        self._calc_block_hash(hashobj, self._cmd_block())
        self._calc_block_hash(hashobj, self._param_block())
        self._calc_block_hash(hashobj, self._gen_input_block())
        self._calc_block_hash(hashobj, self._status_block())

        if int(self._to_plc_words_length) or int(self._from_plc_words_length):
            # None of this is needed I think...
            # but kept for hash stability
            properties = OrderedDict()
            properties[CMD_BLOCK.length_keyword()]    = self._words_length_of(self._cmd_block())
            properties[PARAM_BLOCK.length_keyword()]  = self._words_length_of(self._param_block())
            properties[STATUS_BLOCK.length_keyword()] = self._words_length_of(self._status_block())

            hashobj.update(str(properties))

        return hashobj


    @staticmethod
    def _check_pv_name(pv_names, var):
        if var.pv_name() in pv_names:
            raise IfDefSyntaxError("PV Names must be unique")


    def register_pv_name(self, var):
        self._check_pv_name(self._pv_names, var)
        self._pv_names[var.pv_name()] = var


    def register_plc_name(self, var):
        if var.name() in self._plc_names:
            raise IfDefSyntaxError("PLC variable names must be unique")
        self._plc_names.add(var.name())


    def interfaces(self):
        self._exception_if_active()

        return self._ifaces


    def status_block(self):
        self._exception_if_active()

        return self._status_block()


    def status_interfaces(self):
        block = self.status_block()

        if block:
            return block.interfaces()
        return []


    def has_status_pvs(self):
        block = self.status_block()

        if block:
            return block.length() > 0

        return False


    def command_block(self):
        self._exception_if_active()

        return self._cmd_block()


    def command_interfaces(self):
        block = self.command_block()

        if block:
            return block.interfaces()
        return []


    def has_command_pvs(self):
        block = self.command_block()

        if block:
            return block.length() > 0

        return False


    def parameter_block(self):
        self._exception_if_active()

        return self._param_block()


    def parameter_interfaces(self):
        block = self.parameter_block()

        if block:
            return block.interfaces()
        return []


    def has_parameter_pvs(self):
        block = self.parameter_block()

        if block:
            return block.length() > 0

        return False


    def general_input_block(self):
        self._exception_if_active()

        return self._gen_input_block()


    def general_input_interfaces(self):
        block = self.general_input_block()

        if block:
            return block.interfaces()
        return []


    def has_general_input_pvs(self):
        block = self.general_input_block()

        if block:
            return block.length() > 0

        return False


    def warnings(self):
        if self._filename:
            in_file = "In file {filename}".format(filename = self._filename)
            warns = ['', in_file, '=' * len(in_file)]
        else:
            warns = []

        for iface in self.interfaces():
            if iface.warnings() is not None:
                warns.extend(iface.warnings())

        return warns if len(warns) > 3 else []


    def external_validity_pvs(self):
        self._exception_if_active()

        return self._external_validity_pvs


    def to_plc_words_length(self):
        self._exception_if_active()

        return self._to_plc_words_length


    def from_plc_words_length(self):
        self._exception_if_active()

        return self._from_plc_words_length


    def ess_name(self):
        """
            Returns the ESS name of this 'device'
        """
        return self._inst_slot


    def root_ess_name(self):
        """
            Returns the ESS name of the root device
        """
        return self._root_inst_slot


    def inst_slot(self, nonnull = True):
        # If nonnull is False and we are using the default installation slot, then return None
        if not nonnull and self._inst_slot == IF_DEF.DEFAULT_INSTALLATION_SLOT:
            return None

        return self._inst_slot


    def datablock_name(self):
        return self._datablock_name


    def alarms(self):
        self._exception_if_active()

        if self._status_block() is None:
            return []

        return filter(lambda a: isinstance(a, ALARM), self._status_block().interfaces())


    def has_pv(self, pv_name, prefix = None):
        """
            Returns the PV with `pv_name`. If `prefix` is specified and `pv_name` starts with `prefix` then it will be ignored when matching the name
        """
        self._exception_if_active()

        # `pv_name` might or might not start with `prefix`
        if prefix and pv_name.startswith(prefix):
            pv_name = pv_name[len(prefix):]

        return self._pv_names.get(pv_name)


    def macros(self):
        return self._macros


    @ifdef_interface
    def require_feature(self, *features):
        if len(features) == 0:
            raise IfDefSyntaxError("Must specify at least one required feature")

        for feature in features:
            if not isinstance(feature, str):
                raise IfDefSyntaxError("Features must be strings")

            if feature.upper() not in self._features:
                if feature.upper() in self._experimental_features:
                    raise IfDefExperimentalFeatureError(feature)
                raise IfDefFeatureMissingError(feature)

        return SOURCE(self._source)


    def __do_with_defaults(self, func, *keywords):
        """
        Calls 'func' for every interface function in keywords
        """
        interface_func_type = type(self.set_defaults)
        for keyword in keywords:
            # Catch case when function is specified as-is; without quotes
            if not isinstance(keyword, str):
                if type(keyword) == interface_func_type:
                    keyword = self._interface_funcs[keyword]
                    if keyword in self.IGNORE_DEFAULTS_FOR:
                        continue
                else:
                    raise IfDefSyntaxError("Not an Interface Definition keyword: " + str(keyword))

            func(keyword)


    @ifdef_interface
    def clear_defaults(self, *keywords):
        """
        Clears defaults set for a definition type
        """
        if not keywords:
            raise IfDefSyntaxError("'clear_defaults' requires at least one Interface Definition keyword")

        def __clear(kw):
            del self._defaults[kw]

        self.__do_with_defaults(__clear, *keywords)

        return SOURCE(self._source)


    @ifdef_interface
    def set_defaults(self, *keywords, **keyword_params):
        """
        Sets defaults for a definition type. Additional calls will append new defaults
        """
        if not keywords:
            self._global_defaults.update(keyword_params)
        else:
            def __set(kw):
                d = self._defaults.get(kw, dict())
                d.update(keyword_params)
                self._defaults[kw] = d

            self.__do_with_defaults(__set, *keywords)

        return SOURCE(self._source)


    @ifdef_interface
    def define_installation_slot(self, name):
        if self._pv_names:
            raise IfDefSyntaxError("Cannot define installation slot after adding PVs!")
        if self._inst_slot != IF_DEF.DEFAULT_INSTALLATION_SLOT:
            raise IfDefSyntaxError("Installation slot redefinition is not possible!")

        self._inst_slot = name
        if name[0] == '$':
            self._macros.append(name)

        return self._add_source()


    @ifdef_interface
    def external_validity_pv(self, validity_pv, VALIDITY_CONDITION):
        if not isinstance(validity_pv, str):
            raise IfDefSyntaxError("Validity PV name must be a string!")
        if not isinstance(VALIDITY_CONDITION, str) and not isinstance(VALIDITY_CONDITION, bool):
            raise IfDefSyntaxError("Validity PV condition must be a string or boolean (True/False)!")

        try:
            if self._external_validity_pvs[validity_pv] != VALIDITY_CONDITION:
                raise IfDefSyntaxError("Cannot change validity condition of external validity PV '{}'".format(validity_pv))
        except KeyError:
            self._external_validity_pvs[validity_pv] = VALIDITY_CONDITION

        return SOURCE(self._source)


    @ifdef_interface
    def define_template(self, name, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Template name must be a string!")

        if not isinstance(keyword_params, dict):
            raise IfDefSyntaxError("Template must be dictionary")

        if name in self._templates:
            raise IfDefSyntaxError("Template is already defined: " + name)

        self._templates[name] = keyword_params

        return self._add_source()


    @ifdef_interface
    def define_status_block(self):
        if self._STATUS is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._STATUS = STATUS_BLOCK(self._source, self._optimize)
        return self._add(self._STATUS)


    @ifdef_interface
    def define_command_block(self):
        if self._readonly:
            raise IfDefSyntaxError("Cannot declare command block when in read-only mode")
        if self._CMD is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._CMD = CMD_BLOCK(self._source, self._optimize)
        return self._add(self._CMD)


    @ifdef_interface
    def define_parameter_block(self):
        if self._readonly:
            raise IfDefSyntaxError("Cannot declare parameter block when in read-only mode")
        if self._PARAM is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._PARAM = PARAM_BLOCK(self._source, self._optimize)
        return self._add(self._PARAM)


    @ifdef_interface
    def define_general_input_block(self):
        if self._readonly:
            raise IfDefSyntaxError("Cannot declare input block when in read-only mode")
        if self._GEN_INPUT is not None:
            raise IfDefSyntaxError("Block redefinition is not possible!")

        self._active_BLOCK = self._GEN_INPUT = GEN_INPUT_BLOCK(self._source, self._optimize)
        return self._add(self._GEN_INPUT)


    @experimental_interface
    @ifdef_interface
    def define_overlap(self):
        if self._active_BLOCK is None:
            raise IfDefSyntaxError("Define block first")
        if self._overlap is not None:
            raise IfDefSyntaxError("End current overlap first")

        self._overlap = self._active_BLOCK.get_overlap()
        return self._add_source()


    @experimental_interface
    @ifdef_interface
    def end_overlap(self):
        if self._overlap is None:
            raise IfDefSyntaxError("No overlap found")

        self._overlap.end()
        self._overlap = None
        return self._add_source()


    @ifdef_interface
    def define_datablock(self, name):
        if name is None:
            name = self.DEFAULT_DATABLOCK_NAME

        self._datablock_name = name

        return self._add_source()


    @ifdef_interface
    def define_plc_array(self, name, USE_GATEWAY_DB = True, START_IDX = 1):
        if self._plc_array is not None:
            raise IfDefSyntaxError("Nesting of arrays is not possible")

        # check if there is a block defined
        # redundant with hash_message _active_block() call
        # not removing: if hash_message ever changes uncomment the following line
#        self._active_block()
        ifa_line = "DEFINE_ARRAY\n{}\n{}{}".format(name, "" if USE_GATEWAY_DB else "NO_GATEWAY\nTrue\n", "" if START_IDX == 1 else "START_IDX\n{}\n".format(START_IDX))
        hash_message = "{}, DEFINE_PLC_ARRAY, {}{}{}".format(self._active_block().type(), name, "" if USE_GATEWAY_DB else ", False", "" if START_IDX == 1 else ", {}".format(START_IDX))
        var = PRINTER_METADATA(self._source, "IFA", ifa_line, hash_message = hash_message)
        self._plc_array = (name, None, USE_GATEWAY_DB)
        return self._add(var)


    @ifdef_interface
    def end_plc_array(self):
        if self._plc_array is None:
            raise IfDefSyntaxError("No array is defined yet")

        # check if there is a block defined
        # redundant with hash_message _active_block() call
        # not removing: if hash_message ever changes uncomment the following line
#        self._active_block()
        var = PRINTER_METADATA(self._source, "IFA", "END_ARRAY\n{}\n".format(self._plc_array[0]), hash_message = "{}, END_PLC_ARRAY".format(self._active_block().type()))
        self._plc_array = None
        return self._add(var)


    @ifdef_interface
    def define_metadata(self, name, **keyword_params):
        return SOURCE(self._source, keyword_params = keyword_params)


    @ifdef_interface
    def add_metadata(self, *params, **keyword_params):
        return SOURCE(self._source, keyword_params = keyword_params)


    @ifdef_interface
    def add_bit(self, name = None, **keyword_params):
        return self.add_digital(name, **keyword_params)


    @ifdef_interface
    def add_digital(self, name = None, **keyword_params):
        if name is None:
            _test_and_set(keyword_params, "SKIP_BITS", 1)

            if len(keyword_params) != 1:
                raise IfDefSyntaxError("Skipped digitals cannot have parameters")

            return self.skip_digitals(keyword_params["SKIP_BITS"])
        else:
            keyword_params = self._handle_extra_params(keyword_params)

            bit_def = self._active_bit_def()

            var = BIT(self._source, bit_def, name, keyword_params)
            return self._add(var)


    def _add_alarm(self, name, sevr, alarm_message, **keyword_params):
        keyword_params = self._handle_extra_params(keyword_params)

        if not sevr in [ "MINOR", "MAJOR" ]:
            raise IfDefSyntaxError("Invalid alarm severity: " + sevr)
        if not isinstance(alarm_message, str):
            raise IfDefSyntaxError("Alarm message is missing: {func}(\"{name}\", \"Short alarm message\")".format(name = name, func = "add_minor_alarm" if sevr == "MINOR" else "add_major_alarm"))

        if self._active_BLOCK is None or not self._active_BLOCK.from_plc():
            raise IfDefSyntaxError("Alarms can only be defined as STATUS variables!")

        if keyword_params.get("INVERSE_LOGIC", False) or keyword_params.get("ALARM_IF", True) == False:
            keyword_params.update(PV_ZSV  = sevr)
            _test_and_set_pv(keyword_params, "ZNAM", alarm_message)
        else:
            keyword_params.update(PV_OSV  = sevr)
            _test_and_set_pv(keyword_params, "ONAM", alarm_message)

        var = ALARM(self._source, self._active_bit_def(), name, sevr, alarm_message, keyword_params)
        return self._add(var)


    # Accept None as alarm_message, so that we could display a meaningful
    #  error message in _add_alarm() if it is not provided
    @ifdef_interface
    def add_minor_alarm(self, name, alarm_message = None, **keyword_params):
        return self._add_alarm(name, "MINOR", alarm_message, **keyword_params)


    @ifdef_interface
    def add_major_alarm(self, name, alarm_message = None, **keyword_params):
        return self._add_alarm(name, "MAJOR", alarm_message, **keyword_params)


    def _get_previous_analog_var(self):
        """
            Returns the most recent `BASE_TYPE` variable skipping `non-BASE_TYPE`-s. If it finds a `DFANOUT` then returns its affected PV
        """

        # Get the most recent variable; it must be an ANALOG.
        var = None
        try:
            sifaces = self._active_BLOCK.interfaces()
            i = -1
            while True:
                var = sifaces[i]
                i -= 1
                if isinstance(var, DFANOUT):
                    var = var.affected_pv()
                    break
                if not isinstance(var, BASE_TYPE):
                    continue
                if isinstance(var, BASE_TYPE):
                    break
        except IndexError:
            raise IfDefSyntaxError("Could not find variable this limit belongs to; you must add one with 'add_analog(...)' before adding a limit!")

        if not isinstance(var, ANALOG):
            raise IfDefSyntaxError("Limits can only be defined for analog variables!")

        return var


    def _get_alarm_limited_var(self):
        """
            Returns the "limited" variable
        """

        if self._active_BLOCK is None or not self._active_BLOCK.from_plc():
            raise IfDefSyntaxError("Alarm limits can only be defined for analog STATUS variables!")

        var = self._get_previous_analog_var()

        return var


    def _add_alarm_limit(self, name, plc_var_type, limit_severity, limit_type, **keyword_params):
        """
            Adds alarm limit variable and helper PV to set the limit of the limited variable based on the value of the alarm limit variable
        """

        if plc_var_type is not None and not isinstance(plc_var_type, str):
            raise IfDefSyntaxError("PLC type must be a string!")

        limited_var = self._get_alarm_limited_var()
        if plc_var_type is None:
            plc_var_type = limited_var.plc_type()

        # Add readback variable
        self.add_analog(name, plc_var_type, **keyword_params)

        # Add helper PV to set alarm limit
        # Sanitize keyword_params: they were meant to the add_analog() part
        s_keyword_params = dict()
        try:
            s_keyword_params[PV.PV_NAME] = keyword_params[PV.PV_NAME]
        except KeyError:
            pass
        return self._set_alarm_limit(name, limit_severity, limit_type, limited_var, **s_keyword_params)


    def _set_alarm_limit(self, name, limit_severity, limit_type, limited_var = None, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        if limited_var is None:
            limited_var = self._get_alarm_limited_var()

        var = ANALOG_ALARM_LIMIT.create(self, self._source, name, limit_severity, limit_type, limited_var, **keyword_params)
        if var:
            return self._add(var)

        return self._add_source()


    @ifdef_interface
    def add_minor_low_limit(self, name, plc_var_type = None, **keyword_params):
        return self._add_alarm_limit(name, plc_var_type, ANALOG_ALARM_LIMIT.MINOR_SEVERITY, ANALOG_ALARM_LIMIT.LOW_LIMIT, **keyword_params)


    @ifdef_interface
    def add_major_low_limit(self, name, plc_var_type = None, **keyword_params):
        return self._add_alarm_limit(name, plc_var_type, ANALOG_ALARM_LIMIT.MAJOR_SEVERITY, ANALOG_ALARM_LIMIT.LOW_LIMIT, **keyword_params)


    @ifdef_interface
    def add_minor_high_limit(self, name, plc_var_type = None, **keyword_params):
        return self._add_alarm_limit(name, plc_var_type, ANALOG_ALARM_LIMIT.MINOR_SEVERITY, ANALOG_ALARM_LIMIT.HIGH_LIMIT, **keyword_params)


    @ifdef_interface
    def add_major_high_limit(self, name, plc_var_type = None, **keyword_params):
        return self._add_alarm_limit(name, plc_var_type, ANALOG_ALARM_LIMIT.MAJOR_SEVERITY, ANALOG_ALARM_LIMIT.HIGH_LIMIT, **keyword_params)


    @ifdef_interface
    def set_minor_low_limit_from(self, name, EXTERNAL_PV = False):
        return self._set_alarm_limit(name, ANALOG_ALARM_LIMIT.MINOR_SEVERITY, ANALOG_ALARM_LIMIT.LOW_LIMIT, EXTERNAL_PV = EXTERNAL_PV)


    @ifdef_interface
    def set_major_low_limit_from(self, name, EXTERNAL_PV = False):
        return self._set_alarm_limit(name, ANALOG_ALARM_LIMIT.MAJOR_SEVERITY, ANALOG_ALARM_LIMIT.LOW_LIMIT, EXTERNAL_PV = EXTERNAL_PV)


    @ifdef_interface
    def set_minor_high_limit_from(self, name, EXTERNAL_PV = False):
        return self._set_alarm_limit(name, ANALOG_ALARM_LIMIT.MINOR_SEVERITY, ANALOG_ALARM_LIMIT.HIGH_LIMIT, EXTERNAL_PV = EXTERNAL_PV)


    @ifdef_interface
    def set_major_high_limit_from(self, name, EXTERNAL_PV = False):
        return self._set_alarm_limit(name, ANALOG_ALARM_LIMIT.MAJOR_SEVERITY, ANALOG_ALARM_LIMIT.HIGH_LIMIT, EXTERNAL_PV = EXTERNAL_PV)


    def _set_drive(self, name, drive_type, **keyword_params):
        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        if self._active_BLOCK is None or not self._active_BLOCK.to_plc():
            raise IfDefSyntaxError("Drive limits can only be defined for analog OUTPUT variables!")

        driven_var = self._get_previous_analog_var()

        var = ANALOG_DRIVE_LIMIT.create(self, self._source, name, drive_type, driven_var, **keyword_params)
        if var:
            return self._add(var)

        return self._add_source()


    @ifdef_interface
    def set_low_drive_limit_from(self, name, EXTERNAL_PV = False):
        return self._set_drive(name, ANALOG_DRIVE_LIMIT.LOW, EXTERNAL_PV = EXTERNAL_PV)


    @ifdef_interface
    def set_high_drive_limit_from(self, name, EXTERNAL_PV = False):
        return self._set_drive(name, ANALOG_DRIVE_LIMIT.HIGH, EXTERNAL_PV = EXTERNAL_PV)


    @ifdef_interface
    def skip_bit(self):
        return self.skip_digital()


    @ifdef_interface
    def skip_digital(self):
        return self.skip_digitals(1)


    @ifdef_interface
    def skip_bits(self, num):
        return self.skip_digitals(num)


    @ifdef_interface
    def skip_digitals(self, num):
        try:
            num = int(num)
        except (TypeError, ValueError):
            raise IfDefSyntaxError("Parameter must be a number!")

        bit_def = self._active_bit_def()
        BIT.skip(bit_def, num)
        return self._add_source()


    @ifdef_interface
    def add_float(self, name, plc_var_type, **keyword_params):
        return self.add_analog(name, plc_var_type, **keyword_params)


    @ifdef_interface
    def add_analog(self, name, plc_var_type, **keyword_params):
        keyword_params = self._handle_extra_params(keyword_params)

        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")
        if not isinstance(plc_var_type, str):
            raise IfDefSyntaxError("PLC type must be a string!")

        block = self._active_block()
        var = ANALOG(self._source, block, name, plc_var_type, keyword_params)
        return self._add(var)


    @ifdef_interface
    def add_time(self, name, **keyword_params):
        keyword_params = self._handle_extra_params(keyword_params)

        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")

        if PV.PV_EGU not in keyword_params:
            keyword_params[PV.PV_EGU] = "ms"

        block = self._active_block()
        var = TIME(self._source, block, name, keyword_params)
        return self._add(var)


    @ifdef_interface
    def add_enum(self, name, plc_var_type, nobt = -1, shift = 0, **keyword_params):
        keyword_params = self._handle_extra_params(keyword_params)

        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")
        if not isinstance(plc_var_type, str):
            raise IfDefSyntaxError("PLC type must be a string!")

        block = self._active_block()
        var = ENUM(self._source, block, name, plc_var_type, nobt, shift, keyword_params)
        return self._add(var)


    @ifdef_interface
    def add_bitmask(self, name, plc_var_type, nobt = -1, shift = 0, **keyword_params):
        keyword_params = self._handle_extra_params(keyword_params)

        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")
        if not isinstance(plc_var_type, str):
            raise IfDefSyntaxError("PLC type must be a string!")

        block = self._active_block()
        var = BITMASK(self._source, block, name, plc_var_type, nobt, shift, keyword_params)
        return self._add(var)


    @ifdef_interface
    def add_string(self, name, max_len = None, **keyword_params):
        keyword_params = self._handle_extra_params(keyword_params)

        if not isinstance(name, str):
            raise IfDefSyntaxError("Name must be a string!")
        if max_len is not None and not isinstance(max_len, int):
            raise IfDefSyntaxError("max_len must be an integer!")

        block = self._active_block()
        var   = STRING(self._source, block, name, max_len, keyword_params)
        return self._add(var)


    @ifdef_interface
    def add_verbatim(self, verbatim):
        if not isinstance(verbatim, str):
            raise IfDefSyntaxError("Only strings can be copied verbatim!")

        var = VERBATIM(("add_verbatim()\n", self._source[1]), verbatim)
        return self._add(var)


    @ifdef_interface
    def end_bits(self):
        return self.end_digitals()


    @ifdef_interface
    def end_digitals(self):
        var = self._add_source()
        BITS.end()
        return var


    def _end(self):
        if self._overlap is not None:
            raise IfDefSyntaxError("Overlap is not ended")

        self._end_block(self._cmd_block())
        self._end_block(self._param_block())
        self._end_block(self._gen_input_block())
        self._end_block(self._status_block())

        self._to_plc_words_length   = str(self._words_length_of(self._cmd_block()) + self._words_length_of(self._param_block()) + self._words_length_of(self._gen_input_block()))
        self._from_plc_words_length = str(self._words_length_of(self._status_block()))

        #
        # Make sure that the order of data TO the PLC is
        # 1. Commands
        # 2. Parameters
        # 3. General inputs
        #
        if self._CMD and self._PARAM:
            cmd_length = self._CMD.length()
            self._PARAM.set_start_offset(cmd_length)

        if self._GEN_INPUT:
            length = 0
            if self._PARAM:
                length = self._PARAM.start_offset() + self._PARAM.length()
            elif self._CMD:
                length = self._CMD.length()
            self._GEN_INPUT.set_start_offset(length)

        self._active = False

        param_uploads = PARAMETER_UPLOAD_FO.create_pvs_for_parameters(self.parameter_interfaces())
        self._param_uploader = param_uploads[0] if param_uploads else None
        self._ifaces.extend(param_uploads)

        PV.init(None)



class ROOT_IF_DEF(IF_DEF):
    @staticmethod
    def create_dummy_plcf():
        return DummyPLCF({ "[PLCF#{}]".format(IF_DEF.DEFAULT_INSTALLATION_SLOT) : "ROOT-INST:SLOT", "[PLCF#ROOT_INSTALLATION_SLOT]" : "ROOT-INST:SLOT" })


    def __init__(self, **keyword_params):
        if "PLCF" not in keyword_params:
            keyword_params["PLCF"] = ROOT_IF_DEF.create_dummy_plcf()
        super(ROOT_IF_DEF, self).__init__(**keyword_params)



class HEADER_IF_DEF(ROOT_IF_DEF):
    def __init__(self, device, **keyword_params):
        super(HEADER_IF_DEF, self).__init__(**keyword_params)

        self.__device = device


    def calculate_hash(self, hashobj):
        self._hash = hashobj.getCRC32()



class FOOTER_IF_DEF(ROOT_IF_DEF):
    def __init__(self, device, ifdefs, **keyword_params):
        super(FOOTER_IF_DEF, self).__init__(**keyword_params)

        self.__device = device
        self.__ifdefs = ifdefs

        # Check if we have an IFDEF that belongs to the PLC
        self.__plc_ifdef = None
        for ifdef in self.__ifdefs:
            if ifdef.ess_name() == self.ess_name():
                self.__plc_ifdef = ifdef
                break

        if self.__plc_ifdef:
            self.register_pv_name = self.__register_pv_name

        self.__upload_parameters_cmd()
        self._end()


    def __register_pv_name(self, var):
        self._check_pv_name(self.__plc_ifdef._pv_names, var)
        super(FOOTER_IF_DEF, self).register_pv_name(var)


    def __upload_parameters_cmd(self):
        # Create the InitUploadStat, DoneUploadStat, AssertUploadStat helper PVs
        helper_pvs = PARAMETER_UPLOAD_FO.create_stat_pvs()

        # Create the main UploadParametersCmd PV(s)
        self._ifaces.extend(PARAMETER_UPLOAD_FO.create_pvs(map(lambda x: x._param_uploader, filter(lambda ifdef: ifdef._param_uploader, self.__ifdefs)), True))

        # Add the helper PVs; not added before because previous versions had the UploadParametersCmd first and maintaining that order makes verifying this version easier
        self._ifaces.extend(helper_pvs)

        # Augment the very last parameter so that it calls DoneUploadStat when its done
        if not self.__ifdefs:
            return

        last_param = None
        for i in reversed(self.__ifdefs):
            for p in reversed(i.parameter_interfaces()):
                if isinstance(p, BASE_TYPE):
                    last_param = p
                    break
            if last_param:
                break

        if not last_param:
            return

        if last_param.get_pv_field(PV.PV_FLNK):
            self._ifaces.append(PARAMETER_UPLOAD_FO.create_helper_to_doneupload(last_param))
        else:
            last_param.set_pv_field(PV.PV_FLNK, PV.create_fqpn(PARAMETER_UPLOAD_FO.DONE_UPLOAD_STAT_PV))


    def calculate_hash(self, hashobj):
        pass


    def _end(self):
        self._active = False
        PV.init(None)



#
# PV class
#
class PV(SOURCE):
    DISABLE_WITH_PLC = True
    DONT_DISABLE_WITH_PLC = False

    FQPN_LEN  = 60

    PV_PREFIX = "PV_"
    PV_ALIAS  = PV_PREFIX + "ALIAS"
    PV_NAME   = PV_PREFIX + "NAME"
    PV_DESC   = PV_PREFIX + "DESC"
    PV_EGU    = PV_PREFIX + "EGU"
    PV_PREC   = PV_PREFIX + "PREC"
    PV_ONAM   = PV_PREFIX + "ONAM"
    PV_ZNAM   = PV_PREFIX + "ZNAM"
    PV_DRVL   = PV_PREFIX + "DRVL"
    PV_DRVH   = PV_PREFIX + "DRVH"
    PV_LOPR   = PV_PREFIX + "LOPR"
    PV_HOPR   = PV_PREFIX + "HOPR"
    PV_FLNK   = PV_PREFIX + "FLNK"

    PV_ZRST   = PV_PREFIX + "ZRST"
    PV_ONST   = PV_PREFIX + "ONST"
    PV_TWST   = PV_PREFIX + "TWST"
    PV_THST   = PV_PREFIX + "THST"
    PV_FRST   = PV_PREFIX + "FRST"
    PV_FVST   = PV_PREFIX + "FVST"
    PV_SXST   = PV_PREFIX + "SXST"
    PV_SVST   = PV_PREFIX + "SVST"
    PV_EIST   = PV_PREFIX + "EIST"
    PV_NIST   = PV_PREFIX + "NIST"
    PV_TEST   = PV_PREFIX + "TEST"
    PV_ELST   = PV_PREFIX + "ELST"
    PV_TVST   = PV_PREFIX + "TVST"
    PV_TTST   = PV_PREFIX + "TTST"
    PV_FTST   = PV_PREFIX + "FTST"
    PV_FFST   = PV_PREFIX + "FFST"

    # (len, strict) if strict is True, the text will be truncated
    field_lengths  = { PV_NAME  : (20, False),
                       PV_ALIAS : (20, False),
                       PV_DESC  : (40, True),
                       PV_EGU   : (15, True),
                       PV_PREC  : (15, False),
                       PV_ONAM  : (25, True),
                       PV_ZNAM  : (25, True),

                       PV_ZRST  : (25, True),
                       PV_ONST  : (25, True),
                       PV_TWST  : (25, True),
                       PV_THST  : (25, True),
                       PV_FRST  : (25, True),
                       PV_FVST  : (25, True),
                       PV_SXST  : (25, True),
                       PV_SVST  : (25, True),
                       PV_EIST  : (25, True),
                       PV_NIST  : (25, True),
                       PV_TEST  : (25, True),
                       PV_ELST  : (25, True),
                       PV_TVST  : (25, True),
                       PV_TTST  : (25, True),
                       PV_FTST  : (25, True),
                       PV_FFST  : (25, True)
                    }

    ifdef = None


    @staticmethod
    def init(ifdef):
        if PV.ifdef and ifdef:
            raise IfDefInternalError("Previous IF_DEF is not closed yet!")

        PV.ifdef = ifdef


    @staticmethod
    def to_pv_field(field):
        """
            Returns the internal representation of field name `field`
        """
        if field.startswith(PV.PV_PREFIX):
            return field

        return PV.PV_PREFIX + field


    @staticmethod
    def determine_pv_name(name, pv_fields):
        """
            Returns the PV name; `name` or "PV_NAME" from `pv_fields` if set
        """
        return pv_fields.get(PV.PV_NAME, name)


    @staticmethod
    def get_non_fpqn(name):
        """
            Returns the property part of `name`
            Assumes that everything after the last ':' is the property
        """
        return name.rpartition(':')[2]


    @staticmethod
    def __fqpn(q, p):
        name = "{slot}:{property}".format(slot = q, property = p)
        try:
            # If it has a macro then the length cannot be determined
            # If it has a field then that should not be counted in the length
            if '$' in name or len(name) <= PV.FQPN_LEN or name.index('.') < PV.FQPN_LEN:
                return (True, name)
        except ValueError:
            # No `.` in name and longer than PV.FQPN_LEN
            pass

        return (False, name)


    @staticmethod
    def create_fqpn(q, p = None):
        """
            Creates an FQPN from `q` and `p`; `q` being the ESS-name or and IF_DEF and `p` the property name. If `p` is omitted then `q` is assumed to be the property and ESS-name is taken from PV.ifdef
        """
        if p is None:
            if PV.ifdef is None:
                raise IfDefInternalError("No PV.ifdef")

            p = q
            q = PV.ifdef.ess_name()

        if not isinstance(q, str):
            q = q.ess_name()

        valid, name = PV.__fqpn(q, p)
        if valid:
            return name

        raise PVNameLengthException(name)


    @staticmethod
    def create_root_fqpn(p):
        """
            Creates an FQPN where ESS-name is taken from the root device
        """
        if PV.ifdef is None:
            raise IfDefInternalError("No PV.ifdef")
        return PV.create_fqpn(PV.ifdef.root_ess_name(), p)


    @staticmethod
    def is_fqpn(name):
        """
            Returns True if name is a FQPN
        """
        return False if name.find(':') == -1 else True


    def __init__(self, source, name, pv_type = None, disable_with_plc = False, **keyword_params):
        super(PV, self).__init__(source, keyword_params = keyword_params)

        assert isinstance(name, str), func_param_msg("name", "string")

        # Save ifdef locally (class var will be overwritten when a new IF_DEF class is instantiated)
        self.ifdef = PV.ifdef

        if name == "":
            raise IfDefSyntaxError("Empty name")

        for pv_ in self._keyword_params.keys():
            if not pv_.startswith(PV.PV_PREFIX):
                continue

            val = str(self._keyword_params[pv_])
            if len(val.splitlines()) > 1:
                raise IfDefSyntaxError("{} cannot span multiple lines".format(pv_))

        self._name = name
        self.__pv_type = pv_type
        self._disable_with_plc = disable_with_plc

        self._keyword_params[PV.PV_NAME] = self._check_pv_field(PV.PV_NAME, self.determine_pv_name(self._name, self._keyword_params))

        if isinstance(self, BASE_TYPE):
            self._pv_fields = {}
        else:
            self._pv_fields = OrderedDict()
        self._pv_aliases = []

        self._create_pv_fields()

        self._pvname = self._keyword_params[PV.PV_NAME]
        self._fqpvname = self.fqpn(self._pvname)

        if self._pvname == "":
            raise IfDefSyntaxError("Empty PV_NAME")

        if ' ' in self._pvname:
            raise IfDefSyntaxError("PV Names cannot contain spaces")

        self._register_pv_name()

        self.__comment = []
        self.add_comment(keyword_params.get("COMMENT"))


    def _register_pv_name(self):
        self.ifdef.register_pv_name(self)


    def _exception_params(self):
        return dict(filename = self.ifdef._filename, line = self.source(), linenum = self.sourcenum())


    def pv_name(self):
        """
            Returns the property part of PV name
        """
        return self._pvname


    def ess_name(self):
        """
            Returns the ESS name of this PV
        """
        return self.ifdef.ess_name()


    def fqpn(self, pv_name = None):
        """
            Returns the 'fully qualified' PV name
        """
        if pv_name is None:
            return self._fqpvname

        name = "{slot}:{property}".format(slot = self.ess_name(), property = pv_name)
        valid, name = PV.__fqpn(self.ess_name(), pv_name)
        if valid:
            return name

        raise PVNameLengthException(name, self._exception_params())


    def pv_type(self):
        """
            Returns the PV type (ai, ao, bi, etc)
        """
        if self.__pv_type:
            return self.__pv_type

        raise NotImplementedError


    def get_pv_field(self, field):
        """
            Returns the PV field `field` or None if no such field is set
        """
        return self._pv_fields.get(self.to_pv_field(field))


    def set_pv_field(self, field, value):
        """
            Sets the PV field `field` to `value`
        """
        field = self.to_pv_field(field)
        # Add the unmodfied (i.e. not truncated) field value to _keyword_params
        self._keyword_params[field] = value
        # Add the (possibly) truncated field value to _pv_fields
        self._pv_fields[field] = self._check_pv_field(field, value)


    def add_comment(self, comment):
        if comment is None:
            return

        if not isinstance(comment, list):
            comment = comment.splitlines()

        # Remove last element; it must be an empty string
        if self.__comment:
            self.__comment.pop()

        for c in comment:
            if not c.startswith("#"):
                c = "#".join(['', c])

            self.__comment.append(c)

        # This will cause "\n".join to append a newline in to_epics_record()
        self.__comment.append("")


    def add_alias(self, alias):
        """
            Adds an alias to the PV
        """

        if alias == "" or alias == []:
            raise IfDefSyntaxError("Empty PV_ALIAS")

        if isinstance(alias, str):
            self._pv_aliases.append(self._check_pv_field(PV.PV_ALIAS, alias))
        elif isinstance(alias, list):
            self._pv_aliases.extend(map(lambda a: self._check_pv_field(PV.PV_ALIAS, a), alias))
        elif not isinstance(alias, list):
            raise IfDefSyntaxError("PV_ALIAS must be a string or a list")


    def build_pv_extra(self, sort = False):
        """
            Returns the PV fields in EPICS format:
             field(key, "value")
        """

        if not self._pv_fields:
            return ""

        pv_field3 = """\tfield({key},  "{value}")"""
        pv_field4 = """\tfield({key}, "{value}")"""

        if sort:
            fields = sorted(self._pv_fields.keys())
        elif PV.PV_DESC in self._pv_fields.keys():
            fields = list(self._pv_fields.keys())
        else:
            fields = None

        if fields:
            # Make DESC the first field
            try:
                fields.remove(PV.PV_DESC)
                fields.insert(0, PV.PV_DESC)
            except ValueError:
                pass

            # Make FLNK the last field
            try:
                fields.remove(PV.PV_FLNK)
                fields.append(PV.PV_FLNK)
            except ValueError:
                pass
        else:
            fields = self._pv_fields.keys()

        formatter = lambda f: pv_field3 if len(f) == 6 else pv_field4
        return """
{}""".format('\n'.join(map(lambda f: formatter(f).format(key = f[3:], value = self._pv_fields[f]), fields)))


    def build_pv_alias(self):
        """
            Returns the alias specifications for the PV in EPICS format
            'create_pv_name' is a function to create the fully qualified PV name
        """

        if not self._pv_aliases:
            return ""

        fmt = """\talias("{}")"""
        # empty line
        # aliases
        # empty line
        return """
{}
""".format("\n".join(map(lambda alias : fmt.format(self.fqpn(alias)), self._pv_aliases)))


    def to_epics_record(self, sdis_fields = ""):
        return """{comment}record({recordtype}, "{pv_name}")
{{{alias}{pv_extra}{sdis_fields}
}}

""".format(comment     = "\n".join(self.__comment) if self.__comment else "",
           recordtype  = self.pv_type(),
           pv_name     = self.fqpn(),
           alias       = self.build_pv_alias(),
           pv_extra    = self.build_pv_extra(),
           sdis_fields = sdis_fields if self._disable_with_plc else "")


    def _check_pv_field_length(self, field, field_val, length_strict):
        msg_hdr_fmt = "The {field} field of the pv is too long: "

        field_val = str(field_val)

        (length, strict) = length_strict
        if len(field_val) > length:
            msg_hdr = msg_hdr_fmt.format(field = field)
            if self.sourcenum() != -1:
                print("At line number {lnum}:".format(lnum = self.sourcenum()))
            print(self._add_warning((msg_hdr + "{value} (length: {len} / {max_len})").format(value   = field_val,
                                                                                             len     = len(field_val),
                                                                                             max_len = length)))
            print(self._add_warning(" " * (len(msg_hdr) + length) + "^"))

            if strict:
                return field_val[:length]

        return field_val


    def _create_pv_fields(self):
        for field, value in self._keyword_params.items():
            if not field.startswith(PV.PV_PREFIX) or field == PV.PV_NAME:
                continue

            if field == PV.PV_ALIAS:
                self.add_alias(value)
            else:
                self._pv_fields[field] = self._check_pv_field(field, value)


    def _check_pv_field(self, field, value):
        if not isinstance(value, str) and not isinstance(value, int):
            raise IfDefSyntaxError("Field {} can only be a string".format(field))

        try:
            length_strict = PV.field_lengths[field]
        except KeyError:
            return value

        return self._check_pv_field_length(field, value, length_strict)



#
# Types
#
class BASE_TYPE(PV):
    ASYN_TIMEOUT   = "100"


    def __init__(self, source, block, name, plc_var_type, keyword_params):
        super(BASE_TYPE, self).__init__(source, name, disable_with_plc = True, **keyword_params)

        assert isinstance(block,        BLOCK),  func_param_msg("block",         "BLOCK")
        assert isinstance(plc_var_type, str),    func_param_msg("plc_var_type",  "string")

        if block.from_plc():
            reserved_params = ["DTYP", "INP", "SCAN"]
        else:
            reserved_params = ["DTYP", "OUT"]

        for param in map(lambda x: PV.PV_PREFIX + x, reserved_params):
            if param in self._pv_fields:
                raise IfDefSyntaxError(param + " is reserved!")

        """
           Check for PLC_TYPE="{S7PLCTYPE|MODBUSTYPE}"
        """
        (p, e) = block.pair_types(self._keyword_params)
        if p is not None:
            if p != plc_var_type:
                raise IfDefSyntaxError("PLC variable type ({}) cannot be overriden with {}={} construct".format(plc_var_type, p, e))
            self._plc_type = p
        else:
            self._plc_type = plc_var_type
        if e is None:
            e = block.plc_type_to_epics_type(self._plc_type)

        self._dtyp_var_type  = e

        self._block          = block
        self._datablock_name = self._keyword_params["DATABLOCK"]
        self._width          = self._calc_width_in_bytes()

        # Has to be after _width is initialized
        self._end_bits()

        if isinstance(block, OVERLAP):
            self._overlapped = not block.is_empty()
        else:
            self._overlapped = False

        self.compute_offset()

        if self._name == "":
            raise IfDefSyntaxError("Empty PLC variable name")

        self._register_plc_name()


    def _register_plc_name(self):
        self.ifdef.register_plc_name(self)


    def _calc_width_in_bytes(self):
        return _bytes_in_type(self._plc_type)


    def _end_bits(self):
        BITS.end(self._width)


    def hash_message(self):
        return "{block}, {name}, {plc_type}, {offset}.{bit_number}".format(block      = self.block_type(),
                                                                           name       = self.name(),
                                                                           plc_type   = self.plc_type(),
                                                                           offset     = self.offset(),
                                                                           bit_number = self.bit_number())


    def name(self):
        """
           The name of the variable
        """
        return self._name


    def dtyp_var_type(self):
        return self._dtyp_var_type


    def endian_correct_dtyp_var_type(self):
        return self._block.endian_correct_epics_type(self.dtyp_var_type())


    def datablock_name(self):
        return self._datablock_name


    def plc_type(self):
        """
           The type that is used on the PLC side. One of:
            - BOOL
            - BYTE
            - INT
            - WORD
            - DINT
            - DWORD
            - REAL
            - TIME
            - STRING
        """
        return self._plc_type


    def dtyp(self):
        return self._block.dtyp()


    def inst_io(self):
        return self._block.inst_io()


    def inp_out(self, **keyword_params):
        return self._block.inp_out(**keyword_params)


    def dimension(self):
        return 1


    def offset(self):
        return self._offset + self._block.start_offset()


    def from_plc(self):
        return self._block.from_plc()


    def to_plc(self):
        return self._block.to_plc()


    def is_status(self):
        return self._block.is_status_block()


    def is_command(self):
        return self._block.is_command_block()


    def is_parameter(self):
        return self._block.is_parameter_block()


    def is_general_input(self):
        return self._block.is_general_input_block()


    def is_overlapped(self):
        return self._overlapped


    def _get_user_link_extra(self):
        try:
            return " " + self._keyword_params["LINK_EXTRA"]
        except KeyError:
            return ""


    def bit_number(self):
        return 0


    def block_basetype(self):
        return self._block.basetype()


    def block_type(self):
        return self._block.type()


    def compute_offset(self):
        self._offset = self._block.offset_for(self._width)
        self._block.compute_offset(self._width)


    def link_offset(self, plc_to_epics_offset, epics_to_plc_offset):
        return self._block.link_offset(self, plc_to_epics_offset, epics_to_plc_offset)


    def build_pv_extra(self):
        return super(BASE_TYPE, self).build_pv_extra(True)


    def pv_template(self, **keyword_params):
        return self._block.pv_template(**keyword_params)


    def link_extra(self):
        link_extra_templates = { MODBUS.TYPE : BASE_TYPE.ASYN_TIMEOUT,   STATUS_BLOCK.TYPE : "" }
        return link_extra_templates[self.block_basetype()]



class BITS(object):
    active_bits = None

    def __init__(self, block):
        assert isinstance(block,    BLOCK),   func_param_msg("block", "BLOCK")
        super(BITS, self).__init__()

        BITS.end()

        if block.optimize() and block._block_offset % 2:
            # There is space for 8 bits only
            self._max_num_bits  = 8
            self._dtyp_var_type = "UINT8"
        else:
            self._max_num_bits  = 16
            self._dtyp_var_type = "UINT16"
        self._num_bits     = 0
        self._started      = True
        self._block        = block
        self._offset       = -1
        BITS.active_bits   = self


    @staticmethod
    def get_bit_def(block):
        assert isinstance(block, BLOCK),      func_param_msg("block", "BLOCK")

        if BITS.active_bits is None:
            return BITS(block)

        active_bits = BITS.active_bits

        if not block == active_bits._block:
            raise IfDefInternalError("Mixing BITS between BLOCKS")

        # Check if we ran out of space because of skip_digitals()
        if active_bits._num_bits >= active_bits._max_num_bits:
            excess_bits = active_bits._num_bits - active_bits._max_num_bits
            bits = BITS(block)
            if excess_bits > 0:
                # Carry over skipped digitals
                bits.add_bit(excess_bits)
            return bits

        return active_bits


    def add_bit(self, num):
        assert isinstance(num, int), func_param_msg("num", "integer")

        if not self._started:
            raise IfDefInternalError("BIT is undefined!")
        if num < 0:
            raise IfDefSyntaxError("Number of bits to skip must be greater than zero!")

        self._num_bits += num


    def dtyp_var_type(self):
        return self._dtyp_var_type


    def compute_offset(self, byte):
        self._block.compute_offset(byte)


    def calc_mask(self, bit):
        return '0x{:04X}'.format(1 << bit.bit_number())


    def link_extra(self, bit):
        if self._block.from_plc():
            return " B={bit_num}".format(bit_num = bit.bit_number())
        elif self._block.to_plc():
            template = "{mask}, " + BASE_TYPE.ASYN_TIMEOUT
            return template.format(mask = self.calc_mask(bit))
        else:
            raise IfDefInternalError("Unknown db type: " + self._block.type())


    @staticmethod
    def end(next_var_width = None):
        if BITS.active_bits is None:
            return

        self = BITS.active_bits
        if self._started == False:
            return

        # Optimize if bits fit into one byte and next var is a byte
        if self._block.optimize() and self._num_bits <= 8 and next_var_width is not None and next_var_width == 1:
            self._dtyp_var_type = "UINT8"

        byte_width   = _bytes_in_type(self.dtyp_var_type())
        self._offset = self._block.offset_for(byte_width)

        self.compute_offset(byte_width)
        self._started    = False
        BITS.active_bits = None



class BIT(BASE_TYPE):
    pv_types       = { MODBUS.TYPE : "bo",   STATUS_BLOCK.TYPE : "bi" }

    @staticmethod
    def skip(bit_def, num):
        bit_def.add_bit(num)


    def __init__(self, source, bit_def, name, keyword_params):
        assert isinstance(bit_def, BITS), func_param_msg("bit_def", "BITS")

        self._bit_def  = bit_def
        self._bit_num  = bit_def._num_bits

        #
        # BASE_TYPE.__init__ must be after self initialization
        #
        # 'WORD' is used as a placeholder only
        super(BIT, self).__init__(source, bit_def._block, name, "WORD", keyword_params)


    def _end_bits(self):
        pass


    def pv_type(self):
        return BIT.pv_types[self.block_basetype()]


    def plc_type(self):
        return "BOOL"


    def dtyp(self):
        if self.from_plc():
            return super(BIT, self).dtyp()

        return "asynUInt32Digital"


    def inst_io(self):
        if self.from_plc():
            return super(BIT, self).inst_io()

        return "asynMask"


    def offset(self):
        return self._bit_def._offset + self._block.start_offset()


    def bit_number(self):
        return self._bit_num


    def compute_offset(self):
        self._bit_def.add_bit(1)


    def link_extra(self):
        return self._bit_def.link_extra(self)


    def dtyp_var_type(self):
        if self.to_plc():
            return ""

        return self._bit_def.dtyp_var_type()



class ALARM(BIT):
    def __init__(self, source, bit_def, name, severity, message, keyword_params):
        super(ALARM, self).__init__(source, bit_def, name, keyword_params)

        self._severity = severity
        self._message  = message
        self._archive  = keyword_params.get("ARCHIVE", False)
        if not isinstance(self._archive, bool):
            self._archive = True


    def archive(self):
        return self._archive


    def message(self):
        return self._message



class ANALOG(BASE_TYPE):
    pv_types = { MODBUS.TYPE : "ao",   STATUS_BLOCK.TYPE : "ai" }

    def __init__(self, source, block, name, plc_var_type, keyword_params):
        limit_warnings = []
        if block.to_plc():
            try:
                limits = PLC_type_limits[plc_var_type]
                # Set DRVL/DRVH limits
                if keyword_params.get(PV.PV_DRVL, limits[0]) <= limits[0]:
                    if keyword_params.get(PV.PV_DRVL, limits[0]) < limits[0]:
                        limit_warnings.append("Specified DRVL ({}) is lower than limit ({}) of PLC data type '{}'".format(keyword_params[PV.PV_DRVL], limits[0], plc_var_type))
                    keyword_params[PV.PV_DRVL] = limits[0]
                if keyword_params.get(PV.PV_DRVH, limits[1]) >= limits[1]:
                    if keyword_params.get(PV.PV_DRVH, limits[1]) > limits[1]:
                        limit_warnings.append("Specified DRVH ({}) is higher than limit ({}) of PLC data type '{}'".format(keyword_params[PV.PV_DRVH], limits[1], plc_var_type))
                    keyword_params[PV.PV_DRVH] = limits[1]
                # Set LOPR/HOPR limits
                if keyword_params.get(PV.PV_LOPR, limits[0]) <= limits[0]:
                    if keyword_params.get(PV.PV_LOPR, limits[0]) < limits[0]:
                        limit_warnings.append("Specified LOPR ({}) is lower than limit ({}) of PLC data type '{}'".format(keyword_params[PV.PV_LOPR], limits[0], plc_var_type))
                    keyword_params[PV.PV_LOPR] = limits[0]
                if keyword_params.get(PV.PV_HOPR, limits[1]) >= limits[1]:
                    if keyword_params.get(PV.PV_HOPR, limits[1]) > limits[1]:
                        limit_warnings.append("Specified HOPR ({}) is higher than limit ({}) of PLC data type '{}'".format(keyword_params[PV.PV_HOPR], limits[1], plc_var_type))
                    keyword_params[PV.PV_HOPR] = limits[1]
            except KeyError:
                pass

        super(ANALOG, self).__init__(source, block, name, plc_var_type, keyword_params)
        for w in limit_warnings:
            print(self._add_warning(w))


    def dtyp(self):
        if not self.from_plc() and self._dtyp_var_type in self._block.valid_type_pairs()["REAL"]:
            return "asynFloat64"

        return super(ANALOG, self).dtyp()


    def pv_type(self):
        return ANALOG.pv_types[self.block_basetype()]



class TIME(ANALOG):
    def __init__(self, source, block, name, keyword_params):
        super(TIME, self).__init__(source, block, name, "TIME", keyword_params)



class DFANOUT(PV):
    OUTx    = [ 'OUTA', 'OUTB', 'OUTC', 'OUTD', 'OUTE', 'OUTF', 'OUTG', 'OUTH' ]


    @staticmethod
    def construct_name(input_name):
        return "#{}".format(PV.get_non_fpqn(input_name))


    def __init__(self, source, name, affected_pv, link, disable_with_plc, **keyword_params):
        super(DFANOUT, self).__init__(source, self.construct_name(name), "dfanout", disable_with_plc, **keyword_params)
        self.__outx = 0

        if PV.is_fqpn(name) or keyword_params.get("EXTERNAL_PV", False):
            source_pv = name
        else:
            source_pv = affected_pv.fqpn(name)

        self.set_pv_field("DOL", "{} CP".format(source_pv))
        self.set_pv_field("OMSL", "closed_loop")
        self._set_outx(affected_pv, link)


    def affected_pv(self):
        """
            Returns the PV that is the endpoint of the last OUTx link
        """
        return self.__affected_pv


    def _set_outx(self, affected_pv, link):
        self.__affected_pv = affected_pv

        try:
            outx = self.OUTx[self.__outx]
        except IndexError:
            raise IfDefSyntaxError("Sorry, cannot add more outputs :(")

        self.__outx += 1
        self.set_pv_field(outx, link)



class FANOUT(PV):
    # LNK0 is intentionally left out;
    #  - it needs SHFT set to '0'
    #  - allows late inserting of links
    LNKx = [ 'LNK1', 'LNK2', 'LNK3', 'LNK4', 'LNK5', 'LNK6', 'LNK7', 'LNK8', 'LNK9', 'LNKA', 'LNKB', 'LNKC', 'LNKD', 'LNKE', 'LNKF' ]


    class NoMoreLinksException(RuntimeError):
        pass


    @staticmethod
    def construct_name(input_name):
        return "#{}-FO".format(PV.get_non_fpqn(input_name))


    def __init__(self, source, name, link, disable_with_plc, keyword_params):
        super(FANOUT, self).__init__(source, self.construct_name(name), "fanout", disable_with_plc, **keyword_params)
        self.__lnkx = 0
        self._set_lnkx(link)


    def _set_lnkx(self, link):
        try:
            lnkx = self.LNKx[self.__lnkx]
        except IndexError:
            raise FANOUT.NoMoreLinksException()

        self.__lnkx += 1
        self.set_pv_field(lnkx, link)



class ANALOG_ALARM_LIMIT(DFANOUT):
    MAJOR_SEVERITY    = "MAJOR"
    MINOR_SEVERITY    = "MINOR"
    HIGH_LIMIT        = "HIGH"
    LOW_LIMIT         = "LOW"
    LIMIT_FIELD       = { (MAJOR_SEVERITY, LOW_LIMIT)  : "LOLO",
                          (MINOR_SEVERITY, LOW_LIMIT)  : "LOW",
                          (MAJOR_SEVERITY, HIGH_LIMIT) : "HIHI",
                          (MINOR_SEVERITY, HIGH_LIMIT) : "HIGH" }
    LIMIT_ALARM_FIELD = { (MAJOR_SEVERITY, LOW_LIMIT)  : "LLSV",
                          (MINOR_SEVERITY, LOW_LIMIT)  : "LSV",
                          (MAJOR_SEVERITY, HIGH_LIMIT) : "HHSV",
                          (MINOR_SEVERITY, HIGH_LIMIT) : "HSV" }


    def __init__(self, source, name, limit_severity, limit_type, limited_pv, **keyword_params):
        super(ANALOG_ALARM_LIMIT, self).__init__(source, name, limited_pv, self.__construct_link(limited_pv, limit_severity, limit_type), PV.DISABLE_WITH_PLC, **keyword_params)
        self.set_pv_field(PV.PV_DESC, "Set alarm limit value")

        # Set limit severity of _limited_ PV
        limited_pv.set_pv_field(ANALOG_ALARM_LIMIT.LIMIT_ALARM_FIELD[(limit_severity, limit_type)], limit_severity)


    @staticmethod
    def __construct_link(limited_pv, limit_severity, limit_type):
        return "{}.{}".format(limited_pv.fqpn(), ANALOG_ALARM_LIMIT.LIMIT_FIELD[(limit_severity, limit_type)])


    @staticmethod
    def create(ifdef, source, name, limit_severity, limit_type, limited_pv, **keyword_params):
        # Set limit severity of _limited_ PV
        limited_pv.set_pv_field(ANALOG_ALARM_LIMIT.LIMIT_ALARM_FIELD[(limit_severity, limit_type)], limit_severity)

        var = ifdef._pv_names.get(ANALOG_ALARM_LIMIT.construct_name(PV.determine_pv_name(name, keyword_params)))

        if var:
            if not isinstance(var, ANALOG_ALARM_LIMIT):
                raise IfDefSyntaxError("Internal variable already exists: {}".format(var.pv_name()))

            var.set_outx(limited_pv, limit_severity, limit_type)
            return None

        return ANALOG_ALARM_LIMIT(source, name, limit_severity, limit_type, limited_pv, **keyword_params)


    def limited_pv(self):
        """
            Shortcut to DFANOUT.affected_pv()
        """
        return self.affected_pv()


    def set_outx(self, limited_pv, limit_severity, limit_type):
        self._set_outx(limited_pv, self.__construct_link(limited_pv, limit_severity, limit_type))



class ANALOG_DRIVE_LIMIT(DFANOUT):
    HIGH = "HOPR"
    LOW  = "LOPR"


    def __init__(self, source, name, drive_field, driven_pv, **keyword_params):
        super(ANALOG_DRIVE_LIMIT, self).__init__(source, name, driven_pv, self.__construct_link(driven_pv, drive_field), PV.DISABLE_WITH_PLC, **keyword_params)
        self.set_pv_field(PV.PV_DESC, "Set drive limit value")


    @staticmethod
    def __construct_link(driven_pv, drive_field):
        return "{}.{}".format(driven_pv.fqpn(), drive_field)


    @staticmethod
    def create(ifdef, source, name, drive_type, driven_pv, **keyword_params):
        var = ifdef._pv_names.get(ANALOG_DRIVE_LIMIT.construct_name(PV.determine_pv_name(name, keyword_params)))
        if var:
            if not isinstance(var, ANALOG_DRIVE_LIMIT):
                raise IfDefSyntaxError("Internal variable already exists: {}".format(var.pv_name()))

            var.set_outx(driven_pv, drive_type)
            return None

        return ANALOG_DRIVE_LIMIT(source, name, drive_type, driven_pv, **keyword_params)


    def driven_pv(self):
        """
            Shortcut to DFANOUT.affected_pv()
        """
        return self.affected_pv()


    def set_outx(self, driven_pv, drive_field):
        self._set_outx(driven_pv, self.__construct_link(driven_pv, drive_field))



class PARAMETER_UPLOAD_FO(FANOUT):
    INITIAL_GLOBAL_PV = "UploadParametersCmd"
    INITIAL_DEVICE_PV = "#plcfDUplParamsCmd"

    GLOBAL_FO_PV = "#plcfGUplParam{:02X}-FO"
    DEVICE_FO_PV = "#plcfDUplParam{:02X}-FO"

    INIT_UPLOAD_STAT_PV = "#plcfInitUploadStat"
    DONE_UPLOAD_STAT_PV = "#plcfDoneUploadStat"
    ASSERT_UPLOAD_STAT_PV = "#plcfAssertUplStat"
    INTERMEDIATE_FO_PV = "#plcfLastPrmHlper-FO"

    __pvs = []
    __inituploadstat = None
    __doneuploadstat = None
    __assertuploadst = None


    @staticmethod
    def create_pvs_for_parameters(parameters):
        """
            Create uploader fanouts for all the `BASE_TYPE` interfaces in `parameters`
        """
        return PARAMETER_UPLOAD_FO.create_pvs(filter(lambda param: isinstance(param, BASE_TYPE), parameters), device_uploader = True)


    @staticmethod
    def create_pvs(parameters, initialize = False, device_uploader = False):
        """
            Create uploader fanouts for all the PVs in `parameters`
            If `initialize` is True then the very first fanout's first link will initialize upload statistics PV
        """
        PARAMETER_UPLOAD_FO.__pvs = []

        upload = None
        for param in parameters:
            upload = PARAMETER_UPLOAD_FO.__add_parameter(upload, param, initialize = initialize, device_uploader = device_uploader)

        # Create an empty UploadParametersCmd PV when there are no parameters and we are initializing
        if upload is None and initialize:
            PARAMETER_UPLOAD_FO.__add_parameter(None, PARAMETER_UPLOAD_FO.__doneuploadstat, initialize = True)

        pvs = PARAMETER_UPLOAD_FO.__pvs
        PARAMETER_UPLOAD_FO.__pvs = []

        return pvs


    @staticmethod
    def create_stat_pvs():
        PARAMETER_UPLOAD_FO.__inituploadstat = PV("", PARAMETER_UPLOAD_FO.INIT_UPLOAD_STAT_PV, "bo", PV.DONT_DISABLE_WITH_PLC)
        PARAMETER_UPLOAD_FO.__inituploadstat.set_pv_field(PV.PV_DESC,"Initialize parameter uploading status")
        PARAMETER_UPLOAD_FO.__inituploadstat.set_pv_field("DOL", PV.create_fqpn("#plcfC1"))
        PARAMETER_UPLOAD_FO.__inituploadstat.set_pv_field("OMSL", "closed_loop")
        PARAMETER_UPLOAD_FO.__inituploadstat.set_pv_field("OUT", PV.create_fqpn("#plcfUploadStatToPLCS PP"))

        PARAMETER_UPLOAD_FO.__doneuploadstat = PV("", PARAMETER_UPLOAD_FO.DONE_UPLOAD_STAT_PV, "longout", PV.DONT_DISABLE_WITH_PLC)
        PARAMETER_UPLOAD_FO.__doneuploadstat.set_pv_field(PV.PV_DESC, "Done parameter uploading status")
        PARAMETER_UPLOAD_FO.__doneuploadstat.set_pv_field("DOL", PV.create_fqpn("#plcfC2"))
        PARAMETER_UPLOAD_FO.__doneuploadstat.set_pv_field("OMSL", "closed_loop")
        PARAMETER_UPLOAD_FO.__doneuploadstat.set_pv_field("OUT", PV.create_fqpn("#plcfUploadStatToPLCS PP"))
        # Disable this PV if not uploading:
        #  `uploading` is '1', `uploaded` is '2', so we disable on `never_uploaded` (0)
        PARAMETER_UPLOAD_FO.__doneuploadstat.set_pv_field("SDIS", PV.create_fqpn("UploadStat-RB"))
        PARAMETER_UPLOAD_FO.__doneuploadstat.set_pv_field("DISV", "0")

        PARAMETER_UPLOAD_FO.__assertuploadst = PV("", PARAMETER_UPLOAD_FO.ASSERT_UPLOAD_STAT_PV, "calcout", PV.DONT_DISABLE_WITH_PLC, COMMENT = "If PLC says we are uploading but #plcfInitUploadStat was never processed ==> reset upload status in the PLC")
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field(PV.PV_DESC, "Assert validity of upload statistics")
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field("INPA", PV.create_fqpn("UploadStat-RB CP"))
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field("INPB", "{}.UDF".format(PARAMETER_UPLOAD_FO.__inituploadstat.fqpn()))
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field("CALC", "A == 1 && B == 1")
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field("OOPT", "When Non-zero")
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field("DOPT", "Use OCAL")
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field("OCAL", "0")
        PARAMETER_UPLOAD_FO.__assertuploadst.set_pv_field("OUT", PV.create_fqpn("#plcfUploadStatToPLCS PP"))

        return [PARAMETER_UPLOAD_FO.__inituploadstat, PARAMETER_UPLOAD_FO.__doneuploadstat, PARAMETER_UPLOAD_FO.__assertuploadst]


    @staticmethod
    def create_helper_to_doneupload(last_param):
        intermediate_fo = PV("", PARAMETER_UPLOAD_FO.INTERMEDIATE_FO_PV, "fanout", PV.DONT_DISABLE_WITH_PLC)
        intermediate_fo.set_pv_field(PV.PV_DESC, "Helper PV to inject processing of #DoneUploadStat")
        intermediate_fo.set_pv_field("LNK1", last_param.get_pv_field(PV.PV_FLNK))
        intermediate_fo.set_pv_field(PV.PV_FLNK, PARAMETER_UPLOAD_FO.__doneuploadstat.fqpn())

        # Inject the intermediate fanout as the last parameter's FLNK
        last_param.set_pv_field(PV.PV_FLNK, intermediate_fo.fqpn())

        return intermediate_fo


    @staticmethod
    def __add_parameter(upload_fo, parameter, initialize = False, device_uploader = False):
        if upload_fo is None:
            keyword_params = dict()
            if initialize:
                keyword_params["PV_SHFT"] = "0"
                keyword_params["PV_LNK0"] = PV.create_root_fqpn(PARAMETER_UPLOAD_FO.INIT_UPLOAD_STAT_PV)
            if device_uploader:
                # Start with sending a heartbeat; uploading parameters can take a while and we don't want the PLC to think we are dead
                keyword_params["PV_SHFT"] = "0"
                keyword_params["PV_LNK0"] = PV.create_root_fqpn("HeartbeatToPLCS")
            else:
                keyword_params[PV.PV_ALIAS] = "UploadParametersS"
            upload_fo = PARAMETER_UPLOAD_FO(PARAMETER_UPLOAD_FO.INITIAL_DEVICE_PV if device_uploader else PARAMETER_UPLOAD_FO.INITIAL_GLOBAL_PV, parameter, **keyword_params)
        else:
            try:
                upload_fo.set_lnkx(parameter)
            except FANOUT.NoMoreLinksException:
                keyword_params = dict()
                if device_uploader:
                    # Start with sending a heartbeat; uploading parameters can take a while and we don't want the PLC to think we are dead
                    keyword_params["PV_SHFT"] = "0"
                    keyword_params["PV_LNK0"] = PV.create_root_fqpn("HeartbeatToPLCS")
                new_upload_fo = PARAMETER_UPLOAD_FO(PARAMETER_UPLOAD_FO.DEVICE_FO_PV if device_uploader else PARAMETER_UPLOAD_FO.GLOBAL_FO_PV, parameter, **keyword_params)
                upload_fo.set_pv_field("FLNK", new_upload_fo.fqpn())
                upload_fo = new_upload_fo

        return upload_fo


    @staticmethod
    def construct_name(input_name):
        if input_name == PARAMETER_UPLOAD_FO.INITIAL_GLOBAL_PV or input_name == PARAMETER_UPLOAD_FO.INITIAL_DEVICE_PV:
            return input_name

        return input_name.format(len(PARAMETER_UPLOAD_FO.__pvs))


    def __init__(self, name, parameter, **keyword_params):
        super(PARAMETER_UPLOAD_FO, self).__init__("", name, parameter.fqpn(), PV.DISABLE_WITH_PLC, keyword_params)
        self.set_pv_field(PV.PV_DESC, "Upload parameter values")
        PARAMETER_UPLOAD_FO.__pvs.append(self)


    def set_lnkx(self, param):
        self._set_lnkx(param.fqpn())



class nobt_helper(object):
    NOBT = "NOBT"
    SHFT = "SHFT"

    def _set_nobt(self, nobt, shift, keyword_params):
        _test_and_set_pv(keyword_params, self.NOBT, nobt)
        _test_and_set_pv(keyword_params, self.SHFT, shift)


    def _check_nobt(self):
        nobt = int(self.get_pv_field(self.NOBT))
        calc_nobt = _bits_in_type(self.plc_type())

        if nobt == -1:
            nobt = max(16, calc_nobt)
        elif calc_nobt < nobt:
            print(self._add_warning("NOBT ({}) is higher than width ({}) of PLC data type '{}'".format(nobt, calc_nobt, self.plc_type())))

        self.set_pv_field(self.NOBT, nobt)



class ENUM(BASE_TYPE, nobt_helper):
    class VLST(object):
        _st = PV.PV_PREFIX + "{}ST"
        _vl = PV.PV_PREFIX + "{}VL"

        def __init__(self, idx, prefix):
            self._idx    = idx
            self._prefix = prefix


        def idx(self):
            return self._idx


        def st(self):
            return ENUM.VLST._st.format(self._prefix)


        def vl(self):
            return ENUM.VLST._vl.format(self._prefix)



    pv_types = { MODBUS.TYPE : "mbbo",   STATUS_BLOCK.TYPE : "mbbi" }
    vlst = [ VLST( 0, "ZR"),
             VLST( 1, "ON"),
             VLST( 2, "TW"),
             VLST( 3, "TH"),
             VLST( 4, "FR"),
             VLST( 5, "FV"),
             VLST( 6, "SX"),
             VLST( 7, "SV"),
             VLST( 8, "EI"),
             VLST( 9, "NI"),
             VLST(10, "TE"),
             VLST(11, "EL"),
             VLST(12, "TV"),
             VLST(13, "TT"),
             VLST(14, "FT"),
             VLST(15, "FF") ]

    def __init__(self, source, block, name, plc_var_type, nobt, shift, keyword_params):
        for vlst in ENUM.vlst:
            if vlst.st() in keyword_params:
                _test_and_set(keyword_params, vlst.vl(), vlst.idx())
        self._set_nobt(nobt, shift, keyword_params)
        super(ENUM, self).__init__(source, block, name, plc_var_type, keyword_params)
        self._check_nobt()


    def pv_type(self):
        return ENUM.pv_types[self.block_basetype()]



class BITMASK(BASE_TYPE, nobt_helper):
    pv_types = { MODBUS.TYPE : "mbboDirect",   STATUS_BLOCK.TYPE : "mbbiDirect" }

    def __init__(self, source, block, name, plc_var_type, nobt, shift, keyword_params):
        self._set_nobt(nobt, shift, keyword_params)
        super(BITMASK, self).__init__(source, block, name, plc_var_type, keyword_params)
        self._check_nobt()


    def pv_type(self):
        return BITMASK.pv_types[self.block_basetype()]


    def dtyp(self):
        if self.from_plc():
            return super(BITMASK, self).dtyp()

        return "asynUInt32Digital"


    def inst_io(self):
        if self.from_plc():
            return super(BITMASK, self).inst_io()

        return "asynMask"


    def link_extra(self):
        if self.from_plc():
            return ""
        elif self.to_plc():
            return "0xFFFF, " + BASE_TYPE.ASYN_TIMEOUT
        else:
            raise IfDefInternalError("Unknown db type: " + self.block_type())



class STRING(BASE_TYPE):
    pv_types = { MODBUS.TYPE : "stringout",   STATUS_BLOCK.TYPE : "stringin" }

    def __init__(self, source, block, name, max_len, keyword_params):
        if max_len is not None:
            if max_len < 1:
                raise IfDefSyntaxError("String length has to be greater than 0")
            if max_len > STRING.default_len():
                raise IfDefSyntaxError("Strings cannot be longer than {} characters".format(STRING.default_len()))
        else:
            max_len = STRING.default_len()

        # Include the terminating zero byte in the dimension calculation
        self._max_dim = max_len + 1
        super(STRING, self).__init__(source, block, name, "STRING", keyword_params)


    @staticmethod
    def default_len():
        return STRING.default_dim() - 1


    @staticmethod
    def default_dim():
        return 40


    def dimension(self):
        return self._max_dim


    def _calc_width_in_bytes(self):
        return self.dimension()


    def pv_type(self):
        return self.pv_types[self.block_basetype()]


    def endian_correct_dtyp_var_type(self):
        ec_dtyp_var_type = super(STRING, self).endian_correct_dtyp_var_type()
        if self.from_plc():
            return ec_dtyp_var_type

        return "{}={}".format(ec_dtyp_var_type, self.dimension())


    def dtyp(self):
        if self.from_plc():
            return super(STRING, self).dtyp()

        return "asynOctetWrite"


    def hash_message(self):
        return "{}, {}".format(super(STRING, self).hash_message(), self.dimension())


    def link_extra(self):
        if self.from_plc():
            return " L={}".format(self.dimension())

        return super(STRING, self).link_extra()





#
# Internal functions
#

def func_param_msg(param, ptype, atype = None):
    if atype is None:
        return "'{param}' must be of type {type}!".format(param = param, type = ptype)
    return "'{param}' must be of type {type} (not it is {atype})!".format(param = param, type = ptype, atype = atype)


def _test_and_set(keyword_params, key, value):
    if key not in keyword_params:
       keyword_params[key] = str(value)


def _test_and_set_pv(keyword_params, key, value):
    _test_and_set(keyword_params, PV.to_pv_field(key), value)


def _bits_in_type(var_type):
    try:
        return bits_in_type_map[var_type]
    except KeyError:
        raise IfDefSyntaxError("Cannot calculate number of bits, unknown type: " + var_type)


def _bytes_in_type(var_type):
    assert isinstance(var_type, str)

    return _bits_in_type(var_type) // 8


"""
"""


if __name__ == "__main__":
    pass
