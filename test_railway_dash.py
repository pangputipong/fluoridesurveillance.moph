import requests
import urllib3
urllib3.disable_warnings()

try:
    url = 'https://fluoridesurveillancemoph-production.up.railway.app/dashboard'
    res = requests.get(url, verify=False)
    print(f"Status: {res.status_code}")
except Exception as e:
    print(e)
