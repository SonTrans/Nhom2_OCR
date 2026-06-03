from backend.database import connection

def create_receipt(
    user_id,
    category_id,
    company_name,
    receipt_date,
    total_amount
):

    conn, cursor = connection.get_connection()

    query = """
    INSERT INTO receipts (
        user_id,
        category_id,
        company_name,
        receipt_date,
        total_amount
    )
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
    """

    cursor.execute(query, (
        user_id,
        category_id,
        company_name,
        receipt_date,
        total_amount
    ))

    receipt_id = cursor.fetchone()[0]

    conn.commit()

    connection.close_connection(conn, cursor)

    return receipt_id

