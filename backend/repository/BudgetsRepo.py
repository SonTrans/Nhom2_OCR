from backend.database import connection

from backend.database import connection

def create_budget_repo(user_id, start_date, end_date, budget, total_amount):

    conn, cursor = connection.get_connection()

    query = """
    INSERT INTO budgets (
        user_id,
        start_date,
        end_date,
        budget,
        total_amount
    )
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
    """

    cursor.execute(query, (
        user_id,
        start_date,
        end_date,
        budget,
        total_amount
    ))

    budget_id = cursor.fetchone()[0]

    conn.commit()

    connection.close_connection(conn, cursor)

    return budget_id


def get_all_budgets():

    conn, cursor = connection.get_connection()

    query = "SELECT * FROM budgets;"

    cursor.execute(query)

    budgets = cursor.fetchall()

    connection.close_connection(conn, cursor)

    return budgets

def get_all_budgets_by_user_id(user_id):

    conn, cursor = connection.get_connection()

    query = "SELECT * FROM budgets WHERE user_id = %s;"

    cursor.execute(query, (user_id,))

    budgets = cursor.fetchall()

    connection.close_connection(conn, cursor)

    return budgets


