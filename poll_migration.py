import requests
import time
import urllib3
urllib3.disable_warnings()

url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/migrate_water'
print(f"Polling {url} ...")
for i in range(30):
    try:
        res = requests.get(url, verify=False, timeout=5)
        print(f"Attempt {i+1}: Status {res.status_code} - {res.text[:50]}")
        if res.status_code == 200 and 'Migration complete' in res.text:
            print("SUCCESS! Migration is done.")
            break
    except Exception as e:
        print(f"Attempt {i+1} failed: {e}")
    time.sleep(10)
