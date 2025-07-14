import requests
from bs4 import BeautifulSoup

def obtener_html(url):
    """Realiza una petición GET y devuelve el contenido HTML."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        respuesta = requests.get(url, headers=headers, timeout=10)
        respuesta.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx
        return respuesta.text
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la página {url}: {e}")
        return None

def extraer_titulo_pagina(html_contenido):
    """Extrae el título de la página web."""
    if html_contenido:
        soup = BeautifulSoup(html_contenido, 'html.parser')
        titulo = soup.title.string if soup.title else "No se encontró título"
        return titulo
    return "No se pudo procesar HTML"

# ---código para ejecutar las funciones ---

# URL a scrapear
url= "https://jsonplaceholder.typicode.com/posts" # Un sitio seguro para practicar

# Obtiene el contenido HTML de la URL
html_del_sitio = obtener_html(url)

# Si se obtuvo el HTML, extrae y muestra el título
if html_del_sitio:
    titulo = extraer_titulo_pagina(html_del_sitio)
    print(f"Título de la página: {titulo}")
else:
    print("No se pudo obtener el contenido HTML.")