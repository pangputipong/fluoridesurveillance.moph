import os
import glob

files = glob.glob('templates/*.html')

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace href="/..." with href="{{ BASE_URL }}/..."
    # But only if it's not already replaced and not /static or /api (we did /static already)
    # We should match href="/", href="/dashboard", href="/knowledge", href="/community"
    
    replacements = [
        ('href="/"', 'href="{{ BASE_URL }}/"'),
        ('href="/dashboard"', 'href="{{ BASE_URL }}/dashboard"'),
        ('href="/knowledge"', 'href="{{ BASE_URL }}/knowledge"'),
        ('href="/community"', 'href="{{ BASE_URL }}/community"')
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

print("Updated links in all HTML files.")
