import json

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

migration_code = '''
            # MIGRATION: Force update schema for 3 water reports
            water_reports = ['แหล่งน้ำดิบ', 'แหล่งน้ำประปา', 'แหล่งน้ำบริโภค']
            for wr in water_reports:
                row = conn.execute(text("SELECT schema_data FROM report_schemas WHERE report_name = :n"), {"n": wr}).fetchone()
                if row:
                    try:
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
                    except Exception as e:
                        pass
'''

insert_point = content.find('print("\u2714\ufe0f \u0e15\u0e32\u0e23\u0e32\u0e07\u0e10\u0e32\u0e19\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e1e\u0e23\u0e49\u0e2d\u0e21\u0e43\u0e0a\u0e49\u0e07\u0e32\u0e19")')
if insert_point != -1:
    new_content = content[:insert_point] + migration_code + '\n            ' + content[insert_point:]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Migration injected into app.py")
else:
    print("Could not find insertion point")
