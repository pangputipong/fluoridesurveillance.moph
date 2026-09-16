import json
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# find index of @app.route('/api/migrate_water
idx = content.find('@app.route(' + "'" + '/api/migrate_water' + "'")
if idx != -1:
    content = content[:idx]

code = '''
@app.route('/api/migrate_water', methods=['GET'])
def migrate_water():
    import json
    water_reports = ['แหล่งน้ำดิบ', 'แหล่งน้ำประปา', 'แหล่งน้ำบริโภค']
    try:
        with engine.begin() as conn:
            for wr in water_reports:
                row = conn.execute(text("SELECT schema_data FROM report_schemas WHERE report_name = :n"), {"n": wr}).fetchone()
                if row:
                    schema_data = json.loads(row[0])
                    config = schema_data.get('config', {})
                    config['drilldown'] = 'จังหวัด'
                    config['proportion'] = 'ปริมาณฟลูออไรด์'
                    config['map'] = 'ปริมาณฟลูออไรด์'
                    config['proportion_rules'] = [
                        {"op": "<=", "val1": 0.7, "val2": "", "label": "ปลอดภัย (<= 0.7 mg/L)"},
                        {"op": "between", "val1": 0.7001, "val2": 1.5, "label": "เฝ้าระวัง (0.7 - 1.5 mg/L)"},
                        {"op": ">", "val1": 1.5, "val2": "", "label": "เกินเกณฑ์ (> 1.5 mg/L)"}
                    ]
                    config['map_colors'] = [
                        {"min": 0, "max": 0.7, "color": "#10b981"},
                        {"min": 0.7001, "max": 1.5, "color": "#f59e0b"},
                        {"min": 1.5001, "max": 99, "color": "#ef4444"}
                    ]
                    schema_data['config'] = config
                    conn.execute(text("UPDATE report_schemas SET schema_data = :sd WHERE report_name = :n"), {"sd": json.dumps(schema_data, ensure_ascii=False), "n": wr})
        return "Migration complete!"
    except Exception as e:
        return str(e)
'''

content += code

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
