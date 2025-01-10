import argparse
import helpers
import json

# Updated to load project configuration from a JSON file and handle local device definitions
def load_project_config(json_file):
    with open(json_file, 'r') as file:
        return json.load(file)

def load_template(template_file):
    """Load a template file."""
    with open(template_file, 'r') as file:
        return file.read()

def generate_plc_output(devices, template, output_file):
    """Generate PLC configuration files based on a template."""
    with open(output_file, 'w') as file:
        for device in devices:
            device_output = template
            for key, value in device.items():
                placeholder = f"{{{{ {key} }}}}"  # Template placeholder format
                device_output = device_output.replace(placeholder, str(value))
            file.write(device_output + "\n")

def process_local_devices(devices, ioc_output_file, plc_output_file, plc_template_file):
    """Process local device configurations and generate output files for IOC and PLC."""
    ioc_devices = [device for device in devices if device.get('type') == 'IOC']
    plc_devices = [device for device in devices if device.get('type') == 'PLC']

    # Generate IOC configuration
    print("Generating IOC configuration...")
    with open(ioc_output_file, 'w') as file:
        file.write("# IOC configuration output\n")
        for device in ioc_devices:
            file.write(f"Device Name: {device['name']}\n")
            file.write(f"Properties: {json.dumps(device['properties'], indent=4)}\n\n")

    # Generate PLC configuration using template
    print("Generating PLC configuration...")
    template = load_template(plc_template_file)
    generate_plc_output(plc_devices, template, plc_output_file)

def main():
    parser = argparse.ArgumentParser(description="PLC Factory Tool")
    parser.add_argument("--config", help="JSON configuration file for the project", required=True)
    parser.add_argument("--devices", help="JSON file with device definitions", required=True)
    parser.add_argument("--ioc-output", help="Output file for IOC configuration", required=True)
    parser.add_argument("--plc-output", help="Output file for PLC configuration", required=True)
    parser.add_argument("--plc-template", help="Template file for PLC configuration", required=True)

    args = parser.parse_args()

    # Load project configuration
    config = load_project_config(args.config)

    # Load local device definitions
    devices = load_project_config(args.devices)

    # Process and generate output for IOC and PLC configurations
    process_local_devices(devices, args.ioc_output, args.plc_output, args.plc_template)

if __name__ == "__main__":
    main()
