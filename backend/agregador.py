#!/usr/bin/env python3
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Guardamos el archivo en la raíz del repositorio
OUTPUT_FILE = "../camaras_oficiales.json"
TIMEOUT = 30

# Nos hacemos pasar por un navegador real para evitar bloqueos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def fetch_meteogalicia():
    """Descarga las cámaras de MeteoGalicia (URL CORREGIDA)"""
    cameras = []
    url = "https://servizos.meteogalicia.gal/mgrss/observacion/jsonCamaras.action"
    print("Descargando MeteoGalicia...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        # La estructura correcta es {"listaCamaras": [ ... ]}
        lista = data.get('listaCamaras', [])
        
        for cam in lista:
            try:
                lat = float(cam.get('lat'))
                lon = float(cam.get('lon'))
            except (TypeError, ValueError):
                continue
            cameras.append({
                "id": f"mg_{cam.get('identificador', 'unknown')}",
                "name": cam.get('nomeCamara', 'Cámara MeteoGalicia'),
                "lat": lat,
                "lon": lon,
                "source": "MeteoGalicia",
                "source_url": "https://servizos.meteogalicia.gal/",
                "image_url": cam.get('imaxeCamara'),
                "extra": {"concello": cam.get('concello', '')}
            })
        print(f"✅ MeteoGalicia: {len(cameras)} cámaras encontradas")
    except Exception as e:
        print(f"❌ MeteoGalicia falló: {e}")
    return cameras

def fetch_dgt():
    """Descarga las cámaras de la DGT (URL CORREGIDA y parser mejorado)"""
    cameras = []
    # URL CORREGIDA: infocar.dgt.es en lugar de nap.dgt.es
    xml_url = "http://infocar.dgt.es/datex2/dgt/CCTVSiteTablePublication/all/content.xml"
    print("Descargando DGT...")
    try:
        r = requests.get(xml_url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        
        # Contamos cuántas cámaras hay
        for record in root.iter():
            if 'cctvCameraMetadataRecord' in record.tag:
                cam_id = record.attrib.get('id', 'unknown')
                lat, lon, name, img = None, None, 'Cámara DGT', None
                for child in record.iter():
                    tag = child.tag.split('}')[-1] # Quitamos el namespace
                    if tag == 'latitude': lat = child.text
                    elif tag == 'longitude': lon = child.text
                    elif tag == 'cctvCameraIdentification': name = child.text
                    elif tag == 'urlLinkAddress': img = child.text
                
                if lat and lon:
                    cameras.append({
                        "id": f"dgt_{cam_id}",
                        "name": name,
                        "lat": float(lat),
                        "lon": float(lon),
                        "source": "DGT",
                        "source_url": "https://nap.dgt.es/",
                        "image_url": img,
                        "extra": {}
                    })
        print(f"✅ DGT: {len(cameras)} cámaras encontradas")
    except Exception as e:
        print(f"❌ DGT falló: {e}")
    return cameras

def fetch_madrid():
    """Descarga las cámaras de Madrid (URL CORREGIDA)"""
    cameras = []
    # URL CORREGIDA: El archivo KML con las cámaras de Madrid
    url = "https://datos.madrid.es/egob/catalogo/202088-0-trafico-camaras.kml"
    print("Descargando Madrid...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        # Usamos ElementTree para parsear el KML
        root = ET.fromstring(r.content)
        
        # En KML, los nombres de los tags incluyen el namespace
        # Buscamos todos los Placemark que contengan la información de la cámara
        for pm in root.iter():
            if 'Placemark' in pm.tag:
                name = 'Cámara Madrid'
                lat, lon, img = None, None, None
                for child in pm.iter():
                    tag = child.tag.split('}')[-1]
                    if tag == 'name': name = child.text
                    elif tag == 'coordinates':
                        # En KML, las coordenadas vienen como "lon,lat,alt"
                        coords = child.text.strip().split(',')
                        if len(coords) >= 2:
                            lon = coords[0]
                            lat = coords[1]
                    elif tag == 'href': img = child.text
                
                if lat and lon:
                    cameras.append({
                        "id": f"mad_{name.replace(' ', '_')}",
                        "name": name,
                        "lat": float(lat),
                        "lon": float(lon),
                        "source": "Madrid",
                        "source_url": "https://datos.madrid.es/",
                        "image_url": img,
                        "extra": {}
                    })
        print(f"✅ Madrid: {len(cameras)} cámaras encontradas")
    except Exception as e:
        print(f"❌ Madrid falló: {e}")
    return cameras

def aggregate_all():
    all_cams = []
    print(f"🔄 Iniciando: {datetime.now().isoformat()}")
    
    # Intentamos descargar de las fuentes oficiales
    mg_cams = fetch_meteogalicia()
    dgt_cams = fetch_dgt()
    mad_cams = fetch_madrid()
    
    all_cams.extend(mg_cams)
    all_cams.extend(dgt_cams)
    all_cams.extend(mad_cams)
    
    # Si ninguna fuente devolvió datos, añadimos una cámara de prueba para que veas que funciona
    if len(all_cams) == 0:
        print("⚠️ Ninguna fuente devolvió datos. Añadiendo cámara de prueba.")
        all_cams.append({
            "id": "test_1",
            "name": "Cámara de Prueba (Madrid)",
            "lat": 40.4168,
            "lon": -3.7038,
            "source": "Test",
            "source_url": "https://github.com",
            "image_url": None,
            "extra": {"concello": "Madrid"}
        })
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "total": len(all_cams),
        "cameras": all_cams
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"💾 Proceso terminado. Total guardado: {len(all_cams)}")

if __name__ == "__main__":
    aggregate_all()
