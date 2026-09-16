import json
import urllib3
import requests
urllib3.disable_warnings()

url_get = 'https://fluoridesurveillancemoph-production.up.railway.app/api/get_schemas'
res_get = requests.get(url_get, verify=False)
data = res_get.json().get('data', {})
schema = data.get('แหล่งน้ำประปา', {})

if not schema:
    print("Schema not found!")
    exit()

# Update config
schema['config']['drilldown'] = "จังหวัด"
schema['config']['proportion'] = "ปริมาณฟลูออไรด์"
schema['config']['proportion_rules'] = [
    {"op": "<=", "val1": 0.7, "val2": "", "label": "น้อยกว่าหรือเท่ากับ 0.7 mg/L (ปลอดภัย)"},
    {"op": "between", "val1": 0.7, "val2": 1.5, "label": "0.7 - 1.5 mg/L (เฝ้าระวัง)"},
    {"op": ">", "val1": 1.5, "val2": "", "label": "มากกว่า 1.5 mg/L (เกินเกณฑ์)"}
]
schema['config']['map_colors'] = [
    {"min": 0, "max": 0.7, "color": "#10b981"},      # Green
    {"min": 0.71, "max": 1.5, "color": "#f59e0b"},   # Yellow/Orange
    {"min": 1.51, "max": 99, "color": "#ef4444"}     # Red
]
schema['config']['map'] = "ปริมาณฟลูออไรด์"

# Update fields to ensure water_type is not a formula
for f in schema['fields']:
    if f['db_ref'] == 'water_type':
        f['type'] = 'DB_Column'
        f['formula'] = ''

payload = {
    "report_name": "แหล่งน้ำประปา",
    "category": "env",
    "schema_data": {
        "fields": schema['fields'],
        "config": schema['config']
    }
}

url_save = 'https://fluoridesurveillancemoph-production.up.railway.app/api/save_schema'
headers = {'Content-Type': 'application/json'}
res_save = requests.post(url_save, json=payload, headers=headers, verify=False)
print(res_save.json())
