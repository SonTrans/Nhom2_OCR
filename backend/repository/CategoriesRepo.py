from backend.database import connection

def create_category(name):

    conn, cursor = connection.get_connection()

    query = """
    INSERT INTO categories (name)
    VALUES (%s)
    RETURNING id;
    """

    cursor.execute(query, (name,))

    category_id = cursor.fetchone()[0]

    conn.commit()

    connection.close_connection(conn, cursor)

    return category_id

