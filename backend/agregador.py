#!/usr/bin/env python3
import json
import requests
from datetime import datetime
import os
from lxml import etree

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "camaras_oficiales.json")
TIMEOUT = 60

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def fetch_meteogalicia():
    cameras = []
    url = "https://servizos.meteogalicia.gal/mgrss/observacion/jsonCamaras.action"
    print("Descargando MeteoGalicia...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for cam in data.get('listaCamaras', []):
            try:
                lat = float(cam.get('lat'))
                lon = float(cam.get('lon'))
            except (TypeError, ValueError):
                continue
            cameras.append({
                "id": f"mg_{cam.get('identificador', 'unknown')}",
                "name": cam.get('nomeCamara', 'Cámara MeteoGalicia'),
                "lat": lat, "lon": lon,
                "source": "MeteoGalicia",
                "source_url": "https://servizos.meteogalicia.gal/",
                "image_url": cam.get('imaxeCamara'),
                "extra": {"concello": cam.get('concello', '')}
            })
        print(f"✅ MeteoGalicia: {len(cameras)} cámaras encontradas")
    except Exception as e:
        print(f"❌ MeteoGalicia falló: {e}")
    return cameras


def get_text(elem, xpath_expr):
    """Helper: devuelve el texto del primer resultado de un XPath, o None."""
    result = elem.xpath(xpath_expr)
    if result and result[0].text:
        return result[0].text.strip()
    return None


def fetch_dgt():
    """Parser definitivo de la DGT (tags: device, pointLocation, latitude, longitude, deviceUrl)"""
    cameras = []
    xml_url = "https://nap.dgt.es/dataset/camaras-dgt-datex2-v3-7/resource/31f5727a-bbfe-4aa8-b1dc-d2fce1302e69/download/camaras_datex2_v37.xml"
    print("Descargando DGT...")
    try:
        r = requests.get(xml_url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        print(f"   📦 Descargados {len(r.content)} bytes")
        
        tree = etree.fromstring(r.content)
        
        # Buscar TODOS los elementos <device> en cualquier namespace
        devices = tree.xpath('//*[local-name()="device"]')
        print(f"   🔍 Encontrados {len(devices)} elementos <device>")
        
        for idx, dev in enumerate(devices):
            try:
                # Coordenadas: pueden estar anidadas dentro de pointCoordinates
                lat = get_text(dev, './/*[local-name()="latitude"]')
                lon = get_text(dev, './/*[local-name()="longitude"]')
                
                if not lat or not lon:
                    continue
                
                # URL de la imagen
                img = get_text(dev, './/*[local-name()="deviceUrl"]')
                
                # Información extra
                road = get_text(dev, './/*[local-name()="roadName"]') or ''
                km = get_text(dev, './/*[local-name()="kilometerPoint"]') or ''
                province = get_text(dev, './/*[local-name()="province"]') or ''
                type_dev = get_text(dev, './/*[local-name()="typeOfDevice"]') or ''
                
                # Nombre descriptivo
                name_parts = []
                if road:
                    name_parts.append(road)
                if km:
                    name_parts.append(f"km {km}")
                if province:
                    name_parts.append(f"({province})")
                name = " - ".join(name_parts) if name_parts else f"Cámara DGT #{idx+1}"
                
                cameras.append({
                    "id": f"dgt_{idx+1}",
                    "name": name,
                    "lat": float(lat),
                    "lon": float(lon),
                    "source": "DGT",
                    "source_url": "https://nap.dgt.es/",
                    "image_url": img,
                    "extra": {
                        "road": road,
                        "km": km,
                        "province": province,
                        "type": type_dev
                    }
                })
            except Exception as e:
                continue
        
        print(f"✅ DGT: {len(cameras)} cámaras encontradas")
    except Exception as e:
        print(f"❌ DGT falló: {e}")
        import traceback
        traceback.print_exc()
    return cameras


def fetch_madrid():
    cameras = []
    url = "https://datos.madrid.es/egob/catalogo/202088-0-trafico-camaras.kml"
    print("Descargando Madrid...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        tree = etree.fromstring(r.content)
        for pm in tree.iter():
            if 'Placemark' in str(pm.tag):
                name, lat, lon, img = 'Cámara Madrid', None, None, None
                for child in pm.iter():
                    tag = child.tag.split('}')[-1]
                    if tag == 'name': name = child.text
                    elif tag == 'coordinates' and child.text:
                        coords = child.text.strip().split(',')
                        if len(coords) >= 2:
                            lon, lat = coords[0], coords[1]
                    elif tag == 'href': img = child.text
                if lat and lon:
                    cameras.append({
                        "id": f"mad_{name.replace(' ', '_')}",
                        "name": name,
                        "lat": float(lat), "lon": float(lon),
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
    
    all_cams.extend(fetch_meteogalicia())
    all_cams.extend(fetch_dgt())
    all_cams.extend(fetch_madrid())
    
    if len(all_cams) == 0:
        print("⚠️ Ninguna fuente devolvió datos. Añadiendo cámara de prueba.")
        all_cams.append({
            "id": "test_1", "name": "Cámara de Prueba (Madrid)",
            "lat": 40.4168, "lon": -3.7038, "source": "Test",
            "source_url": "https://github.com", "image_url": None,
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
