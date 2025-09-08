import sys
import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import requests
import urllib.parse
from urllib.parse import quote_plus
import difflib 
from search_canales import cargar_enlaces_desde_json
from update_list import actualizar_lista2, actualizar_lista_generica # Importar la función para actualizar la lista
from directos import get_tv_programs, find_closest_channel  # Importa find_closest_channel de directos
from tdt import obtener_canales_tdt
import time

# from directos2 import obtener_eventos
# from links_cine import obtener_eventos_nuevos, search_movies

from links_series import obtener_series, obtener_episodios, buscar_series, obtener_pelis, buscar_peliculas

from download import download_db
# from links_series import obtener_series, obtener_episodios_serie, buscar_series, obtener_imagen_de_serie

import requests, re
session = requests.Session()

def mostrar_notificacion(titulo, mensaje, duracion=3000):
    xbmcgui.Dialog().notification(titulo, mensaje, time=duracion, sound=False)

# Constants
ADDON = xbmcaddon.Addon()
PLUGIN_URL = sys.argv[0]
HANDLE = int(sys.argv[1])
BD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templ.db")

class KodiAddonWrapper:
    def __init__(self):
        self.handle = HANDLE
        self.plugin_url = PLUGIN_URL
    
    def show_main_menu(self):
        
        """Display the main menu with options."""
        main_options = [
        "TDT", "Directos", "Canales", 
        "Actualizar canales opcion 1", "Actualizar canales opcion 2 (por defecto)", 
        "Actualizar canales opcion 3","Actualizar canales opcion 4", "Cine", "Series", "Obtener series y pelis"
        ]
        
        # Definir un diccionario de colores para las opciones, por ejemplo:
        colors = {
            "TDT": "white",  # Color hexadecimal
            "Directos": "white",  # RGB
            "Canales": "white",  # Nombre de color
            "Actualizar canales opcion 1": "lightyellow",  # Tomate (hexadecimal)
            "Actualizar canales opcion 2 (por defecto)": "aqua",  # Azul
            "Actualizar canales opcion 3": "yellowgreen",  # Naranja
            "Actualizar canales opcion 4": "blue",  # Naranja
            "Cine": "white",  # Oro (hexadecimal)
            "Series": "white",  # Púrpura
            "Obtener series y pelis": "white",  # Rosa
        }

        for option in main_options:
            color = colors.get(option, "white")  # Si no hay color asignado, por defecto será blanco
            list_item = xbmcgui.ListItem(label=f"[COLOR {color}] {option} [/COLOR]")  # Aplicar color al texto
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=f"{self.plugin_url}?action={option.lower().replace(' ', '_')}",
                listitem=list_item,
                isFolder=True,
            )
    
        note_id = "e07hh8864iiw"
        clave = "666900"
        self.show_notepad_note_items(note_id, clave)
        xbmcplugin.endOfDirectory(self.handle)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://notepad.cc",
    })
    def show_notepad_note_items(self, note_id, clave):
        # Autenticación
        auth_url = f"https://notepad.cc/api/notes/{note_id}/authenticate?readonly=true"
        auth_resp = session.post(auth_url, json={"password": clave}, headers={
            "Referer": f"https://notepad.cc/share/{note_id}"
        })
        if auth_resp.status_code != 200:
            return

        # Obtener nota
        note_url = f"https://notepad.cc/api/notes/{note_id}?readonly=true"
        note_resp = session.get(note_url, headers={
            "Referer": f"https://notepad.cc/share/{note_id}"
        })
        if note_resp.status_code != 200:
            return

        text = note_resp.text

        # 🔹 Buscar INFO y LINKS más rápido (sin findall)
        info_match = re.search(r"INFO:\s*\[(.*?)\]", text)
        info_text = info_match.group(1).strip() if info_match else ""

        links_match = re.search(r"LINKS:\s*\[(.*?)\]", text)
        links_raw = links_match.group(1) if links_match else ""

        # 🔹 Procesar LINKS sin regex
        ace_links, channel_names = [], []
        if links_raw:
            links_items = [item.strip() for item in links_raw.replace("\\n", "").split(",") if item.strip()]
            for item in links_items:
                if "|" in item:
                    ace, name = item.split("|", 1)
                    ace_links.append(ace.strip())
                    channel_names.append(name.strip())
                else:
                    ace_links.append(item.strip())
                    channel_names.append("")

        # 🔹 Añadir los canales
        for ace, name in zip(ace_links, channel_names):
            hash_id = ace.replace("acestream://", "")
            list_item = xbmcgui.ListItem(label=name or hash_id)
            list_item.setInfo("video", {"title": name or hash_id})
            list_item.setProperty("IsPlayable", "true")
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=f"plugin://script.module.horus?action=play&id={hash_id}",
                listitem=list_item,
                isFolder=False
            )

        # 🔹 Añadir INFO al final
        if info_text:
            list_item = xbmcgui.ListItem(label=f"[COLOR yellow]{info_text}[/COLOR]")
            list_item.setArt({'icon': 'DefaultIconInfo.png'})
            list_item.setInfo("video", {"title": info_text})
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url="#",
                listitem=list_item,
                isFolder=False
            )

    def mostrar_canales_tdt(self):
        canales = obtener_canales_tdt()
        if not canales:
            xbmcgui.Dialog().notification("Error", "No se pudieron cargar los canales de TDT.", xbmcgui.NOTIFICATION_ERROR)
            return
        
        for canal in canales:
            if canal["url"]:
                list_item = xbmcgui.ListItem(label=canal["name"])
                list_item.setArt({'thumb': canal["logo"]})
                list_item.setInfo("video", {"title": canal["name"]})
                url = canal["url"]  # Link directo para la reproducción
                xbmcplugin.addDirectoryItem(
                    handle=self.handle, 
                    url=url, 
                    listitem=list_item, 
                    isFolder=False,
                )

        xbmcplugin.endOfDirectory(self.handle)
    
    def show_directos(self):
        """Display live events with their associated channels, grouped by date."""
        canales_url = "https://ipfs.io/ipns/k51qzi5uqu5dgg9al11vomikugim0o1i3l3fxp3ym3jwaswmy9uz8pq4brg1u9"
        links, names, colortext = cargar_enlaces_desde_json()

        if not links or not names:
            links, names, colortext = actualizar_lista2(canales_url)

        # Obtener los eventos deportivos
        channel_map = {"names": names, "links": links}
        eventos = get_tv_programs(channel_map=channel_map)

        # Agrupar eventos por fecha
        eventos_por_fecha = {}
        for evento in eventos:
            
            # Agregar el evento a la lista de esa fecha
            if evento.day not in eventos_por_fecha:
                eventos_por_fecha[evento.day] = []
            eventos_por_fecha[evento.day].append(evento)  # Guardamos el objeto Event, no una tupla

        # Definir los deportes que queremos mostrar
        deportes_validos = ["Fútbol", "Fórmula 1", "Motos"]
        
        # Mostrar los eventos en el menú, agrupados por fecha
        for fecha, eventos_lista in eventos_por_fecha.items():
            # Enviar la fecha como un "comentario" sin enlace, con color amarillo
            list_item_fecha = xbmcgui.ListItem(label=f"[COLOR yellow]{fecha}[/COLOR]")
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url="#",  # No tiene enlace, es solo un comentario
                listitem=list_item_fecha,
                isFolder=False
            )

            # Mostrar cada evento de esa fecha con su hora
            for evento in eventos_lista:
                hora = evento.time
                nombre_evento = evento.name
                canal = evento.channel
                tipoevento = evento.sport
                closest_channel = find_closest_channel(canal, names)

                # Filtrar los eventos por los deportes válidos
                if evento.sport not in deportes_validos:
                    continue  # Si el deporte no es válido, omitir el evento

                # Si hay enlace
                if closest_channel:
                    idx = names.index(closest_channel)
                    acestream_link = links[idx]
                    # Incluir la hora, nombre del evento y canal en el label
                    list_item = xbmcgui.ListItem(label=f"[COLOR {colortext}]{hora} - {nombre_evento} - {canal} - {tipoevento}[/COLOR]")
                    list_item.setInfo("video", {"title": f"{nombre_evento} - {tipoevento}"})
                    list_item.setProperty("IsPlayable", "true")

                    xbmcplugin.addDirectoryItem(
                        handle=self.handle,
                        url=f"plugin://script.module.horus?action=play&id={acestream_link}",
                        listitem=list_item,
                        isFolder=False
                    )

            # Si no hay eventos válidos (sin enlace o sin deporte válido), no se añaden al menú.
            # No es necesario mostrar nada si no se encuentra enlace o si el deporte es inválido.

        xbmcplugin.endOfDirectory(self.handle)
    
    
    def show_canales(self):
        """Display the Canales menu."""
        canales_url = "https://ipfs.io/ipns/k51qzi5uqu5dgg9al11vomikugim0o1i3l3fxp3ym3jwaswmy9uz8pq4brg1u9" 
        links, names, colortext = cargar_enlaces_desde_json()

        if not links or not names:
            # Si no hay enlaces, busca y guarda en JSON
            links, names, colortext = actualizar_lista2(canales_url)

        # Mostrar los canales en el menú
        for idx, (name, link) in enumerate(zip(names, links), start=1):
            # Aplicar el color al texto del nombre del canal usando el valor colortext
            list_item = xbmcgui.ListItem(label=f"[COLOR {colortext}] {name} [/COLOR]")  # Aplicar color
            list_item.setInfo("video", {"title": name})  # Añadir información sobre el video
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=f"plugin://script.module.horus?action=play&id={link}",  # URL para reproducir
                listitem=list_item,
                isFolder=False,
            )
        
        xbmcplugin.endOfDirectory(self.handle)

    def update_list(self):
        config_eventos = {
            "mode": "html",
            "selector": "td.canales a",
            "attr": "href",
            "prefix": "acestream://",
            "text": True
        }
        colortext = "lightyellow"
        links, names, colortext  = actualizar_lista_generica("https://eventos-uvl7.vercel.app/", config_eventos, colortext)

    def update_list2(self):
        """Update the list of channels el cano."""
        canales_url = "https://ipfs.io/ipns/k51qzi5uqu5dgg9al11vomikugim0o1i3l3fxp3ym3jwaswmy9uz8pq4brg1u9"  

        links, names, colortext = actualizar_lista2(canales_url)  # Llamar a la función para actualizar la lista

    def update_list3(self):
        canales_url = "https://fr.4everproxy.com/direct/aHR0cHM6Ly9jaXJpYWNvLWxpYXJ0LnZlcmNlbC5hcHAv"

        config_freijo = {
            "mode": "html",            
            "selector": "tr td a",
            "attr": "href",
            "prefix": "acestream://",
            "text": True
        }
        colortext = "yellowgreen"
        links, names, colortext = actualizar_lista_generica(canales_url, config_freijo, colortext)

    def update_list4(self):
        """Update the list of channels."""
        config_canalcard = {
            "mode": "html",
            "selector": "article.canal-card a.acestream-link",
            "attr": "href",
            "prefix": "acestream://",
            "text": False,
            "name_selector": "span.canal-nombre",
            "parent_tag": "article"   # para buscar el nombre dentro del mismo bloque
        }
        colortext = "blue"
        links, names, colortext = actualizar_lista_generica("https://shickat.me/", config_canalcard, colortext)



    

    

    def mostrar_pelis(self, pagina=1):
        """Display new events with their associated links and images."""

        # Verificar si la base de datos existe
        if not os.path.exists(BD_PATH):
            # Si no existe la base de datos, mostrar una notificación y salir
            xbmcgui.Dialog().notification("Error", "Base de datos no encontrada, Pulsa en obtener series y pelis primero", xbmcgui.NOTIFICATION_ERROR, 5000)
            return  # Salir de la función si no se encuentra la base de datos
        
        # Agregar un enlace para buscar por título
        buscar_item = xbmcgui.ListItem(label="BUSCAR POR TITULO")
        buscar_url = f"{sys.argv[0]}?action=buscar_titulo_peli"
        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url=buscar_url,
            listitem=buscar_item,
            isFolder=True
        )

        eventos_nuevos = obtener_pelis(pagina)  

        for evento in eventos_nuevos:
            nombre_evento = evento['titulo']
            enlace = evento['url']
            url_codificada = quote_plus(enlace)
            url_imagen = evento['imagen']
            descripcion = evento.get('descripcion', "Descripción no disponible.")  #descripción

            # Crear el ListItem para Kodi
            list_item = xbmcgui.ListItem(label=nombre_evento)
            # list_item.setArt({'thumb': url_imagen})  # Establecer la imagen
            list_item.setArt({'thumb': url_imagen, 'icon': url_imagen, 'fanart': url_imagen})
            list_item.setInfo("video", {
                "title": nombre_evento,
                "plot": descripcion  # Añadir la descripción 
            })
            list_item.setProperty("IsPlayable", "true")  # Marcarlo como reproducible

            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=f"plugin://plugin.video.elementum/play?uri={url_codificada}",  # enlace de descarga para reproducir
                listitem=list_item,
                isFolder=False
            )

        # Si hay más páginas de resultados, añadir el enlace "Mostrar más resultados"
        next_page_url = f"{sys.argv[0]}?action=cine&pagina={pagina + 1}"
        next_page_item = xbmcgui.ListItem(label="MOSTRAR MÁS RESULTADOS")
        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url=next_page_url,
            listitem=next_page_item,
            isFolder=True  # Esto indica que es un "folder" (una página más de resultados)
        )

        xbmcplugin.endOfDirectory(self.handle)

    def buscar_titulo_peli(self):
        """Función para buscar series por título."""
        dialog = xbmcgui.Dialog()
        titulo = dialog.input("Ingrese el título de la pelicula:")
        
        if titulo: 
            eventos_nuevos = buscar_peliculas(titulo)  
            
            # Verificar si se encontraron resultados
            if not eventos_nuevos:
                mostrar_notificacion("No se encontraron resultados", "No se encontraron peliculas con ese título.", 3000)
                return
        for evento in eventos_nuevos:
            nombre_evento = evento['titulo']
            enlace = evento['url']
            url_codificada = quote_plus(enlace)
            url_imagen = evento['imagen']
            descripcion = evento.get('descripcion', "Descripción no disponible.")  #descripción

            # Crear el ListItem para Kodi
            list_item = xbmcgui.ListItem(label=nombre_evento)
            # list_item.setArt({'thumb': url_imagen})  # Establecer la imagen
            list_item.setArt({'thumb': url_imagen, 'icon': url_imagen, 'fanart': url_imagen})
            list_item.setInfo("video", {
                "title": nombre_evento,
                "plot": descripcion  # Añadir la descripción 
            })
            list_item.setProperty("IsPlayable", "true")  # Marcarlo como reproducible

            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=f"plugin://plugin.video.elementum/play?uri={url_codificada}",  # enlace de descarga para reproducir
                listitem=list_item,
                isFolder=False
            )
            
        mostrar_notificacion("Terminado", "Mostrando lista", 1000)
        xbmcplugin.endOfDirectory(self.handle)

    
    
    def mostrar_series(self, pagina=1):
        """Muestra las series con sus imágenes y descripciones en el addon de Kodi."""
        # Verificar si la base de datos existe
        if not os.path.exists(BD_PATH):
            # Si no existe la base de datos, mostrar una notificación y salir
            xbmcgui.Dialog().notification("Error", "Base de datos no encontrada, Pulsa en obtener series y pelis primero", xbmcgui.NOTIFICATION_ERROR, 5000)
            return  # Salir de la función si no se encuentra la base de datos
        # Elemento para buscar por título
        buscar_item = xbmcgui.ListItem(label="BUSCAR POR TITULO")
        buscar_url = f"{sys.argv[0]}?action=buscar_titulo_serie"
        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url=buscar_url,
            listitem=buscar_item,
            isFolder=True
        )

        # Obtener las series de la base de datos (página específica)
        series = obtener_series(pagina)  # Pasamos la página a obtener_series

        # Iterar sobre las series y añadirlas a la interfaz de Kodi
        for serie in series:
            nombre_serie = serie['titulo']
            url_imagen = serie['imagen']
            serieID = serie['serieID']
            descripcion = serie.get('descripcion', "Descripción no disponible.")
            url_serie = f"{sys.argv[0]}?action=mostrar_episodios&serieID={serieID}&imagen={url_imagen}"
            
            # Crear un ListItem para la serie
            list_item = xbmcgui.ListItem(label=nombre_serie)
            list_item.setArt({'thumb': url_imagen, 'icon': url_imagen, 'fanart': url_imagen})
            list_item.setInfo("video", {
                "title": nombre_serie,
                "plot": descripcion
            })
            
            # Añadir el item a la interfaz de Kodi
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=url_serie,
                listitem=list_item,
                isFolder=True  # Esto hace que sea un "folder" para navegar
            )

        # Si hay más páginas de resultados, añadir el enlace "Mostrar más resultados"
        next_page_url = f"{sys.argv[0]}?action=series&pagina={pagina + 1}"
        next_page_item = xbmcgui.ListItem(label="MOSTRAR MÁS RESULTADOS")
        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url=next_page_url,
            listitem=next_page_item,
            isFolder=True  # Esto indica que es un "folder" (una página más de resultados)
        )

        # Finaliza el directorio de la lista
        xbmcplugin.endOfDirectory(self.handle)

    def buscar_titulo_serie(self):
        """Función para buscar series por título."""
        dialog = xbmcgui.Dialog()
        titulo = dialog.input("Ingrese el título de la serie:")
        
        if titulo: 

            series = buscar_series(titulo)
            
            # Verificar si se encontraron resultados
            if not series:
                mostrar_notificacion("No se encontraron resultados", "No se encontraron series con ese título.", 3000)
                return
                        
            # Iterar sobre las series y añadirlas a la interfaz de Kodi
            for serie in series:
                nombre_serie = serie['titulo']
                url_imagen = serie['imagen']
                serieID = serie['serieID']
                descripcion = serie.get('descripcion', "Descripción no disponible.")
                url_serie = f"{sys.argv[0]}?action=mostrar_episodios&serieID={serieID}&imagen={url_imagen}"
                
                # Crear un ListItem para la serie
                list_item = xbmcgui.ListItem(label=nombre_serie)
                list_item.setArt({'thumb': url_imagen, 'icon': url_imagen, 'fanart': url_imagen})
                list_item.setInfo("video", {
                    "title": nombre_serie,
                    "plot": descripcion
                })
                
                # Añadir el item a la interfaz de Kodi
                xbmcplugin.addDirectoryItem(
                    handle=self.handle,
                    url=url_serie,
                    listitem=list_item,
                    isFolder=True  # Esto hace que sea un "folder" para navegar
                )

            mostrar_notificacion("Terminado", "Mostrando lista", 1000)
            xbmcplugin.endOfDirectory(self.handle)
    
    def mostrar_episodios(self, serieID, url_imagen):
        """Muestra los episodios de una serie específica en el addon de Kodi."""
        episodios = obtener_episodios(serieID)

        for episodio in episodios:
            nombre_episodio = episodio['titulo']
            enlace_descarga = episodio['stream_url']
            url_codificada = quote_plus(enlace_descarga)
            fecha = episodio['fecha']
            
            # Crear el ListItem para Kodi
            list_item = xbmcgui.ListItem(label=nombre_episodio)
            
            # Formatear la fecha de emisión
            descripcion = f"Emitido el {fecha}"  # Aseguramos que 'fecha' es una cadena de texto
            
            # Configurar la imagen de la serie
            list_item.setArt({'thumb': url_imagen, 'icon': url_imagen, 'fanart': url_imagen})
            
            # Establecer la información del episodio
            list_item.setInfo("video", {
                "title": nombre_episodio,
                "plot": descripcion  # Usamos la descripción formateada como cadena
            })
            
            # Indicamos que el episodio es reproducible
            list_item.setProperty("IsPlayable", "true")

            # Añadir el episodio a la interfaz de Kodi
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=f"plugin://plugin.video.elementum/play?uri={url_codificada}",  
                listitem=list_item,
                isFolder=False  # Esto indica que no es un folder, es un episodio reproducible
            )

        # Finalizar el directorio de la lista
        xbmcplugin.endOfDirectory(self.handle)

    def download_shows_movies(self):
        download_db()

    def run(self):
        """Run the addon by handling the current action."""
        # Parse query parameters
        params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
        action = params.get("action")
        
        if action == "directos":
            self.show_directos()
        # elif action == "directos_2_(lista_propia)":
        #     self.show_directos2()
        elif action == "obtener_series_y_pelis":
            self.download_shows_movies()
        elif action == "cine":  
            pagina = int(params.get("pagina", 1))  
            self.mostrar_pelis(pagina)
        elif action == "series":  
            pagina = int(params.get("pagina", 1))  
            self.mostrar_series(pagina)
        elif action == 'mostrar_episodios':
            serieID = params.get('serieID')
            url_imagen = params.get('imagen')  # Obtener la imagen de la serie
            self.mostrar_episodios(serieID, url_imagen)
        elif action == 'buscar_titulo_peli':
            self.buscar_titulo_peli()
        elif action == 'buscar_titulo_serie':
            self.buscar_titulo_serie()
        elif action == "tdt":
            self.mostrar_canales_tdt()
        elif action == "canales":
            self.show_canales()
        elif action == "actualizar_canales_opcion_1":
            self.update_list()
            xbmcgui.Dialog().notification("Info", "Lista actualizada exitosamente.")
        elif action == "actualizar_canales_opcion_2_(por_defecto)":
            self.update_list2()
            xbmcgui.Dialog().notification("Info", "Lista actualizada exitosamente.")
        elif action == "actualizar_canales_opcion_3":
            self.update_list3()
            xbmcgui.Dialog().notification("Info", "Lista actualizada exitosamente.")
        elif action == "actualizar_canales_opcion_4":
            self.update_list4()
            xbmcgui.Dialog().notification("Info", "Lista actualizada exitosamente.")
        else:
            self.show_main_menu()
            

def main():
    addon = KodiAddonWrapper()
    addon.run()


if __name__ == "__main__":
    main()
