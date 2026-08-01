import os
from db import get_connection

def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    print(f"Reading schema from {schema_path}")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
        
    print("Connecting to database...")
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return

    try:
        with conn.cursor() as cur:
            print("Executing schema.sql...")
            cur.execute(schema_sql)
        conn.commit()
        print("Database initialization successful.")
    except Exception as e:
        print(f"An error occurred while executing the schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
