import pymysql
import os

from dotenv import load_dotenv
load_dotenv()

db_url = os.getenv('MYSQL_URL') or os.getenv('DATABASE_URL') or os.getenv('DB_URI')
if not db_url:
    print('DB URL not found')
    # Try looking in app.py directly
    with open('app.py', 'r', encoding='utf-8') as f:
        for line in f.readlines():
            if 'getenv' in line and ('mysql' in line.lower() or 'db' in line.lower() or 'url' in line.lower()):
                print(line.strip())
