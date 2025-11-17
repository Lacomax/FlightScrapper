# FlightScraper Multi-API

Buscador de vuelos multi-origen con capacidad para consultar:
- Expedia (web scraping)
- Kiwi.com (API)
- Skyscanner (API via RapidAPI)
- Amadeus (API)

## Requisitos

```bash
pip install selenium requests cachetools webdriver-manager python-dotenv
```

## Estructura

- **flight_scraper_main.py**: Script principal
- **webdriver_utils.py**: Utilidades para Selenium
- **flight_parser.py**: Procesamiento de datos
- **proxies.py**: Gestión de proxies
- **kiwi_api.py**: Integración Kiwi.com
- **skyscanner_api.py**: Integración Skyscanner
- **amadeus_api.py**: Integración Amadeus

## Características

- Búsqueda en múltiples orígenes y destinos
- Comparación automática entre varias fuentes
- Rotación automática de proxies para evitar bloqueos
- Paralelización para máxima eficiencia
- Filtrado por vuelos directos, escalas máximas
- Configuración de fecha, estancia mínima/máxima
- Opciones para viajeros (adultos, niños)
- Generación de enlaces directos para reserva

## Uso

```bash
# Ejecución básica
python flight_scraper_main.py

# Usar configuración guardada previamente
python flight_scraper_main.py --load

# Especificar fuentes de datos
python flight_scraper_main.py --apis expedia,kiwi,skyscanner

# Modo debug y con proxies
python flight_scraper_main.py --verbose --proxies
```

## Configuración API

Para usar las APIs, necesitarás registrarte y obtener claves:

1. **Kiwi.com**: https://tequila.kiwi.com
2. **Skyscanner**: https://rapidapi.com/skyscanner/api/skyscanner-flight-search
3. **Amadeus**: https://developers.amadeus.com

Coloca tus claves en los archivos correspondientes o introdúcelas cuando el programa las solicite.

## Resultados

- **resultados_vuelos.json**: Datos completos en formato JSON
- **resultados_vuelos.txt**: Tabla formateada con las mejores combinaciones