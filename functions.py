from datetime import datetime
import os
import socket
import uuid
import datasource as ds


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

        
def get_station_data():
    station_data = {
        "id": -1,
        "name": '-',
        "host_name": socket.gethostname(),
        "ip": '-',
        "mac": '-'
    }

    station_data["ip"] = socket.gethostbyname(station_data["host_name"])
    mac_num = hex(uuid.getnode()).replace('0x', '').zfill(12)
    station_data["mac"] = ':'.join(mac_num[i:i+2] for i in range(0, 12, 2))

    return station_data


def get_user_data(prime_nr: str):
    user_data = {
        "id": -1,
        "name": '-',
        "prime_nr": '-',
        "language": '-',
        "role_id": -1
    }

    if prime_nr != '-':
        sql_datas = ds.get_user_datas(prime_nr)
        if sql_datas:
            user_data["prime_nr"] = prime_nr
            user_data['id']       = sql_datas['userId']
            user_data['name']     = sql_datas['userName']
            user_data['language'] = sql_datas['language']
            user_data['role_id']  = sql_datas['roleId']

    return user_data


def get_type_data(product_code: str):
    type_data = {
        "id": -1,
        "code": '',
        "name": '',
        "log_nr": ''
    }

    if product_code != '-':
        sql_datas = ds.get_type_datas(product_code)
        if sql_datas:
            type_data['code']   = product_code
            type_data["id"]     = sql_datas['productId']
            type_data["name"]   = sql_datas['productName']
            type_data["log_nr"] = sql_datas['logNr']

    return type_data


def get_label_data(product_id: str, entry_nr: int):
    label_data = {
        "last_sn": '',
        "hwsw": '',
        "bom": '',
        "label_code": '',
        "foil_type": '',
        "label_file": '',
        "sn_format": '',
        "sn_reset": '',
        "copies": ''
    }

    if product_id != '-':
        sql_datas = ds.get_label_datas(product_id, entry_nr)
        if sql_datas:
            label_data['last_sn']    = sql_datas['lastSn']
            label_data["hwsw"]       = sql_datas['hwswIndex']
            label_data["bom"]        = sql_datas['bomNr']
            label_data["label_code"] = sql_datas['labelCode']
            label_data["foil_type"]  = sql_datas['foilType']
            label_data["label_file"] = sql_datas['labelFile']
            label_data["sn_format"]  = sql_datas['snFormat']
            label_data["sn_reset"]   = sql_datas['snResetType']
            label_data["copies"]     = sql_datas['copies']

    return label_data