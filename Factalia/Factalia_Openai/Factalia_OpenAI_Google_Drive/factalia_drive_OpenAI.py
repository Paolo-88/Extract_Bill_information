import os
import io
import csv
import pdfplumber
import openai
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# Configura le credenziali di Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Sostituisci con il percorso del tuo file di credenziali

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Configura OpenAI API
openai.api_key = 'YOU_OPENAI_API_KEY'  

# Funzione per scaricare un PDF da Google Drive
def download_pdf(file_id, destination):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")

# Funzione per estrarre il testo dalle prime due pagine di un PDF utilizzando GPT-3.5 Turbo
def extract_text_from_pdf(pdf_path, prompt):
    MAX_TOKENS = 4096  # Limite massimo di token per GPT-3.5-turbo per ogni richiesta
    extracted_data = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            combined_extracted_text = ""

            # Limita la lettura alle prime due pagine
            total_pages = min(2, len(pdf.pages))

            for page_number in range(total_pages):
                page = pdf.pages[page_number]
                text = page.extract_text()
                if text:
                    print(f"Text from page {page.page_number}: {text[:500]}")  # Mostra solo i primi 500 caratteri
                    combined_extracted_text += text + "\n"

                    # Prepara il messaggio per la richiesta
                    message_content = prompt + "\n" + combined_extracted_text

                    # Controlla se il messaggio supera il limite di token e tronca se necessario
                    if len(message_content) > MAX_TOKENS:
                        print(f"Warning: Content length exceeds the maximum token limit for GPT-3.5-turbo.")
                        message_content = message_content[:MAX_TOKENS]  # Tronca il testo se necessario

                    try:
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant that extracts key information from invoices."},
                                {"role": "user", "content": message_content}
                            ]
                        )
                        response_text = response['choices'][0]['message']['content']
                        print(f"OpenAI response: {response_text[:500]}")  # Mostra solo i primi 500 caratteri
                        
                        # Unisce i dati estratti dalla risposta
                        combined_extracted_text += response_text
                    except openai.error.InvalidRequestError as e:
                        print(f"Error extracting text: {e}")
                        continue

            # Analizza il testo combinato finale per estrarre i dati
            data = parse_extracted_data(combined_extracted_text)
            extracted_data.append(data)

    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []
    
    return extracted_data

# Funzione per parsare i dati direttamente dalla risposta di OpenAI
def parse_extracted_data(response_text):
    """Parsa i dati dalla risposta strutturata di OpenAI."""
    lines = response_text.split('\n')
    data = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            cleaned_key = key.strip().replace('-', '').strip()  # Rimuove i trattini e spazi extra
            data[cleaned_key] = value.strip()
    return data

# Funzione per gestire il flusso di lavoro
def process_invoices_from_drive(input_folder_id, output_folder_id, prompt):
    results = drive_service.files().list(
        q=f"'{input_folder_id}' in parents and mimeType='application/pdf'",
        fields="files(id, name)"
    ).execute()
    items = results.get('files', [])

    all_extracted_data = []

    if not items:
        print('No files found.')
    else:
        for item in items:
            file_id = item['id']
            file_name = item['name']
            print(f'Processing file: {file_name}')

            pdf_path = f'/tmp/{file_name}'
            download_pdf(file_id, pdf_path)

            extracted_data = extract_text_from_pdf(pdf_path, prompt)
            for data in extracted_data:
                data["File"] = file_name

            all_extracted_data.extend(extracted_data)
            os.remove(pdf_path)

    return all_extracted_data

# Funzione per salvare i risultati estratti in un file CSV
def save_results_to_csv(results, csv_path):
    """Salva i risultati estratti in un file CSV con colonne mappate correttamente."""
    if not results:
        print("No data to save.")
        return

    # Mappatura chiavi estratte a intestazioni CSV standard
    fieldnames = [
        'File', 'Número de factura', 'Fecha de la factura', 'IVA', 'BASE TOTAL',
        'IVA TOTAL', 'TOTAL', 'Nombre cliente', 'NIF cliente',
        'Compañía de servicio', 'NIF de la Compañía de servicio'
    ]

    key_mapping = {
        'Número de factura': 'Número de factura',
        'Fecha factura': 'Fecha de la factura',
        'IVA': 'IVA',
        'BASE TOTAL': 'BASE TOTAL',
        'IVA TOTAL': 'IVA TOTAL',
        'TOTAL': 'TOTAL',
        'Nombre cliente': 'Nombre cliente',
        'NIF Cliente': 'NIF cliente',
        'Compañía de servicio': 'Compañía de servicio',
        'NIF de la Compañía de servicio': 'NIF de la Compañía de servicio'
    }

    # Salvataggio dei dati nel CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            # Mappatura delle chiavi usando key_mapping
            standardized_result = {key_mapping.get(k, k): v for k, v in result.items() if key_mapping.get(k, k) in fieldnames}
            # Aggiungi campi vuoti per le chiavi mancanti
            for field in fieldnames:
                standardized_result.setdefault(field, '')
            print(f"Saving result: {standardized_result}")
            writer.writerow(standardized_result)

# Funzione per caricare un file su Google Drive
def upload_file_to_drive(file_path, folder_id):
    """Carica un file su Google Drive."""
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='text/csv')
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def main():
    input_folder_id = '18MmwjM_mYcKCEKa2JBIhDmlfNWbOO7YX'  # Inserisci l'ID della cartella Google Drive da cui leggere i PDF
    output_folder_id = '1XAoW6XrMcqHGS-bbHJ6ewIJslocyZNYp'  # Inserisci l'ID della cartella Google Drive in cui salvare il CSV
    csv_path = '/tmp/extracted_data.csv'  # Percorso temporaneo per salvare il file CSV localmente

    prompt = (
    "Extrae los siguientes datos clave de la factura:\n"
    "- Número de factura\n"
    "- Fecha factura\n"
    "- IVA\n"
    "- BASE TOTAL\n"
    "- IVA TOTAL\n"
    "- TOTAL\n"
    "- Nombre del cliente\n"
    "- NIF del cliente\n"
    "- Compañía de servicio\n"
    "- NIF de la compañía de servicio\n"
    "Formato del resultado:\n"
    "Número de factura: [valor]\n"
    "Fecha factura: [valor]\n"
    "IVA: [valor]\n"
    "BASE TOTAL: [valor]\n"
    "IVA TOTAL: [valor]\n"
    "TOTAL: [valor]\n"
    "Nombre del cliente: [valor]\n"
    "NIF del cliente: [valor]\n"
    "Compañía de servicio: [valor]\n"
    "NIF de la compañía de servicio: [valor]\n"
    )


    extracted_data = process_invoices_from_drive(input_folder_id, output_folder_id, prompt)
    save_results_to_csv(extracted_data, csv_path)
    upload_file_to_drive(csv_path, output_folder_id)

if __name__ == "__main__":
    main()


