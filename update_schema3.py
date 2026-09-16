import json
import urllib3
import requests
urllib3.disable_warnings()

s = requests.Session()

# Login
url_login = 'https://fluoridesurveillancemoph-production.up.railway.app/api/login'
res_login = s.post(url_login, json={'username': 'admin', 'password': 'admin'}, verify=False)

if not res_login.json().get('success'):
    print("Login failed:", res_login.json())
    exit()

print("Login success!")

url_get = 'https://fluoridesurveillancemoph-production.up.railway.app/api/get_schemas'
res_get = s.get(url_get, verify=False)
data = res_get.json().get('data', {})
schema = data.get('แหล่งน้ำประปา', {})

if not schema:
    print("Schema not found!")
    exit()

# Update config
schema['config']['drilldown'] = "จังหวัด"
schema['config']['proportion'] = "ปริมาณฟลูออไรด์"
schema['config']['proportion_rules'] = [
    {"op": "<=", "val1": 0.7, "val2": "", "label": "ปลอดภัย (<= 0.7 mg/L)"},
    {"op": "between", "val1": 0.7001, "val2": 1.5, "label": "เฝ้าระวัง (0.7 - 1.5 mg/L)"},
    {"op": ">", "val1": 1.5, "val2": "", "label": "เกินเกณฑ์ (> 1.5 mg/L)"}
]
schema['config']['map_colors'] = [
    {"min": 0, "max": 0.7, "color": "#10b981"},      # Green
    {"min": 0.7001, "max": 1.5, "color": "#f59e0b"}, # Yellow/Orange
    {"min": 1.5001, "max": 99, "color": "#ef4444"}   # Red
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
res_save = s.post(url_save, json=payload, headers=headers, verify=False)
print("Save result:", res_save.json())
