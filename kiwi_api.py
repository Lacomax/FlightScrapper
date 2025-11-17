"""
Integración con API de Kiwi.com (Tequila) para búsqueda de vuelos.

Este módulo proporciona funciones para buscar vuelos usando la API Tequila de Kiwi.com,
incluyendo cache de 1 hora y reintentos automáticos ante rate limiting.

Requisitos:
    - Obtener API key en https://tequila.kiwi.com/portal/login
    - Instalar: pip install requests
"""

import os
import requests
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from cachetools import TTLCache, cached

# Configuración
API_KEY = os.environ.get("KIWI_API_KEY", "")
API_URL = "https://api.tequila.kiwi.com/v2/search"
CACHE = TTLCache(maxsize=1000, ttl=3600)  # Cache de 1 hora


@cached(CACHE)
def search_flights(
    from_loc: str,
    to_loc: str,
    depart_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    children: int = 0,
    currency: str = "EUR",
    max_stops: int = 1
) -> Optional[List[Dict]]:
    """
    Busca vuelos en Kiwi.com API (Tequila).

    Realiza búsqueda con caché de 1 hora y reintentos automáticos
    ante rate limiting (error 429).

    Args:
        from_loc (str): Código IATA del aeropuerto de origen o nombre de ciudad
        to_loc (str): Código IATA del aeropuerto destino o nombre de ciudad
        depart_date (str): Fecha de salida (formato DD/MM/YYYY o YYYY-MM-DD)
        return_date (str, optional): Fecha de retorno. Si es None, vuelo de ida.
        adults (int): Número de adultos. Default: 1
        children (int): Número de niños. Default: 0
        currency (str): Moneda de respuesta. Default: 'EUR'
        max_stops (int): Número máximo de escalas. Default: 1

    Returns:
        List[Dict] or None: Lista de vuelos encontrados o None si hay error

    Example:
        >>> flights = search_flights("MUC", "JRO", "06/06/2025", adults=2)
        >>> processed = extract_flights(flights)
    """
    if not API_KEY:
        logging.warning("API_KEY de Kiwi no configurada")
        return None

    headers = {"apikey": API_KEY}
    params = {
        "fly_from": from_loc,
        "fly_to": to_loc,
        "date_from": _fmt_date(depart_date),
        "date_to": _fmt_date(depart_date),
        "adults": adults,
        "children": children,
        "curr": currency,
        "max_stopovers": max_stops,
        "limit": 10
    }

    if return_date:
        params.update({
            "return_from": _fmt_date(return_date),
            "return_to": _fmt_date(return_date)
        })

    # Reintentos con backoff ante rate limiting
    for attempt in range(3):
        try:
            logging.debug(f"Kiwi: Búsqueda {from_loc}->{to_loc} (intento {attempt + 1}/3)")
            response = requests.get(API_URL, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json().get("data", [])
                logging.debug(f"Kiwi: {len(data)} vuelos encontrados")
                return data

            elif response.status_code == 429:  # Rate limit
                if attempt < 2:
                    logging.warning("Kiwi: Rate limit alcanzado, esperando...")
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s

            elif response.status_code == 400:
                logging.warning(f"Kiwi: Error en parámetros de búsqueda")
                break

        except requests.exceptions.Timeout:
            logging.warning(f"Kiwi: Timeout en búsqueda (intento {attempt + 1})")
        except Exception as e:
            logging.error(f"Kiwi: Error en búsqueda: {e}")
            break

    return None


def _fmt_date(date_str: str) -> str:
    """
    Convierte fecha al formato DD/MM/YYYY requerido por Kiwi.

    Args:
        date_str (str): Fecha en formato DD/MM/YYYY o YYYY-MM-DD

    Returns:
        str: Fecha en formato DD/MM/YYYY
    """
    try:
        fmt = "%d/%m/%Y" if "/" in date_str else "%Y-%m-%d"
        dt = datetime.strptime(date_str, fmt)
        return dt.strftime("%d/%m/%Y")
    except Exception as e:
        logging.warning(f"Error formateando fecha para Kiwi: {e}")
        return date_str


def get_cheapest_flight(
    from_loc: str,
    to_loc: str,
    depart_date: str,
    return_date: Optional[str] = None
) -> Optional[Dict]:
    """
    Obtiene el vuelo más barato de una búsqueda.

    Args:
        from_loc (str): Código IATA de origen
        to_loc (str): Código IATA de destino
        depart_date (str): Fecha de salida
        return_date (str, optional): Fecha de retorno

    Returns:
        Dict or None: El vuelo más barato o None si no hay resultados
    """
    data = search_flights(from_loc, to_loc, depart_date, return_date)
    if data:
        return min(data, key=lambda x: float(x.get("price", float("inf"))))
    return None


def extract_flights(kiwi_data: Optional[List[Dict]]) -> List[Dict]:
    """
    Extrae información de vuelos desde respuesta de Kiwi.

    Procesa la respuesta raw de Kiwi y extrae información en formato
    estándar compatible con el resto del programa.

    Args:
        kiwi_data (List[Dict] or None): Respuesta de API Kiwi

    Returns:
        List[Dict]: Lista de vuelos procesados con estructura estándar

    Example:
        >>> raw_response = search_flights("MUC", "JRO", "06/06/2025")
        >>> flights = extract_flights(raw_response)
        >>> for flight in flights:
        ...     print(f"{flight['Compañía']} {flight['Precio']}€")
    """
    if not kiwi_data:
        return []
    return [_parse_flight(f) for f in kiwi_data]


def _parse_flight(flight: Dict) -> Dict:
    """
    Parsea un vuelo individual desde respuesta de Kiwi.

    Args:
        flight (Dict): Datos de vuelo desde API de Kiwi

    Returns:
        Dict: Vuelo procesado con estructura estándar
    """
    try:
        # Procesar duración
        total_seconds = flight.get("duration", {}).get("total", 0)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)

        return {
            "Precio": float(flight.get("price", 0)),
            "Compañía": flight.get("airlines", ["Desconocida"])[0],
            "Origen": flight.get("flyFrom", ""),
            "Destino": flight.get("flyTo", ""),
            "Día": datetime.fromtimestamp(flight.get("dTime", 0)).strftime("%d/%m/%Y"),
            "Hora_Salida": datetime.fromtimestamp(flight.get("dTime", 0)).strftime("%H:%M"),
            "Hora_Llegada": datetime.fromtimestamp(flight.get("aTime", 0)).strftime("%H:%M"),
            "Duración": f"{hours}:{minutes:02d}",
            "Escalas": len(flight.get("route", [])) - 1 if flight.get("route") else 0
        }
    except Exception as e:
        logging.debug(f"Error parseando vuelo de Kiwi: {e}")
        return {}