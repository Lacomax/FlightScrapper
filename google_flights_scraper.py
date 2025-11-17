"""
Scraper para Google Flights usando Selenium.

Nota: Google Flights carga contenido con JavaScript, requiere Selenium.
Es más lento pero proporciona una buena comparativa de precios.
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def search_google_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    driver: webdriver.Chrome = None
) -> Optional[List[Dict]]:
    """
    Busca vuelos en Google Flights.

    Args:
        origin (str): Código IATA de origen (MUC)
        destination (str): Código IATA de destino (BCN)
        departure_date (str): Fecha salida DD/MM/YYYY
        return_date (str): Fecha regreso DD/MM/YYYY
        driver (WebDriver): Instancia de Selenium WebDriver

    Returns:
        List[Dict]: Vuelos encontrados, o None si hay error
    """
    if not driver:
        logging.error("Google Flights requiere WebDriver válido")
        return None

    try:
        # Convertir fechas para URL
        dep_dt = datetime.strptime(departure_date, "%d/%m/%Y")
        ret_dt = datetime.strptime(return_date, "%d/%m/%Y")

        # URL de búsqueda en Google Flights
        url = (
            f"https://www.google.com/travel/explore?"
            f"tfs=CBwQAxpNCjcKBQjnFAISAhAAEgoyMDI1LTA="
            f"&q={origin}%20to%20{destination}%20{dep_dt.strftime('%m/%d/%Y')}"
        )

        logging.debug(f"Google Flights URL: {url}")
        driver.get(url)

        # Esperar a que cargue (Google Flights es lento)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-test-id='flight-card']"))
            )
        except:
            logging.warning("Timeout esperando resultados de Google Flights")
            return []

        flights = _parse_google_flights_page(driver, origin, destination, departure_date, return_date)
        return flights

    except Exception as e:
        logging.error(f"Error en Google Flights: {e}")
        return None


def _parse_google_flights_page(
    driver: webdriver.Chrome,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str
) -> List[Dict]:
    """
    Parsea la página de Google Flights.

    Args:
        driver (WebDriver): Instancia de Selenium WebDriver
        origin (str): Código IATA
        destination (str): Código IATA
        departure_date (str): Fecha DD/MM/YYYY
        return_date (str): Fecha DD/MM/YYYY

    Returns:
        List[Dict]: Vuelos extraídos
    """
    flights = []

    try:
        # Selectores aproximados (Google Flights cambia frecuentemente)
        flight_cards = driver.find_elements(By.CSS_SELECTOR, "div[data-test-id='flight-card']")

        for card in flight_cards:
            try:
                # Intentar extraer información
                # Los selectores varían mucho, por eso es frágil
                text = card.text if hasattr(card, 'text') else ""

                # Patrones típicos:
                # "14:00 – 18:30  Lufthansa  3h 30m  1 stop
                #  €450  Save €50"

                price_match = re.search(r"€(\d+(?:[.,]\d{2})?)", text)
                stops_match = re.search(r"(\d+)\s*stop", text, re.IGNORECASE)
                time_match = re.search(r"(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})", text)

                price = float(price_match.group(1).replace(",", ".")) if price_match else 0.0
                stops = int(stops_match.group(1)) if stops_match else 0
                dep_time = time_match.group(1) if time_match else "N/A"
                arr_time = time_match.group(2) if time_match else "N/A"

                # Extraer aerolínea (palabra entre horarios)
                airline_words = text.split()
                airline = airline_words[2] if len(airline_words) > 2 else "Unknown"

                flight = {
                    "Aerolínea": airline,
                    "Origen": origin,
                    "Destino": destination,
                    "Fecha": departure_date,
                    "Hora_Salida": dep_time,
                    "Hora_Llegada": arr_time,
                    "Escalas": stops,
                    "Precio": price,
                    "Moneda": "EUR"
                }
                flights.append(flight)

            except Exception as e:
                logging.debug(f"Error parseando vuelo Google Flights: {e}")
                continue

    except Exception as e:
        logging.error(f"Error extrayendo vuelos Google Flights: {e}")

    logging.debug(f"Google Flights: {len(flights)} vuelos encontrados")
    return flights
