import requests
import json
import urllib3
urllib3.disable_warnings()

url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/data?report_name=แหล่งน้ำบริโภค'
res = requests.get(url, verify=False)
print("STATUS CODE:", res.status_code)
print("RESPONSE TEXT HEAD:", res.text[:200])
