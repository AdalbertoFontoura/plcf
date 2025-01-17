import argparse
import helpers
import json
import os
import shutil
from interface_factory import InterfaceFactorySiemens

# Updated to load project configuration from a JSON file and handle local device definitions
def load_project_config(json_file):
    with open(json_file, 'r') as file:
        return json.load(file)

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

def load_template(template_path):
    """Load a template file."""
    with open(template_path, 'r') as file:
        return file.read()

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

def generate_output_files(devices, template_dir, output_dir):
    """Generate configuration files based on templates from a directory."""
    os.makedirs(output_dir, exist_ok=True)
    for device in devices:
        template_path = os.path.join(template_dir, f"{device['type']}.template")
        if not os.path.exists(template_path):
            print(f"Template for {device['type']} not found at {template_path}. Skipping.")
            continue

        template = load_template(template_path)
        device_output = template
        for key, value in device.items():
            placeholder = f"{{{{ {key} }}}}"  # Template placeholder format
            device_output = device_output.replace(placeholder, str(value))

        output_file_path = os.path.join(output_dir, f"{device['name']}.txt")
        with open(output_file_path, 'w') as file:
            file.write(device_output)

def generate_plc_blocks(project_config):
    """Use InterfaceFactorySiemens to generate PLC blocks."""
    devices = project_config.get("PROJ", {}).get("CTRL", {}).get("DEVICE", [])
    if not devices:
        print("No devices found in project configuration.")
        return

    # Initialize InterfaceFactorySiemens
    #plc_factory = InterfaceFactorySiemens()

    for device in devices:
        essname = device.get("essname", "Unknown")
        template_path = device.get("template_path")
        template_name = device.get("template_name")

        if not template_path or not template_name:
            print(f"Skipping device {essname}: Missing template information.")
            continue

        template_file = os.path.join(template_path, template_name)
        if not os.path.exists(template_file):
            print(f"Template file not found: {template_file} for device {essname}.")
            continue

        # Generate block using InterfaceFactorySiemens
        try:
            plc_factory.load_template(template_file)
            block_data = plc_factory.generate_block(essname)

            # Write block data to file
            output_dir = os.path.join(os.path.dirname(__file__), 'plc_blocks')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{essname}.ifa")

            with open(output_file, 'w') as f:
                f.write(block_data)

            print(f"Generated PLC block for {essname} at {output_file}.")

        except Exception as e:
            print(f"Error generating block for {essname}: {e}")

def process_local_devices(devices, ioc_output_dir, plc_output_dir, project_config):
    """Process local device configurations and generate output files for IOC and PLC."""
    #ioc_devices = [device for device in devices if device.get('type') == 'IOC']
    #plc_devices = [device for device in devices if device.get('type') == 'PLC']

    # Generate IOC configuration
    print("Generating IOC configuration...")
    template_dir = os.path.join(os.path.dirname(__file__), 'template_factory/printers')
    if not template_dir or not os.path.isdir(template_dir):
        print(f"Invalid or missing template directory: {template_dir}")
        return

    #generate_output_files(ioc_devices, template_dir, ioc_output_dir)

    # Generate PLC configuration
    print("Generating PLC configuration...")
    #generate_output_files(plc_devices, template_dir, plc_output_dir)

def main():
    parser = argparse.ArgumentParser(description="PLC Factory Tool")
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
    #plc_template, ioc_template = process_local_devices(devices, ioc_output_dir, plc_output_dir, project_config, output_path) #consertar esta função para gerar os templates a serem usados na proxima função

    # Generate PLC blocks using InterfaceFactorySiemens
    #generate_plc_files(plc_template, plc_output_dir)
    #generate_ioc_files(ioc_template, ioc_output_dir)

if __name__ == "__main__":
    main()
