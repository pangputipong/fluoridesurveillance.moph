import sys

with open(r'C:\Users\HP-255G10-R5-2-001\Desktop\fluoride-dashboard\static\js\dashboard.js', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('.map-layer-toggle:checked:visible', '.map-layer-toggle:checked')

with open(r'C:\Users\HP-255G10-R5-2-001\Desktop\fluoride-dashboard\static\js\dashboard.js', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced successfully.")
