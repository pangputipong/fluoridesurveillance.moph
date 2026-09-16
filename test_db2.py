import pymysql
import os

from dotenv import load_dotenv
load_dotenv()

# We can query the database directly using Railway's database URL.
# Wait, let's see how app.py connects.
with open('app.py', 'r', encoding='utf-8') as f:
    for line in f.readlines():
        if 'sqlalchemy' in line.lower() or 'create_engine' in line or 'DATABASE_URL' in line:
            print(line.strip())
