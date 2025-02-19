import argparse
import helpers
import json
import os
import shutil
from interface_factory import InterfaceFactorySiemens
import zlib
import sys
import plcf # this is the module to create plcf object
sys.path.insert(0, 'template_factory')
from tf_ifdef import IF_DEF, FOOTER_IF_DEF # this is the module to create ifdef object
import tf
from interface_factory import IFA # this is the module to create SCL code
import helpers


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

##########Functions
#
def findTag(lines, tag):
    tagPos = -1

    if not lines:
        return tagPos

    assert isinstance(lines, list)
    assert isinstance(tag,   str)

    for i in range(len(lines)):
        if lines[i].startswith(tag):
            tagPos = i
            break

    return tagPos

#Create new file
def createFilename(cplcf, header):
    assert isinstance(header, list)

    tag    = "#FILENAME"
    tagPos = findTag(header, tag)

    # default filename is chosen when no custom filename is specified
    if tagPos == -1:
        header = [ '{} [PLCF#RAW_INSTALLATION_SLOT]_[PLCF#DEVICE_TYPE]-[PLCF#TEMPLATE]_[PLCF#TIMESTAMP].scl'.format(tag) ]
        tagPos = 0

    filename = header[tagPos]

    # remove tag and strip surrounding whitespace
    filename = filename[len(tag):].strip()
    filename = cplcf.process(filename)

    return helpers.sanitizeFilename(filename)

#Create the header
def processHash(header, hashobj):
    assert isinstance(header, list)

    tag     = "#HASH"
    pos     = -1

    for i in range(len(header)):
        if tag in header[i]:
            pos = i
            hashSum     = str(hashobj)
            line        = header[pos]
            tagPos      = line.find(tag)
            line        = line[:tagPos] + hashSum + line[tagPos + len(tag):]
            header[pos] = line

    return header

#Get EOL
def getEOL(header):
    assert isinstance(header, list)

    tag    = "#EOL"
    tagPos = findTag(header, tag)

    if tagPos == -1:
        return "\n"

    # this really is a quick and dirty hack
    # should be replaced by something like
    # #EOL CR LF
    return header[tagPos][len(tag):].strip().replace('\\n', '\n').replace('\\r', '\r').strip('"').strip("'")

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
    print(template_names)
    return device_names, template_names

#Calculate CRC32 for a file
def crc32_file(filepath):
    """Calculate the CRC32 for a unique file."""
    crc32 = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):  # Read in blocks of 4KB
            crc32 = zlib.crc32(chunk, crc32)
    return crc32

#calculate CRC32 for an entyre folder
def calculate_folder_crc32(folder_path):
    """Calculete the CRC32 for all Device templates in the folder"""
    combined_crc = 0
    
    # Read al files in folder
    for filename in sorted(os.listdir(folder_path)):  # Make some order to keep the consistence 
        if filename.endswith(".json"):  # filter to use only .json files
            file_path = os.path.join(folder_path, filename)
            file_crc = crc32_file(file_path)
            combined_crc = zlib.crc32(file_crc.to_bytes(4, 'big'), combined_crc)  # Update CRC geral

    # Return a number signed to be compatible
    return combined_crc if combined_crc <= 0x7FFFFFFF else combined_crc - 0x100000000

#Load PLC propoerties from Project.json file
def load_plc_properties(json_input):
    if isinstance(json_input, str):
        with open(json_input, 'r', encoding='utf-8') as file:
            data = json.load(file)
    else:
        data = json_input
    
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
    
    return properties, hw_data.get("essname", "TBD:Ctrl-PLC-001")

def get_pvs(devfiles_dir, dev_type, ifdefobj, block, type):
    print(dev_type)
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
            arch =          dev_data.get("archiver", "")        #check how to create the archiver info tag?
            aa_pol =        dev_data.get("aa_policy", "")       
            hihi =          dev_data.get("HIHI", "")
            hhsv =          dev_data.get("HHSV", "")
            high =          dev_data.get("HIGH", "")
            hsv =           dev_data.get("HSV", "")
            low =           dev_data.get("LOW", "")
            lsv =           dev_data.get("LSV", "")
            lolo =          dev_data.get("LOLO", "")
            ifdefobj.add_analog(name, var_type, PV_DESC=desc, PV_EGU=egu, PV_HIHI = hihi, PV_HHSV = hhsv, PV_HIGH = high, PV_HSV = hsv, PV_LOW = low, PV_LSV = lsv, PV_LOLO = lolo)
        elif type == "digital":
            name =          dev_data.get("property", "")
            var_type =      dev_data.get("plcvartype", "INT")
            desc =          dev_data.get("DESC", "")
            set_asField =   dev_data.get("set_as_field", "None")
            arch =          dev_data.get("archiver", "")        #check how to create the archiver info tag?
            aa_pol =        dev_data.get("aa_policy", "")
            onam =          dev_data.get("ONAM", "")
            znam =          dev_data.get("ZNAM", "")
            zsv =           dev_data.get("ZSV", "")
            osv =           dev_data.get("OSV", "")
            cosv =          dev_data.get("COSV", "")
            ifdefobj.add_digital(name, PV_DESC=desc, PV_ONAM=onam, PV_ZNAM=znam, PV_ZSV=zsv, PV_OSV=osv, PV_COSV=cosv)
        #elif type == "time":
        #    ifdefobj.add_time(name, PV_DESC=desc, PV_EGU=egu, PV_HIHI = hihi, PV_HHSV = hhsv, PV_HIGH = high, PV_HSV = hsv, PV_LOW = low, PV_LSV = lsv, PV_LOLO = lolo)
        #elif type == "enum":
        #    ifdefobj.add_enum(name, PV_DESC=desc, PV_EGU=egu, PV_HIHI = hihi, PV_HHSV = hhsv, PV_HIGH = high, PV_HSV = hsv, PV_LOW = low, PV_LSV = lsv, PV_LOLO = lolo)
        #elif type == "bitmask":
        #    ifdefobj.add_bitmask(name, PV_DESC=desc, PV_EGU=egu, PV_HIHI = hihi, PV_HHSV = hhsv, PV_HIGH = high, PV_HSV = hsv, PV_LOW = low, PV_LSV = lsv, PV_LOLO = lolo)
        #elif type == "string":
        #    ifdefobj.add_string(name, PV_DESC=desc, PV_EGU=egu, PV_HIHI = hihi, PV_HHSV = hhsv, PV_HIGH = high, PV_HSV = hsv, PV_LOW = low, PV_LSV = lsv, PV_LOLO = lolo)
    
    return ifdefobj

#Process local devices to generate Templates
def process_local_devices(ioc_output_dir, plc_output_dir, devfiles_dir, project_config, hash):
    """Process local device configurations and generate output files for IOC and PLC."""
    json_file_path = project_config
    plc_properties, plc_name = load_plc_properties(json_file_path)
    print(plc_name)
    plc_device = Device(
        name=plc_name,
        description='Desc',
        deviceType='PLC',
        propertiesDict=plc_properties,
    )
    dev_list = load_devices(project_config,plc_device)

    ######## keywords to pass
    ifdef_params = {'PLC_TYPE': 'SIEMENS', 'PLCF_STATUS': True, 'COMMIT_ID': 'commitID', 'ROOT_INSTALLATION_SLOT': plc_device.name(), 'EXPERIMENTAL': False, 'PLC_READONLY': False, 'PLC_HOSTNAME': None}
    
    ######### create the plcf objects from a Device object 
    plc_plcf = plcf.PLCF(plc_device)
    #dev_plcf = plcf.PLCF(dev_list)
    
    ######### Template to be created: IFA, EPICS-DB and IOCSH are the three templates
    templates = ['IFA', 'EPICS-DB','IOCSH']

    for template in templates:
        if template == 'IFA':
            output_dir = plc_output_dir
        else:
            output_dir = ioc_output_dir


        ######### import the template and add the TEMPLATE keyword to the Device _properties dictionary
        printer = tf.get_printer(template)
        plc_plcf.register_template(template)
        #dev_plcf.register_template(template)

        ######### create the template header, ROOT_DEVICE is the PLC Device object , PLCF is the PLC plcf object 
        header_template = []
        printer.header(None, header_template, ROOT_DEVICE = plc_device, PLCF = plc_plcf, OUTPUT_DIR = output_dir, HELPERS = helpers, **ifdef_params)


        ######### create the outpufile
        output_file = os.path.join(output_dir, createFilename(plc_plcf, header_template))

        ######### process the header of the template
        header_template = plc_plcf.process(header_template)
        header_template = processHash(header_template, hash)

        ifdef_list = []
        ifdef_dict = {}
        body_template = []
        footer_template = []

        for dev in dev_list:
            dev_plcf = getPLCF(dev)
            dev_plcf.register_template(template)
            with IF_DEF(PLCF = dev_plcf, **ifdef_params) as ifdefobj:
                
                categories = ["Status", "Command", "Parameter"]
                pv_types = ["analog", "digital"] #, "time", "enum", "bitmask", "string"]

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
                        print(f"Category: {category}, Type: {pv_type}")
                        #create ifdefobj with all pvs in device template file    
                        ifdefobj = get_pvs(devfiles_dir, dev.deviceType(), ifdefobj, category, pv_type)

            ####### filling ifdef object list and dictionary
            ifdef_list.append(ifdefobj)
            ifdef_dict.update({dev.name(): ifdefobj})

            ################# create body of the template

            printer.body(ifdef_dict.get(dev.name()), body_template, DEVICE = dev, PLCF = dev_plcf)


        ################# create footer of the template
    
        footer_ifdef = FOOTER_IF_DEF(plc_device, ifdef_list, PLCF = plc_plcf, **ifdef_params)
        printer.footer(footer_ifdef, footer_template, PLCF = plc_plcf)
        footer_template = plc_plcf.process(footer_template)
        footer_template = processHash(footer_template, hash)

        ############### create output template
        output_template = header_template + body_template + footer_template
        (output_template, _) = plcf.PLCF.evalCounters(output_template)
    
        ############## write the output template to file
        eol = getEOL(header_template)
        # write file
        with open(output_file, 'w') as f:
            for line in output_template:
                line = line.rstrip()
                if not line.startswith("#COUNTER") \
                    and not line.startswith("#FILENAME") \
                    and not line.startswith("#EOL"):
                    print(line, end = eol, file = f)

        print("Output template {} file {} written".format(template, output_file))
        print("Hash sum:", hash)

        generate_output_files(template, output_dir, output_file, ifdef_params)

    
#### to be done
def generate_output_files(template, output_dir, output_file, ifdef_params):
    """Generate configuration files based on templates from a directory."""
        ############# if the template is a IFA it will create the scl code
    if template == 'IFA':
        IFA.produce(output_dir, output_file, TIAVersion = '18', nodiag = True, onlydiag = False, commstest = False, verify = None, readonly = False, commit_id = ifdef_params['COMMIT_ID'])

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

    #Create the hash number for all files
    hash = calculate_folder_crc32(output_path)
    print(f"CRC32 for all Device template Files: {hash}")
 
    # Process and generate output for IOC and PLC configurations
    process_local_devices(ioc_output_dir, plc_output_dir, output_path, project_config, hash)


if __name__ == "__main__":
    main()
