from datetime import datetime
import os
import socket
import uuid
import fitz
import psutil
from typing import Dict, Any, Optional
import json 


# --- Konfiguráció Betöltő Függvény ---
# A service nevét a SvcDoRun-ban tudod lekérdezni (self._svc_name_), azt át kell adni.
def load_service_instance_config(config_file_path: str, service_name: str) -> Optional[Dict[str, Any]]:
    """
    Betölti az összes konfigurációt a fájlból, és visszaadja
    az aktuális service-hez tartozó config dictionary-t.
    None-t ad vissza hiba vagy nem található config esetén.
    Használja a servicemanager-t a korai logoláshoz.
    """
    # A servicemanager csak a service környezetben érhető el!
    # Ha ezt a függvényt service-en kívülről hívod, hibát dob, vagy kell egy fallback.
    # Service környezetben:
    # servicemanager.LogInfoMsg(...)
    
    all_configs: Dict[str, Any] = {}

    if not os.path.exists(config_file_path):
        print(f"FATAL: Konfigurációs fájl nem található: {config_file_path}")
        return None

    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            all_configs = json.load(f)
            print(f"Konfigurációs fájl sikeresen betöltve: {config_file_path}")

    except Exception as e:
        print(f"FATAL: Nem sikerült betölteni a konfigurációt a fájlból ({config_file_path}): {e}")
        return None

    instance_config = all_configs.get(service_name, None)
    if instance_config is None:
        print(f"FATAL: Nincs konfiguráció '{service_name}' nevű service-hez a fájlban.")
        return None

    print(f"Aktuális service '{service_name}' konfigurációja betöltve.")
    return instance_config


def log_to_file(event: str, logdir: str):
    # Dátum alapú fájlnév
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f'log_{date_str}.txt'
    full_path = os.path.join(logdir, filename)

    # Esemény időbélyeggel
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f'[{timestamp}] {event}'

    # Fájlba írás (hozzáfűzés)
    with open(full_path, 'a', encoding='utf-8') as f:
        f.write(entry + '\n')


def load_settings(file_path, setting_type):
    settings = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            exec(content, {}, settings)
            return settings.get(setting_type)
    except FileNotFoundError:
        print(f"Hiba: A fájl '{file_path}' nem található.")
        return None
    except Exception as e:
        print(f"Hiba a fájl beolvasása vagy feldolgozása során: {e}")
        return None
    

def pdf_to_images(pdf_path, output_dir="images"):
    """PDF oldalak konvertálása képekké."""
    import os
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(100/72, 100/72)  # Átalakítás DPI-re (az alapértelmezett 72 DPI)
        pix = page.get_pixmap(matrix=mat)
        output_file = os.path.join(output_dir, f"page_{page_num + 1}.png")
        pix.save(output_file)
        image_paths.append(output_file)
    doc.close()
    return image_paths


def get_windows_uptime():
    """
    Lekéri a Windows rendszer uptime idejét a psutil segítségével.
    Visszatérési érték: timedelta objektum az uptime-mal.
    """
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        total_seconds = int(uptime.total_seconds())
        days = total_seconds // (24 * 3600)
        hours = (total_seconds % (24 * 3600)) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return {'days':days, 'hours':hours, 'minutes':minutes, 'seconds':seconds}

    except Exception as e:
        print(f"Hiba az uptime lekérésekor: {e}")
        return None

        
def get_station_data():
    station_data = {
        "id": 8013,
        "name": 'EnOcean Labeling',
        "host_name": socket.gethostname(),
        "ip": '-',
        "mac": '-'
    }

    station_data["ip"] = socket.gethostbyname(station_data["host_name"])
    mac_num = hex(uuid.getnode()).replace('0x', '').zfill(12)
    station_data["mac"] = ':'.join(mac_num[i:i+2] for i in range(0, 12, 2))

    return station_data
