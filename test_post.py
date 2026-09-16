import requests
import json
import urllib3
urllib3.disable_warnings()

url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/data'
res = requests.post(url, json={'report_name': 'แหล่งน้ำบริโภค'}, verify=False)
data = res.json()

print(f"Total rows returned: {len(data.get('data', []))}")
schema = data.get('schema', {})
print(f"Schema config: {json.dumps(schema.get('config', {}), ensure_ascii=False)}")
