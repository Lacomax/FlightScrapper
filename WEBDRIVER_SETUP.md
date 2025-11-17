# Configuración del WebDriver de Edge

## Problema
Si ves el error `Could not reach host. Are you offline?` aunque tengas conexión, es porque `webdriver-manager` intenta descargar el driver desde internet pero falla. También puedes ver:
```
This version of Microsoft Edge WebDriver only supports Microsoft Edge version X
Current browser version is Y with binary path...
```
Esto significa que la versión del WebDriver NO COINCIDE con tu versión de Edge.

## ⚠️ IMPORTANTE: La versión DEBE coincidir exactamente

El `msedgedriver.exe` para Edge 142 NO funciona con Edge 134, y viceversa. Debes descargar la versión exacta que instalaste.

## Solución: Usar msedgedriver.exe Local

### Opción 1: Descarga Manual (RECOMENDADO)

#### Paso 1: Verifica tu versión exacta de Edge

1. Abre Microsoft Edge
2. Ve a `Menu (⋯) → Configuración → Acerca de Microsoft Edge`
3. **Anota los 4 números completos** (ej: `142.0.3595.53`, no solo `142`)

#### Paso 2: Descarga el WebDriver correspondiente

**Método A - Desde Azure CDN (más rápido):**
```powershell
# Reemplaza VERSION con tu número completo (ej: 142.0.3595.53)
$version = "142.0.3595.53"
$url = "https://msedgedriver.azureedge.net/v${version}/edgedriver_win64.zip"
Invoke-WebRequest -Uri $url -OutFile "edgedriver.zip"
Expand-Archive "edgedriver.zip" -DestinationPath "webdrivers"
Remove-Item "edgedriver.zip"
```

**Método B - Desde sitio web:**
- Ve a: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
- Selecciona tu versión exacta
- Descarga (Windows 64-bit): `edgedriver_win64.zip`
- Extrae a la carpeta `webdrivers/`

#### Paso 3: Estructura de carpetas

```
FlightScrapper/
├── webdrivers/
│   └── msedgedriver.exe  ← Archivo extraído aquí
├── flight_scraper_main.py
└── ...
```

#### Paso 4: Verifica la instalación

```powershell
# Verificar que el archivo existe
Test-Path ".\webdrivers\msedgedriver.exe"
# Debe devolver: True

# Verificar la versión del driver (opcional)
.\webdrivers\msedgedriver.exe --version
```

### Opción 2: Descarga Alternativa - Script Automatizado

Si prefieres automatizar, crea un archivo `setup_webdriver.ps1`:

```powershell
# setup_webdriver.ps1
# Obtén tu versión: Menu (⋯) → Configuración → Acerca de Microsoft Edge

$version = Read-Host "Ingresa tu versión exacta de Edge (ej: 142.0.3595.53)"
$url = "https://msedgedriver.azureedge.net/v${version}/edgedriver_win64.zip"

Write-Host "Descargando WebDriver v${version}..."
Invoke-WebRequest -Uri $url -OutFile "edgedriver.zip" -ErrorAction Stop
Write-Host "Extrayendo..."
Expand-Archive "edgedriver.zip" -DestinationPath "webdrivers" -Force
Remove-Item "edgedriver.zip"
Write-Host "✓ WebDriver instalado en webdrivers/msedgedriver.exe"
```

Ejecuta:
```powershell
PowerShell -ExecutionPolicy Bypass -File setup_webdriver.ps1
```

### Opción 3: Si Edge no es necesario - Usa Chrome en su lugar

Si quieres evitar problemas de versiones, puedes usar Chrome. Edita `webdriver_utils.py`:

**Busca esta función:**
```python
def setup_edge_driver(headless=True, user_agent=None, proxy=None):
    # ... código ...
    driver = webdriver.Edge(service=service, options=opts)
    return driver
```

**Reemplázala con:**
```python
def setup_edge_driver(headless=True, user_agent=None, proxy=None):
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager

    opts = ChromeOptions()
    if headless: opts.add_argument("--headless=new")
    if user_agent: opts.add_argument(f"user-agent={user_agent}")
    if proxy: opts.add_argument(f"--proxy-server={proxy}")

    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver
```

## ✓ Verificación Final

Una vez instalado el webdriver, prueba:

```powershell
cd FlightScrapper
python flight_scraper_main.py --apis expedia --verbose
```

**Deberías ver:**
- ✓ Logs de búsqueda sin "Could not reach host"
- ✓ La palabra "Usando Edge driver local" en los logs
- ✓ Resultados de vuelos encontrados

## Links de Referencia

| Recurso | URL |
|---------|-----|
| **Microsoft Edge WebDriver** | https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/ |
| **Azure CDN (descarga directa)** | https://msedgedriver.azureedge.net/ |
| **Historial de versiones** | https://msedgedriver.azureedge.net/LATEST_RELEASE |
| **Documentación Selenium** | https://selenium-python.readthedocs.io/ |
