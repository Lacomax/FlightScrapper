# FlightScrapper - Buscador Privado de Vuelos

Herramienta simple y privada para buscar vuelos usando:
- **Google Flights**: Web scraping con Selenium (múltiples fuentes de vuelos)

**Nota**: RyanAir cambió su API y ya no es accesible. Google Flights incluye
resultados de RyanAir de todas formas.

**Uso privado SOLO** - No comercial, no distribuido.

## 🚀 Características

- ✅ Búsqueda en Google Flights (múltiples aerolíneas)
- ✅ Renderizado completo de JavaScript con Selenium
- ✅ Combinación inteligente de vuelos ida + vuelta
- ✅ Filtrado por duración de estancia
- ✅ Persistencia de configuración (recuerda última búsqueda)
- ✅ Soporte para múltiples pasajeros (adultos + niños)
- ✅ Exportación a JSON
- ✅ Logging detallado

## 📦 Instalación

### Requisitos

- Python 3.8+
- Windows/Mac/Linux

### Pasos

1. **Clonar y entrar al directorio**
```bash
cd FlightScrapper
```

2. **Crear entorno virtual (opcional pero recomendado)**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Descargar WebDriver de Edge** (requerido para Google Flights)

Ver `WEBDRIVER_SETUP.md` para instrucciones detalladas.

## 🎯 Uso Rápido

```bash
# Búsqueda interactiva
python flight_scraper_main.py

# Cargar última búsqueda
python flight_scraper_main.py --load

# Con logs detallados
python flight_scraper_main.py --verbose

# Mostrar navegador (no headless)
python flight_scraper_main.py --gui
```

### Ejemplo Interactivo

```
===== Buscador de Vuelos (Google Flights) =====
Última búsqueda: MUC → JRO
Presiona Enter para valores de la última búsqueda.

Aeropuertos origen [MUC, FMM, NUR]: MUC
Destinos [JRO]: BCN

Fecha mín salida DD/MM/YYYY [6/6/2025]: 20/12/2025
Fecha máx regreso [22/6/2025]: 3/1/2026

Estancia mínima (o MAX) [8]: MAX
Estancia máxima [14]: 14

Adultos [2]: 2
Niños [2]: 2
Edad niño 1 [12]: 12
Edad niño 2 [12]: 12

Buscando vuelos usando: Google Flights
```

## 📁 Estructura

```
FlightScrapper/
├── flight_scraper_main.py      # Script principal
├── google_flights_scraper.py   # Scraper Google Flights (Selenium)
├── webdriver_utils.py          # Utilidades Selenium
├── webdrivers/                 # Carpeta para msedgedriver.exe
├── last_config.json            # Última configuración (auto-generado)
├── resultados_vuelos.json      # Resultados (auto-generado)
├── flight_scraper.log          # Logs (auto-generado)
├── requirements.txt            # Dependencias
├── WEBDRIVER_SETUP.md          # Guía configuración WebDriver
└── README.md                   # Este archivo
```

## 🔧 Configuración

### Parámetros de Búsqueda

Interactivamente se pregunta por:

| Parámetro | Ejemplo | Notas |
|-----------|---------|-------|
| Origen | MUC | Códigos IATA, separar con comas |
| Destino | BCN | Código IATA |
| Salida | 20/12/2025 | Formato DD/MM/YYYY |
| Regreso | 3/1/2026 | Formato DD/MM/YYYY |
| Est. mínima | 8 o MAX | MAX = auto-calcula máximo posible |
| Est. máxima | 14 | Días máximo permitido |
| Adultos | 2 | Número entero |
| Niños | 2 | Número entero |
| Edades | 12;12 | Separadas por punto y coma |

### last_config.json

Se guarda automáticamente tu última búsqueda:

```json
{
  "AIRPORTS": ["MUC"],
  "DESTINATIONS": ["BCN"],
  "PASSENGERS": {
    "adults": 2,
    "children": "2[12;12]"
  },
  "DATES": {
    "from": "20/12/2025",
    "to": "03/01/2026"
  },
  "STAY_DURATION": {
    "min_days": 8,
    "max_days": 14
  }
}
```

## 📊 Resultados

### Formato Console

```
────────────────────────────────────────────────────────
OPCIÓN 1
────────────────────────────────────────────────────────
IDA:      2025-12-20 | 14:00 → 18:30 | RyanAir | €199.99
VUELTA:   2026-01-03 | 09:15 → 15:45 | RyanAir | €199.99
ESTANCIA: 14 días
TOTAL:    €399.98 por persona
FAMILIA:  €1599.92
```

### Archivo resultados_vuelos.json

```json
[
  {
    "Ida_Fecha": "2025-12-20",
    "Ida_Hora": "14:00 → 18:30",
    "Ida_Aerolínea": "RyanAir",
    "Ida_Precio": 199.99,
    "Vuelta_Fecha": "2026-01-03",
    "Vuelta_Hora": "09:15 → 15:45",
    "Vuelta_Aerolínea": "RyanAir",
    "Vuelta_Precio": 199.99,
    "Días": 14,
    "Precio_Total": "€399.98",
    "Precio_Familia": "€1599.92"
  }
]
```

## 🔍 Troubleshooting

### Error: "Could not reach host" o versión mismatch
Ver `WEBDRIVER_SETUP.md` - Es un problema de versión de Edge WebDriver.
La versión del driver DEBE coincidir exactamente con tu Edge.

### Google Flights: "Timeout esperando resultados"
- Google Flights requiere esperar a JavaScript (normal, 30-60 segundos)
- Usa `--gui` para ver qué está haciendo
- Si la conexión es lenta, aumenta timeout en `google_flights_scraper.py`
- Timeout está configurado a 60 segundos (aumentar si es necesario)

### "0 vuelos encontrados"
- Comprobación: Los códigos IATA son correctos (3 letras)
- Puede no haber vuelos disponibles en esas fechas
- Intentar con diferentes fechas o rutas

## 📋 Requisitos

```
selenium>=4.15.0
requests>=2.31.0
webdriver-manager>=4.0.0
```

## ⚖️ Aviso Legal

**Uso privado solo**. No para:
- ❌ Distribución comercial
- ❌ Competencia con scrapers masivos
- ❌ Venta de datos
- ❌ Violación de Terms of Service

RyanAir API es oficial. Google Flights: respetar robots.txt.

## 📝 Logs

Archivo `flight_scraper.log` contiene:
- Todas las búsquedas realizadas
- Errores y warnings
- Debugging detallado (con `--verbose`)

## 🎓 Notas Técnicas

### Google Flights
- Carga con Selenium (JavaScript renderizado)
- Parsing de DOM con regex (frágil a cambios)
- Múltiples aerolíneas incluidas (RyanAir, Vueling, etc.)
- Timeout: 60 segundos (puedes aumentar en `google_flights_scraper.py`)
- Tiempo típico: 30-60 segundos por búsqueda

### Limitaciones Conocidas
- Google Flights actualiza su estructura HTML frecuentemente
- Si el parsing falla, el CSS selector puede necesitar actualización
- No es posible paralelizar múltiples búsquedas de forma segura con Selenium

## 🚀 Mejoras Futuras

- [ ] Soporte para más aerolíneas (EasyJet, Vueling)
- [ ] Cache de resultados
- [ ] Notificaciones por email si baja precio
- [ ] Interfaz gráfica (Qt/PySimpleGUI)
- [ ] Historial de búsquedas

## 📧 Soporte

Para problemas:
1. Ejecuta con `--verbose` y mira los logs
2. Revisa `flight_scraper.log`
3. Comprueba `WEBDRIVER_SETUP.md` para problemas de WebDriver

---

**FlightScrapper v2.1** - Solo Google Flights (RyanAir API ya no disponible).
