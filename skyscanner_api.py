"""
Integración con API de Skyscanner via RapidAPI.

Este módulo proporciona funciones para buscar vuelos usando la API Skyscanner
a través de RapidAPI, incluyendo cache de 30 minutos.

Requisitos:
    - Obtener API key en https://rapidapi.com/skyscanner/api/skyscanner-flight-search
    - Instalar: pip install requests
"""

import os
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from cachetools import TTLCache, cached

# Configuración
SKY_CACHE = TTLCache(maxsize=500, ttl=1800)  # Cache de 30 minutos
RAPID_KEY = os.environ.get("RAPID_API_KEY", "")


@cached(SKY_CACHE)
def search_skyscanner(
    from_loc: str,
    to_loc: str,
    depart_date: str,
    return_date: Optional[str] = None,
    adults: int = 1
) -> Optional[List[Dict]]:
    """
    Busca vuelos en Skyscanner via RapidAPI.

    Realiza búsqueda con caché de 30 minutos para evitar exceder límites
    de rate limit de RapidAPI.

    Args:
        from_loc (str): Código IATA del aeropuerto de origen
        to_loc (str): Código IATA del aeropuerto destino
        depart_date (str): Fecha de salida (formato DD/MM/YYYY o YYYY-MM-DD)
        return_date (str, optional): Fecha de retorno. Si es None, vuelo de ida.
        adults (int): Número de adultos. Default: 1

    Returns:
        List[Dict] or None: Lista de "buckets" con vuelos o None si hay error

    Example:
        >>> buckets = search_skyscanner("MUC", "JRO", "06/06/2025")
        >>> flights = extract_sky_flights(buckets)
    """
    if not RAPID_KEY:
        logging.warning("RAPID_API_KEY de Skyscanner no configurada")
        return None

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
        logging.debug(f"Skyscanner: Búsqueda {from_loc}->{to_loc}")
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json().get('itineraries', {}).get('buckets', [])
            logging.debug(f"Skyscanner: {len(data)} buckets encontrados")
            return data

        elif response.status_code == 429:
            logging.warning("Skyscanner: Rate limit alcanzado")
        else:
            logging.warning(f"Skyscanner: Error HTTP {response.status_code}")

    except requests.exceptions.Timeout:
        logging.warning("Skyscanner: Timeout en búsqueda")
    except Exception as e:
        logging.error(f"Skyscanner: Error en búsqueda: {e}")

    return None


def _fmt_date_iso(date_str: str) -> str:
    """
    Convierte fecha al formato ISO (YYYY-MM-DD) requerido por Skyscanner.

    Args:
        date_str (str): Fecha en formato DD/MM/YYYY o YYYY-MM-DD

    Returns:
        str: Fecha en formato YYYY-MM-DD
    """
    try:
        fmt = "%d/%m/%Y" if "/" in date_str else "%Y-%m-%d"
        return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
    except Exception as e:
        logging.warning(f"Error formateando fecha para Skyscanner: {e}")
        return date_str


def extract_sky_flights(data: Optional[List[Dict]]) -> List[Dict]:
    """
    Extrae información de vuelos desde respuesta de Skyscanner.

    Procesa la respuesta raw de Skyscanner (buckets) y extrae información
    en formato estándar compatible con el resto del programa.

    Args:
        data (List[Dict] or None): Buckets de itinerarios desde Skyscanner

    Returns:
        List[Dict]: Lista de vuelos procesados con estructura estándar

    Example:
        >>> raw_response = search_skyscanner("MUC", "JRO", "06/06/2025")
        >>> flights = extract_sky_flights(raw_response)
        >>> for flight in flights:
        ...     print(f"{flight['Compañía']} {flight['Precio']}€")
    """
    results = []

    if not data:
        return results

    for bucket in data:
        for item in bucket.get('items', []):
            try:
                legs = item.get('legs', [])
                if not legs:
                    continue

                origin_leg = legs[0]
                price = float(item.get('price', {}).get('raw', 0))

                # Procesar compañía
                carriers = origin_leg.get('carriers', {}).get('marketing', [{}])
                airline_name = carriers[0].get('name', 'Desconocida') if carriers else 'Desconocida'

                # Procesar duración
                duration_minutes = origin_leg.get('durationInMinutes', 0)
                hours = duration_minutes // 60
                minutes = duration_minutes % 60

                flight = {
                    "Precio": price,
                    "Compañía": airline_name,
                    "Origen": origin_leg.get('origin', {}).get('displayCode', ''),
                    "Destino": origin_leg.get('destination', {}).get('displayCode', ''),
                    "Día": datetime.fromisoformat(
                        origin_leg.get('departure', '').replace('Z', '+00:00')
                    ).strftime("%d/%m/%Y"),
                    "Hora_Salida": datetime.fromisoformat(
                        origin_leg.get('departure', '').replace('Z', '+00:00')
                    ).strftime("%H:%M"),
                    "Hora_Llegada": datetime.fromisoformat(
                        origin_leg.get('arrival', '').replace('Z', '+00:00')
                    ).strftime("%H:%M"),
                    "Duración": f"{hours}:{minutes:02d}",
                    "Escalas": len(origin_leg.get('segments', [])) - 1
                }
                results.append(flight)

            except Exception as e:
                logging.debug(f"Error procesando vuelo Skyscanner: {e}")
                continue

    return results