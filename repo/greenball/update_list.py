import os
import json
import requests
from bs4 import BeautifulSoup
import xbmcgui
from concurrent.futures import ThreadPoolExecutor, as_completed


# Constants
CWD = os.path.dirname(os.path.abspath(__file__))
LINKS_FILE = os.path.join(CWD, 'acestream_links.json')

def mostrar_notificacion(titulo, mensaje, duracion=3000):
    xbmcgui.Dialog().notification(titulo, mensaje, time=duracion, sound=False)
def obtener_acestream_link(href):
    """
    Función para manejar la redirección de un enlace de TinyURL
    y obtener el enlace AceStream final.
    """
    try:
        # Realizar la redirección para obtener el enlace real
        redirect_response = requests.get(href, allow_redirects=False)
        redirected_url = redirect_response.headers.get('Location', None)

        # Verificar si la URL redirigida es un enlace AceStream
        if redirected_url and redirected_url.startswith("acestream://"):
            acestream_id = redirected_url.split("://")[1]  # Extraer el ID de AceStream
            return acestream_id, href  # Devuelve el ID AceStream y el enlace original
        else:
            return None, None  # Si no es un enlace AceStream
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a {href}: {e}")
        return None, None
    
def actualizar_lista(url):
    acestream_links = []
    link_names = []

    mostrar_notificacion("Actualizando lista, espera a que termine", "Obteniendo enlaces AceStream...", 40000)

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        enlaces = soup.find_all('div', class_='clearfix')
        resultados = []

        with ThreadPoolExecutor(max_workers=10) as executor:  # Usamos 10 hilos
            futures = []  # Lista para los futuros de las solicitudes
            
            # Recolectar todos los enlaces para procesarlos en paralelo
            for div in enlaces:
                ps = div.find_all('p')  # Buscar todos los <p> dentro del <div>
                for p in ps:
                    a_tag = p.find('a')  # Buscar el <a> dentro del <p>
                    if a_tag and 'href' in a_tag.attrs:
                        href = a_tag['href']  # Enlace acortado
                        if 'tinyurl.com' in href:
                            # Extraer el nombre de la parte anterior al "Enlace:"
                            nombre = p.text.split('Enlace:')[0].strip()
                            nombre = nombre.lstrip('• ').strip()
                            if not nombre:  # Si no encontramos un nombre, asignar algo predeterminado
                                nombre = "Nombre desconocido"

                            # Enviar la tarea de redirección a los hilos para procesar en paralelo
                            futures.append(executor.submit(obtener_acestream_link, href))
                            resultados.append((nombre, href))  # Guardamos nombre y enlace original

            # Procesar los resultados de las tareas concurrentes
            for future in as_completed(futures):
                acestream_id, href = future.result()
                if acestream_id:
                    # Recuperar el nombre correspondiente al AceStream ID encontrado
                    # Este sería el nombre que corresponde al enlace AceStream
                    matching_result = next((result for result in resultados if result[1] == href), None)
                    if matching_result:
                        nombre = matching_result[0]
                        link_names.append(nombre)
                        acestream_links.append(acestream_id) 

        # Guardar los enlaces en el archivo JSON
        with open(LINKS_FILE, 'w') as f:
            json.dump({'links': acestream_links, 'names': link_names, 'colortext': 'yellowgreen'}, f)

        mostrar_notificacion("Lista actualizada", "Búsqueda completada", 2000)

    except requests.exceptions.RequestException as e:
        mostrar_notificacion("Error", f"Error al actualizar la lista: {e}", 2000)

    return acestream_links, link_names, 'yellowgreen'


def actualizar_lista2(url):
    acestream_links = []
    link_names = []

    mostrar_notificacion("Actualizando lista, espera a que termine", "Obteniendo enlaces AceStream...", 40000)

    try:
        # Obtener el contenido de la URL
        response = requests.get(url)
        response.raise_for_status()  # Verifica errores HTTP
        soup = BeautifulSoup(response.content, 'html.parser')

        # Buscar la etiqueta <script>
        script_tag = soup.find('script')
        if not script_tag or not script_tag.string:
            raise ValueError("No se encontró contenido en la etiqueta <script>.")

        script_content = script_tag.string

        # Extraer el JSON de los enlaces
        start = script_content.find('{')
        end = script_content.rfind('};')
        if start == -1 or end == -1:
            raise ValueError("No se pudo encontrar el bloque JSON en el contenido del script.")

        json_text = script_content[start:end + 1]

        # Cargar y procesar el JSON
        data = json.loads(json_text)
        links = data.get("links", [])

        for link in links:
            nombre_canal = link.get("name", "Sin nombre")
            url = link.get("url", "Sin URL")
            acestream_link = url.strip().replace("acestream://", "")

            acestream_links.append(acestream_link)
            link_names.append(nombre_canal)

        # Guardar los enlaces en el archivo JSON
        with open(LINKS_FILE, 'w') as f:
            json.dump({'links': acestream_links, 'names': link_names, 'colortext': 'aqua'}, f)

        mostrar_notificacion("Lista actualizada", "Búsqueda completada", 2000)

    except requests.exceptions.RequestException as e:
        mostrar_notificacion("Error", f"Error al conectar: {e}", 2000)
    except ValueError as e:
        mostrar_notificacion("Error", f"Error en el formato de los datos: {e}", 2000)
    except Exception as e:
        mostrar_notificacion("Error", f"Error inesperado: {e}", 2000)

    return acestream_links, link_names, 'aqua'

def actualizar_lista3(url):
    acestream_links = []
    link_names = []

    mostrar_notificacion("Actualizando lista", "Obteniendo enlaces AceStream...", 40000)

    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar todos los <a> dentro de la tabla con class="canales"
        enlaces = soup.select("td.canales a")

        for enlace in enlaces:
            href = enlace.get("href")
            texto = enlace.get_text(strip=True)

            if href and href.startswith("acestream://"):
                acestream_link = href.replace("acestream://", "").strip()
                nombre_canal = texto.strip()

                acestream_links.append(acestream_link)
                link_names.append(nombre_canal)

        # Guardar en JSON
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'links': acestream_links, 'names': link_names, 'colortext': 'lightyellow'}, f, ensure_ascii=False)

        mostrar_notificacion("Lista actualizada", "Búsqueda completada", 2000)

    except requests.exceptions.RequestException as e:
        mostrar_notificacion("Error", f"Error al actualizar la lista: {e}", 2000)

    return acestream_links, link_names, "lightyellow"

def actualizar_lista_generica(url, config, colortext):
    """
    Función genérica para extraer enlaces AceStream.
    Configuración posible en 'config':
      - mode: "m3u" o "html"
      - selector: (solo html) selector CSS para los enlaces
      - attr: (solo html) atributo donde está el link (ej. 'href')
      - prefix: prefijo a filtrar (ej. 'acestream://')
      - text: si True, usa el texto del <a> como nombre
      - name_selector: (opcional) otro selector para el nombre
    """
    acestream_links = []
    link_names = []

    mostrar_notificacion("Actualizando lista", f"Obteniendo enlaces...", 1000)

    try:
        response = requests.get(url)
        response.encoding = 'utf-8'

        # ---- MODO M3U ----
        if config.get("mode") == "m3u":
            lines = response.text.splitlines()
            nombre_canal = None

            for line in lines:
                if line.startswith("#EXTINF:"):
                    nombre_canal = line.split(",", 1)[1].strip()
                elif line.startswith("acestream://"):
                    link = line.replace("acestream://", "").strip()
                    acestream_links.append(link)
                    link_names.append(nombre_canal if nombre_canal else "Canal")

        # ---- MODO HTML ----
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            enlaces = soup.select(config["selector"])

            for enlace in enlaces:
                link = enlace.get(config.get("attr", "href"))
                if not link:
                    continue

                if config.get("prefix") and not link.startswith(config["prefix"]):
                    continue

                link = link.replace(config["prefix"], "").strip()

                # Nombre del canal
                name = None
                if "name_selector" in config:
                    parent = enlace.find_parent(config.get("parent_tag", "*"))
                    if parent:
                        name_el = parent.select_one(config["name_selector"])
                        if name_el:
                            name = name_el.get_text(strip=True)

                if not name:
                    name = enlace.get_text(strip=True) if config.get("text", True) else "Canal"

                acestream_links.append(link)
                link_names.append(name)

        # Guardar en JSON
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(
                {"links": acestream_links, "names": link_names, "colortext": colortext},
                f,
                ensure_ascii=False
            )

        mostrar_notificacion("Lista actualizada", f"Búsqueda completada", 1000)

    except requests.exceptions.RequestException as e:
        mostrar_notificacion("Error", f"Error al actualizar la lista: {e}", 1000)

    return acestream_links, link_names, colortext