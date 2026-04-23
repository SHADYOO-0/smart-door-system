import mysql.connector
import web_config
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=web_config.DB_HOST,
            user=web_config.DB_USER,
            password=web_config.DB_PASSWORD,
            database=web_config.DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def get_user_by_name(username):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, password, status, email FROM person WHERE name = %s", (username,))
        user = cursor.fetchone()
        return user
    except mysql.connector.Error as err:
        print(f"Error fetching user by name: {err}")
        return None
    finally:
        if conn.is_connected():
            conn.close()

def check_password(hashed_password, plain_password):
    return bcrypt.check_password_hash(hashed_password, plain_password)

def update_user_password(user_id, new_password):
    conn = get_db_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    hashed_new_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    try:
        cursor.execute("UPDATE person SET password = %s WHERE id = %s", (hashed_new_password, user_id))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error updating password: {err}")
        conn.rollback()
        return False
    finally:
        if conn.is_connected():
            conn.close()

def get_all_visit_logs():
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    logs = []
    try:
        sql = """
            SELECT vl.id, p.name as person_name, vl.visit_date
            FROM visits_log vl
            JOIN person p ON vl.person_id = p.id
            ORDER BY vl.visit_date DESC
        """
        cursor.execute(sql)
        logs = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error fetching visit logs: {err}")
    finally:
        if conn.is_connected():
            conn.close()
    return logs

def hash_existing_passwords_in_db():
    conn = get_db_connection()
    if not conn:
        print("Could not connect to DB for hashing.")
        return
    cursor = conn.cursor(dictionary=True)
    update_cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, password FROM person")
        users = cursor.fetchall()
        updated_count = 0
        for user in users:
            if user['password'] and not user['password'].startswith('$2b$'):
                hashed_pw = bcrypt.generate_password_hash(user['password']).decode('utf-8')
                update_cursor.execute("UPDATE person SET password = %s WHERE id = %s", (hashed_pw, user['id']))
                print(f"Updated password for user ID {user['id']}")
                updated_count +=1
        conn.commit()
        print(f"Finished hashing. Updated {updated_count} passwords.")
    except mysql.connector.Error as err:
        print(f"Error hashing passwords: {err}")
        conn.rollback()
    finally:
        if conn.is_connected():
            conn.close()

# (ONLY RUN ONCE and CAREFULLY)
# if __name__ == '__main__':
#     print("ATTENTION: This will attempt to hash existing passwords in the database.")
#     confirm = input("Are you sure you want to proceed? (yes/no): ")
#     if confirm.lower() == 'yes':
#         hash_existing_passwords_in_db()
#     else:
#         print("Operation cancelled.")