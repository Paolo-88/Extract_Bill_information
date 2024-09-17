import os
import re
import csv
import requests
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
import numpy as np
import shutil  # Per spostare i file

# Funzione per estrarre testo da una singola immagine usando PaddleOCR
def extract_text_from_image(image):
    image_np = np.array(image)
    
    ocr = PaddleOCR(use_angle_cls=True, lang='es')  # Usa la lingua spagnola
    result = ocr.ocr(image_np)
    
    extracted_text = []
    for line in result[0]:
        text = line[1][0]
        extracted_text.append(text)
        
    return ' '.join(extracted_text)

# Funzione per estrarre testo dalle prime due pagine del PDF
def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    pages_to_process = images[:2]  # Processa solo le prime due pagine
    
    all_text = []
    for i, image in enumerate(pages_to_process):
        print(f"Procesando página {i + 1}...")
        text = extract_text_from_image(image)
        all_text.append(text)
    
    return ' '.join(all_text)

# Funzione di segmentazione del testo
def split_text(text, max_length=2000):
    segments = []
    while len(text) > max_length:
        split_index = text.rfind(' ', 0, max_length)
        if split_index == -1:
            split_index = max_length
        segments.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if text:
        segments.append(text)
    return segments

# Funzione per inviare il testo al modello LLaMA 3 e ottenere una risposta formattata
def query_llama_3(api_key, api_url, prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False,
        "max_tokens": 500
    }
   
    response = requests.post(api_url, headers=headers, json=payload)
   
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    try:
        response_json = response.json()
        if isinstance(response_json, dict) and 'response' in response_json:
            response_text = response_json['response']
        elif isinstance(response_json, list):
            response_text = ' '.join([res['response'] for res in response_json if 'response' in res])
        else:
            response_text = ''
    except ValueError as e:
        print(f"Error de decodificación JSON: {e}")
        response_text = ''
        
    return response_text

# Funzione per estrarre le informazioni specifiche dal testo formattato
def extract_info_from_text(formatted_text, api_key, api_url, pdf_file_name):
    prompt_extraction = (
        "Por favor, responde proporcionando solo la información en el siguiente formato:\n"
        "Nombre de la empresa de servicio: [ ]\n"
        "CIF/NIF de la empresa de servicio: [ ]\n"
        "Número de factura: [ ]\n"
        "Fecha de factura: [ ]\n"
        "IVA %: [ ]\n"
        "IVA TOTAL: [ ]\n"
        "SUBTOTAL: [ ]\n"
        "TOTAL FACTURA: [ ]\n\n"
        "Llena cada campo con la información correspondiente, o usa 'No disponible' si no hay información.\n\n"
        f"Texto formateado:\n{formatted_text}\n"
    )
    
    response = query_llama_3(api_key, api_url, prompt_extraction)
    
    patterns = {
        'Nombre de la empresa de servicio': r'Nombre de la empresa de servicio\s*[:\s]*([^\n]*)',
        'CIF/NIF de la empresa de servicio': r'CIF/NIF de la empresa de servicio\s*[:\s]*([A-Z0-9]+)',  # Cattura solo il CIF/NIF
        'Número de factura': r'Número de factura\s*[:\s]*([^\n]*)',
        'Fecha de factura': r'Fecha de factura\s*[:\s]*([^\n]*)',
        'IVA %': r'IVA %\s*[:\s]*([^\n]*)',
        'IVA TOTAL': r'IVA TOTAL\s*[:\s]*([^\n]*)',
        'SUBTOTAL': r'SUBTOTAL\s*[:\s]*([^\n]*)',
        'TOTAL FACTURA': r'TOTAL FACTURA\s*[:\s]*([^\n]*)'
    }

    info = {key: 'No disponible' for key in patterns.keys()}
    info['Nombre del archivo PDF'] = pdf_file_name

    if response:
        for key, pattern in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                info[key] = clean_text(match.group(1).strip())  # Usa clean_text per rimuovere i caratteri non desiderati

    return info

# Funzione per rimuovere caratteri non desiderati
def clean_text(text):
    # Rimuove apici, virgolette e asterischi
    text = text.replace('*', '')
    text = text.replace('"', '')
    text = text.replace("'", '')
    return text

# Funzione per rinominare e spostare il file PDF
def rename_and_move_pdf(pdf_path, extracted_info, output_folder):
    new_file_name = (
        f"{extracted_info.get('Fecha de factura', 'Fecha_no_disponible')}_"
        f"{extracted_info.get('Nombre de la empresa de servicio', 'Nombre_no_disponible')}_"
        f"{extracted_info.get('Número de factura', 'Numero_no_disponible')}_"
        f"{extracted_info.get('TOTAL FACTURA', 'total_no_disponible')}.pdf"
    )
    
    new_file_name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', new_file_name)
    new_file_path = os.path.join(output_folder, new_file_name)
    
    shutil.move(pdf_path, new_file_path)
    
    print(f"File PDF rinominato e spostato a: {new_file_path}")

# Funzione principale per elaborare tutti i file PDF in una cartella
def process_pdf_folder(folder_path, api_key, api_url, csv_file, output_folder):
    with open(csv_file, 'w', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file, delimiter=';')  # Imposta il separatore a ";"
        csv_writer.writerow([
            'Nombre del archivo PDF',
            'Nombre de la empresa de servicio',
            'CIF/NIF de la empresa de servicio',
            'Número de factura',
            'Fecha de factura',
            'IVA %',
            'IVA TOTAL',
            'SUBTOTAL',
            'TOTAL FACTURA'
        ])
        
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith('.pdf'):
                pdf_path = os.path.join(folder_path, file_name)
                
                print(f"\nElaborando: {pdf_path}")
                
                extracted_text = extract_text_from_pdf(pdf_path)
                segmented_text = split_text(extracted_text)
                all_formatted_texts = []

                for segment in segmented_text:
                    prompt_formatting = (
                        "Formatea el texto recibido de manera que sea ordenado y dividido en secciones. "
                        "Organiza el texto en las siguientes secciones:\n"
                        "- Costos\n"
                        "- Información sobre la factura\n"
                        "- Información sobre la compañía del servicio\n\n"
                        "Asegúrate de que cada sección esté claramente separada y que el texto esté bien estructurado y sea fácil de leer.\n\n"
                        f"Texto a formatear:\n{segment}\n"
                    )
                    
                    formatted_text = query_llama_3(api_key, api_url, prompt_formatting)
                    if formatted_text:
                        all_formatted_texts.append(formatted_text)
                
                formatted_text_output = "\n\n".join(all_formatted_texts)

                extracted_info = extract_info_from_text(formatted_text_output, api_key, api_url, file_name)
                
                csv_writer.writerow([
                    clean_text(extracted_info.get('Nombre del archivo PDF', 'No disponible')),
                    clean_text(extracted_info.get('Nombre de la empresa de servicio', 'No disponible')),
                    clean_text(extracted_info.get('CIF/NIF de la empresa de servicio', 'No disponible')),
                    clean_text(extracted_info.get('Número de factura', 'No disponible')),
                    clean_text(extracted_info.get('Fecha de factura', 'No disponible')),
                    clean_text(extracted_info.get('IVA %', 'No disponible')),
                    clean_text(extracted_info.get('IVA TOTAL', 'No disponible')),
                    clean_text(extracted_info.get('SUBTOTAL', 'No disponible')),
                    clean_text(extracted_info.get('TOTAL FACTURA', 'No disponible'))
                ])

                rename_and_move_pdf(pdf_path, extracted_info, output_folder)

                print(f"Información extraída para {file_name} guardada en el CSV.")

# Sostituisci con i tuoi dati
api_key = 'ollama'  # La tua chiave API
api_url = 'http://localhost:11434/api/generate'  # L'URL del tuo endpoint

# Percorso della cartella contenente i file PDF
folder_path = '/home/paolo/facturalia/ollama_test/bill_input'  # Percorso della cartella contenente i file PDF

# Nome del file CSV per salvare le informazioni estratte
csv_file = '/home/paolo/facturalia/ollama_test/csv/extracted_info4.csv'  # Percorso del file CSV

# Percorso della cartella di output per i file PDF rinominati
output_folder = '/home/paolo/facturalia/ollama_test/bill_output'  # Percorso della cartella di output

# Esegui il processo
process_pdf_folder(folder_path, api_key, api_url, csv_file, output_folder)
