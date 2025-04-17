from nicegui import ui
import threading
import webview
import time
import serial
import queue
import os
import socket
import uuid


SERIAL_PORT = 'COM6'
BAUDRATE = 9600
HOST_NAME = socket.gethostname()
HOST_IP = socket.gethostbyname(HOST_NAME)
mac_num = hex(uuid.getnode()).replace('0x', '').zfill(12)
HOST_MAC = ':'.join(mac_num[i:i+2] for i in range(0, 12, 2))


data_queue = queue.Queue()
serial_nr = ''
ui.add_head_html('<link href="https://cdn.jsdelivr.net/npm/@mdi/font@6.5.95/css/materialdesignicons.min.css" rel="stylesheet">')

def print_sn():
    os.system('copy /b cimke.zpl "\\\\localhost\\ZDesignerGK420t"')

# Header
with ui.header(elevated=True).style('background-color: #333; color: white; padding: 4px 0px; height: 65px'):
    with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%;'):
        ui.icon('mdi-sitemap').style('font-size: 38px; color: #555;')
        ui.select(['PCB_HAND_LABELING', ''], value='PCB_HAND_LABELING').style('width: 150px; margin-right: 16px; flex: auto; font-size: 18px')
        ui.icon('mdi-account-circle').style('font-size: 38px; color: #555')
        ui.input(placeholder='Felhasználó...').style('width: 150px; margin-right: 16px; flex: auto; font-size: 18px')
        ui.input(placeholder='-').style('width: 150px; margin-right: 16px; flex: none;font-size: 18px')
        ui.input(placeholder='-').style('width: 150px; flex: auto; font-size: 18px')

# Footer
with ui.footer().style('background-color: #333; color: white; padding: 4px 0px; height: 25px'):
    with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%;'):
        ui.label(HOST_MAC)
        ui.label(HOST_IP)
        ui.label('-')
        ui.label('-')
        ui.label(HOST_NAME)

# Fő tartalom a fejléc és lábléc nélkül
with ui.row().style('width: 100%; height: calc(100vh - 122px);'): 
    with ui.column().style('flex-grow: 1; background-color: #333; color: white; height: 100%;'):
        # Ide jöhet a fő oldal tartalma
        status_label = ui.label('📡 Várakozás vonalkódra...').classes('text-h5 q-mt-lg')
        ui.button('Címke nyomtatása', on_click=print_sn).props('color=secondary')

    with ui.column().style('width: 180px; height: 100%; flex-shrink: 0; background-color: #333; color: white; ' \
        'flex-direction: column; justify-content: flex-end; gap: 0px;'):
        # Ide jöhet az oldalsáv tartalma
        with ui.column().style('width: 100%; margin-right: 5px; gap: 0px'):
            clock_label = ui.label('12:14:25').classes('text-right w-full').style('font-size: 25px')
            uptime_label = ui.label('Uptime: 0d 0h 00m').classes('text-right w-full').style('font-size: 12px')

def update_clock():
    current_time = time.strftime('%H:%M:%S')
    clock_label.text = current_time

# Háttérszál: olvassa a soros portot, és beírja a queue-ba
def serial_reader():
    try:
        with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1) as ser:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    data_queue.put(line)
    except Exception as e:
        data_queue.put(f'Hiba a soros porton: {e}')

# GUI frissítő: lekérdezi a queue-t és frissíti a labelt
def update_gui():
    global serial_nr
    if not data_queue.empty():
        new_data = data_queue.get()
        status_label.set_text(f'📦 Beolvasva: {new_data}')
        serial_nr = new_data
        print_sn
    ui.timer(0.05, update_gui, once=True)

# GUI szerver indítása külön szálon
def start_gui():
    ui.timer(0.05, update_gui, once=True)
    ui.timer(1, update_clock)
    ui.run(host='127.0.0.1', port=8080, reload=False, show=False, dark=True)

# Indítás
if __name__ == '__main__':
    threading.Thread(target=start_gui, daemon=True).start()
    threading.Thread(target=serial_reader, daemon=True).start()
    time.sleep(1)
    webview.create_window('Labeling 2.0.0', 'http://127.0.0.1:8080', width=1200, height=710)
    webview.start()
