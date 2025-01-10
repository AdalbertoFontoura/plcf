import json
import os
from plcfactory import processDevice, processTemplateID

def load_json(file_path):
    """Carrega os dados do arquivo JSON."""
    with open(file_path, 'r') as file:
        return json.load(file)

def main(json_file_path):
    """
    Processa o arquivo JSON, extrai os parâmetros e utiliza funções do plcfactory.py
    para gerar arquivos STL para o PLC.
    """
    # Carregar os dados do JSON
    data = load_json(json_file_path)

    # Extrair dispositivos e parâmetros globais
    devices = data["PROJ"]["CTRL"]["DEVICE"]
    hw_params = data["PROJ"]["HW"]

    # Diretório de saída (usando OUTPUT_DIR do plcfactory.py se existir)
    output_dir = "output_stl"
    os.makedirs(output_dir, exist_ok=True)

    # Iterar pelos dispositivos para gerar os arquivos STL
    for device in devices:
        essname = device["essname"]
        template_path = os.path.join(device["template_path"], device["template_name"])

        print(f"Processando dispositivo: {essname}")

        # Processar templates usando processTemplateID
        processTemplateID(template_path, [device])

    print(f"Arquivos STL gerados no diretório: {output_dir}")

if __name__ == "__main__":
    # Caminho para o arquivo JSON
    json_file_path = "MBL-010CDL_Cryo-PLC-010.json"

    # Executar o programa
    main(json_file_path)
