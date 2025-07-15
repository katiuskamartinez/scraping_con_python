import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.robotparser import RobotFileParser
import pandas as pd
import logging
import sys # Para SystemExit

# --- Configuración Ética y de Scraping ---
# User-Agent que simula un navegador común. Es una buena práctica variar este o usar uno más específico
# si el sitio tiene reglas detalladas para diferentes agentes.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"
MIN_DELAY_SECONDS = 3  # Retardo mínimo entre solicitudes para evitar sobrecargar el servidor
MAX_DELAY_SECONDS = 7  # Retardo máximo entre solicitudes
OUTPUT_CSV_FILE = "datos_inmobiliarios_barcelona.csv"

# Configuración básica de logging para ver el progreso y los errores
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_html_content(url, session, robots_parser):
    """
    Realiza una petición GET a una URL, respetando robots.txt y añadiendo un User-Agent.
    """
    if not robots_parser.can_fetch(USER_AGENT, url):
        logging.warning(f"URL bloqueada por robots.txt para {USER_AGENT}: {url}. Omitiendo.")
        return None

    try:
        headers = {"User-Agent": USER_AGENT}
        # Timeout para evitar esperas infinitas si el servidor no responde
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
        logging.info(f"Éxito al obtener contenido de: {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al acceder a {url}: {e}")
        return None

def parse_property_listing(html_content):
    """
    Parsea el HTML de una página de listado para extraer información de propiedades.
    Esta función necesita ser personalizada para cada sitio web específico.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    properties_data = []

    # --- SELECTORES CSS EJEMPLO ---
    # **IMPORTANTE**: inspeccionar el sitio web real para encontrar los selectores CSS correctos.
    # Usar las herramientas de desarrollo de tu navegador (F12) para identificar las clases y etiquetas.
    # Por ejemplo, si cada tarjeta de propiedad tiene la clase 'property-item':
    property_cards = soup.find_all('div', class_='col-lg-3 col-md-6') # O 'article', 'li', 'section', etc.

    if not property_cards:
        logging.warning("No se encontraron elementos de propiedad con la clase 'property-item'. "
                        "Revisa los selectores CSS o si la página está vacía/tiene otro formato.")

    for card in property_cards:
        # Intenta encontrar cada pieza de información. Usa 'N/A' si no se encuentra para evitar errores.
        title_element = card.find('h2', class_='title-dot') # Ejemplo: h2 con clase 'item-title'
        price_element = card.find('span', class_='pr2') # Ejemplo: span con clase 'item-price'
        bedrooms_element = card.find('span', class_='inf') # Ejemplo: span con clase 'item-bedrooms'
        #area_element = card.find('span', class_='item-area') # Ejemplo: span con clase 'item-area'
        location_element = card.find('span', class_='location') # Ejemplo: p con clase 'item-location'
        #url_element = card.find('a', class_='item-link') # Ejemplo: a con clase 'item-link'

        properties_data.append({
            'titulo': title_element.text.strip() if title_element else 'N/A',
            'precio': price_element.text.strip() if price_element else 'N/A',
            'habitaciones': bedrooms_element.text.strip() if bedrooms_element else 'N/A',
            #'area_m2': area_element.text.strip() if area_element else 'N/A',
            'ubicacion': location_element.text.strip() if location_element else 'N/A',
            #'url_anuncio': url_element['href'] if url_element and 'href' in url_element.attrs else 'N/A'
        })
    return properties_data

def main_scraper(base_url, total_pages_to_scrape):
    """
    Función principal que orquesta el scraping de múltiples páginas.
    """
    all_properties = []
    
    # --- Manejo Ético y Robusto del robots.txt ---
    rp = RobotFileParser()
    robots_txt_url = f"{base_url}/robots.txt"
    rp.set_url(robots_txt_url)

    try:
        rp.read()
        logging.info(f"robots.txt cargado exitosamente desde: {robots_txt_url}")
        
        # Obtener y aplicar un crawl-delay si está especificado en robots.txt
        # Esto es una capa extra de ética si el sitio la define
        global MIN_DELAY_SECONDS, MAX_DELAY_SECONDS # Necesitamos acceder a las variables globales para ajustarlas
        crawl_delay_from_robots = rp.crawl_delay(USER_AGENT)
        if crawl_delay_from_robots and crawl_delay_from_robots > MAX_DELAY_SECONDS:
            logging.info(f"Ajustando el retardo mínimo a {crawl_delay_from_robots} segundos (crawl-delay en robots.txt).")
            MIN_DELAY_SECONDS = crawl_delay_from_robots
            MAX_DELAY_SECONDS = crawl_delay_from_robots + 2 # un poco más para variar el delay

    except requests.exceptions.RequestException as req_err:
        logging.error(f"Error de red o HTTP al cargar robots.txt de {robots_txt_url}: {req_err}")
        logging.error("No se pudo leer robots.txt. Es IMPRESCINDIBLE respetar las políticas del sitio.")
        logging.error("Considera detener el script o contactar al administrador del sitio para evitar bloqueos o problemas legales.")
        # En un entorno de producción real, lo más ético y seguro es detenerse si robots.txt no es accesible.
        sys.exit("Error crítico: No se pudo cargar robots.txt. Deteniendo la ejecución del scraper.")

    except Exception as generic_err:
        logging.error(f"Error inesperado al procesar robots.txt de {robots_txt_url}: {generic_err}")
        logging.error("No se pudo procesar robots.txt correctamente. Es IMPRESCINDIBLE respetar las políticas del sitio.")
        logging.error("Considera detener el script o contactar al administrador del sitio para evitar bloqueos o problemas legales.")
        # se recomienda detenerse aquí si hay un problema al leer el robots.txt
        sys.exit("Error crítico: Problema al procesar robots.txt. Deteniendo la ejecución del scraper.")
    # --- FIN DE robots.txt ---

    with requests.Session() as session:
        for page_num in range(1, total_pages_to_scrape + 1):
            # Construye la URL de la página. ESTO NECESITA SER AJUSTADO SEGÚN LA ESTRUCTURA DEL SITIO
            # Puede ser con un parámetro de consulta (?page=X), o una ruta (/page/X), etc.
            # Ejemplo: si el sitio usa "/propiedades?pagina=X"
            target_url = f"{base_url}?pagina={page_num}" 

            logging.info(f"Intentando scrapear página {page_num}: {target_url}")
            html = get_html_content(target_url, session, rp) # Pasa el parser a la función de obtención de contenido

            if html:
                properties_on_page = parse_property_listing(html)
                all_properties.extend(properties_on_page)
                logging.info(f"Se encontraron {len(properties_on_page)} propiedades en la página {page_num}.")
            else:
                logging.warning(f"No se pudo obtener HTML o la URL fue bloqueada para la página {page_num}. Podría ser el final de los resultados o un bloqueo.")
                if page_num > 1 and not properties_on_page: # Si no hay propiedades en una página que no es la primera, puede ser el final
                    logging.info("Asumiendo que no hay más páginas con propiedades disponibles.")
                    break # Salir del bucle si no hay más propiedades

            # Pausa ética y aleatoria para simular comportamiento humano y no sobrecargar el servidor
            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            logging.info(f"Esperando {delay:.2f} segundos antes de la siguiente petición...")
            time.sleep(delay)
            
    # Guardar los datos en un archivo CSV al finalizar
    df = pd.DataFrame(all_properties)
    if not df.empty:
        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8')
        logging.info(f"Datos guardados en {OUTPUT_CSV_FILE}")
        logging.info(f"Total de propiedades scrapeadas: {len(all_properties)}")
    else:
        logging.info("No se encontraron propiedades para guardar en el archivo CSV.")
        
    return df

if __name__ == "__main__":
    # Definir la URL base del portal inmobiliario que se desea scrapear .
    # Ejemplo: Si buscas apartamentos en venta en Lechería, la URL podría ser algo como:
    # "https://www.tuinmueble.com.ve/apartamentos/venta/anzoategui/lecheria"
    
    portal_inmobiliario_url = "https://www.tuinmueble.com.ve/apartamentos/venta/anzoategui/lecheria" # ¡MODIFICAR ESTA URL!
    
    # Número de páginas a scrapear. Comienzar con un número pequeño (ej. 1-3) para probar los selectores.
    paginas_a_scrapear = 1 # Ajusta esto según cuántas páginas se quiera procesar

    # --- Ejecutar el scraper ---
    logging.info("Iniciando el Radar Inmobiliario Ético...")
    scraped_data = main_scraper(portal_inmobiliario_url, paginas_a_scrapear)
    
    if not scraped_data.empty:
        logging.info("\nPrimeras 5 filas de los datos recolectados:")
        print(scraped_data.head())
    else:
        logging.info("No se recolectaron datos. Esto puede deberse a URL incorrecta, selectores CSS erróneos, "
                     "robots.txt que prohíbe el acceso, o que no hay propiedades en las páginas analizadas.")
    logging.info("Radar Inmobiliario Ético finalizado.")