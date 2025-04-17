from nicegui import ui
import threading
import webview
import time
import serial
import queue
import os

import printing


SERIAL_PORT = 'COM6'
BAUDRATE = 9600

data_queue = queue.Queue()
serial_nr = ''

def print_sn():
    os.system('copy /b cimke.zpl "\\\\localhost\\ZDesignerGK420t"')

# Header
with ui.header(elevated=True).style('background-color: #333; color: white; padding: 8px 8px; height: 70px'):
    with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%;'):
        ui.select(['Opció 1', 'Opció 2'], value='Opció 1').style('width: 150px; margin-right: 16px;')
        ui.input(placeholder='Szűrés...').style('width: 150px; margin-right: 16px;')
        ui.button(icon='folder_open').props('flat round').style('margin-right: 16px;')
        ui.input(placeholder='-').style('width: 80px; margin-right: 16px;')
        ui.button(icon='save').props('flat round').style('margin-right: 16px;')
        ui.input(placeholder='-').style('width: 80px;')

# Footer
with ui.footer().style('background-color: #333; color: white; padding: 8px 8px; height: 35px'):
    with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%;'):
        ui.label('C8:5A:CF:BE:B8:1D')
        ui.label('10.180.12.72')
        ui.label('9999 / 35')
        ui.label('Robot V7')
        ui.label('KHLIM01076')

# Fő tartalom a fejléc és lábléc nélkül
with ui.row().style('width: 100%; height: calc(100vh - 138px);'): 
    with ui.column().style('flex-grow: 1; background-color: #333; color: white; height: 100%;'):
        # Ide jöhet a fő oldal tartalma
        status_label = ui.label('📡 Várakozás vonalkódra...').classes('text-h5 q-mt-lg')
        ui.button('Címke nyomtatása', on_click=print_sn).props('color=primary')

    with ui.column().style('width: 200px; height: 100%; flex-shrink: 0; background-color: #333; color: white; ' \
        'flex-direction: column; justify-content: flex-end; gap: 0px;'):
        # Ide jöhet az oldalsáv tartalma
        with ui.column().style('width: 100%; margin-right: 5px; gap: 0px'):
            clock_label = ui.label('12:14:25').classes('text-right w-full').style('font-size: 25px')
            uptime_label = ui.label('Uptime: 0d 5h 48m').classes('text-right w-full').style('font-size: 12px')

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
    ui.run(host='127.0.0.1', port=8080, reload=False, show=False, dark=True)

# Indítás
if __name__ == '__main__':
    threading.Thread(target=start_gui, daemon=True).start()
    threading.Thread(target=serial_reader, daemon=True).start()
    time.sleep(1)
    webview.create_window('Labeling 1.1.0', 'http://127.0.0.1:8080', width=1200, height=800)
    webview.start()
