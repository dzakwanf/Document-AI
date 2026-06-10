import os
import logging
import sys
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.cloud import storage

# Konfigurasi logging verbose
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- KONFIGURASI GCP (Sesuaikan dengan lab kamu) ---
PROJECT_ID = "qwiklabs-gcp-04-5027a4f721c0"
PROCESSOR_ID = "c1ec7a3ac97d4b0"  # ID dari OCR Processor yang kamu buat
LOCATION = "us"                                  # Biasanya 'us' atau 'eu'
BUCKET_NAME = "qwiklabs-gcp-04-5027a4f721c0-cepf-documentai"
INPUT_FILE = "sample-batch-ocr.pdf"
OUTPUT_FILE = "cepf_online_ocr.txt"

def process_document_and_upload():
    logger.info("Memulai Online OCR Process...")
    logger.debug(f"Target Bucket: {BUCKET_NAME}")

    opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
    docai_client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # Ambil path lengkap ke processor
    processor_path = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

    logger.info(f"Membaca file lokal: {INPUT_FILE}")
    with open(INPUT_FILE, "rb") as pdf_file:
        file_content = pdf_file.read()
    logger.debug(f"Ukuran file: {len(file_content)} bytes")

    # Siapkan objek dokumen mentah
    raw_document = documentai.RawDocument(
        content=file_content, 
        mime_type="application/pdf"
    )

    # Buat request untuk online processing
    request = documentai.ProcessRequest(name=processor_path, raw_document=raw_document)

    logger.info("Mengirim dokumen ke Document AI (Synchronous)...")
    result = docai_client.process_document(request=request, timeout=300)
    
    extracted_text = result.document.text
    logger.info(f"Ekstraksi berhasil. Karakter ditemukan: {len(extracted_text)}")

    logger.info(f"Mengunggah hasil ke GCS: {OUTPUT_FILE}")
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(OUTPUT_FILE)

    blob.upload_from_string(extracted_text, content_type="text/plain")
    logger.info(f"File sukses disimpan di: gs://{BUCKET_NAME}/{OUTPUT_FILE}")

if __name__ == "__main__":
    # Memastikan file input ada sebelum dijalankan
    if not os.path.exists(INPUT_FILE):
        logger.error(f"File {INPUT_FILE} tidak ditemukan!")
    else:
        process_document_and_upload()
