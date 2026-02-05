import psycopg2
import sys

try:
    conn = psycopg2.connect(
        dbname="healchain",
        user="postgres",
        password="Varun@2210121314",
        host="localhost",
        port="5432"
    )
    print("✅ Successfully connected to the database!")
    conn.close()
except Exception as e:
    print(f"❌ Failed to connect to the database: {e}")
    sys.exit(1)
