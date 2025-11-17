import os, sys, json, time, random, logging, argparse, concurrent.futures, multiprocessing
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By

from webdriver_utils import setup_edge_driver, wait_for_elements, get_element_safely, get_elements_safely, random_delay, get_random_proxy
from flight_parser import (parse_flight_details, find_best_combinations, format_combination_table, build_expedia_url,
                          generate_date_range, save_results_json, save_results_text, fix_unicode_arrows)

try: from kiwi_api import search_flights, extract_flights; KIWI_AVAILABLE = True
except: KIWI_AVAILABLE = False

try: from skyscanner_api import search_skyscanner, extract_sky_flights; SKYSCANNER_AVAILABLE = True
except: SKYSCANNER_AVAILABLE = False

try: from amadeus_api import search_flights as amadeus_search, extract_amadeus_flights; AMADEUS_AVAILABLE = True
except: AMADEUS_AVAILABLE = False

DEFAULT_CONFIG = {
    "AIRPORTS": ["MUC", "FMM", "NUR"], "DESTINATIONS": ["JRO"],
    "PASSENGERS": {"adults": 2, "children": "2[12;12]", "seniors": 0, "infantinlap": "Y"},
    "DATES": {"from": "6/6/2025", "to": "22/6/2025"},
    "TIMEOUTS": {"selenium": 60, "retry": 3}, "REQUEST_DELAY": (1, 3),
    "STAY_DURATION": {"min_days": 8, "max_days": 14},
    "DIRECT_FLIGHTS_ONLY": False, "MAX_STOPS": 1, "CABIN_CLASS": "economy",
    "MAX_WORKERS": min(multiprocessing.cpu_count() - 1, 8), "MAX_RETRIES": 3,
    "API_SOURCES": ["expedia"],
    "USER_AGENTS": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    ],
    "SELECTORS": {
        "flight_card": "li[data-test-id='offer-listing']", 
        "flight_details": "button span",
        "no_results": "/html/body/div[2]/div[1]/div/div[2]/div[3]/div/div/div/main/div[3]/div/div[1]",
        "empty_state": "div.uitk-empty-state-body",
        "details_toggle": "button[data-test-id='offer-listing-details-toggle']",
        "flight_segment": "div[data-test-id='flight-segment']",
        "arrival_airport": "span[data-test-id='arrival-airport']",
        "layover_duration": "div[data-test-id='layover-duration']"
    },
    "OUTPUT_FILE": "resultados_vuelos.json", "MAX_RESULTS": 20, "USE_PROXIES": False
}

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s",
                        handlers=[logging.FileHandler("flight_scraper.log", encoding="utf-8"), 
                                  logging.StreamHandler(sys.stdout)])
    
    if sys.stdout.encoding != 'utf-8':
        try: sys.stdout.reconfigure(encoding='utf-8')
        except: pass
    
    for logger in ["selenium", "urllib3"]: logging.getLogger(logger).setLevel(logging.WARNING)

def get_user_input():
    cfg = DEFAULT_CONFIG.copy()
    print("\n===== Buscador de Vuelos Mejorado =====\nPresiona Enter para valores predeterminados.\n")
    
    # Campos básicos
    for key, prompt in [("AIRPORTS", f"Aeropuertos origen [{', '.join(cfg['AIRPORTS'])}]: "), 
                        ("DESTINATIONS", f"Destinos [{', '.join(cfg['DESTINATIONS'])}]: ")]:
        inp = input(prompt)
        if inp.strip(): cfg[key] = [x.strip().upper() for x in inp.split(",")]
    
    # Fechas y estancia
    for key, subkey, prompt in [
        ("DATES", "from", f"Fecha mín salida (DD/MM/YYYY) [{cfg['DATES']['from']}]: "),
        ("DATES", "to", f"Fecha máx regreso [{cfg['DATES']['to']}]: "),
        ("STAY_DURATION", "min_days", f"Estancia mínima [{cfg['STAY_DURATION']['min_days']}]: "),
        ("STAY_DURATION", "max_days", f"Estancia máxima [{cfg['STAY_DURATION']['max_days']}]: ")]:
        inp = input(prompt)
        if inp.strip() and (not subkey.endswith('days') or inp.isdigit()):
            cfg[key][subkey] = int(inp) if subkey.endswith('days') else inp
    
    # Pasajeros
    cfg["PASSENGERS"]["adults"] = int(input(f"Adultos [{cfg['PASSENGERS']['adults']}]: ") or cfg["PASSENGERS"]["adults"])
    children = input("Niños [0]: ")
    if children.strip() and children.isdigit() and int(children) > 0:
        ages = [input(f"Edad niño {i+1} [11]: ").strip() or "11" for i in range(int(children))]
        cfg["PASSENGERS"]["children"] = f"{children}[{';'.join(ages)}]"
    elif children.strip() and children.isdigit(): cfg["PASSENGERS"]["children"] = "0"
    
    # Preferencias de vuelo
    cfg["DIRECT_FLIGHTS_ONLY"] = input("¿Solo directos? (s/n) [n]: ").lower().startswith('s')
    if not cfg["DIRECT_FLIGHTS_ONLY"]:
        max_stops = input(f"Escalas máx [{cfg['MAX_STOPS']}]: ")
        if max_stops.strip() and max_stops.isdigit(): cfg["MAX_STOPS"] = int(max_stops)
    
    # Clase y resultados
    cabin = input(f"Clase (economy,premium,business,first) [{cfg['CABIN_CLASS']}]: ").lower()
    if cabin in ["economy", "premium", "business", "first"]: cfg["CABIN_CLASS"] = cabin
    max_results = input(f"Resultados a mostrar [{cfg['MAX_RESULTS']}]: ")
    if max_results.strip() and max_results.isdigit(): cfg["MAX_RESULTS"] = int(max_results)
    
    # Opciones avanzadas
    if input("\n¿Opciones avanzadas? (s/n) [n]: ").lower().startswith('s'):
        # Configuración técnica
        for key, prompt, typ in [
            ("MAX_WORKERS", f"Búsquedas paralelas [{cfg['MAX_WORKERS']}]: ", int),
            ("MAX_RETRIES", f"Intentos reconexión [{cfg['MAX_RETRIES']}]: ", int),
            ("OUTPUT_FILE", f"Archivo salida [{cfg['OUTPUT_FILE']}]: ", str)]:
            inp = input(prompt)
            if inp.strip() and (typ != int or inp.isdigit()): cfg[key] = typ(inp)
                
        # Fuentes de datos
        print("\nFuentes disponibles:")
        sources = {"1": "expedia"}
        if KIWI_AVAILABLE: sources["2"] = "kiwi"; print("2. Kiwi.com API")
        if SKYSCANNER_AVAILABLE: sources["3"] = "skyscanner"; print("3. Skyscanner API")
        if AMADEUS_AVAILABLE: sources["4"] = "amadeus"; print("4. Amadeus API")
        print(f"1. Expedia (predeterminado)")
        
        inp = input(f"Seleccione fuentes (coma): ")
        if inp.strip():
            sel_sources = [sources[s.strip()] for s in inp.split(',') if s.strip() in sources]
            if sel_sources: cfg["API_SOURCES"] = sel_sources
        
        # Configurar API keys
        handle_api_keys(cfg)
        cfg["USE_PROXIES"] = input("¿Usar proxies? (s/n) [n]: ").lower().startswith('s')
    
    # Guardar configuración
    with open("last_config.json", "w") as f:
        save_cfg = {k: v for k, v in cfg.items() if k not in ["USER_AGENTS", "SELECTORS"]}
        save_cfg["REQUEST_DELAY"] = list(cfg["REQUEST_DELAY"])
        json.dump(save_cfg, f, indent=4)
    
    return cfg

def handle_api_keys(cfg):
    """Configura API keys para los servicios seleccionados"""
    if "kiwi" in cfg["API_SOURCES"] and KIWI_AVAILABLE:
        from kiwi_api import API_KEY as KIWI_KEY
        if not KIWI_KEY:
            key = input("API Key para Kiwi.com: ")
            if key.strip(): 
                import kiwi_api
                kiwi_api.API_KEY = key
    
    if "skyscanner" in cfg["API_SOURCES"] and SKYSCANNER_AVAILABLE:
        from skyscanner_api import RAPID_KEY
        if not RAPID_KEY:
            key = input("Rapid API Key para Skyscanner: ")
            if key.strip(): 
                import skyscanner_api
                skyscanner_api.RAPID_KEY = key
                
    if "amadeus" in cfg["API_SOURCES"] and AMADEUS_AVAILABLE:
        from amadeus_api import AMADEUS_ID, AMADEUS_SECRET
        if not AMADEUS_ID or not AMADEUS_SECRET:
            client_id = input("Amadeus Client ID: ")
            client_secret = input("Amadeus Client Secret: ")
            if client_id.strip() and client_secret.strip():
                import amadeus_api
                amadeus_api.AMADEUS_ID = client_id
                amadeus_api.AMADEUS_SECRET = client_secret

def load_saved_config():
    try:
        if os.path.exists("last_config.json"):
            with open("last_config.json", "r") as f:
                cfg = json.load(f)
                cfg["USER_AGENTS"], cfg["SELECTORS"] = DEFAULT_CONFIG["USER_AGENTS"], DEFAULT_CONFIG["SELECTORS"]
                cfg["REQUEST_DELAY"] = tuple(cfg["REQUEST_DELAY"])
                if "API_SOURCES" not in cfg: cfg["API_SOURCES"] = DEFAULT_CONFIG["API_SOURCES"]
                return cfg
    except Exception as e: logging.warning(f"Error cargando config: {e}")
    return None

class FlightScraper:
    def __init__(self, config, headless=True):
        self.config, self.headless = config, headless
        self.driver_pool, self.max_retries = [], config.get("MAX_RETRIES", 3)
    
    def _get_driver_from_pool(self):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if not self.driver_pool:
                    proxy = get_random_proxy() if self.config.get("USE_PROXIES", False) else None
                    driver = setup_edge_driver(self.headless, random.choice(self.config['USER_AGENTS']), proxy)
                    driver.set_page_load_timeout(60)
                    return driver
                return self.driver_pool.pop()
            except Exception as e:
                if attempt < max_attempts - 1:
                    logging.warning(f"Error creando driver (intento {attempt+1}/{max_attempts}): {e}")
                    time.sleep(2)
                else: raise
    
    def _return_driver_to_pool(self, driver):
        try:
            if len(self.driver_pool) < self.config["MAX_WORKERS"]:
                driver.current_url
                self.driver_pool.append(driver)
            else: self._close_driver(driver)
        except: self._close_driver(driver)

    def _close_driver(self, driver): 
        try: driver.quit()
        except: pass

    def fetch_prices(self, origin, destination, dep_dates):
        results = []
        
        # Consultar Kiwi API
        if "kiwi" in self.config.get("API_SOURCES", []) and KIWI_AVAILABLE:
            for dep_date in dep_dates:
                logging.info(f"Kiwi: {origin} - {destination} | {dep_date}")
                try:
                    kiwi_data = search_flights(origin, destination, dep_date)
                    if kiwi_data:
                        flights = extract_flights(kiwi_data)
                        results.extend([{**f, "Origen": origin, "Destino": destination} 
                                      for f in flights if (not self.config["DIRECT_FLIGHTS_ONLY"] or f["Escalas"] == 0) 
                                      and f["Escalas"] <= self.config["MAX_STOPS"]])
                except Exception as e: logging.warning(f"Error Kiwi: {e}")
                    
        # Consultar Skyscanner API
        if "skyscanner" in self.config.get("API_SOURCES", []) and SKYSCANNER_AVAILABLE:
            for dep_date in dep_dates:
                logging.info(f"Skyscanner: {origin} - {destination} | {dep_date}")
                try:
                    sky_data = search_skyscanner(origin, destination, dep_date)
                    if sky_data:
                        flights = extract_sky_flights(sky_data)
                        results.extend([{**f, "Origen": origin, "Destino": destination} 
                                      for f in flights if (not self.config["DIRECT_FLIGHTS_ONLY"] or f["Escalas"] == 0) 
                                      and f["Escalas"] <= self.config["MAX_STOPS"]])
                except Exception as e: logging.warning(f"Error Skyscanner: {e}")
        
        # Consultar Amadeus API
        if "amadeus" in self.config.get("API_SOURCES", []) and AMADEUS_AVAILABLE:
            for dep_date in dep_dates:
                logging.info(f"Amadeus: {origin} - {destination} | {dep_date}")
                try:
                    amadeus_data = amadeus_search(origin, destination, dep_date, 
                                                direct=self.config["DIRECT_FLIGHTS_ONLY"], 
                                                adults=self.config["PASSENGERS"]["adults"])
                    if amadeus_data:
                        flights = extract_amadeus_flights(amadeus_data)
                        results.extend([{**f, "Origen": origin, "Destino": destination} 
                                      for f in flights if (not self.config["DIRECT_FLIGHTS_ONLY"] or f["Escalas"] == 0) 
                                      and f["Escalas"] <= self.config["MAX_STOPS"]])
                except Exception as e: logging.warning(f"Error Amadeus: {e}")
        
        # Web scraping de Expedia
        if "expedia" in self.config.get("API_SOURCES", []) or not results:
            driver, retry_count = self._get_driver_from_pool(), 0

            for dep_date in dep_dates:
                url = build_expedia_url(origin, destination, dep_date, self.config)
                logging.info(f"Expedia: {origin} - {destination} | {dep_date}")

                while retry_count < self.max_retries:
                    try:
                        driver.get(url)
                        random_delay(*self.config["REQUEST_DELAY"])

                        # Check no results
                        no_res = get_element_safely(driver, self.config["SELECTORS"]["no_results"], By.XPATH)
                        empty = get_element_safely(driver, self.config["SELECTORS"]["empty_state"])
                        
                        if (no_res and "couldn't find any flights" in no_res.text) or \
                           (empty and "might not have regularly scheduled flights" in empty.text):
                            logging.info(f"No hay vuelos: {origin} -> {destination} | {dep_date}")
                            break

                        # Get flights
                        try:
                            wait_for_elements(driver, self.config["SELECTORS"]["flight_card"], 
                                            timeout=self.config["TIMEOUTS"]["selenium"])
                        except: 
                            logging.info(f"Timeout: {origin} -> {destination} | {dep_date}")
                            break

                        # Process flights
                        for flight in get_elements_safely(driver, self.config["SELECTORS"]["flight_card"]):
                            try:
                                details = get_element_safely(flight, self.config["SELECTORS"]["flight_details"])
                                if not details: continue
                                
                                airline, dep_time, orig_txt, arr_time, dest_txt, price, duration, stops = \
                                    parse_flight_details(details.text)
                                
                                if self.config["DIRECT_FLIGHTS_ONLY"] and stops > 0: continue
                                if stops > self.config["MAX_STOPS"]: continue

                                # Capturar detalles de escalas
                                stopover_details = []
                                if stops > 0:
                                    toggle = get_element_safely(flight, self.config["SELECTORS"]["details_toggle"])
                                    if toggle:
                                        toggle.click()
                                        random_delay(1, 2)
                                        segments = get_elements_safely(flight, self.config["SELECTORS"]["flight_segment"])
                                        for i in range(len(segments) - 1):
                                            try:
                                                airport = get_element_safely(segments[i], self.config["SELECTORS"]["arrival_airport"]).text
                                                layover = get_element_safely(segments[i], self.config["SELECTORS"]["layover_duration"]).text
                                                stopover_details.append({"airport": airport, "duration": layover})
                                            except: pass

                                results.append({
                                    "Origen": origin, "Destino": destination, "Día": dep_date,
                                    "Hora_Salida": dep_time, "Hora_Llegada": arr_time,
                                    "Compañía": airline, "Duración": duration, 
                                    "Escalas": stops, "Precio": price,
                                    "Detalles_Escalas": stopover_details
                                })
                            except Exception as e: logging.debug(f"Error vuelo: {e}")
                        
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        logging.warning(f"Error búsqueda (intento {retry_count}/{self.max_retries}): {e}")
                        if retry_count >= self.max_retries:
                            logging.warning(f"Demasiados errores: {origin}->{destination} | {dep_date}")
                            self._close_driver(driver)
                            driver = self._get_driver_from_pool()
                            retry_count = 0
                        random_delay(2, 4)
                
                retry_count = 0
            
            self._return_driver_to_pool(driver)
        
        return results

    def process_airport_pair(self, origin, destination):
        logging.info(f"Procesando: {origin} - {destination}")
        
        # Calculate date ranges
        from_date = datetime.strptime(self.config["DATES"]["from"], "%d/%m/%Y")
        to_date = datetime.strptime(self.config["DATES"]["to"], "%d/%m/%Y")
        date_range = (to_date - from_date).days - self.config["STAY_DURATION"]["min_days"]
        
        outbound_dates = generate_date_range(self.config["DATES"]["from"], 0, date_range)
        return_dates = generate_date_range(self.config["DATES"]["to"], date_range, 0)
        
        # Get outbound and return flights
        outbound_flights = self.fetch_prices(origin, destination, outbound_dates)
        return_flights = self.fetch_prices(destination, origin, return_dates)
        
        # Find best combinations
        combinations = find_best_combinations(
            outbound_flights, return_flights,
            self.config["STAY_DURATION"]["min_days"],
            self.config["STAY_DURATION"]["max_days"],
            self.config["PASSENGERS"]["adults"],
            int(self.config["PASSENGERS"]["children"].split("[")[0]) if "[" in self.config["PASSENGERS"]["children"] else 0
        )
        
        return {
            "origin": origin, "destination": destination,
            "combinations": combinations[:self.config["MAX_RESULTS"]]
        }

    def close(self): 
        [self._close_driver(d) for d in self.driver_pool]
        self.driver_pool = []

def main():
    parser = argparse.ArgumentParser(description="Buscador de Vuelos Multi-API")
    parser.add_argument("--load", "-l", action="store_true", help="Cargar config guardada")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose")
    parser.add_argument("--headless", action="store_true", default=True, help="Sin interfaz")
    parser.add_argument("--max-workers", type=int, help="Procesos paralelos")
    parser.add_argument("--apis", type=str, help="Fuentes (expedia,kiwi,skyscanner,amadeus)")
    parser.add_argument("--proxies", action="store_true", help="Usar proxies rotativas")
    args = parser.parse_args()
    
    # Corregir problemas de Unicode
    fix_unicode_arrows(".")
    
    setup_logging(args.verbose)
    config = load_saved_config() if args.load and load_saved_config() else get_user_input()
    if args.max_workers: config["MAX_WORKERS"] = args.max_workers
    if args.apis: config["API_SOURCES"] = [s.strip() for s in args.apis.split(",")]
    if args.proxies: config["USE_PROXIES"] = True
    
    scraper = FlightScraper(config, headless=args.headless)
    print(f"\nBuscando vuelos usando: {', '.join(config['API_SOURCES'])}")
    
    try:
        t_start = time.time()
        pairs = [(o, d) for o in config["AIRPORTS"] for d in config["DESTINATIONS"]]
        all_results, all_combinations = [], []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["MAX_WORKERS"]) as ex:
            futures = {ex.submit(scraper.process_airport_pair, o, d): (o, d) for o, d in pairs}
            
            for future in concurrent.futures.as_completed(futures):
                o, d = futures[future]
                try:
                    result = future.result()
                    all_results.append(result)
                    all_combinations.extend(result["combinations"])
                    logging.info(f"Completado: {o} - {d}")
                except Exception as e:
                    logging.error(f"Error en {o} - {d}: {e}")
        
        best_combinations = sorted(all_combinations, key=lambda x: float(x["Precio_Total"]))[:config["MAX_RESULTS"]]
        t_total = time.time() - t_start
        
        if best_combinations:
            print(f"\nMejores combinaciones ({t_total:.1f}s):")
            print(format_combination_table(best_combinations))
            save_results_json(all_results, config["OUTPUT_FILE"])
            save_results_text(best_combinations)
            print(f"\nMejor opción: {best_combinations[0]['Precio_Total']}€/persona ({best_combinations[0]['Días_Estancia']} días)")
            if "Precio_Total_Familia" in best_combinations[0]:
                print(f"Precio total familia: {best_combinations[0]['Precio_Total_Familia']}€")
            print(f"- Ida: {best_combinations[0]['Ida_Fecha']} {best_combinations[0]['Ida_Ruta']} - {best_combinations[0]['Ida_Compañía']}")
            print(f"- Vuelta: {best_combinations[0]['Vuelta_Fecha']} {best_combinations[0]['Vuelta_Ruta']} - {best_combinations[0]['Vuelta_Compañía']}")
            
            if "Detalles_Escalas" in best_combinations[0] and best_combinations[0]["Detalles_Escalas"]:
                print("\nDetalles de escalas:")
                for i, escala in enumerate(best_combinations[0]["Detalles_Escalas"]):
                    print(f"- Escala {i+1}: Aeropuerto {escala['airport']}, duración: {escala['duration']}")
                    
            if "Enlaces" in best_combinations[0]:
                print("\nReservar en:")
                for name, url in best_combinations[0]["Enlaces"].items():
                    print(f"- {name.capitalize()}: {url}")
        else:
            print("\nNo se encontraron combinaciones válidas.")

    except KeyboardInterrupt:
        print("\nBúsqueda interrumpida.")
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
    finally:
        scraper.close()
        sys.exit(0)

if __name__ == "__main__":
    main()