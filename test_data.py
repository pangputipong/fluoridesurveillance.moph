import requests
import json
import urllib3
urllib3.disable_warnings()

try:
    url_data = 'https://fluoridesurveillancemoph-production.up.railway.app/api/data'
    res = requests.post(url_data, json={"type": "แหล่งน้ำประปา"}, verify=False)
    if res.status_code == 200:
        data = res.json()
        td = data.get('table_data', [])
        print(f"Total: {len(td)}")
        if len(td) > 0:
            print("Row 0:", json.dumps(td[0], ensure_ascii=False))
            print("Row 0 fluoride:", td[0].get("ปริมาณฟลูออไรด์"))
            print("Row 0 lat:", td[0].get("ละติจูด"))
            print("Row 0 lon:", td[0].get("ลองจิจูด"))
    else:
        print(f"Error /api/data: {res.status_code}")
except Exception as e:
    print(e)
