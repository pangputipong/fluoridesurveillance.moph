import json
import urllib3
import requests
urllib3.disable_warnings()
s = requests.Session()
payload = {
    'type': 'แหล่งน้ำบริโภค',
    'ปี': 'ทั้งหมด',
    'ภาค': 'ทั้งหมด',
    'เขตสุขภาพ': 'ทั้งหมด',
    'จังหวัด': 'ทั้งหมด',
    'อำเภอ': 'ทั้งหมด',
    'ตำบล': 'ทั้งหมด'
}
res = s.post('https://fluoridesurveillancemoph-production.up.railway.app/api/data', json=payload, verify=False)
data = res.json()
print("get_data length:", len(data.get('table_data', [])))
print("kpis:", len(data.get('kpis', [])))
if len(data.get('table_data', [])) > 0:
    print(data['table_data'][0])
