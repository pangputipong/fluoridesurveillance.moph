from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

try:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://fluoridesurveillancemoph-production.up.railway.app/dashboard')
    
    # Wait for page to load
    time.sleep(3)
    
    # Click แหล่งน้ำดิบ
    menu = driver.find_element(By.CSS_SELECTOR, "a[data-type='แหล่งน้ำดิบ']")
    menu.click()
    
    # Wait for map to render
    time.sleep(5)
    
    driver.save_screenshot('map_screenshot.png')
    print("Screenshot saved to map_screenshot.png")
    
    # Check if there are markers on the map
    markers = driver.find_elements(By.CSS_SELECTOR, ".leaflet-marker-icon")
    print(f"Number of markers: {len(markers)}")
    
    driver.quit()
except Exception as e:
    print(f"Error: {e}")
