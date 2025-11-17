"""
Integración con API de Amadeus para búsqueda de vuelos.

Este módulo proporciona funciones para buscar vuelos usando la API oficial
de Amadeus, incluyendo cache de resultados y extracción de información.

Requisitos:
    - Obtener credenciales en https://developers.amadeus.com
    - Instalar: pip install amadeus
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from cachetools import TTLCache, cached

# Configuración
AMADEUS_ID = os.environ.get("AMADEUS_CLIENT_ID", "")
AMADEUS_SECRET = os.environ.get("AMADEUS_CLIENT_SECRET", "")
AMADEUS_CACHE = TTLCache(maxsize=500, ttl=1800)  # Cache de 30 minutos
_amadeus_client = None

try:
    from amadeus import Client, ResponseError
    AMADEUS_AVAILABLE = True
except ImportError:
    AMADEUS_AVAILABLE = False
    logging.warning("Módulo 'amadeus' no disponible. Instálalo con: pip install amadeus")


def get_amadeus_client():
    """
    Obtiene o crea una instancia del cliente de Amadeus.

    Crea un singleton del cliente de Amadeus con las credenciales configuradas.

    Returns:
        Client or None: Instancia del cliente de Amadeus o None si no está configurado

    Note:
        Requiere AMADEUS_ID y AMADEUS_SECRET en variables de entorno o módulo
    """
    global _amadeus_client
    if not _amadeus_client and AMADEUS_ID and AMADEUS_SECRET:
        try:
            _amadeus_client = Client(client_id=AMADEUS_ID, client_secret=AMADEUS_SECRET)
            logging.debug("Cliente de Amadeus inicializado correctamente")
        except Exception as e:
            logging.error(f"Error al crear cliente Amadeus: {e}")
    return _amadeus_client


@cached(AMADEUS_CACHE)
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    direct: bool = False,
    currency: str = "EUR"
) -> List[Dict]:
    """
    Busca vuelos en la API de Amadeus.

    Realiza una búsqueda de vuelos con caché de 30 minutos para evitar
    exceder límites de rate limit.

    Args:
        origin (str): Código IATA del aeropuerto de origen (ej: 'MUC')
        destination (str): Código IATA del aeropuerto destino (ej: 'JRO')
        departure_date (str): Fecha de salida (formato DD/MM/YYYY o YYYY-MM-DD)
        return_date (str, optional): Fecha de retorno. Si es None, vuelo de ida.
        adults (int): Número de adultos. Default: 1
        direct (bool): Si es True, busca solo vuelos directos. Default: False
        currency (str): Moneda de respuesta. Default: 'EUR'

    Returns:
        List[Dict]: Lista de ofertas de vuelos de Amadeus (raw response)

    Example:
        >>> results = search_flights("MUC", "JRO", "06/06/2025", adults=2)
        >>> flights = extract_amadeus_flights(results)
    """
    if not AMADEUS_AVAILABLE:
        logging.warning("Módulo Amadeus no disponible. Instálalo con 'pip install amadeus'")
        return []

    client = get_amadeus_client()
    if not client:
        logging.warning("Cliente de Amadeus no configurado")
        return []

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

        logging.debug(f"Buscando vuelos Amadeus: {origin} -> {destination} ({departure_formatted})")
        response = client.shopping.flight_offers_search.get(**search_params)
        return response.data

    except Exception as e:
        logging.error(f"Error con API Amadeus: {e}")
        return []


def _format_date_for_amadeus(date_str: str) -> str:
    """
    Convierte fecha al formato requerido por Amadeus (YYYY-MM-DD).

    Args:
        date_str (str): Fecha en formato DD/MM/YYYY o YYYY-MM-DD

    Returns:
        str: Fecha en formato YYYY-MM-DD
    """
    try:
        if "/" in date_str:
            return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        return date_str
    except Exception as e:
        logging.warning(f"Error formateando fecha para Amadeus: {e}")
        return date_str


def extract_amadeus_flights(data: List[Dict]) -> List[Dict]:
    """
    Extrae información de vuelos desde respuesta de Amadeus.

    Procesa la respuesta raw de Amadeus y extrae información en formato
    estándar compatible con el resto del programa.

    Args:
        data (List[Dict]): Respuesta de API Amadeus (flight_offers)

    Returns:
        List[Dict]: Lista de vuelos procesados con estructura estándar

    Example:
        >>> raw_response = search_flights("MUC", "JRO", "06/06/2025")
        >>> flights = extract_amadeus_flights(raw_response)
        >>> for flight in flights:
        ...     print(f"{flight['Compañía']} {flight['Precio']}€")
    """
    if not data:
        return []

    results = []
    for offer in data:
        try:
            itinerary = offer["itineraries"][0]
            first_segment = itinerary["segments"][0]
            last_segment = itinerary["segments"][-1]
            stops = len(itinerary["segments"]) - 1
            airline_code = first_segment["carrierCode"]

            # Procesar detalles de escalas
            stopover_details = []
            for i in range(len(itinerary["segments"]) - 1):
                segment = itinerary["segments"][i]
                next_segment = itinerary["segments"][i + 1]

                arrival_time = datetime.fromisoformat(
                    segment["arrival"]["at"].replace("Z", "+00:00")
                )
                departure_time = datetime.fromisoformat(
                    next_segment["departure"]["at"].replace("Z", "+00:00")
                )

                layover_minutes = int((departure_time - arrival_time).total_seconds() / 60)
                stopover_details.append({
                    "airport": segment["arrival"]["iataCode"],
                    "duration": f"{layover_minutes // 60}h {layover_minutes % 60}m"
                })

            # Procesar horarios
            departure_time = datetime.fromisoformat(
                first_segment["departure"]["at"].replace("Z", "+00:00")
            )
            arrival_time = datetime.fromisoformat(
                last_segment["arrival"]["at"].replace("Z", "+00:00")
            )

            # Procesar duración
            duration_str = itinerary.get("duration", "PT0H0M")
            hours = 0
            minutes = 0

            if "H" in duration_str:
                h_part = duration_str.split("H")[0]
                hours = int(h_part.split("PT")[-1]) if "PT" in duration_str else int(h_part)
            if "M" in duration_str:
                m_part = duration_str.split("M")[0].split("H")[-1]
                minutes = int(m_part) if m_part else 0

            flight = {
                "Precio": float(offer.get("price", {}).get("total", 0)),
                "Compañía": airline_code,
                "Origen": first_segment["departure"]["iataCode"],
                "Destino": last_segment["arrival"]["iataCode"],
                "Día": departure_time.strftime("%d/%m/%Y"),
                "Hora_Salida": departure_time.strftime("%H:%M"),
                "Hora_Llegada": arrival_time.strftime("%H:%M"),
                "Duración": f"{hours}h {minutes}m",
                "Escalas": stops,
                "Detalles_Escalas": stopover_details
            }

            results.append(flight)

        except Exception as e:
            logging.debug(f"Error procesando oferta de Amadeus: {e}")
            continue

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