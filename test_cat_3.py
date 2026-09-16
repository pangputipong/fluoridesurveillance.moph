import requests
import json
import urllib3
urllib3.disable_warnings()

url = 'https://fluoridesurveillancemoph-production.up.railway.app/api/get_schemas'
res = requests.get(url, verify=False)
data = res.json()
print("สภาวะฟันตกกระ (เด็ก) config:", json.dumps(data.get('data', {}).get('สภาวะฟันตกกระ (เด็ก)', {}).get('config', {}), ensure_ascii=False))
