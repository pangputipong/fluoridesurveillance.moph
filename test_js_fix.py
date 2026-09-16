import os

file = 'static/js/dashboard.js'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix DataTables ajax url
content = content.replace("url: '/api/table_data',", "url: BASE_URL + '/api/table_data',")
content = content.replace("?v=3.9", "?v=3.10")

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated {file}")
