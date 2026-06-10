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
# ⚠️ PASTIKAN MENGGUNAKAN ID PROCESSOR "FORM PARSER" KAMU
PROCESSOR_ID = "c2b088f3cf12be83" 
LOCATION = "us" 
BUCKET_NAME = "qwiklabs-gcp-04-5027a4f721c0-cepf-documentai"

INPUT_BLOB_NAME = "sample-form-with-table.pdf"
FINAL_OUTPUT_FILE = "sample-form-with-table-tb0.csv"

def get_text(text_anchor, document_text):
    """Helper untuk mengambil teks berdasarkan rentang indeks (text anchor)"""
    if not text_anchor.text_segments:
        return ""
    response = ""
    for segment in text_anchor.text_segments:
        start_index = segment.start_index
        end_index = segment.end_index
        response += document_text[start_index:end_index]
    return response.strip().replace("\n", " ")

def main():
    logger.info("Memulai ekstraksi tabel menggunakan Form Parser...")
    
    # 1. Download dokumen PDF dari GCS ke memori
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    logger.info(f"Mendownload {INPUT_BLOB_NAME} dari bucket...")
    blob = bucket.blob(INPUT_BLOB_NAME)
    file_bytes = blob.download_as_bytes()

    # 2. Inisialisasi Document AI Client
    opts = ClientOptions(api_endpoint=f"{LOCATION}-documentai.googleapis.com")
    docai_client = documentai.DocumentProcessorServiceClient(client_options=opts)
    processor_path = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

    # 3. Kirim request pemrosesan online
    raw_document = documentai.RawDocument(content=file_bytes, mime_type="application/pdf")
    request = documentai.ProcessRequest(name=processor_path, raw_document=raw_document)
    
    logger.info("Mengirim dokumen ke Document AI API...")
    result = docai_client.process_document(request=request)
    document = result.document
    logger.info("Dokumen berhasil diproses.")

    # 4. Ekstrak data dari tabel pertama (tb0) yang ditemukan
    header_columns = []
    table_rows = []
    table_found = False

    for page in document.pages:
        for table in page.tables:
            logger.info("Tabel ditemukan! Mengekstrak susunan kolom dan baris...")
            
            # Ekstrak baris Header
            for header_row in table.header_rows:
                header_columns = [
                    get_text(cell.layout.text_anchor, document.text) 
                    for cell in header_row.cells
                ]
            logger.debug(f"Header Kolom: {header_columns}")

            # Ekstrak baris Body
            for body_row in table.body_rows:
                row_data = [
                    get_text(cell.layout.text_anchor, document.text) 
                    for cell in body_row.cells
                ]
                table_rows.append(row_data)
                logger.debug(f"Baris Data: {row_data}")
            
            table_found = True
            break # Keluar setelah mengambil tabel pertama (tb0)
        if table_found:
            break

    if not table_found:
        logger.error("❌ Tidak ada tabel yang terdeteksi di dalam dokumen ini.")
        return

    # 5. Konversi data menjadi Pandas DataFrame dan buat format CSV
    logger.info("Menyusun data ke dalam Pandas DataFrame...")
    df = pd.DataFrame(table_rows, columns=header_columns if header_columns else None)
    csv_data = df.to_csv(index=False)

    # 6. Upload file CSV hasil akhir ke GCS Bucket
    logger.info(f"Menyimpan hasil ke gs://{BUCKET_NAME}/{FINAL_OUTPUT_FILE}...")
    output_blob = bucket.blob(FINAL_OUTPUT_FILE)
    output_blob.upload_from_string(csv_data, content_type="text/csv")
    
    logger.info("--- Ekstraksi Tabel Selesai ---")

if __name__ == "__main__":
    main()
