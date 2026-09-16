import requests
import json
import urllib3
urllib3.disable_warnings()

url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/get_schemas'
res = requests.get(url, verify=False)
data = res.json()
print("Keys:", list(data.get('data', {}).keys()))
for k in ['แหล่งน้ำดิบ', 'แหล่งน้ำประปา', 'แหล่งน้ำบริโภค']:
    print(f"{k} config:", json.dumps(data.get('data', {}).get(k, {}).get('config', {}), ensure_ascii=False))
