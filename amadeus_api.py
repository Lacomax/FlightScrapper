import os, logging, json
from datetime import datetime
from typing import Dict, List, Optional, Any
from cachetools import TTLCache, cached

AMADEUS_ID, AMADEUS_SECRET = "", ""
AMADEUS_CACHE = TTLCache(maxsize=500, ttl=1800)
_amadeus_client = None

try:
    from amadeus import Client, ResponseError
    AMADEUS_AVAILABLE = True
except ImportError:
    AMADEUS_AVAILABLE = False

def get_amadeus_client():
    global _amadeus_client
    if not _amadeus_client and AMADEUS_ID and AMADEUS_SECRET:
        try: _amadeus_client = Client(client_id=AMADEUS_ID, client_secret=AMADEUS_SECRET)
        except Exception as e: logging.error(f"Error al crear cliente Amadeus: {e}")
    return _amadeus_client

@cached(AMADEUS_CACHE)
def search_flights(origin: str, destination: str, departure_date: str, 
                  return_date: Optional[str] = None, adults: int = 1, 
                  direct: bool = False, currency: str = "EUR") -> List[Dict]:
    if not AMADEUS_AVAILABLE:
        logging.warning("Módulo Amadeus no disponible. Instálalo con 'pip install amadeus'")
        return []
        
    client = get_amadeus_client()
    if not client: return []
    
    departure_formatted = _format_date_for_amadeus(departure_date)
    
    try:
        search_params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_formatted,
            "adults": adults,
            "currencyCode": currency,
            "max": 50
        }
        
        if return_date:
            search_params["returnDate"] = _format_date_for_amadeus(return_date)
            
        if direct:
            search_params["nonStop"] = True
            
        response = client.shopping.flight_offers_search.get(**search_params)
        return response.data
        
    except ResponseError as e:
        logging.error(f"Error de API Amadeus: {e}")
    except Exception as e:
        logging.error(f"Error inesperado con Amadeus: {e}")
        
    return []

def _format_date_for_amadeus(date_str: str) -> str:
    if "/" in date_str:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    return date_str

def extract_amadeus_flights(data: List[Dict]) -> List[Dict]:
    if not data: return []
    
    results = []
    for offer in data:
        try:
            itinerary = offer["itineraries"][0]
            first_segment = itinerary["segments"][0]
            last_segment = itinerary["segments"][-1]
            stops = len(itinerary["segments"]) - 1
            airline_code = first_segment["carrierCode"]
            
            stopover_details = []
            for i in range(len(itinerary["segments"]) - 1):
                segment, next_segment = itinerary["segments"][i], itinerary["segments"][i + 1]
                arrival_time = datetime.fromisoformat(segment["arrival"]["at"].replace("Z", "+00:00"))
                departure_time = datetime.fromisoformat(next_segment["departure"]["at"].replace("Z", "+00:00"))
                layover_minutes = int((departure_time - arrival_time).total_seconds() / 60)
                stopover_details.append({
                    "airport": segment["arrival"]["iataCode"],
                    "duration": f"{layover_minutes//60}h {layover_minutes%60}m"
                })
            
            departure_time = datetime.fromisoformat(first_segment["departure"]["at"].replace("Z", "+00:00"))
            arrival_time = datetime.fromisoformat(last_segment["arrival"]["at"].replace("Z", "+00:00"))
            
            duration_minutes = int(itinerary["duration"].replace("PT", "").replace("H", "*60+").replace("M", "").replace("*60+", "*60+0"))
            
            flight = {
                "Precio": offer["price"]["total"],
                "Compañía": airline_code,
                "Origen": first_segment["departure"]["iataCode"],
                "Destino": last_segment["arrival"]["iataCode"],
                "Día": departure_time.strftime("%d/%m/%Y"),
                "Hora_Salida": departure_time.strftime("%H:%M"),
                "Hora_Llegada": arrival_time.strftime("%H:%M"),
                "Duración": f"{duration_minutes//60}:{duration_minutes%60:02d}",
                "Escalas": stops,
                "Detalles_Escalas": stopover_details
            }
            
            results.append(flight)
            
        except Exception as e:
            logging.debug(f"Error procesando vuelo Amadeus: {e}")
            
    return results

# Test code
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    AMADEUS_ID = os.environ.get("AMADEUS_API_KEY", "")
    AMADEUS_SECRET = os.environ.get("AMADEUS_API_SECRET", "")
    
    if not AMADEUS_ID or not AMADEUS_SECRET:
        print("Configura AMADEUS_API_KEY y AMADEUS_API_SECRET como variables de entorno")
        exit(1)
    
    results = search_flights("MUC", "JRO", "06/06/2025", adults=2)
    
    if results:
        flights = extract_amadeus_flights(results)
        print(f"Se encontraron {len(flights)} vuelos:")
        for f in flights:
            print(f"{f['Compañía']} {f['Origen']} -> {f['Destino']} | {f['Día']} {f['Hora_Salida']}-{f['Hora_Llegada']} | Escalas: {f['Escalas']} | €{f['Precio']}")
            if f['Detalles_Escalas']:
                print("  Escalas:")
                for s in f['Detalles_Escalas']:
                    print(f"  - {s['airport']} (espera: {s['duration']})")
    else:
        print("No se encontraron vuelos.")