"""
Módulo de procesamiento y parseo de datos de vuelos.

Este módulo proporciona funciones para:
- Parsear detalles de vuelos desde texto
- Combinar vuelos de ida y vuelta
- Generar rangos de fechas
- Formatear y exportar resultados
- Corregir problemas de encodificación Unicode
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional


def fix_unicode_arrows(path):
    """
    Reemplaza flechas Unicode con alternativas ASCII en archivos Python.

    Args:
        path (str): Ruta de archivo o directorio

    Returns:
        bool: True si se procesó correctamente, False en caso contrario
    """
    if not os.path.exists(path):
        return False

    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    fix_file(os.path.join(root, file))
    elif os.path.isfile(path) and path.endswith(".py"):
        fix_file(path)
    else:
        return False

    return True


def fix_file(filepath):
    """
    Corrige flechas Unicode en un archivo Python específico.

    Args:
        filepath (str): Ruta del archivo a procesar

    Returns:
        bool: True si se procesó correctamente
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = re.sub(r'→', '->', content)
        new_content = re.sub(r'←', '<-', new_content)
        new_content = re.sub(r'⟶', '-->', new_content)

        if content != new_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logging.debug(f"Flechas Unicode corregidas en {filepath}")

        return True
    except Exception as e:
        logging.warning(f"Error procesando {filepath}: {e}")
        return False


def parse_flight_details(text: str) -> Tuple[str, str, str, str, str, float, str, int]:
    """
    Parsea detalles de vuelo desde texto de Expedia.

    Extrae información como aerolínea, horarios, precios, duración y escalas
    del texto formateado de Expedia.

    Args:
        text (str): Texto con detalles del vuelo

    Returns:
        Tuple: (aerolínea, hora_salida, origen, hora_llegada, destino, precio, duración, escalas)

    Example:
        >>> texto = "KLM 14:00 MUC → 18:30 JRO 2h45m 1 stop €450"
        >>> airline, dep, origin, arr, dest, price, duration, stops = parse_flight_details(texto)
    """
    try:
        lines = text.strip().split('\n')

        # Variables por defecto
        airline = "Unknown"
        dep_time = "N/A"
        origin = "N/A"
        arr_time = "N/A"
        destination = "N/A"
        price = 0.0
        duration = "N/A"
        stops = 0

        # Procesar líneas del texto
        full_text = ' '.join(lines).strip()

        # Intentar extraer aerolínea (palabras antes de primera hora HH:MM)
        airline_match = re.match(r'^([A-Za-z\s]+?)\s+(\d{1,2}:\d{2})', full_text)
        if airline_match:
            airline = airline_match.group(1).strip()

        # Extraer horarios (HH:MM)
        times = re.findall(r'\d{1,2}:\d{2}', full_text)
        if len(times) >= 2:
            dep_time = times[0]
            arr_time = times[1]

        # Extraer aeropuertos (códigos IATA de 3 letras)
        airports = re.findall(r'\b([A-Z]{3})\b', full_text)
        if len(airports) >= 2:
            origin = airports[0]
            destination = airports[-1]

        # Extraer precio (números con € o €)
        price_match = re.search(r'€\s*(\d+(?:[.,]\d{2})?)', full_text)
        if price_match:
            price_str = price_match.group(1).replace(',', '.')
            price = float(price_str)

        # Extraer duración (Xh Ym o Xh Xm o solo Xh)
        duration_match = re.search(r'(\d+h)(?:\s*(\d+)m)?', full_text)
        if duration_match:
            duration = f"{duration_match.group(1)}" + (f" {duration_match.group(2)}m" if duration_match.group(2) else "")

        # Extraer escalas/paradas
        if 'nonstop' in full_text.lower() or 'direct' in full_text.lower():
            stops = 0
        else:
            stops_match = re.search(r'(\d+)\s*(?:stop|escala)', full_text, re.IGNORECASE)
            if stops_match:
                stops = int(stops_match.group(1))
            else:
                # Contar "via" o "through" como indicador de parada
                stops = full_text.count(' via ') + full_text.count(' through ')

        return airline, dep_time, origin, arr_time, destination, price, duration, stops

    except Exception as e:
        logging.debug(f"Error parseando detalles de vuelo: {e}")
        return "Unknown", "N/A", "N/A", "N/A", "N/A", 0.0, "N/A", 0


def generate_date_range(start_date_str: str, offset_days: int, duration_days: int) -> List[str]:
    """
    Genera un rango de fechas a partir de una fecha inicial.

    Args:
        start_date_str (str): Fecha inicial en formato DD/MM/YYYY
        offset_days (int): Días a sumar a la fecha inicial
        duration_days (int): Cantidad de días a generar desde la fecha modificada

    Returns:
        List[str]: Lista de fechas en formato DD/MM/YYYY

    Example:
        >>> generate_date_range("01/06/2025", 0, 5)
        ['01/06/2025', '02/06/2025', '03/06/2025', '04/06/2025', '05/06/2025']
    """
    try:
        start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
        start_date += timedelta(days=offset_days)

        date_range = []
        for i in range(duration_days + 1):
            current_date = start_date + timedelta(days=i)
            date_range.append(current_date.strftime("%d/%m/%Y"))

        return date_range
    except Exception as e:
        logging.error(f"Error generando rango de fechas: {e}")
        return []


def find_best_combinations(
    outbound_flights: List[Dict],
    return_flights: List[Dict],
    min_stay_days: int,
    max_stay_days: int,
    num_adults: int,
    num_children: int
) -> List[Dict]:
    """
    Encuentra las mejores combinaciones de vuelos ida y vuelta.

    Combina vuelos de ida y vuelta respetando los días mínimos y máximos
    de estancia, y calcula el precio total.

    Args:
        outbound_flights (List[Dict]): Lista de vuelos de ida
        return_flights (List[Dict]): Lista de vuelos de vuelta
        min_stay_days (int): Días mínimos de estancia
        max_stay_days (int): Días máximos de estancia
        num_adults (int): Número de adultos
        num_children (int): Número de niños

    Returns:
        List[Dict]: Lista de combinaciones ordenadas por precio total
    """
    combinations = []

    try:
        if not outbound_flights or not return_flights:
            logging.warning("Uno o ambos tipos de vuelos están vacíos")
            return combinations

        for outbound in outbound_flights:
            # Extraer fecha de salida (formato esperado: DD/MM/YYYY)
            try:
                dep_date_str = outbound.get("Día", "")
                if not dep_date_str:
                    continue

                dep_date = datetime.strptime(dep_date_str, "%d/%m/%Y")
            except (ValueError, KeyError):
                logging.debug(f"Fecha de salida inválida: {outbound.get('Día')}")
                continue

            for return_flight in return_flights:
                try:
                    ret_date_str = return_flight.get("Día", "")
                    if not ret_date_str:
                        continue

                    ret_date = datetime.strptime(ret_date_str, "%d/%m/%Y")

                    # Calcular días de estancia
                    stay_days = (ret_date - dep_date).days

                    # Verificar restricciones de estancia
                    if stay_days < min_stay_days or stay_days > max_stay_days:
                        continue

                    # Calcular precios
                    outbound_price = float(outbound.get("Precio", 0))
                    return_price = float(return_flight.get("Precio", 0))
                    total_price_person = outbound_price + return_price

                    # Calcular precio total para toda la familia
                    num_passengers = num_adults + num_children
                    total_price_family = total_price_person * num_passengers

                    # Construir información de ruta
                    outbound_route = f"{outbound.get('Origen', 'N/A')} → {outbound.get('Destino', 'N/A')}"
                    return_route = f"{return_flight.get('Origen', 'N/A')} → {return_flight.get('Destino', 'N/A')}"

                    # Crear combinación
                    combination = {
                        "Ida_Fecha": outbound.get("Día", "N/A"),
                        "Ida_Hora_Salida": outbound.get("Hora_Salida", "N/A"),
                        "Ida_Hora_Llegada": outbound.get("Hora_Llegada", "N/A"),
                        "Ida_Ruta": outbound_route,
                        "Ida_Compañía": outbound.get("Compañía", "N/A"),
                        "Ida_Duración": outbound.get("Duración", "N/A"),
                        "Ida_Escalas": outbound.get("Escalas", 0),
                        "Ida_Precio": f"€{outbound_price:.2f}",

                        "Vuelta_Fecha": return_flight.get("Día", "N/A"),
                        "Vuelta_Hora_Salida": return_flight.get("Hora_Salida", "N/A"),
                        "Vuelta_Hora_Llegada": return_flight.get("Hora_Llegada", "N/A"),
                        "Vuelta_Ruta": return_route,
                        "Vuelta_Compañía": return_flight.get("Compañía", "N/A"),
                        "Vuelta_Duración": return_flight.get("Duración", "N/A"),
                        "Vuelta_Escalas": return_flight.get("Escalas", 0),
                        "Vuelta_Precio": f"€{return_price:.2f}",

                        "Días_Estancia": stay_days,
                        "Precio_Total": f"€{total_price_person:.2f}",
                        "Precio_Total_Familia": f"€{total_price_family:.2f}",
                        "Pasajeros": f"{num_adults}A+{num_children}N",
                    }

                    # Agregar detalles de escalas si existen
                    if outbound.get("Detalles_Escalas"):
                        combination["Detalles_Escalas"] = outbound["Detalles_Escalas"]

                    combinations.append(combination)

                except (ValueError, KeyError) as e:
                    logging.debug(f"Error procesando vuelo de retorno: {e}")
                    continue

        # Ordenar por precio total
        combinations.sort(key=lambda x: float(x["Precio_Total"].replace("€", "")))

    except Exception as e:
        logging.error(f"Error encontrando combinaciones: {e}")

    return combinations


def format_combination_table(combinations: List[Dict]) -> str:
    """
    Formatea una tabla legible con las mejores combinaciones de vuelos.

    Args:
        combinations (List[Dict]): Lista de combinaciones de vuelos

    Returns:
        str: Tabla formateada en texto ASCII
    """
    if not combinations:
        return "No hay combinaciones para mostrar."

    try:
        # Encabezados
        headers = ["#", "Ida", "Vuelta", "Días", "Precio/Persona", "Familia", "Compañías"]

        # Ancho de columnas
        col_widths = [3, 16, 16, 5, 14, 14, 25]

        # Línea separadora
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

        # Construir tabla
        lines = [separator]

        # Encabezado
        header_line = "|"
        for i, header in enumerate(headers):
            header_line += f" {header:<{col_widths[i]}} |"
        lines.append(header_line)
        lines.append(separator)

        # Filas de datos
        for idx, combo in enumerate(combinations[:20], 1):  # Máximo 20 filas
            ida_fecha = combo.get("Ida_Fecha", "N/A")
            vuelta_fecha = combo.get("Vuelta_Fecha", "N/A")
            dias = combo.get("Días_Estancia", "N/A")
            precio_persona = combo.get("Precio_Total", "N/A")
            precio_familia = combo.get("Precio_Total_Familia", "N/A")
            ida_airline = combo.get("Ida_Compañía", "N/A")[:8]
            vuelta_airline = combo.get("Vuelta_Compañía", "N/A")[:8]
            airlines = f"{ida_airline}/{vuelta_airline}"

            data_line = f"| {idx:<3} | {ida_fecha:<16} | {vuelta_fecha:<16} | {str(dias):<5} | {precio_persona:<14} | {precio_familia:<14} | {airlines:<25} |"
            lines.append(data_line)

        lines.append(separator)

        return "\n".join(lines)

    except Exception as e:
        logging.error(f"Error formateando tabla: {e}")
        return "Error al formatear tabla de combinaciones."


def build_expedia_url(
    origin: str,
    destination: str,
    departure_date: str,
    config: Dict
) -> str:
    """
    Construye URL de búsqueda para Expedia.

    Args:
        origin (str): Código IATA del aeropuerto de origen
        destination (str): Código IATA del aeropuerto de destino
        departure_date (str): Fecha en formato DD/MM/YYYY
        config (Dict): Configuración con parámetros de búsqueda

    Returns:
        str: URL formada para Expedia

    Example:
        >>> url = build_expedia_url("MUC", "JRO", "01/06/2025", config)
        >>> print(url)
        https://www.expedia.com/Flights-Search?...
    """
    try:
        # Convertir fecha a formato MM/DD/YYYY para Expedia
        date_obj = datetime.strptime(departure_date, "%d/%m/%Y")
        expedia_date = date_obj.strftime("%-m/%-d/%Y") if os.name != 'nt' else date_obj.strftime("%m/%d/%Y").lstrip('0').replace('/0', '/')

        # Extraer información de pasajeros
        adults = config.get("PASSENGERS", {}).get("adults", 1)
        children_str = config.get("PASSENGERS", {}).get("children", "0")
        children_count = int(children_str.split("[")[0]) if "[" in children_str else 0

        # Construir parámetros
        params = {
            "trip": "roundtrip",
            "leg1": f"{origin},{expedia_date}",
            "leg2": f"{destination},{expedia_date}",
            "passengers": f"adults,{adults}|children,{children_count}",
            "mode": "search",
            "options": "cabinclass:economy"
        }

        # Base URL de Expedia
        base_url = "https://www.expedia.com/Flights-Search"

        # Construir query string
        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{key}={value}")

        url = f"{base_url}?{'&'.join(query_parts)}"

        return url

    except Exception as e:
        logging.error(f"Error construyendo URL de Expedia: {e}")
        # Retornar URL de búsqueda genérica como fallback
        return f"https://www.expedia.com/Flights-Search?leg1={origin}&leg2={destination}"


def save_results_json(results: List[Dict], filename: str) -> bool:
    """
    Guarda resultados de búsqueda en archivo JSON.

    Args:
        results (List[Dict]): Lista de resultados de búsqueda
        filename (str): Nombre del archivo de salida

    Returns:
        bool: True si se guardó correctamente
    """
    try:
        # Asegurar que el archivo tenga extensión .json
        if not filename.endswith('.json'):
            filename += '.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logging.info(f"Resultados guardados en {filename}")
        return True

    except Exception as e:
        logging.error(f"Error guardando resultados JSON: {e}")
        return False


def save_results_text(combinations: List[Dict], filename: str = "resultados_vuelos.txt") -> bool:
    """
    Guarda mejores combinaciones de vuelos en archivo de texto formateado.

    Args:
        combinations (List[Dict]): Lista de combinaciones de vuelos
        filename (str): Nombre del archivo de salida

    Returns:
        bool: True si se guardó correctamente
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("MEJORES COMBINACIONES DE VUELOS\n")
            f.write("=" * 100 + "\n\n")

            if not combinations:
                f.write("No se encontraron combinaciones de vuelos.\n")
                return True

            for idx, combo in enumerate(combinations[:20], 1):
                f.write(f"\n{'─' * 100}\n")
                f.write(f"OPCIÓN #{idx}\n")
                f.write(f"{'─' * 100}\n")

                f.write(f"VUELO DE IDA:\n")
                f.write(f"  Fecha:       {combo.get('Ida_Fecha', 'N/A')}\n")
                f.write(f"  Ruta:        {combo.get('Ida_Ruta', 'N/A')}\n")
                f.write(f"  Hora:        {combo.get('Ida_Hora_Salida', 'N/A')} → {combo.get('Ida_Hora_Llegada', 'N/A')}\n")
                f.write(f"  Compañía:    {combo.get('Ida_Compañía', 'N/A')}\n")
                f.write(f"  Duración:    {combo.get('Ida_Duración', 'N/A')}\n")
                f.write(f"  Escalas:     {combo.get('Ida_Escalas', 0)}\n")
                f.write(f"  Precio:      {combo.get('Ida_Precio', 'N/A')}\n")

                f.write(f"\nVUELO DE VUELTA:\n")
                f.write(f"  Fecha:       {combo.get('Vuelta_Fecha', 'N/A')}\n")
                f.write(f"  Ruta:        {combo.get('Vuelta_Ruta', 'N/A')}\n")
                f.write(f"  Hora:        {combo.get('Vuelta_Hora_Salida', 'N/A')} → {combo.get('Vuelta_Hora_Llegada', 'N/A')}\n")
                f.write(f"  Compañía:    {combo.get('Vuelta_Compañía', 'N/A')}\n")
                f.write(f"  Duración:    {combo.get('Vuelta_Duración', 'N/A')}\n")
                f.write(f"  Escalas:     {combo.get('Vuelta_Escalas', 0)}\n")
                f.write(f"  Precio:      {combo.get('Vuelta_Precio', 'N/A')}\n")

                f.write(f"\nRESUMEN:\n")
                f.write(f"  Días de estancia:    {combo.get('Días_Estancia', 'N/A')}\n")
                f.write(f"  Precio por persona:  {combo.get('Precio_Total', 'N/A')}\n")
                f.write(f"  Precio familia:      {combo.get('Precio_Total_Familia', 'N/A')}\n")
                f.write(f"  Pasajeros:           {combo.get('Pasajeros', 'N/A')}\n")

        logging.info(f"Resultados guardados en {filename}")
        return True

    except Exception as e:
        logging.error(f"Error guardando resultados de texto: {e}")
        return False


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    fix_unicode_arrows(path)
    print("Corregidas flechas Unicode.")