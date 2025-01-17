import json

# Simulando o carregamento do arquivo JSON
project_config = {
    "CTRL": {
        "TEMPLATEPLACE": "Local",
        "DEVICE": [
            {
                "essname": "MBL-010CDL:Cryo-PLC-010",
                "template_path": "C:/Users/adalbertofontoura/ESS/GIT/plcintegrator/templates",
                "template_name": "PLC.json"
            }
        ]
    }
}

# Verifique o conteúdo da chave 'CTRL' e 'DEVICE'
#print(project_config.get("CTRL", {}))  # Verifica se 'CTRL' existe
#print(project_config.get("CTRL", {}).get("DEVICE", []))  # Verifica se 'DEVICE' existe
devices = project_config.get("CTRL", {}).get("DEVICE", [])
print(devices)
for device in devices:
    essname = device.get("essname")
    print(essname)