import requests, logging, time
from datetime import datetime
from typing import Dict, List, Optional
from cachetools import TTLCache, cached

API_KEY = ""  # Obtén una en https://tequila.kiwi.com/portal/login
API_URL = "https://api.tequila.kiwi.com/v2/search"
CACHE = TTLCache(maxsize=1000, ttl=3600)

@cached(CACHE)
def search_flights(from_loc, to_loc, depart_date, return_date=None, adults=1, children=0, currency="EUR", max_stops=1):
    if not API_KEY: return None
    
    headers = {"apikey": API_KEY}
    params = {
        "fly_from": from_loc, "fly_to": to_loc,
        "date_from": _fmt_date(depart_date), "date_to": _fmt_date(depart_date),
        "adults": adults, "children": children, "curr": currency,
        "max_stopovers": max_stops, "limit": 10
    }
    
    if return_date:
        params.update({
            "return_from": _fmt_date(return_date), 
            "return_to": _fmt_date(return_date)
        })
    
    try:
        for _ in range(3):  # 3 intentos
            resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("data", [])
            elif resp.status_code == 429:  # Rate limit
                time.sleep(1)
            else:
                break
    except Exception as e:
        logging.debug(f"Kiwi API error: {e}")
    
    return None

def _fmt_date(date_str):
    fmt = "%d/%m/%Y" if "/" in date_str else "%Y-%m-%d"
    dt = datetime.strptime(date_str, fmt)
    return dt.strftime("%d/%m/%Y")

def get_cheapest_flight(from_loc, to_loc, depart_date, return_date=None):
    data = search_flights(from_loc, to_loc, depart_date, return_date)
    return min(data, key=lambda x: x.get("price", float("inf"))) if data else None

def extract_flights(kiwi_data):
    return [_parse_flight(f) for f in kiwi_data] if kiwi_data else []

def _parse_flight(flight):
    try:
        return {
            "Precio": str(flight.get("price", 0)),
            "Compañía": flight.get("airlines", ["Desconocida"])[0],
            "Origen": flight.get("flyFrom", ""),
            "Destino": flight.get("flyTo", ""),
            "Día": datetime.fromtimestamp(flight.get("dTime", 0)).strftime("%d/%m/%Y"),
            "Hora_Salida": datetime.fromtimestamp(flight.get("dTime", 0)).strftime("%H:%M"),
            "Hora_Llegada": datetime.fromtimestamp(flight.get("aTime", 0)).strftime("%H:%M"),
            "Duración": str(int(flight.get("duration", {}).get("total", 0)//3600)) + ":" + 
                       str(int((flight.get("duration", {}).get("total", 0)%3600)//60)).zfill(2),
            "Escalas": len(flight.get("route", [])) - 1 if flight.get("route") else 0
        }
    except: return {}