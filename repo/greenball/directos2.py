import requests
from bs4 import BeautifulSoup

def obtener_eventos():
    url = "https://eventos-liartvercelapp.vercel.app/"
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        eventos = []

        # Busca la tabla con los eventos
        tabla = soup.find('table', class_='styled-table')
        filas = tabla.find_all('tr')[1:]  # Ignora la cabecera
        
        for fila in filas:
            celdas = fila.find_all('td')
            if len(celdas) >= 5:  # Asegúrate de que hay suficientes celdas
                hora = celdas[0].text.strip()
                evento = celdas[1].text.strip()
                equipos_deportistas = celdas[2].text.strip() + ' vs ' + celdas[3].text.strip()
                
                # Obtiene los enlaces Acestream
                enlaces_acestream = [a['href'] for a in celdas[4].find_all('a')]
                
                eventos.append({
                    'hora': hora,
                    'evento': evento,
                    'equipos_deportistas': equipos_deportistas,
                    'enlaces_acestream': enlaces_acestream
                })
        
        return eventos
    else:
        print(f"Error al acceder a la URL: {response.status_code}")
        return []

# Ejemplo de uso
eventos = obtener_eventos()
for e in eventos:
    print(e)
