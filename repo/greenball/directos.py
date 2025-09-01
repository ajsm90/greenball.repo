import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import difflib
import json

class Event:
    def __init__(self, day: str, time: str, name: str, channel: str, sport: str, acestream_link: Optional[str] = None):
        self.day = day
        self.time = time
        self.name = name
        self.channel = channel
        self.sport = sport
        self.acestream_link = acestream_link

def find_closest_channel(channel_name: str, channels_names: List[str]) -> Optional[str]:
    """Encuentra el nombre de canal más cercano usando difflib y realiza correcciones de nombre si es necesario."""
    
    # Diccionario de correcciones de nombres de canales
    channel_corrections = {
        "GOL PLAY": "GOL TV",  
        "LALIGA TV HYPERMOTION 2": "LaLiga Hyper 2", 
        "LALIGA TV HYPERMOTION": "LaLiga Hyper TV", 
        "M+ Deportes 2": "M. Deportes 2",
        "M+ Deportes 3": "M. Deportes 3",
        "Movistar Plus+": "M.Plus", 
        "Movistar Plus+": "Movistar Plus",
        "LA 1": "La1",
        "LA 1": "LA 1 Op.1",
        "DAZN LALIGA 2": "DAZN LaLiga 2",
        "M+ LALIGA TV": "M. LaLiga",
    }

    # Aplicar la corrección si el canal actual tiene una sustitución
    corrected_channel_name = channel_corrections.get(channel_name, channel_name)
    
    # Buscar el nombre de canal más cercano usando difflib
    closest_matches = difflib.get_close_matches(corrected_channel_name, channels_names, n=1, cutoff=0.5)
    
    return closest_matches[0] if closest_matches else None


def get_tv_programs(url: str = "https://www.marca.com/programacion-tv.html", channel_map: dict = None) -> List[Event]:
    """Obtiene los programas de TV del URL especificado."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        day_sections = soup.find_all("li", class_="content-item")[1:]
        events_data = []
        seen_events = set()

        for day_section in day_sections:
            day_span = day_section.find("span", class_="title-section-widget")
            if not day_span:
                continue
            day = day_span.text.strip()

            events = day_section.find_all("li", class_="dailyevent")
            for event in events:
                time_tag = event.find("strong", class_="dailyhour")
                event_name_tag = event.find("h4", class_="dailyteams")
                channel_tag = event.find("span", class_="dailychannel")
                sport_tag = event.find("span", class_="dailyday")

                time_text = time_tag.text.strip() if time_tag else "N/A"
                event_name = event_name_tag.text.strip() if event_name_tag else "N/A"
                channel = channel_tag.text.strip() if channel_tag else "N/A"
                sport = sport_tag.text.strip() if sport_tag else "N/A"

                event_id = (day, time_text, event_name, channel)
                if event_id not in seen_events:
                    # Buscar canal más cercano
                    closest_channel = find_closest_channel(channel, channel_map["names"])
                    acestream_link = None
                    if closest_channel:
                        index = channel_map["names"].index(closest_channel)
                        acestream_link = channel_map["links"][index]

                    events_data.append(Event(day, time_text, event_name, channel, sport, acestream_link))
                    seen_events.add(event_id)

        return events_data

    except requests.RequestException as e:
        print(f"Failed to retrieve TV programs from {url}: {e}")
        return []


