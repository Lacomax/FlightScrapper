# FlightScrapper - Buscador Multi-API de Vuelos

Sistema avanzado y modular para búsqueda comparativa de vuelos entre múltiples proveedores en tiempo real, optimizado para encontrar las mejores combinaciones de vuelos ida y vuelta.

## 📋 Descripción

**FlightScrapper** es un proyecto Python que integra múltiples fuentes de datos de vuelos para proporcionar búsquedas rápidas, precisas y baratas. Combina web scraping con acceso a APIs oficiales para ofrecer la máxima cobertura.

### Fuentes de Datos Soportadas

| Fuente | Método | Cobertura | Velocidad | Limitaciones |
|--------|--------|-----------|-----------|--------------|
| **Expedia** | Web Scraping | Global | Media | Requiere Selenium |
| **Kiwi.com** | API (Tequila) | Excelente | Rápida | Rate limit: 180/min |
| **Skyscanner** | API (RapidAPI) | Excelente | Rápida | Limitado por plan |
| **Amadeus** | API Oficial | Excelente | Rápida | Requiere credenciales |

## 🚀 Características Principales

- ✅ **Búsqueda Multi-Origen**: Busca desde múltiples aeropuertos simultáneamente
- ✅ **Comparación Automática**: Combina resultados de múltiples fuentes
- ✅ **Matching Inteligente**: Encuentra mejores combinaciones ida/vuelta
- ✅ **Filtrado Avanzado**: Directos, máximo de escalas, clase de cabina
- ✅ **Caché Automático**: Evita búsquedas redundantes (hasta 1 hora)
- ✅ **Reintentos Inteligentes**: Recuperación automática ante errores
- ✅ **Proxies Rotativos**: Obtención y validación automática de proxies
- ✅ **Paralelización**: ThreadPoolExecutor para máxima eficiencia
- ✅ **Configuración Persistente**: Guarda tu último búsqueda
- ✅ **Exportación Flexible**: JSON y texto formateado
- ✅ **Logging Detallado**: Rastreo completo de operaciones

## 📦 Instalación

### Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd FlightScrapper
```

2. **Crear entorno virtual (recomendado)**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env y agregar tus credenciales de API
```

## ⚙️ Configuración

### Variables de Entorno (.env)

```ini
# Kiwi.com API
KIWI_API_KEY=tu_api_key_aqui

# Skyscanner via RapidAPI
RAPID_API_KEY=tu_rapid_api_key_aqui

# Amadeus API
AMADEUS_CLIENT_ID=tu_client_id_aqui
AMADEUS_CLIENT_SECRET=tu_client_secret_aqui

# Opciones
USE_PROXIES=false
HEADLESS_MODE=true
SELENIUM_TIMEOUT=60
```

### Obtener Credenciales de APIs

#### 1. Kiwi.com (Tequila API)
- Ir a https://tequila.kiwi.com/portal/login
- Crear cuenta de desarrollador
- Copiar API Key a `.env`

#### 2. Skyscanner (via RapidAPI)
- Ir a https://rapidapi.com/skyscanner/api/skyscanner-flight-search
- Suscribirse al plan gratuito o de pago
- Copiar API Key a `.env`

#### 3. Amadeus
- Ir a https://developers.amadeus.com
- Crear aplicación
- Copiar Client ID y Secret a `.env`

## 📚 Estructura del Proyecto

```
FlightScrapper/
├── flight_scraper_main.py      # Script principal de orquestación
├── flight_parser.py             # Procesamiento y parseo de datos
├── webdriver_utils.py           # Utilidades de Selenium
├── amadeus_api.py               # Integración Amadeus
├── kiwi_api.py                  # Integración Kiwi.com
├── skyscanner_api.py            # Integración Skyscanner
├── proxies.py                   # Gestión de proxies
├── requirements.txt             # Dependencias Python
├── .env.example                 # Plantilla de variables de entorno
├── last_config.json             # Configuración guardada
└── README.md                    # Este archivo
```

### Descripción de Módulos

| Módulo | Responsabilidad |
|--------|-----------------|
| **flight_scraper_main.py** | Orquestación, UI interactiva, control de flujo |
| **flight_parser.py** | Parseo de datos, combinación de vuelos, exportación |
| **webdriver_utils.py** | Inicialización de Selenium, manejo de navegador |
| **amadeus_api.py** | Búsqueda y extracción desde API Amadeus |
| **kiwi_api.py** | Búsqueda y extracción desde API Kiwi.com |
| **skyscanner_api.py** | Búsqueda y extracción desde API Skyscanner |
| **proxies.py** | Obtención, validación y gestión de proxies |

## 🎯 Uso

### Ejecución Básica

```bash
python flight_scraper_main.py
```

Se te pedirá que ingreses:
- Aeropuertos de origen (códigos IATA, ej: MUC, VIE)
- Destino (código IATA, ej: JRO)
- Fecha mínima de salida (DD/MM/YYYY)
- Fecha máxima de retorno (DD/MM/YYYY)
- Duración mínima/máxima de estancia
- Número de adultos y niños
- Preferencias de vuelo (directos, escalas)

### Opciones de Línea de Comandos

```bash
# Usar configuración guardada
python flight_scraper_main.py --load

# Modo verbose (debug)
python flight_scraper_main.py --verbose

# Especificar fuentes
python flight_scraper_main.py --apis expedia,kiwi,skyscanner

# Usar proxies
python flight_scraper_main.py --proxies

# Modo GUI (sin interfaz visual)
python flight_scraper_main.py --headless

# Máximo de búsquedas paralelas
python flight_scraper_main.py --max-workers 5

# Combinación
python flight_scraper_main.py --load --verbose --apis kiwi,amadeus
```

## 📊 Ejemplos de Uso

### Ejemplo 1: Búsqueda Simple

```bash
$ python flight_scraper_main.py

===== Buscador de Vuelos Mejorado =====
Presiona Enter para valores predeterminados.

Aeropuertos origen [MUC, FMM, NUR]: MUC, VIE
Destinos [JRO]: JRO
Fecha mín salida (DD/MM/YYYY) [6/6/2025]: 10/06/2025
Fecha máx regreso [22/6/2025]: 20/06/2025
Estancia mínima [8]: 7
Estancia máxima [14]: 10
Adultos [2]: 2
Niños [0]: 2
¿Solo directos? (s/n) [n]: n
Escalas máx [1]: 2
Clase [economy]: economy
```

### Ejemplo 2: Búsqueda Rápida con Config Guardada

```bash
python flight_scraper_main.py --load --verbose
```

### Ejemplo 3: Búsqueda con APIs Específicas

```bash
python flight_scraper_main.py --apis kiwi,amadeus --max-workers 8
```

## 📁 Archivos de Salida

Después de una búsqueda exitosa, se generan:

### 1. **resultados_vuelos.json**
Contiene todos los vuelos encontrados en formato JSON:
```json
[
  {
    "origin": "MUC",
    "destination": "JRO",
    "combinations": [
      {
        "Ida_Fecha": "10/06/2025",
        "Ida_Precio": "€350.00",
        "Vuelta_Fecha": "20/06/2025",
        "Vuelta_Precio": "€380.00",
        "Precio_Total": "€730.00",
        "Precio_Total_Familia": "€2920.00"
      }
    ]
  }
]
```

### 2. **resultados_vuelos.txt**
Tabla formateada legible:
```
════════════════════════════════════════════════════════════════════════════════════════════════════════

                    MEJORES COMBINACIONES DE VUELOS

════════════════════════════════════════════════════════════════════════════════════════════════════════

OPCIÓN #1
────────────────────────────────────────────────────────────────────────────────────────────────────────

VUELO DE IDA:
  Fecha:       10/06/2025
  Ruta:        MUC → JRO
  Hora:        09:15 → 20:45
  Compañía:    Lufthansa
  Duración:    12h 30m
  Escalas:     1
  Precio:      €350.00

VUELO DE VUELTA:
  ...
```

## 🔧 Configuración Avanzada

### Control de Paralelización

```python
# En flight_scraper_main.py
DEFAULT_CONFIG["MAX_WORKERS"] = 4  # Número de búsquedas simultáneas
```

### Ajuste de Timeouts

```python
DEFAULT_CONFIG["TIMEOUTS"] = {
    "selenium": 60,  # segundos
    "retry": 3       # intentos
}
```

### Desactivar Fuentes

```python
DEFAULT_CONFIG["API_SOURCES"] = ["expedia", "kiwi"]  # Excluir skyscanner y amadeus
```

## ⚠️ Limitaciones y Consideraciones

### Rate Limiting

- **Kiwi.com**: 180 peticiones/minuto
- **Skyscanner**: Depende del plan RapidAPI
- **Amadeus**: Depende del plan de desarrollador

Para evitar bloqueos:
- Usar caché (automático, 30-60 minutos)
- Activar proxies rotativos
- Distribuir búsquedas en el tiempo

### Proxies Gratuitos

⚠️ Los proxies gratuitos tienen limitaciones:
- Velocidad lenta
- Confiabilidad variable
- Pueden estar bloqueados
- Se validan automáticamente

Para producción, usar proxies de pago.

### Selectores de Expedia

Los selectores de Expedia pueden cambiar con actualizaciones del sitio. Si el scraping falla:

```python
# Actualizar selectores en DEFAULT_CONFIG
"SELECTORS": {
    "flight_card": "li[data-test-id='offer-listing']",
    # ... otros selectores
}
```

## 🐛 Solución de Problemas

### "ModuleNotFoundError: No module named 'selenium'"

```bash
pip install -r requirements.txt
```

### "AMADEUS_CLIENT_ID/SECRET no configurados"

```bash
# Editar .env y añadir credenciales
nano .env  # o tu editor preferido
```

### "No se encuentran vuelos"

1. Verificar códigos IATA: https://www.iata.org/
2. Probar con otras fechas
3. Ejecutar con `--verbose` para ver logs detallados
4. Verificar que las APIs estén configuradas correctamente

### "Rate limit alcanzado"

```bash
# Esperar o usar proxies
python flight_scraper_main.py --proxies
```

## 📈 Performance

Tiempos típicos de búsqueda (para 3 orígenes x 1 destino):

| Modo | Tiempo | Fuentes |
|------|--------|---------|
| Solo Expedia | 30-60s | 1 |
| Solo APIs | 5-15s | 3 |
| Combinado | 20-45s | 4 |
| Con Proxies | 60-120s | 4 |

## 🔐 Seguridad

- Las credenciales se almacenan en `.env` (no en código)
- Se pueden usar variables de entorno del sistema
- No se guardan datos sensibles en logs
- Los proxies se validan antes de usar

## 📝 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📧 Soporte

Para reportar bugs o sugerencias, crea un issue en el repositorio.

## 🙏 Agradecimientos

- Selenium: Web scraping
- Amadeus: API de vuelos oficial
- Kiwi.com: API Tequila
- RapidAPI: Comunidad y APIs

## ⚡ Roadmap Futuro

- [ ] Integración con Google Flights API
- [ ] Base de datos para histórico de precios
- [ ] Machine learning para predicción de precios
- [ ] Interfaz web (Flask/FastAPI)
- [ ] Notificaciones de cambios de precio
- [ ] Dashboard con gráficas
- [ ] Soporte para hoteles y coches
- [ ] Tests unitarios completos