"""
Buscador de Vuelos - RyanAir + Google Flights

Script limpio para buscar vuelos de forma privada combinando:
- RyanAir API (rápido, solo vuelos RyanAir)
- Google Flights (comparativa, más fuentes)

Uso: python flight_scraper_main.py [opciones]
"""

import os
import sys
import json
import time
import logging
import argparse
import random
from datetime import datetime, timedelta
from typing import List, Dict

# Importar scrapers
from ryanair_scraper import search_ryanair_roundtrip, extract_ryanair_flights
from google_flights_scraper import search_google_flights
from webdriver_utils import setup_edge_driver, random_delay


# ==================== CONFIGURACIÓN ====================

DEFAULT_CONFIG = {
    "AIRPORTS": ["MUC", "FMM", "NUR"],
    "DESTINATIONS": ["JRO"],
    "PASSENGERS": {"adults": 2, "children": "2[12;12]"},
    "DATES": {"from": "6/6/2025", "to": "22/6/2025"},
    "STAY_DURATION": {"min_days": 8, "max_days": 14},
    "SOURCES": ["ryanair", "google"],
    "OUTPUT_FILE": "resultados_vuelos.json",
    "MAX_RESULTS": 20,
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
]


# ==================== LOGGING ====================

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("flight_scraper.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    for logger in ["selenium", "urllib3"]:
        logging.getLogger(logger).setLevel(logging.WARNING)


# ==================== CONFIGURACIÓN DE USUARIO ====================

def load_saved_config():
    """Carga última configuración guardada"""
    try:
        if os.path.exists("last_config.json"):
            with open("last_config.json", "r") as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"Error cargando configuración: {e}")
    return None


def get_user_input() -> Dict:
    """Obtiene entrada del usuario con valores por defecto de última búsqueda"""
    last_cfg = load_saved_config()

    if last_cfg:
        cfg = last_cfg
        print("\n===== Buscador de Vuelos (RyanAir + Google) =====")
        print(f"Última búsqueda: {last_cfg['AIRPORTS'][0]} → {last_cfg['DESTINATIONS'][0]}")
        print("Presiona Enter para valores de la última búsqueda.\n")
    else:
        cfg = DEFAULT_CONFIG.copy()
        print("\n===== Buscador de Vuelos (RyanAir + Google) =====")
        print("Presiona Enter para valores predeterminados.\n")

    # Campos básicos
    for key, prompt in [
        ("AIRPORTS", f"Aeropuertos origen [{', '.join(cfg['AIRPORTS'])}]: "),
        ("DESTINATIONS", f"Destinos [{', '.join(cfg['DESTINATIONS'])}]: ")
    ]:
        inp = input(prompt).strip()
        if inp:
            cfg[key] = [x.strip().upper() for x in inp.split(",")]

    # Fechas y estancia
    for key, subkey, prompt in [
        ("DATES", "from", f"Fecha mín salida DD/MM/YYYY [{cfg['DATES']['from']}]: "),
        ("DATES", "to", f"Fecha máx regreso [{cfg['DATES']['to']}]: "),
        ("STAY_DURATION", "min_days", f"Estancia mínima (o MAX) [{cfg['STAY_DURATION']['min_days']}]: "),
        ("STAY_DURATION", "max_days", f"Estancia máxima [{cfg['STAY_DURATION']['max_days']}]: ")
    ]:
        inp = input(prompt).strip()
        if inp:
            if key == "STAY_DURATION" and subkey == "min_days" and inp.upper() == "MAX":
                try:
                    from_date = datetime.strptime(cfg["DATES"]["from"], "%d/%m/%Y")
                    to_date = datetime.strptime(cfg["DATES"]["to"], "%d/%m/%Y")
                    cfg[key][subkey] = (to_date - from_date).days
                    logging.info(f"Estancia: AUTO-CALCULADA = {cfg[key][subkey]} días")
                except:
                    pass
            elif subkey.endswith('days') and inp.isdigit():
                cfg[key][subkey] = int(inp)
            elif not subkey.endswith('days'):
                cfg[key][subkey] = inp

    # Pasajeros
    adults = input(f"Adultos [{cfg['PASSENGERS']['adults']}]: ").strip()
    if adults:
        cfg["PASSENGERS"]["adults"] = int(adults)

    children = input(f"Niños [{cfg['PASSENGERS']['children'].split('[')[0] if '[' in cfg['PASSENGERS']['children'] else 0}]: ").strip()
    if children and children.isdigit() and int(children) > 0:
        prev_ages = []
        if "[" in cfg['PASSENGERS']['children']:
            try:
                prev_ages = cfg['PASSENGERS']['children'].split("[")[1].rstrip("]").split(";")
            except:
                pass

        ages = []
        for i in range(int(children)):
            default_age = prev_ages[i] if i < len(prev_ages) else "12"
            age = input(f"Edad niño {i+1} [{default_age}]: ").strip() or default_age
            ages.append(age)
        cfg["PASSENGERS"]["children"] = f"{children}[{';'.join(ages)}]"
    elif children and children.isdigit():
        cfg["PASSENGERS"]["children"] = "0"

    # Fuentes
    print(f"\nFuentes disponibles:")
    print("1. RyanAir (rápido, vuelos reales)")
    print("2. Google Flights (lento, comparativa)")
    print(f"3. Ambas [default]")
    sources_input = input("Selecciona (1/2/3): ").strip().lower()

    source_map = {
        "1": ["ryanair"],
        "2": ["google"],
        "3": ["ryanair", "google"],
        "": ["ryanair", "google"],
    }

    cfg["SOURCES"] = source_map.get(sources_input, ["ryanair", "google"])

    # Guardar configuración
    with open("last_config.json", "w") as f:
        json.dump(cfg, f, indent=4)

    return cfg


# ==================== BÚSQUEDA DE VUELOS ====================

def search_all_sources(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    config: Dict,
    driver = None
) -> List[Dict]:
    """
    Busca vuelos en todas las fuentes configuradas.
    """
    all_flights = []

    # RyanAir
    if "ryanair" in config.get("SOURCES", []):
        try:
            logging.info(f"RyanAir: {origin} → {destination}")
            data = search_ryanair_roundtrip(
                origin, destination, departure_date, return_date,
                adults=config["PASSENGERS"]["adults"],
                children=int(config["PASSENGERS"]["children"].split("[")[0]) if "[" in config["PASSENGERS"]["children"] else 0
            )
            if data:
                flights = extract_ryanair_flights(data)
                all_flights.extend(flights)
                logging.info(f"  → {len(flights)} vuelos encontrados")
        except Exception as e:
            logging.warning(f"Error RyanAir: {e}")

    # Google Flights
    if "google" in config.get("SOURCES", []) and driver:
        try:
            logging.info(f"Google Flights: {origin} → {destination}")
            flights = search_google_flights(origin, destination, departure_date, return_date, driver)
            if flights:
                all_flights.extend(flights)
                logging.info(f"  → {len(flights)} vuelos encontrados")
        except Exception as e:
            logging.warning(f"Error Google Flights: {e}")

    return all_flights


def find_best_combinations(
    outbound_flights: List[Dict],
    return_flights: List[Dict],
    min_stay: int,
    max_stay: int,
    num_adults: int,
    num_children: int
) -> List[Dict]:
    """
    Combina vuelos de ida y vuelta respetando duración de estancia.
    """
    combinations = []

    if not outbound_flights or not return_flights:
        logging.warning(f"Vuelos insuficientes: IDA={len(outbound_flights)}, VUELTA={len(return_flights)}")
        return combinations

    for out_flight in outbound_flights:
        for ret_flight in return_flights:
            try:
                # Extraer fechas (pueden estar en varios formatos)
                out_date_str = out_flight.get("Fecha", "")
                ret_date_str = ret_flight.get("Fecha", "")

                # Intentar parsear fecha
                try:
                    if "T" in out_date_str:
                        out_date = datetime.fromisoformat(out_date_str.split("T")[0])
                    else:
                        out_date = datetime.strptime(out_date_str, "%Y-%m-%d")

                    if "T" in ret_date_str:
                        ret_date = datetime.fromisoformat(ret_date_str.split("T")[0])
                    else:
                        ret_date = datetime.strptime(ret_date_str, "%Y-%m-%d")
                except:
                    continue

                # Calcular días de estancia
                stay_days = (ret_date - out_date).days

                if not (min_stay <= stay_days <= max_stay):
                    continue

                # Calcular precios
                out_price = float(out_flight.get("Precio", 0))
                ret_price = float(ret_flight.get("Precio", 0))
                total_price = out_price + ret_price
                total_family = total_price * (num_adults + num_children)

                combination = {
                    "Ida_Fecha": out_date_str,
                    "Ida_Hora": f"{out_flight.get('Hora_Salida')} → {out_flight.get('Hora_Llegada')}",
                    "Ida_Aerolínea": out_flight.get("Aerolínea"),
                    "Ida_Precio": out_price,

                    "Vuelta_Fecha": ret_date_str,
                    "Vuelta_Hora": f"{ret_flight.get('Hora_Salida')} → {ret_flight.get('Hora_Llegada')}",
                    "Vuelta_Aerolínea": ret_flight.get("Aerolínea"),
                    "Vuelta_Precio": ret_price,

                    "Días": stay_days,
                    "Precio_Total": f"€{total_price:.2f}",
                    "Precio_Familia": f"€{total_family:.2f}",
                }
                combinations.append(combination)

            except Exception as e:
                logging.debug(f"Error combinando vuelos: {e}")
                continue

    # Ordenar por precio
    combinations.sort(key=lambda x: float(x["Precio_Total"].replace("€", "")))
    return combinations


def print_results(combinations: List[Dict], limit: int = 10):
    """Imprime resultados de forma bonita"""
    if not combinations:
        print("\n❌ No se encontraron combinaciones válidas.")
        return

    print(f"\n✅ Encontradas {len(combinations)} combinaciones válidas\n")

    for i, combo in enumerate(combinations[:limit], 1):
        print(f"{'─' * 80}")
        print(f"OPCIÓN {i}")
        print(f"{'─' * 80}")
        print(f"IDA:      {combo['Ida_Fecha']} | {combo['Ida_Hora']} | {combo['Ida_Aerolínea']} | €{combo['Ida_Precio']:.2f}")
        print(f"VUELTA:   {combo['Vuelta_Fecha']} | {combo['Vuelta_Hora']} | {combo['Vuelta_Aerolínea']} | €{combo['Vuelta_Precio']:.2f}")
        print(f"ESTANCIA: {combo['Días']} días")
        print(f"TOTAL:    {combo['Precio_Total']} por persona")
        print(f"FAMILIA:  {combo['Precio_Familia']}")


# ==================== MAIN ====================

def main():
    parser = argparse.ArgumentParser(description="Buscador de Vuelos Privado")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verbose")
    parser.add_argument("--load", "-l", action="store_true", help="Cargar última búsqueda")
    parser.add_argument("--gui", action="store_true", help="Usar navegador (no headless)")
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Obtener configuración
    if args.load:
        cfg = load_saved_config() or get_user_input()
    else:
        cfg = get_user_input()

    print(f"\nBuscando vuelos usando: {', '.join(cfg['SOURCES'])}")

    # Inicializar WebDriver si necesita Google Flights
    driver = None
    if "google" in cfg["SOURCES"]:
        try:
            logging.info("Inicializando navegador para Google Flights...")
            driver = setup_edge_driver(headless=not args.gui, user_agent=random.choice(USER_AGENTS))
        except Exception as e:
            logging.warning(f"No se pudo inicializar navegador: {e}")
            logging.warning("Continuando solo con RyanAir...")
            cfg["SOURCES"] = [s for s in cfg["SOURCES"] if s != "google"]

    try:
        t_start = time.time()
        all_combinations = []

        # Procesar cada par origen-destino
        for origin in cfg["AIRPORTS"]:
            for destination in cfg["DESTINATIONS"]:
                logging.info(f"Procesando: {origin} → {destination}")

                # Calcular fechas
                from_date = datetime.strptime(cfg["DATES"]["from"], "%d/%m/%Y")
                to_date = datetime.strptime(cfg["DATES"]["to"], "%d/%m/%Y")

                # Rango de fechas de salida
                date_range_days = (to_date - from_date).days - cfg["STAY_DURATION"]["min_days"]

                # Buscar múltiples fechas de salida (cada 3 días para no saturar)
                for days_offset in range(0, min(date_range_days + 1, 30), 3):
                    dep_date = from_date + timedelta(days=days_offset)
                    dep_str = dep_date.strftime("%d/%m/%Y")

                    # Buscar vuelos de ida y vuelta
                    outbound = search_all_sources(origin, destination, dep_str, to_date.strftime("%d/%m/%Y"), cfg, driver)
                    return_flights = search_all_sources(destination, origin, to_date.strftime("%d/%m/%Y"), dep_str, cfg, driver)

                    # Combinar
                    combos = find_best_combinations(
                        outbound, return_flights,
                        cfg["STAY_DURATION"]["min_days"],
                        cfg["STAY_DURATION"]["max_days"],
                        cfg["PASSENGERS"]["adults"],
                        int(cfg["PASSENGERS"]["children"].split("[")[0]) if "[" in cfg["PASSENGERS"]["children"] else 0
                    )
                    all_combinations.extend(combos)

                    random_delay(1, 2)

        t_total = time.time() - t_start

        # Mostrar resultados
        all_combinations.sort(key=lambda x: float(x["Precio_Total"].replace("€", "")))
        print_results(all_combinations[:cfg["MAX_RESULTS"]], limit=cfg["MAX_RESULTS"])

        # Guardar JSON
        if all_combinations:
            with open(cfg["OUTPUT_FILE"], "w") as f:
                json.dump(all_combinations, f, indent=2, ensure_ascii=False)
            logging.info(f"Resultados guardados en {cfg['OUTPUT_FILE']}")

        print(f"\n⏱️  Búsqueda completada en {t_total:.1f}s")

    except KeyboardInterrupt:
        print("\n⚠️  Búsqueda interrumpida por usuario")
    except Exception as e:
        logging.error(f"Error durante búsqueda: {e}", exc_info=True)
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    main()
