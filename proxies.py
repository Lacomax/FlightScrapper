import requests, time, random
from concurrent.futures import ThreadPoolExecutor

PROXY_LIST = []
PROXY_FETCH_TIME = 0
PROXY_REFRESH_INTERVAL = 3600  # 1 hora

def fetch_free_proxies():
    global PROXY_LIST, PROXY_FETCH_TIME
    if time.time() - PROXY_FETCH_TIME < PROXY_REFRESH_INTERVAL and PROXY_LIST:
        return PROXY_LIST
    
    proxies = []
    try:
        r = requests.get("https://free-proxy-list.net/")
        lines = r.text.split("<tr><td>")
        for line in lines[1:]:
            try:
                parts = line.split("</td><td>")
                ip, port = parts[0], parts[1]
                if parts[6].startswith("yes"):  # Solo HTTPS proxies
                    proxies.append(f"{ip}:{port}")
            except: pass
    except: pass
    
    # Intentar fuentes alternativas si la principal falló
    if not proxies:
        try:
            r = requests.get("https://www.sslproxies.org/")
            lines = r.text.split("<tr><td>")
            for line in lines[1:]:
                try:
                    parts = line.split("</td><td>")
                    ip, port = parts[0], parts[1]
                    proxies.append(f"{ip}:{port}")
                except: pass
        except: pass
    
    # Filtrar proxies activos
    working_proxies = filter_working_proxies(proxies, max_workers=20)
    
    PROXY_LIST = working_proxies
    PROXY_FETCH_TIME = time.time()
    return working_proxies

def is_proxy_working(proxy, timeout=3):
    try:
        requests.get(
            "https://www.google.com", 
            proxies={"https": f"https://{proxy}"}, 
            timeout=timeout
        )
        return proxy
    except:
        return None

def filter_working_proxies(proxies, max_workers=10):
    if not proxies: return []
    working_proxies = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(is_proxy_working, proxies)
        working_proxies = [proxy for proxy in results if proxy]
    
    return working_proxies

# Auto-inicializar
fetch_free_proxies()