import requests
import urllib3
urllib3.disable_warnings()

try:
    url_data = 'https://fluoridesurveillancemoph-production.up.railway.app/api/data'
    res = requests.post(url_data, json={"type": "แหล่งน้ำประปา"}, verify=False)
    if res.status_code == 200:
        data = res.json()
        td = data.get('table_data', [])
        valid_coords = 0
        for r in td:
            lat = r.get('ละติจูด')
            lon = r.get('ลองจิจูด')
            if lat and lon:
                try:
                    float(lat)
                    float(lon)
                    valid_coords += 1
                except:
                    pass
        print(f"Total: {len(td)}, Valid coords: {valid_coords}")
    else:
        print(f"Error /api/data: {res.status_code}")
except Exception as e:
    print(e)
