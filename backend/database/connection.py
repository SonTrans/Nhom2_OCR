import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database="receipt_ocr",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD"),
        port=5432
    )

    cursor = conn.cursor()

    return conn, cursor


def close_connection(conn, cursor):
    cursor.close()
    conn.close()