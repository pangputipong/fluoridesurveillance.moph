import sqlite3
import os

# Wait, is it MySQL or SQLite?
# App uses MySQL. Let's see the app.py configuration for connection.
with open('app.py', 'r', encoding='utf-8') as f:
    for line in f.readlines():
        if 'water_records' in line or 'latitude' in line or 'longitude' in line or 'lat' in line or 'lon' in line:
            print(line.strip())
