import os
import json
import requests
from bs4 import BeautifulSoup
import xbmcgui

# Constants
CWD = os.path.dirname(os.path.abspath(__file__))
LINKS_FILE = os.path.join(CWD, 'acestream_links.json')

def mostrar_notificacion(titulo, mensaje, duracion=3000):
    xbmcgui.Dialog().notification(titulo, mensaje, time=duracion, sound=False)

def cargar_enlaces_desde_json():
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, 'r') as f:
            data = json.load(f)
            links = data.get('links', [])
            names = data.get('names', [])
            colortext = data.get('colortext', 'white')  # Devuelve el color defecto white
            return links, names, colortext
    return [], [], 'white'  # Si no existe el archivo, devuelve listas vacías y color por defecto
