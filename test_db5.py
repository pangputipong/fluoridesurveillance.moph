import pymysql
import os

print('Looking for columns...')
with open('app.py', 'r', encoding='utf-8') as f:
    for line in f.readlines():
        if 'INSERT INTO water_records' in line or 'water_category' in line or 'water_type' in line:
            print(line.strip())
