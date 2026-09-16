import requests
import json
import urllib3
urllib3.disable_warnings()

try:
    url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/get_schemas'
    res = requests.get(url, verify=False)
    if res.status_code == 200:
        data = res.json()
        schema = data.get('data', {}).get('แหล่งน้ำประปา', {})
        print(json.dumps(schema, ensure_ascii=False, indent=2))
    else:
        print(f"Error: {res.status_code}")
except Exception as e:
    print(e)
