import requests
import json
import urllib3
urllib3.disable_warnings()

s = requests.Session()
url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/data?report_name=แหล่งน้ำบริโภค'
res = s.get(url, verify=False)
data = res.json()

print(f"Total rows returned: {len(data.get('data', []))}")
if data.get('data'):
    print(f"Sample row: {data['data'][0]}")

schema = data.get('schema', {})
print(f"Schema config: {json.dumps(schema.get('config', {}), ensure_ascii=False)}")
