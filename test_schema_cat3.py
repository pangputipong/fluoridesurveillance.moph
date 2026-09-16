import requests
import urllib3
import json
urllib3.disable_warnings()

try:
    url_data = 'https://fluoridesurveillancemoph-production.up.railway.app/api/get_schemas'
    res = requests.get(url_data, verify=False)
    if res.status_code == 200:
        data = res.json()
        schema = data.get('แหล่งน้ำประปา', {})
        print(json.dumps(schema.get('config', {}), indent=2))
    else:
        print(f"Error: {res.status_code}")
except Exception as e:
    print(e)
