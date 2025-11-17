import requests, logging, json
from datetime import datetime
from typing import Dict, List
from cachetools import TTLCache, cached

SKY_CACHE = TTLCache(maxsize=500, ttl=1800)
RAPID_KEY = ""  # Obtén en RapidAPI - SkyScanner

@cached(SKY_CACHE)
def search_skyscanner(from_loc, to_loc, depart_date, return_date=None, adults=1):
    if not RAPID_KEY: return None
    
    url = "https://skyscanner44.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPID_KEY,
        "X-RapidAPI-Host": "skyscanner44.p.rapidapi.com"
    }
    
    params = {
        "adults": adults,
        "origin": from_loc,
        "destination": to_loc,
        "departureDate": _fmt_date_iso(depart_date),
        "currency": "EUR"
    }
    
    if return_date:
        params["returnDate"] = _fmt_date_iso(return_date)
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json().get('itineraries', {}).get('buckets', [])
    except Exception as e:
        logging.debug(f"Skyscanner API error: {e}")
    
    return None

def _fmt_date_iso(date_str):
    fmt = "%d/%m/%Y" if "/" in date_str else "%Y-%m-%d"
    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")

def extract_sky_flights(data):
    results = []
    
    if not data: return results
    
    for bucket in data:
        for item in bucket.get('items', []):
            try:
                legs = item.get('legs', [])
                if not legs: continue
                
                origin_leg = legs[0]
                price = str(item.get('price', {}).get('raw', 0))
                
                flight = {
                    "Precio": price,
                    "Compañía": origin_leg.get('carriers', {}).get('marketing', [{}])[0].get('name', 'Desconocida'),
                    "Origen": origin_leg.get('origin', {}).get('displayCode', ''),
                    "Destino": origin_leg.get('destination', {}).get('displayCode', ''),
                    "Día": datetime.fromisoformat(origin_leg.get('departure', '').replace('Z', '+00:00')).strftime("%d/%m/%Y"),
                    "Hora_Salida": datetime.fromisoformat(origin_leg.get('departure', '').replace('Z', '+00:00')).strftime("%H:%M"),
                    "Hora_Llegada": datetime.fromisoformat(origin_leg.get('arrival', '').replace('Z', '+00:00')).strftime("%H:%M"),
                    "Duración": f"{origin_leg.get('durationInMinutes', 0)//60}:{origin_leg.get('durationInMinutes', 0)%60:02d}",
                    "Escalas": len(origin_leg.get('segments', [])) - 1
                }
                results.append(flight)
            except Exception as e:
                logging.debug(f"Error parsing Skyscanner flight: {e}")
    
    return results