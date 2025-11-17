"""
Gestión automática de proxies gratuitos para web scraping.

Este módulo proporciona funciones para obtener, validar y gestionar
una lista de proxies gratuitos para evitar bloqueos de IP durante
el web scraping.

Nota de uso:
    Los proxies gratuitos tienen limitaciones de velocidad y confiabilidad.
    Para producción, se recomienda usar proxies de pago.
"""

import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

# Configuración
PROXY_LIST: List[str] = []
PROXY_FETCH_TIME: float = 0
PROXY_REFRESH_INTERVAL: int = 3600  # Refrescar cada 1 hora

# Fuentes de proxies gratuitos
PROXY_SOURCES = [
    "https://free-proxy-list.net/",
    "https://www.sslproxies.org/"
]


def fetch_free_proxies() -> List[str]:
    """
    Obtiene una lista de proxies gratuitos desde múltiples fuentes.

    Intenta obtener proxies desde varias fuentes en línea, valida que sean
    HTTPS, y filtra los que funcionan realmente. Los resultados se cachean
    durante 1 hora.

    Returns:
        List[str]: Lista de proxies funcionales en formato IP:Puerto

    Note:
        Esta función es blocking y puede tomar varios minutos si hay
        que validar muchos proxies. Se ejecuta automáticamente al importar.

    Example:
        >>> proxies = fetch_free_proxies()
        >>> if proxies:
        ...     proxy = proxies[0]
        ...     print(f"Usando proxy: {proxy}")
    """
    global PROXY_LIST, PROXY_FETCH_TIME

    # Usar caché si está fresco
    if time.time() - PROXY_FETCH_TIME < PROXY_REFRESH_INTERVAL and PROXY_LIST:
        logging.debug(f"Usando lista de proxies en caché ({len(PROXY_LIST)} proxies)")
        return PROXY_LIST

    logging.info("Obteniendo lista de proxies...")
    proxies = []

    # Intentar obtener proxies desde fuentes principales
    for source in PROXY_SOURCES:
        try:
            response = requests.get(source, timeout=10)
            logging.debug(f"Procesando fuente: {source}")

            # Parsear tabla HTML (formato típico de free-proxy-list.net)
            lines = response.text.split("<tr><td>")
            for line in lines[1:]:
                try:
                    parts = line.split("</td><td>")
                    if len(parts) >= 7:
                        ip = parts[0].strip()
                        port = parts[1].strip()

                        # Preferir HTTPS si está disponible (columna 6)
                        if len(parts) > 6 and parts[6].startswith("yes"):
                            proxies.append(f"{ip}:{port}")
                        # Incluir HTTP también si HTTPS no está disponible
                        elif len(parts) <= 6:
                            proxies.append(f"{ip}:{port}")

                except (IndexError, ValueError):
                    continue

            if proxies:
                logging.info(f"Se encontraron {len(proxies)} proxies potenciales")
                break

        except requests.exceptions.RequestException as e:
            logging.warning(f"Error obteniendo proxies de {source}: {e}")
            continue

    # Si no se encontraron proxies, devolver lista vacía
    if not proxies:
        logging.warning("No se pudieron obtener proxies de ninguna fuente")
        PROXY_LIST = []
        PROXY_FETCH_TIME = time.time()
        return []

    # Filtrar proxies que funcionan realmente
    logging.info(f"Validando {len(proxies)} proxies...")
    working_proxies = filter_working_proxies(proxies, max_workers=20)

    logging.info(f"Se encontraron {len(working_proxies)} proxies funcionales")

    PROXY_LIST = working_proxies
    PROXY_FETCH_TIME = time.time()

    return working_proxies


def is_proxy_working(proxy: str, timeout: int = 3) -> Optional[str]:
    """
    Verifica si un proxy funciona realizando una petición de prueba.

    Intenta conectar a Google.com a través del proxy para verificar
    que funciona y que puede manejar conexiones HTTPS.

    Args:
        proxy (str): Proxy en formato IP:Puerto
        timeout (int): Timeout en segundos para la petición. Default: 3

    Returns:
        str or None: El proxy si funciona, None si falla

    Note:
        Esta función es blocking y puede tardar hasta 'timeout' segundos
        si el proxy no responde.
    """
    try:
        requests.get(
            "https://www.google.com",
            proxies={"https": f"https://{proxy}"},
            timeout=timeout
        )
        logging.debug(f"Proxy funcional: {proxy}")
        return proxy

    except requests.exceptions.RequestException:
        logging.debug(f"Proxy no funcional: {proxy}")
        return None
    except Exception as e:
        logging.debug(f"Error validando proxy {proxy}: {e}")
        return None


def filter_working_proxies(proxies: List[str], max_workers: int = 10) -> List[str]:
    """
    Filtra una lista de proxies eliminando los que no funcionan.

    Valida proxies en paralelo usando ThreadPoolExecutor para mayor
    eficiencia. Puede tardar varios minutos si hay muchos proxies.

    Args:
        proxies (List[str]): Lista de proxies a validar
        max_workers (int): Número de hilos para validación paralela. Default: 10

    Returns:
        List[str]: Lista de proxies que funcionan

    Example:
        >>> proxy_list = ["1.2.3.4:8080", "5.6.7.8:3128"]
        >>> working = filter_working_proxies(proxy_list, max_workers=5)
        >>> print(f"De {len(proxy_list)}, funcionan {len(working)}")
    """
    if not proxies:
        return []

    working_proxies = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(is_proxy_working, proxies)
        working_proxies = [proxy for proxy in results if proxy is not None]

    return working_proxies


# NO auto-inicializar al importar. Solo se carga cuando el usuario lo pide explícitamente.