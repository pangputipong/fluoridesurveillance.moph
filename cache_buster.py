import sys

with open(r'C:\Users\HP-255G10-R5-2-001\Desktop\fluoride-dashboard\templates\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('src="/static/js/dashboard.js"', 'src="/static/js/dashboard.js?v=1.1"')

with open(r'C:\Users\HP-255G10-R5-2-001\Desktop\fluoride-dashboard\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated index.html cache buster.")
