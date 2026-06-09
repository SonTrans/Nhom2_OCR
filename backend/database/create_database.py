import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
# Kết nối vào database mặc định postgres
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    database="postgres",
    user="postgres",
    password=os.getenv("POSTGRES_PASSWORD"),
    port=5432
)

conn.autocommit = True

cursor = conn.cursor()

# Tạo database
cursor.execute("CREATE DATABASE receipt_ocr")

cursor.close()
conn.close()