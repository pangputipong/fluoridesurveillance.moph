import requests
import urllib3
urllib3.disable_warnings()

try:
    url_data = 'https://fluoridesurveillancemoph-production.up.railway.app/api/schemas'
    res = requests.get(url_data, verify=False)
    if res.status_code == 200:
        data = res.json()
        schema = data.get('แหล่งน้ำประปา', {})
        print(f"Category: {schema.get('category')}")
    else:
        print(f"Error: {res.status_code}")
except Exception as e:
    print(e)
