import pdfplumber
import requests
import csv
import os

# Función para extraer el texto de un archivo PDF completo
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
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

# Función para extraer la información solicitada
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
        'Número de factura': data.get('* Número de factura', '').replace('*', '').strip(),
        'Razón social del proveedor': data.get('* Razón social del proveedor', '').replace('*', '').strip(),
        'Consumo kWh': data.get('* Consumo kWh', 'No especificado').replace('*', '').strip(),
        'Fecha de emisión de la factura': data.get('* Fecha de emisión de la factura', 'No especificada').replace('*', '').strip(),
        'Período de facturación': data.get('* Período de facturación', 'No especificado').replace('*', '').strip(),
        'Nombre del archivo': filename
    }
    return normalized_data

# Función para escribir los datos extraídos en el archivo CSV
def write_to_csv(data, csv_file_path):
    fieldnames = [
        'Número de factura', 'Razón social del proveedor', 'Consumo kWh', 
        'Fecha de emisión de la factura', 'Período de facturación', 'Nombre del archivo'
    ]
    
    file_exists = os.path.isfile(csv_file_path)
    with open(csv_file_path, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({field: data.get(field, '') for field in fieldnames})

# Función principal para procesar un archivo PDF
def process_invoice(pdf_path, api_key, api_url, csv_file_path):
    filename = os.path.basename(pdf_path)
    print(f"Procesando el archivo: {pdf_path}")

    # Extrae el texto del archivo PDF completo
    text = extract_text_from_pdf(pdf_path)

    # Prompt para limpiar y formatear el texto
    prompt_cleanup = (
        "Has recibido un texto extraído de una factura con una estructura y un diseño complejos. "
        "Tu tarea es limpiar y simplificar el texto para que sea lo más claro y legible posible. "
        "Elimina cualquier ruido, errores y formateo innecesario, haciéndolo fácilmente legible.\n\n"
        "Texto extraído:\n"
        f"{text[:2000]}\n\n"
        "Instrucciones:\n"
        "- Elimina cualquier ruido, caracteres especiales o formato innecesario.\n"
        "- Corrige errores de transcripción u ortografía.\n"
        "- Mantén el texto simple y claro, sin alterar el significado de la información.\n"
        "- No es necesario un formato específico, pero el texto debe ser fácilmente legible."
    )

    formatted_text = clean_and_format_text(text, prompt_cleanup)

    # Prompt para ordenar el texto formateado y eliminar caracteres especiales
    prompt_ordering = (
        "Por favor, organiza el texto según los siguientes criterios y elimina cualquier carácter especial "
        "como asteriscos, signos de puntuación innecesarios u otros símbolos que no sean parte del contenido. "
        "El texto debe presentarse de manera clara y libre de caracteres no deseados. Solo incluye la información "
        "relevante y elimina el texto adicional:\n\n"
        f"Texto formateado:\n{formatted_text}\n"
    )
    
    ordered_text = query_llama_3(api_key, api_url, formatted_text, prompt_ordering)
    print("\nTexto ordenado:")
    print(ordered_text)

    # Prompt para extraer la información del texto ordenado
    prompt_extraction = (
        "Por favor, extrae solamente la siguiente información del resultado, sin incluir otra información:\n"
        "- Número de factura\n"
        "- Razón social del proveedor\n"
        "- Consumo kWh\n"
        "- Fecha de emisión de la factura\n"
        "- Período de facturación\n\n"
        f"Resultado:\n{ordered_text}\n"
    )
    
    data_from_text = extract_info_from_text(ordered_text, prompt_extraction)
    print("\nInformación extraída:")
    print(data_from_text)

    # Controlla los datos antes de escribirlos en el CSV
    print("\nDatos normalizados:")
    normalized_data = normalize_data(data_from_text, filename)
    print(normalized_data)

    # Normaliza y escribe los datos extraídos en el archivo CSV
    write_to_csv(normalized_data, csv_file_path)

# Ruta de la carpeta que contiene los archivos PDF de las facturas
pdf_folder_path = "/home/paolo/facturalia/ollama_test/bill_chris"

# Ruta del archivo CSV para guardar los datos extraídos
csv_file_path = '/home/paolo/facturalia/ollama_test/csv/chris_isemaren.csv'

# Clave API y URL del endpoint (reemplaza con tus datos)
api_key = 'ollama'  
api_url = 'http://localhost:11434/api/generate'

# Procesa cada archivo PDF en la carpeta especificada uno a la vez
for filename in os.listdir(pdf_folder_path):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder_path, filename)
        process_invoice(pdf_path, api_key, api_url, csv_file_path)

