import requests
import urllib3
urllib3.disable_warnings()

try:
    url_data = 'https://fluoridesurveillancemoph-production.up.railway.app/api/data'
    res = requests.post(url_data, json={"type": "ทั้งหมด"}, verify=False)
    if res.status_code == 200:
        data = res.json()
        td = data.get('table_data', [])
        print(f"Total: {len(td)}")
        for r in td:
            print(f"Lat: {r.get('ละติจูด')}, Lon: {r.get('ลองจิจูด')}")
    else:
        print(f"Error /api/data: {res.status_code}")
except Exception as e:
    print(e)
