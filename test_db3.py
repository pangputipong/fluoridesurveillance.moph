import pymysql
import os

from dotenv import load_dotenv
load_dotenv()

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print('DATABASE_URL not found')
    exit()

# mysql://user:pass@host:port/dbname
import urllib.parse
parsed = urllib.parse.urlparse(db_url)
conn = pymysql.connect(
    host=parsed.hostname,
    port=parsed.port,
    user=parsed.username,
    password=parsed.password,
    database=parsed.path[1:],
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("DESCRIBE water_records")
for row in cursor.fetchall():
    print(row)

print('---')
cursor.execute("SELECT water_category, water_type, COUNT(*) FROM water_records GROUP BY water_category, water_type LIMIT 10")
for row in cursor.fetchall():
    print(row)

