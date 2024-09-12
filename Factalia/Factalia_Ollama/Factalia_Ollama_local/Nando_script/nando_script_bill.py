import pdfplumber
import requests
import csv
import os

# Función para extraer el texto de una página específica de un PDF
def extract_text_from_page(pdf_path, page_number):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        if page_number < len(pdf.pages):
            page = pdf.pages[page_number]
            text = page.extract_text() or ""
    return text

# Función para enviar el texto al modelo LLaMA 3 y obtener una respuesta
def query_llama_3(api_key, api_url, text, prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False,
        "max_tokens": 3500
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    return response.json().get('response', '')

# Función para limpiar y formatear el texto
def clean_and_format_text(text, prompt):
    response = query_llama_3(api_key, api_url, text, prompt)
    return response if response else ""

# Función para extraer la información requerida
def extract_info_from_text(text, prompt):
    response = query_llama_3(api_key, api_url, text, prompt)
    data = {}
    if response:
        for line in response.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()
    return data

# Función para normalizar los nombres de los campos
def normalize_data(data, filename):
    normalized_data = {
        'nombre del archivo': filename,
        'número de factura': data.get('* Número de factura', 'None'),
        'fecha de factura': data.get('* Fecha de factura o fecha de emisión de factura', 'None'),
        'Compañía del servicio': data.get('* Compañía del servicio', 'None'),
        'NIF o CIF de la compañía del servicio': data.get('* NIF o CIF de la compañía del servicio', 'None'),
        'Cliente': data.get('* Cliente', 'None'),
        'NIF o CIF del cliente': data.get('* NIF o CIF del cliente', 'None'),
        'IVA': data.get('* IVA', 'None'),
        'Total IVA': data.get('* Total IVA', 'None'),
        'Imponible o base total': data.get('* Imponible o base total', 'None'),
        'total': data.get('* Total', 'None')
    }
    return normalized_data

# Función para escribir los datos extraídos en el CSV
def write_to_csv(data, csv_file_path):
    fieldnames = [
        'nombre del archivo', 'número de factura', 'fecha de factura', 'Compañía del servicio', 
        'NIF o CIF de la compañía del servicio', 'Cliente', 
        'NIF o CIF del cliente', 'IVA', 'Total IVA', 'Imponible o base total', 'total'
    ]
    
    file_exists = os.path.isfile(csv_file_path)
    with open(csv_file_path, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# Función principal para procesar un archivo PDF
def process_invoice(pdf_path, api_key, api_url, csv_file_path):
    print(f"Procesando el archivo: {pdf_path}")
    filename = os.path.basename(pdf_path)  # Extrae solo el nombre del archivo

    # Extrae y limpia el texto de la primera y segunda página
    text_page_1 = extract_text_from_page(pdf_path, 0)
    text_page_2 = extract_text_from_page(pdf_path, 1)

    prompt_cleanup = (
        "Has recibido un texto extraído de una factura con una estructura y un diseño complejos. "
        "Tu tarea es limpiar y simplificar el texto para hacerlo lo más claro y legible posible. "
        "Elimina cualquier ruido, errores y formato innecesario, haciéndolo fácilmente legible.\n\n"
        "Texto extraído:\n"
        f"{text_page_1[:2000]}\n\n"
        "Instrucciones:\n"
        "- Elimina cualquier ruido, caracteres especiales o formato innecesario.\n"
        "- Corrige cualquier error de transcripción u ortografía.\n"
        "- Mantén el texto simple y claro, sin alterar el significado de la información.\n"
        "- No es necesario un formato específico, pero el texto debe ser fácilmente legible."
    )

    formatted_text_page_1 = clean_and_format_text(text_page_1, prompt_cleanup)
    formatted_text_page_2 = clean_and_format_text(text_page_2, prompt_cleanup)

    # Extrae la información de la primera página
    prompt_extraction = (
        "Por favor, extrae solamente la siguiente información del resultado, sin incluir otra información:\n"
        "- número de factura\n"
        "- fecha de factura o fecha de emisión de factura\n"
        "- Compañía del servicio\n"
        "- NIF o CIF de la compañía del servicio\n"
        "- Cliente\n"
        "- NIF o CIF del cliente\n"
        "- IVA (generalmente es un valor porcentual)\n"
        "- Total IVA (generalmente corresponde al valor numérico del porcentaje sobre el total)\n"
        "- Imponible o base total (corresponde al total - Total IVA)\n"
        "- total\n\n"
        f"Resultado:\n{formatted_text_page_1}\n"
    )
    
    data_from_page_1 = extract_info_from_text(formatted_text_page_1, prompt_extraction)

    # Si faltan datos, extrae de la segunda página
    required_fields = [
        'número de factura', 'fecha de factura', 'Compañía del servicio',
        'NIF o CIF de la compañía del servicio', 'Cliente',
        'NIF o CIF del cliente', 'IVA', 'Total IVA',
        'Imponible o base total', 'total'
    ]

    missing_fields = [field for field in required_fields if not data_from_page_1.get(field)]
    
    if missing_fields:
        print(f"Información faltante encontrada en la página 1. Revisando la página 2.")
        prompt_extraction_page_2 = (
            f"Resultado:\n{formatted_text_page_2}\n"
        )
        data_from_page_2 = extract_info_from_text(formatted_text_page_2, prompt_extraction)
        
        # Completa los datos faltantes con los de la segunda página
        for field in missing_fields:
            if data_from_page_2.get(field):
                data_from_page_1[field] = data_from_page_2[field]

    # Normaliza y escribe los datos extraídos en el archivo CSV
    normalized_data = normalize_data(data_from_page_1, filename)
    write_to_csv(normalized_data, csv_file_path)

# Ruta de la carpeta que contiene los archivos PDF de las facturas
pdf_folder_path = "/home/paolo/facturalia/ollama_test/bill/"

# Ruta del archivo CSV para guardar los datos extraídos
csv_file_path = '/home/paolo/facturalia/ollama_test/csv/dati_estratti_fatture12.csv'

# Clave API y URL del endpoint (reemplaza con tus datos)
api_key = 'ollama'  
api_url = 'http://localhost:11434/api/generate'

# Procesa cada archivo PDF en la carpeta especificada uno por uno
for filename in os.listdir(pdf_folder_path):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder_path, filename)
        process_invoice(pdf_path, api_key, api_url, csv_file_path)

