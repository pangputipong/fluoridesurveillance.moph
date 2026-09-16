import requests
import json
import urllib3
urllib3.disable_warnings()

url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/debug_load3'
res = requests.get(url, verify=False)
print("DB water_categories:", res.json())
