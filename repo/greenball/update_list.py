import os
import json
import requests
from bs4 import BeautifulSoup
import xbmcgui
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64, gzip, json, requests
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
    

def actualizar_lista2(url):
    acestream_links = []
    link_names = []

    mostrar_notificacion("Actualizando lista", "Obteniendo enlaces AceStream...", 40000)

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        script_tag = soup.find('script')
        
        if not script_tag or not script_tag.string:
            raise ValueError("No se encontró contenido en la etiqueta <script>.")

        script_content = script_tag.string
        start = script_content.find('{')
        end = script_content.rfind('};')
        if start == -1 or end == -1:
            raise ValueError("No se pudo encontrar el bloque JSON en el contenido del script.")

        json_text = script_content[start:end + 1]
        data = json.loads(json_text)
        links = data.get("links", [])

        for link in links:
            nombre_canal = link.get("name", "Sin nombre")
            url = link.get("url", "").strip()
            acestream_link = url.replace("acestream://", "")

            if acestream_link:  # Solo añadir si hay link AceStream
                acestream_links.append(acestream_link)
                link_names.append(nombre_canal)

        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'links': acestream_links, 'names': link_names, 'colortext': 'aqua'}, f, ensure_ascii=False)

        mostrar_notificacion("Lista actualizada", f"Se encontraron {len(acestream_links)} canales", 5000)

    except requests.exceptions.RequestException as e:
        mostrar_notificacion("Error", f"Error al conectar: {e}", 2000)
    except ValueError as e:
        mostrar_notificacion("Error", f"Error en el formato de los datos: {e}", 5000)
    except Exception as e:
        mostrar_notificacion("Error", f"Error inesperado: {e}", 5000)

    return acestream_links, link_names, 'aqua'


def actualizar_lista_generica(url, config, colortext):
    acestream_links = []
    link_names = []

    mostrar_notificacion("Actualizando lista", f"Obteniendo enlaces...", 1000)

    try:
        response = requests.get(url)
        response.encoding = 'utf-8'

        if config.get("mode") == "m3u":
            lines = response.text.splitlines()
            nombre_canal = None
            for line in lines:
                if line.startswith("#EXTINF:"):
                    nombre_canal = line.split(",", 1)[1].strip()
                elif line.startswith("acestream://"):
                    link = line.replace("acestream://", "").strip()
                    if link:  # Solo añadir si hay enlace
                        acestream_links.append(link)
                        link_names.append(nombre_canal if nombre_canal else "Canal")
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

                if not link:  # Saltar si el enlace queda vacío
                    continue

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

        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"links": acestream_links, "names": link_names, "colortext": colortext}, f, ensure_ascii=False)

        mostrar_notificacion("Lista actualizada", f"Se encontraron {len(acestream_links)} canales", 5000)

    except requests.exceptions.RequestException as e:
        mostrar_notificacion("Error", f"Error al actualizar la lista: {e}", 1000)

    return acestream_links, link_names, colortext


# --- Funciones de codificación/decodificación ---
def obfuscate(domain: str) -> str:
    return base64.b32encode(domain.encode()).decode().strip('=')

def deobfuscate(obf: str) -> str:
    padding = '=' * ((8 - len(obf) % 8) % 8)
    return base64.b32decode(obf + padding).decode()

def decodificar_datos(registro: str):
    try:
        registro = registro.replace('text = ', '').replace('"', '').strip()
        data = base64.b64decode(registro)
        try:
            data = gzip.decompress(data)
        except:
            pass
        return json.loads(data)
    except:
        return []

# --- Función para consultar registros TXT vía Cloudflare DoH ---
def consultar_dominio_doh(domain: str):
    url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=TXT"
    headers = {"Accept": "application/dns-json"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        registros = []
        if 'Answer' in data:
            for ans in data['Answer']:
                txt = ans['data'].strip('"')
                registros.append(txt)
        return registros
    except Exception as e:
        print("Error DNS DoH:", e)
        return []

# --- Función recursiva ---
def obtener_datos_recursivo(codigo, procesados=None):
    if procesados is None:
        procesados = set()
    if codigo in procesados:
        return []
    procesados.add(codigo)

    dominio = f"{codigo}.elcano.top"
    dominio_obf = obfuscate(dominio)
    dominio_final = deobfuscate(dominio_obf)

    registros = consultar_dominio_doh(dominio_final)
    elementos_finales = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {executor.submit(decodificar_datos, r): r for r in registros}
        for fut in as_completed(futuros):
            for elem in fut.result():
                if elem.get('type') == 'category' and elem.get('ref'):
                    elementos_finales.extend(obtener_datos_recursivo(elem['ref'], procesados))
                if elem.get('subLinks'):
                    elementos_finales.extend(elem['subLinks'])
                if elem.get('url'):
                    elementos_finales.append(elem)
    return elementos_finales

# --- Función principal ---
def actualizar_lista_dns(codigo, colortext):
    mostrar_notificacion("Actualizando lista", f"Obteniendo enlaces...", 1000)

    elementos = obtener_datos_recursivo(codigo)
    links = []
    names = []
    vistos = set()

    for elem in elementos:
        url = elem.get('url')
        nombre = elem.get('name', 'Stream sin nombre')

        # Filtrar solo enlaces AceStream válidos
        if not url or not url.startswith("acestream://"):
            continue

        # Evitar duplicados
        if url in vistos:
            continue
        vistos.add(url)

        # Guardar el enlace, el nombre y el color
        links.append(url.replace("acestream://", "").strip())
        names.append(nombre)

    # Guardar la lista en el archivo
    with open(LINKS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"links": links, "names": names, "colortext": colortext}, f, ensure_ascii=False)

    # Mostrar notificación con la cantidad de canales encontrados
    mostrar_notificacion("Lista actualizada", f"Se encontraron {len(links)} canales", 5000)
    print(f"Lista actualizada: {len(links)} canales")

    return links, names, colortext
