import requests
import json
import urllib3
urllib3.disable_warnings()

url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/get_schemas'
res = requests.get(url, verify=False)
data = res.json()
print("แหล่งน้ำบริโภค category:", data.get('data', {}).get('แหล่งน้ำบริโภค', {}).get('category'))
print("แหล่งน้ำดิบ category:", data.get('data', {}).get('แหล่งน้ำดิบ', {}).get('category'))
print("แหล่งน้ำประปา category:", data.get('data', {}).get('แหล่งน้ำประปา', {}).get('category'))
