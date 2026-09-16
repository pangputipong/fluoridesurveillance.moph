import os
import re

file = 'static/js/dashboard.js'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

# fetch('/api/ -> fetch(BASE_URL + '/api/
content = re.sub(r"fetch\(['\"]/api/", "fetch(BASE_URL + '/api/", content)
content = re.sub(r"fetch\(/api/", "fetch(BASE_URL + /api/", content)

# fetch('/static/ -> fetch(BASE_URL + '/static/
content = re.sub(r"fetch\(['\"]/static/", "fetch(BASE_URL + '/static/", content)
content = re.sub(r"fetch\(/static/", "fetch(BASE_URL + /static/", content)

# Some currentGeoUrl values might be hardcoded as '/static/...'
content = re.sub(r"currentGeoUrl = ['\"]/static/", "currentGeoUrl = BASE_URL + '/static/", content)

# Ensure cache busting is updated so clients reload the new JS
content = content.replace("?v=3.8", "?v=3.9")

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated {file}")
