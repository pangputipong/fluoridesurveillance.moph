import requests
import time
import urllib3
urllib3.disable_warnings()
url = 'https://fluoridesurveillancemoph-production.up.railway.app/dashboard'

for _ in range(30):
    try:
        res = requests.get(url, verify=False)
        if 'v=3.6' in res.text:
            print('Railway deployed successfully!')
            break
        else:
            print('Still waiting...')
    except:
        pass
    time.sleep(5)
