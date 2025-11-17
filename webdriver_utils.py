import os, logging, random, time, platform, proxies
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_edge_driver(headless=True, user_agent=None, proxy=None):
    opts = Options()
    if headless: opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-dev-shm-usage")
    if user_agent: opts.add_argument(f"user-agent={user_agent}")
    if proxy: opts.add_argument(f"--proxy-server={proxy}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    
    driver_path = os.path.join("webdrivers", "msedgedriver.exe") if os.path.exists(os.path.join("webdrivers", "msedgedriver.exe")) else None
    service = Service(executable_path=driver_path)
    
    driver = webdriver.Edge(service=service, options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def wait_for_element(driver, selector, by=By.CSS_SELECTOR, timeout=60): 
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))

def wait_for_elements(driver, selector, by=By.CSS_SELECTOR, timeout=60): 
    return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((by, selector)))

def get_element_safely(driver, selector, by=By.CSS_SELECTOR): 
    try: return driver.find_element(by, selector)
    except: return None

def get_elements_safely(driver, selector, by=By.CSS_SELECTOR): 
    try: return driver.find_elements(by, selector)
    except: return []

def random_delay(min_sec=1, max_sec=3): 
    time.sleep(random.uniform(min_sec, max_sec))

def get_random_proxy():
    return random.choice(proxies.PROXY_LIST) if hasattr(proxies, 'PROXY_LIST') and proxies.PROXY_LIST else None