"""
Scraper nativo para RyanAir.

Obtiene vuelos directamente de RyanAir usando su API pública.
Sin necesidad de Selenium, solo requests.
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Configuración
RYANAIR_API = "https://www.ryanair.com/api/farfnd/v4/roundTrip"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def search_ryanair_roundtrip(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    adults: int = 1,
    children: int = 0
) -> Optional[Dict]:
    """
    Busca vuelos de ida y vuelta en RyanAir.

    Args:
        origin (str): Código IATA del aeropuerto de origen (ej: MUC)
        destination (str): Código IATA del aeropuerto de destino (ej: BCN)
        departure_date (str): Fecha salida en formato DD/MM/YYYY
        return_date (str): Fecha regreso en formato DD/MM/YYYY
        adults (int): Número de adultos
        children (int): Número de niños

    Returns:
        Dict: Datos JSON de RyanAir, o None si hay error
    """
    try:
        # Convertir fechas a formato YYYY-MM-DD para RyanAir
        dep_dt = datetime.strptime(departure_date, "%d/%m/%Y")
        ret_dt = datetime.strptime(return_date, "%d/%m/%Y")

        dep_str = dep_dt.strftime("%Y-%m-%d")
        ret_str = ret_dt.strftime("%Y-%m-%d")

        payload = {
            "outboundDates": [dep_str],
            "inboundDates": [ret_str],
            "adults": adults,
            "teens": 0,
            "children": children,
            "infants": 0,
            "origin": origin,
            "destination": destination,
            "discount": 0,
            "isConnectedFlight": False,
            "flightTypes": ["OUTBOUND", "RETURN"]
        }

        logging.debug(f"RyanAir API call: {origin} → {destination} | {departure_date}")
        response = requests.post(RYANAIR_API, json=payload, headers=HEADERS, timeout=15)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.warning(f"Error en RyanAir API: {e}")
        return None
    except Exception as e:
        logging.error(f"Error parseando respuesta RyanAir: {e}")
        return None


def extract_ryanair_flights(data: Dict) -> List[Dict]:
    """
    Extrae información de vuelos de la respuesta de RyanAir.

    Args:
        data (Dict): Respuesta JSON de RyanAir

    Returns:
        List[Dict]: Lista de vuelos con formato estandarizado
    """
    flights = []

    try:
        # Estructura típica: data['trips'][0] = outbound, data['trips'][1] = return
        if not data or "trips" not in data:
            logging.debug("Respuesta RyanAir vacía o formato inesperado")
            return flights

        for trip_idx, trip in enumerate(data.get("trips", [])):
            trip_type = "IDA" if trip_idx == 0 else "VUELTA"

            for flight in trip.get("flights", []):
                try:
                    flight_info = {
                        "Aerolínea": "RyanAir",
                        "Tipo": trip_type,
                        "Fecha": flight.get("departureDate", "").split("T")[0],
                        "Origen": flight.get("departureAirport", {}).get("code", "N/A"),
                        "Destino": flight.get("arrivalAirport", {}).get("code", "N/A"),
                        "Hora_Salida": flight.get("departureDate", "").split("T")[1][:5] if "T" in flight.get("departureDate", "") else "N/A",
                        "Hora_Llegada": flight.get("arrivalDate", "").split("T")[1][:5] if "T" in flight.get("arrivalDate", "") else "N/A",
                        "Escalas": 0 if not flight.get("stops") else len(flight.get("stops", [])),
                        "Duración": flight.get("duration", "N/A"),
                        "Precio": float(flight.get("price", {}).get("totalWithoutDeductions", 0)) if isinstance(flight.get("price"), dict) else 0.0,
                        "Moneda": flight.get("price", {}).get("currencyCode", "EUR") if isinstance(flight.get("price"), dict) else "EUR",
                    }
                    flights.append(flight_info)

                except (KeyError, TypeError, ValueError) as e:
                    logging.debug(f"Error extrayendo vuelo RyanAir: {e}")
                    continue

    except Exception as e:
        logging.error(f"Error procesando vuelos RyanAir: {e}")

    return flights
