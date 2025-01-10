from __future__ import print_function
from __future__ import absolute_import

class IFA(object):
    # Length: 2 words
    EPICSTOPLC_HASH       = 0
    # Length: 1 word
    EPICSTOPLC_HEARTBEAT  = 2
    # Length: 2 words
    EPICSTOPLC_READ_HASH  = 3
    # Length: 1 word
    EPICSTOPLC_UPLOADSTAT = 5
    # Length: 1 word
    EPICSTOPLC_READ_PAYLOAD_SIZE = 6

    # Length: 2 words
    PLCTOEPICS_HASH       = 0
    # Length: 1 word
    PLCTOEPICS_HEARTBEAT  = 2
    # Length: 1 word
    PLCTOEPICS_UPLOADSTAT = 3

    mandatory_variable_properties = dict(VARIABLE    = str,
                                         EPICS       = str,
                                         TYPE        = str,
                                         ARRAY_INDEX = int,
                                         BIT_NUMBER  = int)

    valid_variable_entries = set([ 'EGU', 'NO_GATEWAY' ])
    valid_variable_entries.update(set(mandatory_variable_properties.keys()))

    mandatory_device_properties = dict(DEVICE                    = str,
                                       DEVICE_TYPE               = str,
                                       DATABLOCK                 = str,
                                       EPICSTOPLCLENGTH          = int,
                                       EPICSTOPLCDATABLOCKOFFSET = int,
                                       PLCTOEPICSLENGTH          = int,
                                       PLCTOEPICSDATABLOCKOFFSET = int)

#   EPICSTOPLCPARAMETERSSTART is deprecated and ignored but kept for compatibility
    valid_device_entries   = set([ 'BLOCK', 'DEFINE_ARRAY', 'END_ARRAY', 'EPICSTOPLCPARAMETERSSTART' ])
    valid_device_entries.update(set(mandatory_device_properties.keys()))
    valid_device_entries.update(valid_variable_entries)

    valid_array_entries = set([ 'NO_GATEWAY', 'START_IDX' ])
    valid_device_entries.update(valid_array_entries)

    mandatory_ifa_properties = dict(HASH                     = str,
                                    MAX_IO_DEVICES           = int,
                                    MAX_LOCAL_MODULES        = int,
                                    MAX_MODULES_IN_IO_DEVICE = int,
                                    PLC                      = str,
                                    PLC_TYPE                 = str,
                                    INTERFACE_ID             = str,
                                    S7_CONNECTION_ID         = str,
                                    MODBUS_CONNECTION_ID     = str,
                                    DIAG_CONNECTION_ID       = str,
                                    S7_PORT                  = int,
                                    MODBUS_PORT              = int,
                                    DIAG_PORT                = int,
                                    TOTALEPICSTOPLCLENGTH    = int,
                                    TOTALPLCTOEPICSLENGTH    = int,
                                    PLC_PULSE                = str,
                                    GATEWAY_DATABLOCK        = str)

    valid_line_types = set(mandatory_ifa_properties.keys())
    valid_line_types.update(valid_device_entries)
    valid_line_types.update(valid_array_entries)

    valid_var_types = set([ 'BOOL', 'BYTE', 'CHAR', 'WORD', 'DWORD', 'INT', 'DINT', 'REAL', 'SSTIME', 'TIME', 'LTIME', 'DATE', 'TIME_OF_DAY', 'STRING',
                            'USINT', 'SINT', 'UINT', 'UDINT' ])


    class Exception(Exception):
        pass



    class Warning(Exception):
        pass



    class FatalException(Exception):
        pass



    class Device(object):
        class DeviceItemIterator(object):
            def __init__(self, iters):
                self.__iters = iters


            def next(self):
                return self.__next__()


            def __next__(self):
                try:
                    return next(self.__iters[0])
                except StopIteration:
                    self.__iters.pop(0)
                    return self.next()
                except IndexError:
                    raise StopIteration



        def __init__(self, name):
            self.comments   = []
            self.properties = { "DEVICE": name }

            self.status_items    = []
            self.command_items   = []
            self.parameter_items = []
            self.general_input_items = []


        def __iter__(self):
            return IFA.Device.DeviceItemIterator([ iter(self.status_items), iter(self.command_items), iter(self.parameter_items), iter(self.general_input_items) ])


        def append(self, line):
            self.comments.append(line)


        def extend(self, area):
            self.comments.extend(area)


        def check(self):
            if not set(IFA.mandatory_device_properties.keys()) <= set(self.properties.keys()):
                raise IFA.FatalException("Missing DEVICE properties", set(IFA.mandatory_device_properties.keys()) - set(self.properties.keys()))

            for (keyword, value) in self.properties.items():
                try:
                    IFA.mandatory_device_properties[keyword](value)
                except (ValueError, TypeError):
                    raise IFA.FatalException("Device keyword type mismatch: {keyword} should be {type}".format(keyword = keyword, type = IFA.mandatory_device_properties[keyword].__name__))
                except KeyError:
                    pass



    class DeviceItem(object):
        def __init__(self):
            self.comments = []


        def append(self, line):
            self.comments.append(line)


        def extend(self, area):
            self.comments.extend(area)


        def is_block(self):
            return False


        def is_variable(self):
            return False


        def is_wrapper_array(self):
            return False


        def check(self):
            pass



    class Block(DeviceItem):
        def __init__(self, block):
            super(IFA.Block, self).__init__()
            self.__block = block[0]


        def __repr__(self):
            return "BLOCK " + self.__block


        def name(self):
            return self.__block


        def is_block(self):
            return True


        def is_input(self):
            """
            If it contains inputs to the PLC
            """
            return self.__block != 'S'


        def is_output(self):
            """
            If it contains outputs from the PLC
            """
            return self.__block == 'S'


        def is_status(self):
            return self.__block == 'S'


        def is_command(self):
            return self.__block == 'C'


        def is_parameter(self):
            return self.__block == 'P'


        def is_general_input(self):
            return self.__block == 'G'



    class Variable(Block):
        def __init__(self, name, block):
            super(IFA.Variable, self).__init__(block)
            self.properties  = { "VARIABLE": name }
            self.__dimension = 1


        def __repr__(self):
            return repr(self.properties)


        def name(self):
            return self.properties["VARIABLE"]


        def is_block(self):
            return False


        def is_variable(self):
            return True


        def dimension(self):
            return self.__dimension


        def check(self):
            if not set(IFA.mandatory_variable_properties.keys()) <= set(self.properties.keys()):
                raise IFA.FatalException("Missing VARIABLE properties", set(IFA.mandatory_variable_properties.keys()) - set(self.properties.keys()))

            type_split = self.properties["TYPE"].split('[')
            if len(type_split) > 1:
                self.properties["TYPE"] = type_split[0]
                self.__dimension = int(type_split[1][:-1])
                if self.__dimension <= 1:
                    raise IFA.FatalException("Array dimension must be greater than 1")

            for (keyword, value) in self.properties.items():
                try:
                    IFA.mandatory_variable_properties[keyword](value)
                except (ValueError, TypeError):
                    raise IFA.FatalException("Variable keyword type mismatch: {keyword} should be {type}".format(keyword = keyword, type = IFA.mandatory_variable_properties[keyword].__name__))
                except KeyError:
                    pass

            if self.properties["TYPE"] not in IFA.valid_var_types:
                raise IFA.FatalException("Unsupported PLC type", self.properties["TYPE"])



    class WrapperArray(DeviceItem):
        def __init__(self, array_name, start):
            super(IFA.WrapperArray, self).__init__()
            self.properties   = dict(START_IDX = 1)
            self.__array_name = array_name
            self.__start      = start


        def __repr__(self):
            return ("BEGIN " if self.__start else "END ") + self.__array_name


        def is_wrapper_array(self):
            return True


        def start_idx(self):
            return int(self.properties["START_IDX"])


        def is_start(self):
            return self.__start


        def name(self):
            return self.__array_name



    class WrapperArrayStart(WrapperArray):
        def __init__(self, array_name):
            super(IFA.WrapperArrayStart, self).__init__(array_name, True)



    class WrapperArrayEnd(WrapperArray):
        def __init__(self, array_name):
            super(IFA.WrapperArrayEnd, self).__init__(array_name, False)



    def __init__(self, IfaPath):
        self.properties               = dict()
        self.IfaPath                  = IfaPath
        self.Devices                  = []

        self.PreParse()
        self.Check()


    def PreParse(self):
        print("""
PLCFactory file location: {}
Pre-parsing .ifa file...""".format(self.IfaPath))

        # Pre process IFA to have Status, Command, Parameter order
        with open(self.IfaPath) as f:
            linetype = None

            Area     = None
            Block    = None

            device   = None
            item     = None

            for line in f:
                line = line.strip()

                if linetype is None:
                    if line.startswith("//"):
                        if item   is not None:
                            item.append(line)
                        elif device is not None:
                            device.append(line)
                    else:
                        if line not in IFA.valid_line_types:
                            raise IFA.FatalException("Unknown IFA keyword", line)

                        linetype = line
                    continue

                try:
                    if linetype in IFA.mandatory_ifa_properties:
                        try:
                            if line == "" or line == "None":
                                setattr(self, linetype, None)
                            else:
                                setattr(self, linetype, IFA.mandatory_ifa_properties[linetype](line))
                        except (ValueError, TypeError):
                            raise IFA.FatalException("IFA keyword type mismatch: {keyword} should be {type}".format(keyword = linetype, type = IFA.mandatory_ifa_properties[linetype].__name__))

                        self.properties[linetype] = line
                        continue

                    elif linetype == "DEVICE":
                        Area   = None
                        item   = None
                        device = IFA.Device(line)
                        self.Devices.append(device)
                        continue

                    if device and linetype not in IFA.valid_device_entries:
                        raise IFA.FatalException("Unknown DEVICE keyword", linetype)

                    if linetype == "BLOCK":
                        if line == "STATUS":
                            Area = device.status_items
                        elif line == "COMMAND":
                            Area = device.command_items
                        elif line == "PARAMETER":
                            Area = device.parameter_items
                        elif line == "GENERAL_INPUT":
                            Area = device.general_input_items
                        else:
                            raise IFA.FatalException("Unknown BLOCK type", line)
                        Area.append(IFA.Block(line))
                        Block = line
                        item  = None
                        continue

                    elif linetype == "DEFINE_ARRAY":
                        item = IFA.WrapperArrayStart(line)
                        Area.append(item)
                        continue

                    elif linetype == "END_ARRAY":
                        Area.append(IFA.WrapperArrayEnd(line))
                        continue

                    elif linetype == "VARIABLE":
                        item = IFA.Variable(line, Block)
                        Area.append(item)
                        continue

                    if item:
                        if isinstance(item, IFA.WrapperArrayStart):
                            if linetype not in IFA.valid_array_entries:
                                raise IFA.FatalException("Unknown DEFINE_ARRAY keyword", linetype)
                        elif linetype not in IFA.valid_variable_entries:
                            raise IFA.FatalException("Unknown VARIABLE keyword", linetype)

                    if item is not None:
                        item.properties[linetype] = line
                    elif device is not None:
                        device.properties[linetype] = line
                    else:
                        raise IFA.FatalException("Neither variable nor device")

                finally:
                    linetype = None

            if linetype is not None:
                raise IFA.FatalException("""IFA is not well formed. Last lines:
{type}
{line}
""".format(type = linetype,
           line = line))

        print("Total", str(len(self.Devices)), "device(s) pre-processed.")


    def Check(self):
        if not set(IFA.mandatory_ifa_properties.keys()) <= set(self.properties.keys()):
            raise IFA.FatalException("Missing IFA properties", set(IFA.mandatory_ifa_properties.keys()) - set(self.properties.keys()))

        if self.MAX_IO_DEVICES <= 0:
            self.MAX_IO_DEVICES = 1

        if self.MAX_LOCAL_MODULES <= 0:
            self.MAX_LOCAL_MODULES = 1

        if self.MAX_MODULES_IN_IO_DEVICE <= 0:
            self.MAX_MODULES_IN_IO_DEVICE = 1

        vars_per_devicetype = dict()
        devicetypes_to_modify = set()
        for device in self.Devices:
            device.check()

            for item in device:
                item.check()

            # Now check that every device in a device type has the same variable name
            # might not be the case if CCDB properties were used to customize the variable names

            # Store the different device types
            devtype = device.properties["DEVICE_TYPE"]
            if devtype not in vars_per_devicetype:
                vars_per_devicetype[devtype] = [item.name() for item in device]
                continue

            # We already know it has to be modified
            if devtype in devicetypes_to_modify:
                continue

            # Gather all the variable names
            dvars = [item.name() for item in device]

            # Check if this device type has the same variables as the first one
            if dvars != vars_per_devicetype[devtype]:
                devicetypes_to_modify.add(devtype)

        # "Personalize" the device type name if using custom variable names
        for device in self.Devices:
            devtype = device.properties["DEVICE_TYPE"]
            if devtype in devicetypes_to_modify:
                device.properties["DEVICE_TYPE"] = "{}_as_{}".format(devtype, device.properties["DEVICE"])

        if not self.Devices:
            print("""
Warning:
After pre-processing the .IFA file there were no DEVICES inside!
""")


    @staticmethod
    def consolidate_tia_version(tia_version):
        from .InterfaceFactorySiemens import consolidate_tia_version as ctv
        return ctv(tia_version)


    @staticmethod
    def produce(OutputDir, IfaPath, **kwargs):
        ifa = IFA(IfaPath)

        factory = None
        if ifa.PLC_TYPE == "SIEMENS":
            from .InterfaceFactorySiemens import produce
            factory = produce
        elif ifa.PLC_TYPE == "BECKHOFF":
            from .InterfaceFactoryBeckhoff import produce
            factory = produce
        else:
            raise IFA.FatalException("Unsupported PLC_TYPE", ifa.PLC_TYPE)

        return factory(OutputDir, ifa, **kwargs)
