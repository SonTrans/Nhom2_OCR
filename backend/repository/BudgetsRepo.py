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


def get_current_budget_by_user_id(user_id, current_date):

    conn, cursor = connection.get_connection()

    query = "SELECT * FROM budgets WHERE user_id = %s AND start_date <= %s AND end_date >= %s ORDER BY start_date DESC LIMIT 1;"

    cursor.execute(query, (user_id, current_date, current_date))

    budget = cursor.fetchone()

    connection.close_connection(conn, cursor)

    return budget


def get_current_budgets_by_user_id(user_id, current_date):

    conn, cursor = connection.get_connection()

    query = "SELECT * FROM budgets WHERE user_id = %s AND start_date <= %s AND end_date >= %s;"

    cursor.execute(query, (user_id, current_date, current_date))

    budgets = cursor.fetchall()

    connection.close_connection(conn, cursor)

    return budgets


def update_budget_totals_by_date_range(user_id, amount, current_date):

    conn, cursor = connection.get_connection()

    query = "UPDATE budgets SET total_amount = COALESCE(total_amount, 0) + %s WHERE user_id = %s AND start_date <= %s AND end_date >= %s RETURNING *;"

    cursor.execute(query, (amount, user_id, current_date, current_date))

    updated_budgets = cursor.fetchall()

    conn.commit()

    connection.close_connection(conn, cursor)

    return updated_budgets


def update_budget_total_by_id(budget_id, total_amount):

    conn, cursor = connection.get_connection()

    query = "UPDATE budgets SET total_amount = %s WHERE id = %s RETURNING *;"

    cursor.execute(query, (total_amount, budget_id))

    updated_budget = cursor.fetchone()

    conn.commit()

    connection.close_connection(conn, cursor)

    return updated_budget


