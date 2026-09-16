import os

file = 'templates/index.html'
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('dashboard.js?v=3.9', 'dashboard.js?v=3.10')

with open(file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated {file}")
