import logging
import sys
import pandas as pd
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.cloud import storage

# Konfigurasi logging verbose
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- KONFIGURASI GCP ---
PROJECT_ID = "qwiklabs-gcp-04-5027a4f721c0"
# ⚠️ PASTIKAN MENGGUNAKAN ID PROCESSOR "FORM PARSER" YANG BARU KAMU BUAT (Bukan ID OCR sebelumnya)
PROCESSOR_ID = "c2b088f3cf12be83" 
LOCATION = "us" 
BUCKET_NAME = "qwiklabs-gcp-04-5027a4f721c0-cepf-documentai"

INPUT_BLOB_NAME = "sample-intake-form.pdf"
FINAL_OUTPUT_FILE = "cepf_form_parser.csv"

def get_text(text_anchor, document_text):
    """Helper untuk mengambil teks berdasarkan text anchor dari Document AI"""
    response = ""
    for segment in text_anchor.text_segments:
        start_index = segment.start_index
        end_index = segment.end_index
        response += document_text[start_index:end_index]
    return response.strip().replace("\n", " ")

def main():
    logger.info("Memulai proses Form Parser Online...")
    
    # 1. Inisialisasi Storage Client & Download File PDF dari GCS ke Memori
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    logger.info(f"Mendownload {INPUT_BLOB_NAME} dari bucket {BUCKET_NAME}...")
    blob = bucket.blob(INPUT_BLOB_NAME)
    file_bytes = blob.download_as_bytes()

    # 2. Inisialisasi Document AI Client
    opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
    docai_client = documentai.DocumentProcessorServiceClient(client_options=opts)
    processor_path = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

    # 3. Siapkan Request Online Processing (RawDocument)
    raw_document = documentai.RawDocument(content=file_bytes, mime_type="application/pdf")
    request = documentai.ProcessRequest(name=processor_path, raw_document=raw_document)
    
    logger.info("Mengirim dokumen ke Document AI Form Parser (Online)...")
    result = docai_client.process_document(request=request)
    document = result.document
    logger.info("Dokumen berhasil diproses oleh Form Parser.")

    # 4. Ekstrak Key/Value Menggunakan Perulangan Form Fields
    keys = []
    values = []
    
    for page in document.pages:
        for field in page.form_fields:
            # Ambil teks untuk nama field (Key) dan isi field (Value)
            field_name = get_text(field.field_name.text_anchor, document.text)
            field_value = get_text(field.field_value.text_anchor, document.text)
            
            keys.append(field_name)
            values.append(field_value)
            logger.debug(f"Extracted -> Key: '{field_name}' | Value: '{field_value}'")

    # 5. Membuat DataFrame Pandas dan Konversi ke CSV
    logger.info(f"Membuat DataFrame pandas dengan {len(keys)} pasangan Key/Value...")
    df = pd.DataFrame({
        "Key": keys,
        "Value": values
    })
    
    # Konversi DataFrame menjadi string CSV
    csv_data = df.to_csv(index=False)

    # 6. Upload Hasil Akhir CSV ke Cloud Storage Bucket
    logger.info(f"Menyimpan hasil akhir CSV ke gs://{BUCKET_NAME}/{FINAL_OUTPUT_FILE}...")
    output_blob = bucket.blob(FINAL_OUTPUT_FILE)
    output_blob.upload_from_string(csv_data, content_type="text/csv")
    
    logger.info("--- Form Parser Selesai ---")

if __name__ == "__main__":
    main()
