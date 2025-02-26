import argparse
import json
import shutil
import sys
import plcf # this is the module to create plcf object
sys.path.insert(0, 'template_factory')
from tf_ifdef import IF_DEF, FOOTER_IF_DEF # this is the module to create ifdef object
from template_factory import printers # this is the module to get the template printers
from interface_factory import IFA # this is the module to create SCL code
import helpers
import os
import hashlib
import zlib
import datetime

#############Classess
class Device:
    def __init__(self, 
                name = "", 
                description = "", 
                deviceType = "", 
                propertiesDict = None,
                controlledBy = None, 
                ):
        self._name = name
        self._description = description
        self._deviceType = deviceType
        self._propertiesDict = propertiesDict
        self._controlledBy = controlledBy
    
    def name(self):
        return self._name
    
    def description(self):
        return self._description
    
    def deviceType(self):
        return self._deviceType
    
    def propertiesDict(self):
        if self._propertiesDict:
            return self._propertiesDict
        else:
            return {}
    
    def controlledBy(self):
       return self._controlledBy

    def backtrack(self,prop, exraise=None):
        if self._controlledBy:
            return self._controlledBy.propertiesDict().get(prop)
        else:
            return self._propertiesDict.get(prop)

class Hasher(object):
    def __init__(self, hash_base = None):
        self._hashobj = hashlib.sha256(hash_base.encode())

    def update(self, string):
        try:
            self._hashobj.update(string.encode())
        except UnicodeDecodeError:
            # Happens on Py2 with strings containing unicode characters
            self._hashobj.update(string)


    def _crc32(self):
        return zlib.crc32(self._hashobj.hexdigest().encode())


    def getHash(self):
        return self._hashobj.hexdigest()


    def getCRC32(self):
        crc32 = self._crc32()
        # Python3 returns an UNSIGNED integer. But we need a signed integer
        if crc32 > 0x7FFFFFFF:
            return str(crc32 - 0x100000000)

        return str(crc32)

    def processHash(self, partlist):
        tag = '#HASH'
        return list(map(lambda s: s.replace(tag, self.getCRC32()), partlist))

#Get PLCF
def getPLCF(device):
    #global plcfs
    plcfs = dict()
    device_name = device.name()
    try:
        return plcfs[device_name]
    except KeyError:
        cplcf = plcf.PLCF(device)
        plcfs[device_name] = cplcf
        return cplcf

# Updated to load project configuration from a JSON file and handle local device definitions
def load_project_config(json_file):
    with open(json_file, 'r') as file:
        return json.load(file)

#Download template files 
def load_device_definitions(devices_dir, template_names, output_path):
    """Load templates from a directory based on provided template names and copy them to a specific folder."""
    
    # Verificar se o diretório de saída existe, caso contrário, criar
    os.makedirs(output_path, exist_ok=True)
    
    for filename in os.listdir(devices_dir):
        if filename.endswith('.json'):
            # Verificar se o nome do arquivo está na lista de template_names
            if filename in template_names:
                file_path = os.path.join(devices_dir, filename)
                
                # Caminho de destino para copiar o arquivo
                target_path = os.path.join(output_path, filename)
                    
                # Copiar o arquivo para o diretório de saída
                shutil.copy(file_path, target_path)
                    
    return True

#Load/read template files
def load_template(template_path):
    """Load a template file."""
    with open(template_path, 'r') as file:
        return file.read()

#load Devices
def load_devices(project_config,plc_device):
    """Get devices defined in the project configuration and return devices List."""
    devices = project_config.get("PROJ", {}).get("CTRL", {}).get("DEVICE", [])
    dev_list = []
    for device in devices:
        new_device = Device(
            name = device.get("essname", "Unknown"),
            description=device.get("Desc", "None"),
            deviceType=os.path.splitext(device.get("template_name", "Not specified"))[0],
            propertiesDict={'EGU': 'degC'},
            controlledBy=plc_device,
        )
        dev_list.append(new_device)
    
    return dev_list

#Print Devices configured in the Project
def print_project_devices(project_config):
    """Print all devices defined in the project configuration and return unique device names."""
    devices = project_config.get("PROJ", {}).get("CTRL", {}).get("DEVICE", [])
    device_names = []
    template_names = []
    print("Devices in project configuration:")
    for device in devices:
        essname = device.get("essname", "Unknown")
        template_path = device.get("template_path", "Not specified")
        template_name = device.get("template_name", "Not specified")
        print(f"Device: {essname}\nTemplate Path: {template_path}\nTemplate Name: {template_name}")

        if template_name not in template_names:
            template_names.append(template_name)
        device_names.append(essname)
    #print(template_names)
    return device_names, template_names

#Load PLC propoerties from Project.json file
def load_plc_properties(json_input):
    if isinstance(json_input, str):
        with open(json_input, 'r', encoding='utf-8') as file:
            data = json.load(file)
    else:
        data = json_input
    prj_data = data.get("PROJ", {})
    hw_data = data.get("PROJ", {}).get("HW", {})
    
    properties = {
        "EPICSModule": [],
        "EPICSSnippet": [],
        "PLC-EPICS-COMMS:Endianness": hw_data.get("PLC-EPICS-COMMS:Endianness", "BigEndian"),
        "EPICSToPLCDataBlockStartOffset": hw_data.get("EPICSToPLCDataBlockStartOffset", "0"),
        "PLCToEPICSDataBlockStartOffset": hw_data.get("PLCToEPICSDataBlockStartOffset", "0"),
        "PLC-EPICS-COMMS: MBConnectionID": hw_data.get("PLC-EPICS-COMMS: MBConnectionID", "255"),
        "PLC-EPICS-COMMS: MBPort": hw_data.get("PLC-EPICS-COMMS: MBPort", "502"),
        "PLC-EPICS-COMMS: S7ConnectionID": hw_data.get("PLC-EPICS-COMMS: S7ConnectionID", "256"),
        "PLC-DIAG:Max-Local-Modules": hw_data.get("PLC-DIAG:Max-Local-Modules", "60"),
        "PLC-DIAG:Max-Modules-In-IO-Device": hw_data.get("PLC-DIAG:Max-Modules-In-IO-Device", "60"),
        "PLC-EPICS-COMMS: PLCPulse": hw_data.get("PLC-EPICS-COMMS: PLCPulse", "Pulse_200ms"),
        "PLC-EPICS-COMMS: InterfaceID": hw_data.get("PLC-EPICS-COMMS: InterfaceID", "64"),
        "PLC-EPICS-COMMS: DiagPort": hw_data.get("PLC-EPICS-COMMS: DiagPort", "2001"),
        "PLC-EPICS-COMMS: S7Port": hw_data.get("PLC-EPICS-COMMS: S7Port", "2000"),
        "PLC-DIAG:Max-IO-Devices": hw_data.get("PLC-DIAG:Max-IO-Devices", "20"),
        "PLC-EPICS-COMMS: DiagConnectionID": hw_data.get("PLC-EPICS-COMMS: DiagConnectionID", "254"),
        "Hostname": hw_data.get("ipaddr", "tbd-tbdmon-plc-001.tn.esss.lu.se"),
        "PLC-EPICS-COMMS: GatewayDatablock": None,
    }
    additional_prop = {
        "type": hw_data.get("type", "Siemens"),
        "comm_protocol":hw_data.get("comm_protocol", "TCP/IP-Modbus"),
        "essname": hw_data.get("essname", "TBD:Ctrl-PLC-001"),
        "TIA_v": hw_data.get("tia_portal_version", "v17"),
        "diagnostic":hw_data.get("diagnostic", "False"),
        "template_path": hw_data.get("template_path", ""),
        "template_name": hw_data.get("template_name", ""),
        "ARCH_CLTR": prj_data.get("ARCHIVE",""),
    }
    
    return properties, additional_prop

def get_pvs(devfiles_dir, dev_type, ifdefobj, block, type):
    #print(dev_type)
    dev_file = os.path.join(devfiles_dir, f"{dev_type}.json")
    if isinstance(dev_file, str):
        with open(dev_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
    else:
        data = dev_file
    
    devs_data = data.get("DEV", {}).get(block, {}).get(type, {})
    
    for dev_data in devs_data:
        if type == "analog":
            name =          dev_data.get("property", "")
            var_type =      dev_data.get("plcvartype", "INT")
            desc =          dev_data.get("DESC", "")
            egu =           dev_data.get("EGU", "")
            set_asField =   dev_data.get("set_as_field", "None")
            kwargs={
                "ARCH_POL": dev_data.get("aa_policy", ""),
                "PV_HIHI": dev_data.get("HIHI", ""),
                "PV_HHSV": dev_data.get("HHSV", ""),
                "PV_HIGH": dev_data.get("HIGH", ""),
                "PV_HSV":  dev_data.get("HSV", ""),
                "PV_LOW":  dev_data.get("LOW", ""),
                "PV_LSV":  dev_data.get("LSV", ""),
                "PV_LOLO": dev_data.get("LOLO", ""),
            }
            filtered_kwargs = {k: v for k, v in kwargs.items() if v}
            ifdefobj.add_analog(name, var_type, PV_DESC=desc, PV_EGU=egu, **filtered_kwargs)
        elif type == "digital":
            name        =   dev_data.get("property", "")
            kwargs={
                "var_type"      :   dev_data.get("plcvartype", "BOOL"),
                "set_asField"   :   dev_data.get("set_as_field", "None"),
                "PV_DESC"       :   dev_data.get("DESC", ""),
                "ARCH_POL"      :   dev_data.get("aa_policy", ""),
                "PV_ONAM"       :   dev_data.get("ONAM", ""),
                "PV_ZNAM"       :   dev_data.get("ZNAM", ""),
                "PV_ZSV"        :   dev_data.get("ZSV", ""),
                "PV_OSV"        :   dev_data.get("OSV", ""),
                "PV_COSV"       :   dev_data.get("COSV", ""),
            }
            filtered_kwargs = {k: v for k, v in kwargs.items() if v}
            ifdefobj.add_digital(name, **filtered_kwargs)
        elif type == "time":
            name =          dev_data.get("property", "")
            kwargs={
                "var_type"      :   dev_data.get("plcvartype", "TIME"),
                "set_asField"   :   dev_data.get("set_as_field", "None"),
                "PV_DESC"       :   dev_data.get("DESC", ""),
                "ARCH_POL"      :   dev_data.get("aa_policy", ""),
                "PV_EGU"        :   dev_data.get("EGU", "ms"),
                }
            filtered_kwargs = {k: v for k, v in kwargs.items() if v}
            ifdefobj.add_time(name, **filtered_kwargs )
        elif type == "enum":
            name =          dev_data.get("property", "")
            var_type =      dev_data.get("plcvartype", "")
            desc =          dev_data.get("DESC", "")
            set_asField =   dev_data.get("set_as_field","None")
            egu =           dev_data.get("EGU", "")
            kwargs={
                "ARCH_POL": dev_data.get("aa_policy", ""),
            }
            filtered_kwargs = {k: v for k, v in kwargs.items() if v}
            ifdefobj.add_enum(name, var_type, PV_DESC=desc, PV_EGU=egu, **kwargs)
        elif type == "bitmask":
            name =          dev_data.get("property", "")
            var_type =      dev_data.get("plcvartype", "INT")
            desc =          dev_data.get("DESC", "")
            set_asField =   dev_data.get("set_as_field","None")
            kwargs={
                "ARCH_POL": dev_data.get("aa_policy", ""),
            }
            filtered_kwargs = {k: v for k, v in kwargs.items() if v}
            ifdefobj.add_bitmask(name, var_type, PV_DESC=desc, **kwargs)
        elif type == "string":
            name =          dev_data.get("property", "")
            var_type =      dev_data.get("plcvartype", "STRING")
            desc =          dev_data.get("DESC", "")
            set_asField =   dev_data.get("set_as_field","None")
            kwargs={
                "ARCH_POL": dev_data.get("aa_policy", ""),
            }
            filtered_kwargs = {k: v for k, v in kwargs.items() if v}
            ifdefobj.add_string(name, var_type, PV_DESC=desc, **kwargs)
    return ifdefobj

#Process local devices to generate Templates
def process_local_devices(ioc_output_dir, plc_output_dir, devfiles_dir, project_config):
    """Process project devices and configuration files and generate output files for IOC and PLC."""
    
    ######## Time Stamp
    timestamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
    
    ######## Project File
    json_file_path = project_config
    
    ######## Load PLC Device
    plc_properties, adt_prop = load_plc_properties(json_file_path)
    
    ######## Get aditional data from PLC device
    plc_name = adt_prop.get("essname")
    TIA_v = adt_prop.get("TIA_v")
    arch_cltr = adt_prop.get("ARCH_CLTR")
    
    ######## Create PLC Device
    plc_device = Device(
        name=plc_name,
        description='Desc',
        deviceType='PLC',
        propertiesDict=plc_properties,
    )

    ######### create the plcf objects from a Device object
    device_list = load_devices(project_config,plc_device)

    ######### create the hash object
    hash_string_base = plc_device.name()
    hash_obj = Hasher(hash_string_base)

    ######## keywords to pass
    modulename = (helpers.sanitizeFilename(plc_device.name().lower())).replace('-', '_')
    snippet = modulename
    ifdef_params = {'PLC_TYPE': 'SIEMENS', 
                    'PLCF_STATUS': True, 
                    'COMMIT_ID': 'commitID', 
                    'ROOT_INSTALLATION_SLOT': plc_device.name(), 
                    'EXPERIMENTAL': False, 
                    'PLC_READONLY': False, 
                    'PLC_HOSTNAME': None , 
                    'TIMESTAMP': timestamp,
                    'BRANCH': 'branch',
                    'CMD_LINE': '<cmd_line>',
                   #'MODVERSION': '', define this to override $(PLCIOCVERSION)
                    'DEF_MODVERSION': timestamp,
                    'MODULE_NAME': modulename,
                    'SNIPPET': snippet,
                    }
    
    ######### create the plcf objects from a Device object 
    plc_plcf = plcf.PLCF(plc_device)
    
    ######### Template to be created: IFA, EPICS-DB and IOCSH are the three templates
    file_extension = {'IFA': '.ifa', 'EPICS-DB': '.db', 'IOCSH': '.iocsh','ARCHIVE': '.archive'}

    ifdef_list = []
    ifdef_dict = {}
    plcf_device_list = []

    ######### Read and interact on Template definition files to create the body object
    for dev in device_list:
        plcfobj = plcf.PLCF(dev)
        plcf_device_list.append(plcfobj)
        with IF_DEF(PLCF = plcfobj, **ifdef_params) as ifdefobj:
            
            categories = ["Status", "Command", "Parameter"]
            pv_types = ["analog", "digital", "time", "enum", "bitmask", "string"]

            for category in categories:
                if category == "Status":
                    ####### status block
                    ifdefobj.define_status_block()
                elif category == "Command":
                    ####### command block
                    ifdefobj.define_command_block()
                elif category == "Parameter":
                    ####### parameter block
                    ifdefobj.define_parameter_block()
                for pv_type in pv_types:
                    ifdefobj = get_pvs(devfiles_dir, dev.deviceType(), ifdefobj, category, pv_type)
            
        ####### update hash
        ifdefobj.calculate_hash(hash_obj) 
        
        ####### filling ifdef object list and dictionary
        ifdef_list.append(ifdefobj)
        ifdef_dict.update({plcfobj.getDevice().name(): ifdefobj})


    templates = ['IFA', 'IOCSH','EPICS-DB', 'ARCHIVE']
    for template in templates:
        ######### select new dir to save files
        if template == 'IFA':
            output_dir = plc_output_dir
        else:
            output_dir = ioc_output_dir
        ######### printing message
        print('Processing template {} .....'.format(template))

        ######### create the outpufile
        fname = modulename + '-' + timestamp + file_extension.get(template)
        output_file = os.path.join(output_dir, fname)
        print(output_file)

        ######### import the template and add the TEMPLATE keyword to the Device _properties dictionary
        printer = printers.get_printer(template)
        plc_plcf.register_template(template)

        for plcfobj in plcf_device_list:
            plcfobj.register_template(template)

        header_template = []
        body_template = []
        footer_template = []
        
        ######### create the template header, ROOT_DEVICE is the PLC Device object , PLCF is the PLC plcf object 
        printer.header(None, header_template, ROOT_DEVICE = plc_device, PLCF = plc_plcf, OUTPUT_DIR = output_dir, HELPERS = helpers, **ifdef_params)

        ######### process the header of the template
        header_template = plc_plcf.process(header_template)

        ################# create body of the template looping over devices
        for plcfobj in plcf_device_list:
            printer.body(ifdef_dict.get(plcfobj.getDevice().name()), body_template, DEVICE = plcfobj.getDevice(), PLCF = plcfobj, ARCH_CLTR = arch_cltr)

        ################# create footer of the template

        footer_ifdef = FOOTER_IF_DEF(plc_device, ifdef_list, PLCF = plc_plcf, **ifdef_params)
        printer.footer(footer_ifdef, footer_template, PLCF = plc_plcf)
        footer_template = plc_plcf.process(footer_template)

        ################ replace the calculated hash number in the template
        header_template = hash_obj.processHash(header_template)
        footer_template = hash_obj.processHash(footer_template)

        ############### create output template
        output_template = header_template + body_template + footer_template
        (output_template, _) = plcf.PLCF.evalCounters(output_template)
    
        ############## write the output template to file
        with open(output_file, 'w') as f:
            for line in output_template:
                line = line.rstrip()
                if not line.startswith("#COUNTER") \
                    and not line.startswith("#FILENAME") \
                    and not line.startswith("#EOL"):
                    print(line, file = f)

        print("Output template {} file {} written".format(template, output_file))
        print("Hash sum:", hash)
        #print(output_file)
        generate_output_files(template, output_dir, output_file, ifdef_params, TIA_v, timestamp)
    
#### to be done
def generate_output_files(template, output_dir, output_file, ifdef_params, TIA_v, timestamp):
    """Generate configuration files based on templates from a directory."""
        ############# if the template is a IFA it will create the scl code
    if template == 'IFA':
        IFA.produce(output_dir, output_file, TIAVersion = TIA_v, nodiag = True, onlydiag = False, commstest = False, verify = None, readonly = False, commit_id = ifdef_params['COMMIT_ID'], timestamp = timestamp)


################# MAIN   ##########################

def main():
    parser = argparse.ArgumentParser(description="PLCIntegrator Tool")
    parser.add_argument("--config", help="JSON configuration file for the project", required=True)
    parser.add_argument("--devices", help="Directory with JSON files for device definitions", required=True)

    args = parser.parse_args()

    # Define output directories# Get the base name of the configuration file to create the output directory
    output_dir = os.path.splitext(os.path.basename(args.config))[0]
    output_path = os.path.join(os.path.dirname(__file__), output_dir, 'template_files')
    ioc_output_dir = os.path.join(os.path.dirname(__file__), output_dir, 'ioc')
    plc_output_dir = os.path.join(os.path.dirname(__file__), output_dir, 'plc')
    
    #Create diretories
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(ioc_output_dir, exist_ok=True)
    os.makedirs(plc_output_dir, exist_ok=True)

    # Load project configuration
    project_config = load_project_config(args.config)

    # Print devices in project configuration
    devices, template_names=print_project_devices(project_config)

    # Load local device definitions
    load_device_definitions(args.devices, template_names, output_path)

    # Process and generate output for IOC and PLC configurations
    process_local_devices(ioc_output_dir, plc_output_dir, output_path, project_config)


if __name__ == "__main__":
    main()
