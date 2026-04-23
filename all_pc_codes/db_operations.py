import mysql.connector
import numpy as np
import datetime
import time
import config
from flask_bcrypt import Bcrypt

bcrypt_rpi = Bcrypt()

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def find_person_by_descriptor(descriptor_to_check):
    conn = get_db_connection()
    if not conn:
        return None, None, None, None

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, face_descriptor, status, num_visits FROM person")
    persons = cursor.fetchall()
    conn.close()

    min_dist = float('inf')
    matched_person = None

    descriptor_to_check_np = np.array(descriptor_to_check)

    for person in persons:
        if person['face_descriptor']:
            db_descriptor_np = np.frombuffer(person['face_descriptor'], dtype=np.float64)
            dist = np.linalg.norm(db_descriptor_np - descriptor_to_check_np)
            if dist < min_dist:
                min_dist = dist
                matched_person = person
    
    if matched_person and min_dist < config.FACE_RECOGNITION_THRESHOLD:
        return matched_person['id'], matched_person['name'], matched_person['status'], matched_person['num_visits']
    return None, None, None, None


def add_person(name, face_descriptor, status="guest", num_visits=1, email=None):
    """Adds a new person to the database with a hashed placeholder password."""
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    
    descriptor_bytes = np.array(face_descriptor).astype(np.float64).tobytes()

    placeholder_password_plain = f"RPi_Generated_User_Pass_{name}_{time.time()}"
    hashed_default_password = bcrypt_rpi.generate_password_hash(placeholder_password_plain).decode('utf-8')

    sql = "INSERT INTO person (name, face_descriptor, status, num_visits, email, password) VALUES (%s, %s, %s, %s, %s, %s)"
    val = (name, descriptor_bytes, status, num_visits, email, hashed_default_password)
    try:
        cursor.execute(sql, val)
        conn.commit()
        person_id = cursor.lastrowid
        print(f"Added new person {name} with ID: {person_id}, password hashed.")
        return person_id
    except mysql.connector.Error as err:
        print(f"Error adding person: {err}")
        conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()

def get_owner_emails():
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT email FROM person WHERE status = 'owner' AND email IS NOT NULL AND email != ''")
        owners = cursor.fetchall()
        return [owner['email'] for owner in owners]
    except mysql.connector.Error as err:
        print(f"Error getting owner emails: {err}")
        return []
    finally:
        conn.close()

def log_visit(person_id):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO visit_logs (person_id) VALUES (%s)", (person_id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error logging visit: {err}")
    finally:
        conn.close()

def update_person_visits_and_status(person_id, num_visits, status=None):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        if status:
            cursor.execute("UPDATE person SET num_visits = %s, status = %s WHERE id = %s", (num_visits, status, person_id))
        else:
            cursor.execute("UPDATE person SET num_visits = %s WHERE id = %s", (num_visits, person_id))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error updating person visits/status: {err}")
    finally:
        conn.close()

def reset_monthly_guest_visits():
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE person SET num_visits = 0 WHERE status = 'guest'")
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error resetting monthly guest visits: {err}")
    finally:
        conn.close()