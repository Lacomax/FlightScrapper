"""
Utilidades para Selenium WebDriver.

Este módulo proporciona funciones auxiliares para inicializar, gestionar
y usar navegadores Selenium de manera segura y eficiente.
"""

import os
import logging
import random
import time
import platform
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    import proxies
    PROXIES_AVAILABLE = True
except ImportError:
    PROXIES_AVAILABLE = False
    logging.warning("Módulo de proxies no disponible")


def setup_edge_driver(headless=True, user_agent=None, proxy=None):
    """
    Configura e inicializa un navegador Microsoft Edge con Selenium.

    Configura el navegador con opciones anti-detección para evitar ser
    identificado como bot y ocultar características de automatización.

    Args:
        headless (bool): Si es True, ejecuta sin interfaz gráfica. Default: True
        user_agent (str): User-Agent custom. Si es None, usa el predeterminado.
        proxy (str): Proxy a usar en formato http://host:port. Si es None, sin proxy.

    Returns:
        WebDriver: Instancia del driver de Microsoft Edge configurado

    Raises:
        Exception: Si no se puede inicializar el navegador

    Example:
        >>> driver = setup_edge_driver(headless=True, user_agent="Mozilla/5.0...")
        >>> driver.get("https://example.com")
    """
    opts = Options()

    # Configuración visual
    if headless:
        opts.add_argument("--headless=new")

    # Anti-detección de automatización
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-dev-shm-usage")

    # User-Agent y proxy
    if user_agent:
        opts.add_argument(f"user-agent={user_agent}")
    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")

    # Opciones experimentales para evadir detección
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Usar webdriver-manager si es disponible
    try:
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        service = Service(EdgeChromiumDriverManager().install())
    except ImportError:
        # Fallback a ruta local si existe
        driver_path = os.path.join("webdrivers", "msedgedriver.exe")
        service = Service(executable_path=driver_path if os.path.exists(driver_path) else None)

    driver = webdriver.Edge(service=service, options=opts)

    # Script para ocultar propiedad webdriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def wait_for_element(driver, selector, by=By.CSS_SELECTOR, timeout=60):
    """
    Espera a que un elemento esté presente en el DOM.

    Args:
        driver (WebDriver): Instancia del driver de Selenium
        selector (str): Selector CSS o XPath del elemento
        by (By): Estrategia de búsqueda (CSS_SELECTOR o XPATH). Default: CSS_SELECTOR
        timeout (int): Tiempo máximo de espera en segundos. Default: 60

    Returns:
        WebElement: El elemento encontrado

    Raises:
        TimeoutException: Si el elemento no aparece en el tiempo especificado
    """
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def wait_for_elements(driver, selector, by=By.CSS_SELECTOR, timeout=60):
    """
    Espera a que múltiples elementos estén presentes en el DOM.

    Args:
        driver (WebDriver): Instancia del driver de Selenium
        selector (str): Selector CSS o XPath del elemento
        by (By): Estrategia de búsqueda (CSS_SELECTOR o XPATH). Default: CSS_SELECTOR
        timeout (int): Tiempo máximo de espera en segundos. Default: 60

    Returns:
        List[WebElement]: Lista de elementos encontrados

    Raises:
        TimeoutException: Si los elementos no aparecen en el tiempo especificado
    """
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((by, selector))
    )


def get_element_safely(driver, selector, by=By.CSS_SELECTOR):
    """
    Obtiene un elemento del DOM de forma segura sin lanzar excepciones.

    Args:
        driver (WebDriver): Instancia del driver de Selenium
        selector (str): Selector CSS o XPath del elemento
        by (By): Estrategia de búsqueda (CSS_SELECTOR o XPATH). Default: CSS_SELECTOR

    Returns:
        WebElement or None: El elemento encontrado, o None si no existe
    """
    try:
        return driver.find_element(by, selector)
    except Exception as e:
        logging.debug(f"Elemento no encontrado ({selector}): {e}")
        return None


def get_elements_safely(driver, selector, by=By.CSS_SELECTOR):
    """
    Obtiene múltiples elementos del DOM de forma segura sin lanzar excepciones.

    Args:
        driver (WebDriver): Instancia del driver de Selenium
        selector (str): Selector CSS o XPath de los elementos
        by (By): Estrategia de búsqueda (CSS_SELECTOR o XPATH). Default: CSS_SELECTOR

    Returns:
        List[WebElement]: Lista de elementos encontrados (vacía si no hay coincidencias)
    """
    try:
        return driver.find_elements(by, selector)
    except Exception as e:
        logging.debug(f"Elementos no encontrados ({selector}): {e}")
        return []


def random_delay(min_sec=1, max_sec=3):
    """
    Introduce un delay aleatorio para simular comportamiento humano.

    Ayuda a evitar ser detectado como bot mediante pausas realistas
    entre interacciones.

    Args:
        min_sec (float): Tiempo mínimo de espera en segundos. Default: 1
        max_sec (float): Tiempo máximo de espera en segundos. Default: 3
    """
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    logging.debug(f"Delay: {delay:.2f}s")


def get_random_proxy():
    """
    Obtiene un proxy aleatorio de la lista disponible.

    Returns:
        str or None: URL del proxy en formato http://host:port, o None si no hay proxies

    Note:
        Requiere que el módulo 'proxies' esté disponible y tenga PROXY_LIST
    """
    if not PROXIES_AVAILABLE:
        logging.debug("Módulo de proxies no disponible")
        return None

    if hasattr(proxies, 'PROXY_LIST') and proxies.PROXY_LIST:
        selected_proxy = random.choice(proxies.PROXY_LIST)
        logging.debug(f"Proxy seleccionado: {selected_proxy}")
        return selected_proxy

    return None