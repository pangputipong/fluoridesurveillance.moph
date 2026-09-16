import os
import re

files = [
    'templates/index.html',
    'templates/landing.html',
    'templates/knowledge.html',
    'templates/community.html'
]

for file in files:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace /static/ with {{ BASE_URL }}/static/
        content = content.replace('href="/static/', 'href="{{ BASE_URL }}/static/')
        content = content.replace('src="/static/', 'src="{{ BASE_URL }}/static/')
        
        # Ensure we inject the BASE_URL global var in index.html right before dashboard.js is loaded
        # But wait, it's safer to just inject it at the beginning of the <head> or right before </body>
        # Let's inject it into the <head>
        if '<head>' in content and '<script>const BASE_URL' not in content:
            content = content.replace('<head>', '<head>\n    <script>const BASE_URL = "{{ BASE_URL }}";</script>')
            
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")
