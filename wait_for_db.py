import time
import os
import MySQLdb
import subprocess

host = os.getenv("MYSQL_HOST", "db")
port = int(os.getenv("MYSQL_PORT", "3306"))
user = os.getenv("MYSQL_USER", "admin")
password = os.getenv("MYSQL_PASSWORD", "admin")
database = os.getenv("MYSQL_DATABASE", "car_rental")

print("Waiting for MySQL...")

while True:
    try:
        conn = MySQLdb.connect(
            host=host, port=port, user=user, passwd=password, db=database
        )
        conn.close()
        print("MySQL is up - running migrations")
        break
    except Exception as e:
        print("Waiting for MySQL...", e)
        time.sleep(2)

# Run migrations
subprocess.run(["python", "manage.py", "migrate"])
