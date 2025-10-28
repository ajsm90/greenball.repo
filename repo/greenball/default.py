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
from directos import get_tv_programs, find_closest_channel, normalize_channel_name  # Importa find_closest_channel de directos
from tdt import obtener_canales_tdt
import time

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
        "TDT", "Directos", "Canales"
        ]
        
        # Definir un diccionario de colores para las opciones, por ejemplo:
        colors = {
            "TDT": "white",  # Color hexadecimal
            "Directos": "white",  # RGB
            "Canales": "white"  # Nombre de color
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
        xbmcplugin.endOfDirectory(self.handle)

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
        data = cargar_enlaces_desde_json()

        links = data.get("links", [])
        names = data.get("names", [])
        colortext = data.get("colortext", "white")
        last_update = data.get("last_update", "desconocida")

        data = cargar_enlaces_desde_json()
        last_update = data.get("last_update", "desconocida")

        # Mostrar un item al principio con la fecha de última actualización
        info_item = xbmcgui.ListItem(label=f"[COLOR yellow][B]Canales actualizados: {last_update}[/B][/COLOR]")
        info_item.setInfo("video", {"title": "Última actualización"})
        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url="",
            listitem=info_item,
            isFolder=False
        )

        # Obtener los eventos deportivos
        channel_map = {"names": names, "links": links}
        eventos = get_tv_programs(channel_map=channel_map)

        # Agrupar eventos por fecha
        eventos_por_fecha = {}
        for evento in eventos:
            if evento.day not in eventos_por_fecha:
                eventos_por_fecha[evento.day] = []
            eventos_por_fecha[evento.day].append(evento)

        deportes_validos = ["Fútbol", "Fórmula 1", "Motos", "Baloncesto", "Tenis", "Boxeo", "Ciclismo"]

        # Mostrar los eventos en el menú, agrupados por fecha
        for fecha, eventos_lista in eventos_por_fecha.items():
            list_item_fecha = xbmcgui.ListItem(label=f"[COLOR yellow]{fecha}[/COLOR]")
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url="#",
                listitem=list_item_fecha,
                isFolder=False
            )

            for evento in eventos_lista:
                hora = evento.time
                nombre_evento = evento.name
                canal = evento.channel
                tipoevento = evento.sport

                if evento.sport not in deportes_validos:
                    continue

                # Buscar todos los índices que coincidan con el canal
                indices_coincidentes = [i for i, name in enumerate(names) if normalize_channel_name(name) == normalize_channel_name(canal)]
                
                if not indices_coincidentes:
                    continue

                # Mostrar el primer enlace con el nombre completo del evento
                idx_principal = indices_coincidentes[0]
                acestream_link = links[idx_principal]
                list_item = xbmcgui.ListItem(
                    label=f"[COLOR {colortext}]{hora} | {nombre_evento} | {canal} | {tipoevento}[/COLOR]"
                )
                list_item.setInfo("video", {"title": f"{nombre_evento} | {tipoevento}"})
                list_item.setProperty("IsPlayable", "true")
                xbmcplugin.addDirectoryItem(
                    handle=self.handle,
                    url=f"plugin://script.module.horus?action=play&id={acestream_link}",
                    listitem=list_item,
                    isFolder=False
                )

                # Mostrar los enlaces adicionales como opciones numeradas
                for i, idx in enumerate(indices_coincidentes[1:], start=1):
                    acestream_link = links[idx]
                    list_item = xbmcgui.ListItem(
                        label=f"{hora} | {nombre_evento} | Opción {i}"
                    )
                    list_item.setInfo("video", {"title": f"{nombre_evento} - {tipoevento} (Opción {i})"})
                    list_item.setProperty("IsPlayable", "true")
                    xbmcplugin.addDirectoryItem(
                        handle=self.handle,
                        url=f"plugin://script.module.horus?action=play&id={acestream_link}",
                        listitem=list_item,
                        isFolder=False
                    )


        xbmcplugin.endOfDirectory(self.handle)

    
    
    def show_canales(self):
        """Display the Canales menu."""
        data = cargar_enlaces_desde_json()  # Ahora devuelve también 'last_update'

        links = data.get("links", [])
        names = data.get("names", [])
        colortext = data.get("colortext", "white")
        last_update = data.get("last_update", "desconocida")

        
        data = cargar_enlaces_desde_json()
        last_update = data.get("last_update", "desconocida")

        # Mostrar un item al principio con la fecha de última actualización
        info_item = xbmcgui.ListItem(label=f"[COLOR yellow][B]Canales actualizados: {last_update}[/B][/COLOR]")
        info_item.setInfo("video", {"title": "Última actualización"})
        xbmcplugin.addDirectoryItem(
            handle=self.handle,
            url="",
            listitem=info_item,
            isFolder=False
        )

        # Mostrar los canales en el menú
        for idx, (name, link) in enumerate(zip(names, links), start=1):
            list_item = xbmcgui.ListItem(label=f"[COLOR {colortext}] {name} [/COLOR]")
            list_item.setInfo("video", {"title": name})
            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=f"plugin://script.module.horus?action=play&id={link}",
                listitem=list_item,
                isFolder=False,
            )
        
        xbmcplugin.endOfDirectory(self.handle)

    def run(self):
        """Run the addon by handling the current action."""
        # Parse query parameters
        params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
        action = params.get("action")
        
        if action == "directos":
            self.show_directos()
        elif action == "tdt":
            self.mostrar_canales_tdt()
        elif action == "canales":
            self.show_canales()
        else:
            self.show_main_menu()
            

def main():
    addon = KodiAddonWrapper()
    addon.run()


if __name__ == "__main__":
    main()
