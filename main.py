from nicegui import ui
import threading
import webview
import time
import serial
import queue
import os
import socket
import uuid
import datasource as ds
import functions as fn


STATION_DATA = {
    "id": -1,
    "name": '-',
    "host_name": socket.gethostname(),
    "ip": '-',
    "mac": '-'
}

STATION_DATA["ip"] = socket.gethostbyname(STATION_DATA["host_name"])
mac_num = hex(uuid.getnode()).replace('0x', '').zfill(12)
STATION_DATA["mac"] = ':'.join(mac_num[i:i+2] for i in range(0, 12, 2))

LOG_DIR = r'\\srv14-fs01\production\traceability\marking\ManualLabeling\Programs\Labeling\Log'
fn.log_to_file(f"IP: {STATION_DATA["ip"]}; MAC: {STATION_DATA["mac"]}", LOG_DIR)

SERIALPORT_DATA = {
    "port": 'COM6',
    "baudrate": 9600,
    "data_queue": queue.Queue()
}

USER_DATA = {
    "id": -1,
    "name": '-',
    "prime_nr": '-',
    "language": 'HU',
    "role_id": -1
}

TYPE_DATA = {
    "product_id": -1,
    "product_code": '',
    "product_name": '',
    "log_nr": ''
}

EO_TYPES = ['--- Válassz típust ---', 
            '10000323 - TCM615 CA', 
            '13603089-01 - TCM515U']


def print_sn():
    os.system('copy /b cimke.zpl "\\\\localhost\\ZDesignerGK420t"')

def type_change(selected_type):
    if selected_type.value != '--- Válassz típust ---':
        type_code = selected_type.value.split(' - ')[0]
        sql_datas = ds.get_type_datas(type_code)
        if sql_datas:
            TYPE_DATA["product_id"]   = sql_datas['productId']
            TYPE_DATA['product_code'] = type_code
            TYPE_DATA["product_name"] = sql_datas['productName']
            TYPE_DATA["log_nr"]       = sql_datas['logNr']

            fn.log_to_file(f"Type selected: {selected_type.value} ({TYPE_DATA["product_id"]})", LOG_DIR)

# Header
with ui.header(elevated=True).style('background-color: #333; color: white; padding: 15px 15px; height: 65px'):
    with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%;'):

        ui.select(['ENOCEAN_LABELING',], value='ENOCEAN_LABELING') \
            .style('width: 250px; margin-right: 10px; flex: none; font-size: 15px;') \
            .props('rounded outlined dense')
        
        with ui.input(placeholder='Felhasználó...') \
            .style('width: 150px; margin-right: 10px; flex: auto; font-size: 15px; text-align: center; ') \
            .props('rounded outlined dense') as input_user_name:
            ui.button(color='orange-8', on_click=lambda: input_user_name.set_value(None), icon='logout') \
                .props('flat dense').bind_visibility_from(input_user_name, 'value')
            
        ui.input(placeholder='PO...').style('width: 150px; margin-right: 10px; flex: none;font-size: 15px') \
            .props('rounded outlined dense')
        
        ui.select(EO_TYPES, value=EO_TYPES[0], on_change=type_change) \
            .style('width: 300px; flex: auto; font-size: 15px') \
            .props('rounded outlined dense')

# Footer
with ui.footer().style('background-color: #333; color: white; padding: 4px 0px; height: 25px'):
    with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%;'):
        ui.label(STATION_DATA["mac"])
        ui.label(STATION_DATA["ip"])
        ui.label('-')
        ui.label('-')
        ui.label(STATION_DATA["host_name"])

# Fő tartalom a fejléc és lábléc nélkül
with ui.row().style('width: 100%; height: calc(100vh - 122px);'): 
    # Fő tartalom
    with ui.column().style('flex-grow: 1; background-color: #333; color: white; height: 100%;'):
        with ui.column().style('width: 100%'):
            with ui.column().style('flex-grow: 1; height: calc(100vh - 182px)'):
                ser_nr_input = ui.input(placeholder='Nutzen sorszám...') \
                    .style('width: 400px; margin: 10px; flex: none;font-size: 15px') \
                    .props('outlined dense')
                print_button = ui.button('Nyomtatás', icon='print').style('margin-left: 10px; flex: none').props('push')
            with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%'):
                error_label = ui.label('Hibaüzenet helye').style('border: 1px solid yellow; border-radius: 6px; padding: 8px; background-color: #333;')
                error_label.visible = False

    # Jobb oldali sáv
    with ui.column().style('width: 180px; height: 100%; flex-shrink: 0; background-color: #333; color: white; ' \
        'flex-direction: column; justify-content: flex-end; gap: 0px;'):
        # Ide jöhet az oldalsáv tartalma
        with ui.column().style('width: 97%; margin-right: 5px; gap: 0px'):
            clock_label = ui.label('12:14:25').classes('text-right w-full').style('font-size: 25px')
            uptime_label = ui.label('Uptime: 0d 0h 00m').classes('text-right w-full').style('font-size: 12px')

# Az aktuális idő kiírása
def update_clock():
    current_time = time.strftime('%H:%M:%S')
    clock_label.text = current_time

# Háttérszál: olvassa a soros portot, és beírja a queue-ba
def serial_reader():
    try:
        with serial.Serial(SERIALPORT_DATA["port"], SERIALPORT_DATA["baudrate"], timeout=0.1) as ser:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    SERIALPORT_DATA["data_queue"].put(line)
    except Exception as e:
        SERIALPORT_DATA["data_queue"].put(f'Hiba a soros porton: {e}')

# Beolvasott vonalkód feldolgozása
def proc_serial_data(serial_data: str):
    code_Id = serial_data[2:3]
    bc = serial_data[4:-1]
    if (len(bc) == 10) & (code_Id == 'C'):
        proc_user_barcode(bc)
    else:
        proc_prod_barcode(bc)

def proc_user_barcode(user_bc: str):
    sql_datas = ds.get_user_datas(user_bc)
    if sql_datas:
        USER_DATA["prime_nr"] = user_bc
        USER_DATA['id']       = sql_datas['userId']
        USER_DATA['name']     = sql_datas['userName']
        USER_DATA['language'] = sql_datas['language']
        USER_DATA['role_id']  = sql_datas['roleId']

        input_user_name.value = USER_DATA['name']
        fn.log_to_file(f"User logged in: {USER_DATA['name']} ({USER_DATA['id']})", LOG_DIR)

def proc_prod_barcode(prod_bc: str):
    ser_nr_input.value = prod_bc
    if prod_bc[1:4] != TYPE_DATA['log_nr']:
        error_label.text = 'E101 - Log szám eltérés!'
        error_label.visible = True

# GUI frissítő: lekérdezi a queue-t és kinyeri a vonalkód tartalmat
def update_gui():
    if not SERIALPORT_DATA["data_queue"].empty():
        proc_serial_data(SERIALPORT_DATA["data_queue"].get())
    ui.timer(0.05, update_gui, once=True)

# GUI szerver indítása külön szálon
def start_gui():
    ui.timer(0.05, update_gui, once=True)
    ui.timer(1, update_clock)
    fn.log_to_file('Application started', LOG_DIR)
    ui.run(host='127.0.0.1', port=8080, reload=False, show=False, dark=True)

# Indítás
if __name__ == '__main__':
    threading.Thread(target=start_gui, daemon=True).start()
    threading.Thread(target=serial_reader, daemon=True).start()
    time.sleep(0.5)
    webview.create_window('Labeling 2.0.0', 'http://127.0.0.1:8080', width=1200, height=710)
    webview.start()
