import requests
import urllib3
urllib3.disable_warnings()

try:
    url_data = 'https://fluoridesurveillancemoph-production.up.railway.app/api/data'
    res = requests.post(url_data, json={"type": "แหล่งน้ำประปา"}, verify=False)
    if res.status_code == 200:
        data = res.json()
        td = data.get('table_data', [])
        print(f'Total records in /api/data for แหล่งน้ำประปา: {len(td)}')
        if len(td) > 0:
            print(f"Sample data keys: {list(td[0].keys())}")
    else:
        print(f"Error /api/data: {res.status_code}")
except Exception as e:
    print(e)
