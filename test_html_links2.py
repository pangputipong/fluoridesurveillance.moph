import os
import glob

files = glob.glob('templates/*.html')

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    replacements = [
        ('href="/api/download_template/', 'href="{{ BASE_URL }}/api/download_template/'),
        ('href="/static/ICON_FLUORIDE.png"', 'href="{{ BASE_URL }}/static/ICON_FLUORIDE.png"')
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

print("Updated remaining hardcoded links in HTML files.")
