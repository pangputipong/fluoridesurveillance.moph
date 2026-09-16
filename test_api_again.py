import json
import urllib3
import requests
urllib3.disable_warnings()
s = requests.Session()
res = s.post('https://fluoridesurveillancemoph-production.up.railway.app/api/data', json={"report_name": "แหล่งน้ำบริโภค", "filters": {}}, verify=False)
data = res.json()
print("get_data length:", len(data.get('data', [])))

res2 = s.post('https://fluoridesurveillancemoph-production.up.railway.app/api/table_data', json={"report_name": "แหล่งน้ำบริโภค", "filters": {}}, verify=False)
print("get_table_data:", str(res2.text)[:200])
