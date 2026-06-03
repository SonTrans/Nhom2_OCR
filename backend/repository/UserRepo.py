from backend.database import connection

def create_user_repo(username, password):

    conn, cursor = connection.get_connection()

    query = """
    INSERT INTO users (username, password)
    VALUES (%s, %s)
    RETURNING id;
    """

    cursor.execute(query, (username, password))

    user_id = cursor.fetchone()[0]

    conn.commit()

    connection.close_connection(conn, cursor)

    return user_id


def get_user_by_username(username):

    conn, cursor = connection.get_connection()

    query = """
    SELECT id, username, password
    FROM users
    WHERE username = %s;
    """

    cursor.execute(query, (username,))

    row = cursor.fetchone()

    connection.close_connection(conn, cursor)

    if row is None:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password": row[2]
    }