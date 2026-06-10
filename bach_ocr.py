import logging
import sys
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.cloud import storage

# Konfigurasi logging verbose
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- KONFIGURASI GCP ---
PROJECT_ID = "qwiklabs-gcp-04-5027a4f721c0"
PROCESSOR_ID = "c1ec7a3ac97d4b0" 
LOCATION = "us" 
BUCKET_NAME = "qwiklabs-gcp-04-5027a4f721c0-cepf-documentai"

GCS_INPUT_URI = f"gs://{BUCKET_NAME}/sample-batch-ocr.pdf"
GCS_OUTPUT_PREFIX = f"gs://{BUCKET_NAME}/batch_output/"
FINAL_OUTPUT_FILE = "cepf_batch_ocr.txt"

def main():
    logger.info("Memulai proses Batch OCR untuk novel...")
    
    # 1. Inisialisasi Document AI Client
    opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
    docai_client = documentai.DocumentProcessorServiceClient(client_options=opts)
    processor_path = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

    # 2. Konfigurasi Input dan Output lokasi GCS
    gcs_document = documentai.GcsDocument(gcs_uri=GCS_INPUT_URI, mime_type="application/pdf")
    input_config = documentai.BatchDocumentsInputConfig(gcs_documents=documentai.GcsDocuments(documents=[gcs_document]))
    output_config = documentai.DocumentOutputConfig(
        gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(gcs_uri=GCS_OUTPUT_PREFIX)
    )

    # 3. Kirim Request Batch Processing
    request = documentai.BatchProcessRequest(
        name=processor_path,
        input_documents=input_config,
        document_output_config=output_config,
    )
    
    logger.info(f"Mengirim request batch process untuk: {GCS_INPUT_URI}")
    operation = docai_client.batch_process_documents(request=request)
    
    logger.info(f"Menunggu operasi selesai (ID: {operation.operation.name})...")
    operation.result(timeout=600)
    logger.info("Operasi Document AI selesai dengan sukses.")

    # 4. Membaca semua shard JSON hasil output dari GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    logger.debug("Mencari file JSON hasil output di prefix: batch_output/")
    blobs = bucket.list_blobs(prefix="batch_output/")
    
    full_text = ""
    shard_count = 0
    
    # PERBAIKAN: Hanya cek apakah file berakhiran .json saja
    for blob in blobs:
        if blob.name.endswith(".json"):
            shard_count += 1
            logger.debug(f"Membaca file JSON hasil: {blob.name}")
            json_content = blob.download_as_string().decode("utf-8")
            
            # Parse JSON menjadi objek Document AI
            document = documentai.Document.from_json(json_content, ignore_unknown_fields=True)
            
            # Gabungkan teks
            full_text += document.text

    logger.info(f"📊 Total file JSON yang digabungkan: {shard_count}")
    logger.info(f"📝 Total teks yang diekstrak: {len(full_text)} karakter")
    
    # 5. Mengunggah teks gabungan utuh menjadi file .txt ke GCS
    logger.info(f"Menyimpan hasil akhir ke gs://{BUCKET_NAME}/{FINAL_OUTPUT_FILE}")
    output_blob = bucket.blob(FINAL_OUTPUT_FILE)
    output_blob.upload_from_string(full_text, content_type="text/plain")
    
    logger.info("--- Batch OCR Selesai ---")

if __name__ == "__main__":
    main()
