from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

try:
    driver.get('http://127.0.0.1:5000/')
    time.sleep(1)
    driver.execute_script("sessionStorage.setItem('userRole', 'admin'); sessionStorage.setItem('isLoggedIn', 'true');")
    
    driver.get('http://127.0.0.1:5000/dashboard')
    time.sleep(2)
    
    driver.execute_script("document.querySelectorAll('.report-item')[3].click();")
    time.sleep(3)
    
    markers = driver.execute_script("return document.querySelectorAll('.leaflet-marker-icon').length;")
    print('Markers:', markers)
    
    debug = driver.execute_script('''
        var checkedStatuses = [];
        var nodes = document.querySelectorAll('.map-layer-toggle:checked');
        for(var i=0; i<nodes.length; i++){
            checkedStatuses.push(nodes[i].value);
        }
        return {
            checked: checkedStatuses, 
            legendHtml: document.getElementById('legend-dynamic').innerHTML,
            counts: typeof globalData !== 'undefined' ? globalData.length : 0,
            hasMap: typeof activeChartConfig !== 'undefined' ? activeChartConfig.map : 'undefined',
            isWater: typeof existingSchemas !== 'undefined' && existingSchemas[currentType] ? existingSchemas[currentType].category : 'undefined'
        };
    ''')
    print('Debug:', json.dumps(debug, ensure_ascii=False))
except Exception as e:
    print(e)
finally:
    driver.quit()
