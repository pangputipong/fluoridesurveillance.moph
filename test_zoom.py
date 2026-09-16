with open('static/js/dashboard.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'flyToBounds(bounds' in line or 'flyToBounds(activeBounds' in line:
        print(f"Line {i+1}: {line.strip()}")
