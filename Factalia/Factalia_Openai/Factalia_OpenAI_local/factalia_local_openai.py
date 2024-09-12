import os
import fitz  # PyMuPDF
import openai
import csv

# Configura la tua chiave API di OpenAI
openai.api_key = 'YOU_OPENAI_API_KEY'

def extract_text_from_pdf(pdf_path):
    """Estrae il testo da un file PDF."""
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

def get_info_from_openai(text, prompt):
    """Interroga il modello GPT-3.5-turbo per estrarre informazioni."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Sei un assistente utile che estrae informazioni specifiche dal testo."},
            {"role": "user", "content": prompt + "\n\n" + text}
        ],
        max_tokens=500
    )
    return response.choices[0].message['content'].strip()

def parse_info(info):
    """Parses the extracted information into a dictionary."""
    parsed_data = {}
    lines = info.split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            parsed_data[key.strip()] = value.strip()
    return parsed_data

def process_pdfs_in_folder(folder_path, prompt):
    """Elabora tutti i file PDF in una cartella e estrae le informazioni."""
    results = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(folder_path, filename)
            print(f"Elaborazione del file: {filename}")
            text = extract_text_from_pdf(pdf_path)
            info = get_info_from_openai(text, prompt)
            parsed_data = parse_info(info)
            parsed_data['File'] = filename
            results.append(parsed_data)
    return results

def save_results_to_csv(results, csv_path):
    """Salva i risultati estratti in un file CSV con colonne specifiche."""
    fieldnames = [
        'File', 'Número de factura', 'Fecha de la factura', 'IVA%', 'BASE TOTAL',
        'IVA TOTAL', 'TOTAL', 'Nombre del cliente', 'NIF del cliente',
        'Compañía de servicio', 'NIF de la compañía de servicio', 'IRPF','RETENCIÓN IRPF'
    ]
    
    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            # Assicurati che il dizionario contenga solo le chiavi definite in fieldnames
            row = {key: result.get(key, '') for key in fieldnames}
            writer.writerow(row)
    print(f"Risultati salvati in {csv_path}")

def main():
    folder_path = '/home/robin/Desktop/Facturalia_3/bill'  # Percorso della tua cartella locale
    csv_path = '/home/robin/Desktop/Facturalia_3/csv/data3.csv'  # Percorso del file CSV

    prompt = ("Extrae la siguiente información del texto proporcionado:\n"
              "- número de factura\n"
              "- Fecha factura\n"
              "- IVA%\n"
              "- BASE TOTAL\n"
              "- IVA TOTAL\n"
              "- TOTAL\n"
              "- Nombre cliente\n"
              "- NIF Cliente\n"
              "- La compañía de servicio\n"
              "- NIF compañía de servicio\n\n"
              "- IRPF%\n"
              "- RETENCIÓN IRPF"
              "Ejemplo de cómo debe ser la información extraída:\n"
              "Número de factura: 2024138473\n"
              "Fecha de la factura: 12/08/2024\n"
              "IVA: 21%\n"
              "BASE TOTAL: 767,79\n"
              "IVA TOTAL: 161,24\n"
              "TOTAL: 929,03\n"
              "Nombre del cliente: Buscamobile S.L\n"
              "NIF del cliente: B97463491\n"
              "Compañía de servicio: Telefónica IOT & Big Data Tech, S.A.\n"
              "NIF de la compañía de servicio: A78967577\n"
              "IRPF%: -7%\n"
              "RETENCIÓN IRPF: 3,50")

    if not os.path.isdir(folder_path):
        print("Il percorso della cartella non è valido.")
        return

    results = process_pdfs_in_folder(folder_path, prompt)
    save_results_to_csv(results, csv_path)

if __name__ == "__main__":
    main()
