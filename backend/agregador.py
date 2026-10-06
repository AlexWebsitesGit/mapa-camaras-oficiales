#!/usr/bin/env python3
"""Agregador de cámaras oficiales."""

import json
import requests
import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime

OUTPUT_FILE = "camaras_oficiales.json"
TIMEOUT = 30

NS = {
    'ns2': 'http://datex2.eu/schema/3/d2Payload',
    'ns3': 'http://datex2.eu/schema/3/common',
    'ns4': 'http://datex2.eu/schema/3/locationReferencing',
    'ns5': 'http://datex2.eu/schema/3/trafficInfo',
}

def fetch_meteogalicia():
    cameras = []
    url = "https://servizos.meteogalicia.gal/meteo/json/camaras.json"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return cameras
        for cam in data:
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
        print(f"✅ MeteoGalicia: {len(cameras)}")
    except Exception as e:
        print(f"❌ MeteoGalicia: {e}")
    return cameras

def fetch_dgt():
    cameras = []
    xml_url = "https://nap.dgt.es/dataset/camaras-dgt-datex2-v3-7/resource/31f5727a-bbfe-4aa8-b1dc-d2fce1302e69/download/camaras_datex2_v37.xml"
    try:
        r = requests.get(xml_url, timeout=TIMEOUT)
        r.raise_for_status()
        root = etree.fromstring(r.content)
        records = root.xpath('//*[local-name()="cctvCameraMetadataRecord"]')
        for record in records:
            try:
                cam_id = record.get('id', 'unknown')
                lat_el = record.xpath('.//*[local-name()="latitude"]')
                lon_el = record.xpath('.//*[local-name()="longitude"]')
                if not lat_el or not lon_el:
                    continue
                name_el = record.xpath('.//*[local-name()="cctvCameraIdentification"]')
                url_el = record.xpath('.//*[local-name()="urlLinkAddress"]')
                cameras.append({
                    "id": f"dgt_{cam_id}",
                    "name": name_el[0].text if name_el else 'Cámara DGT',
                    "lat": float(lat_el[0].text),
                    "lon": float(lon_el[0].text),
                    "source": "DGT",
                    "source_url": "https://nap.dgt.es/",
                    "image_url": url_el[0].text if url_el else None,
                    "extra": {}
                })
            except Exception:
                continue
        print(f"✅ DGT: {len(cameras)}")
    except Exception as e:
        print(f"❌ DGT: {e}")
    return cameras

def fetch_madrid():
    cameras = []
    url = "https://datos.madrid.es/FWProjects/egob/Catalogo/Transporte/Calle30/Ficheros/Camaras.xml"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for cam in root.findall('Camara'):
            try:
                cameras.append({
                    "id": f"mad_{cam.find('Nombre').text.replace(' ', '_')}",
                    "name": cam.find('Nombre').text,
                    "lat": float(cam.find('Posicion/Latitud').text),
                    "lon": float(cam.find('Posicion/Longitud').text),
                    "source": "Madrid Calle 30",
                    "source_url": "https://datos.madrid.es/",
                    "image_url": cam.find('URL').text,
                    "extra": {}
                })
            except Exception:
                continue
        print(f"✅ Madrid: {len(cameras)}")
    except Exception as e:
        print(f"❌ Madrid: {e}")
    return cameras

def aggregate_all():
    all_cams = []
    print(f"🔄 {datetime.now().isoformat()}")
    all_cams.extend(fetch_meteogalicia())
    all_cams.extend(fetch_dgt())
    all_cams.extend(fetch_madrid())
    output = {
        "generated_at": datetime.now().isoformat(),
        "total": len(all_cams),
        "cameras": all_cams
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"💾 Total: {len(all_cams)}")

if __name__ == "__main__":
    aggregate_all()
