import mysql.connector
import config

def fix_database():
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        cursor = conn.cursor()
        
        # Create the correct table that db_operations.py expects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS person (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                face_descriptor LONGBLOB,
                status VARCHAR(50) DEFAULT 'guest',
                num_visits INT DEFAULT 0,
                email VARCHAR(255),
                password VARCHAR(255)
            )
        """)
        
        # Also let's create visits_log just in case it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                person_id INT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (person_id) REFERENCES person(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        print("Database schema fixed successfully! Tables are ready.")
        conn.close()
    except Exception as e:
        print(f"Error fixing database: {e}")

if __name__ == "__main__":
    fix_database()
