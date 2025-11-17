# Configuración del WebDriver de Edge

## Problema
Si ves el error `Could not reach host. Are you offline?` aunque tengas conexión, es porque `webdriver-manager` intenta descargar el driver desde internet pero falla.

## Solución: Usar msedgedriver.exe Local

### Opción 1: Descarga Manual (RECOMENDADO - Más Rápido)

1. **Determina la versión de tu Microsoft Edge:**
   - En Edge, ve a `Menu (⋯) → Configuración → Acerca de Microsoft Edge`
   - Anota el número de versión (ej: 131.0.2903.86)

2. **Descarga el WebDriver:**
   - Ve a: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
   - Descarga la versión que coincida con tu Edge
   - O directamente: https://edgedriver.azureedge.net/

3. **Coloca el archivo:**
   ```
   FlightScrapper/
   ├── webdrivers/
   │   └── msedgedriver.exe  ← Aquí va el archivo descargado
   ├── flight_scraper_main.py
   └── ...
   ```

4. **Verifica que existe:**
   ```powershell
   Test-Path ".\webdrivers\msedgedriver.exe"
   # Debe devolver: True
   ```

### Opción 2: Descargar Automáticamente (si tienes conexión)

Si webdriver-manager falla pero tu conexión es buena, ejecuta esto en PowerShell:

```powershell
# Crea el directorio si no existe
mkdir webdrivers -ErrorAction SilentlyContinue

# Descarga usando python (necesita internet)
python -c "
from webdriver_manager.microsoft import EdgeChromiumDriverManager
path = EdgeChromiumDriverManager().install()
print(f'Driver descargado en: {path}')
"
```

Luego copia el archivo a `webdrivers/msedgedriver.exe`.

### Opción 3: Si nada funciona - Usar Chrome en lugar de Edge

Cambia en `webdriver_utils.py`:

```python
# Cambiar de:
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
driver = webdriver.Edge(service=service, options=opts)

# A:
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
```

## Verificar que funciona

Ejecuta esto en PowerShell:

```powershell
cd FlightScrapper
python flight_scraper_main.py --apis expedia --verbose
```

Si ves logs de scraping sin el error "Could not reach host", ¡funciona!

## Más Info

- Edge WebDriver: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
- Versions: https://edgedriver.azureedge.net/
- Compatibilidad Edge: https://edgedriver.azureedge.net/LATEST_RELEASE_STABLE
