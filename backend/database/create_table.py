import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host="localhost",
    database="receipt_ocr",
    user="postgres",
    password=os.getenv("POSTGRES_PASSWORD"),
    port=5432
)

cursor = conn.cursor()
sql = """

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(100) NOT NULL
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE budgets (
    id SERIAL PRIMARY KEY,

    user_id INT NOT NULL,

    start_date DATE,
    end_date DATE,

    budget DECIMAL(12,2),
    total_amount DECIMAL(12,2),

    CONSTRAINT fk_budget_user
        FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE receipts (
    id SERIAL PRIMARY KEY,

    user_id INT NOT NULL,
    category_id INT,

    company_name VARCHAR(255),
    receipt_date DATE,
    total_amount DECIMAL(12,2),

    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_category
        FOREIGN KEY(category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL
);

"""

cursor.execute(sql)

conn.commit()

print("Tạo bảng thành công!")

cursor.close()
conn.close()