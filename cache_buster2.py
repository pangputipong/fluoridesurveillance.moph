import sys

with open(r'C:\Users\HP-255G10-R5-2-001\Desktop\fluoride-dashboard\templates\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('dashboard.js?v=3.4', 'dashboard.js?v=3.5')

with open(r'C:\Users\HP-255G10-R5-2-001\Desktop\fluoride-dashboard\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(content)
