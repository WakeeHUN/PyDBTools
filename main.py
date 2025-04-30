from nicegui import ui, app
import nicepdf
import threading
import webview
import time
import serial
import queue
import os
import functions as fn


STATION_DATA = fn.get_station_data()

LOG_DIR = r'\\srv14-fs01\production\traceability\marking\ManualLabeling\Programs\Labeling\Log'
ZPL_DIR = r"\\srv14-fs01\production\traceability\marking\ManualLabeling\Labels\ZPL"
fn.log_to_file(f"IP: {STATION_DATA["ip"]}; MAC: {STATION_DATA["mac"]}", LOG_DIR)

SERIALPORT_DATA = fn.load_settings('settings.ini', 'SERIALPORT_DATA')
SERIALPORT_DATA["data_queue"] = queue.Queue()

USER_DATA = fn.get_user_data('-')
TYPE_DATA = fn.get_type_data('-')
IND_LABEL_DATA = fn.get_label_data('-', 1)

EO_TYPES = ['--- Válassz típust ---', 
            '10000323 - TCM615 CA', 
            '13603089-01 - TCM515U']

app.add_static_files('/pdf', 'D:/Temp')

def print_sn():
    os.system('copy /b cimke.zpl "\\\\localhost\\ZDesignerGK420t"')

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
        
        ui.select(EO_TYPES, value=EO_TYPES[0], on_change=lambda e: type_change(e)) \
            .style('width: 300px; flex: auto; font-size: 15px') \
            .props('rounded outlined dense')

# Footer
with ui.footer().style('background-color: #333; color: white; padding: 4px 0px; height: 28px'):
    with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%;'):
        ui.label(STATION_DATA["mac"])
        ui.label(STATION_DATA["ip"])
        ui.label(STATION_DATA["id"])
        ui.label(STATION_DATA["name"])
        ui.label(STATION_DATA["host_name"])

# Fő tartalom a fejléc és lábléc nélkül
with ui.row().style('width: 100%; height: calc(100vh - 125px);'): 
    # Fő tartalom
    with ui.column().style('flex-grow: 1; background-color: #333; color: white; height: 100%; width: calc(100vh - 180px);'):
        with ui.column().style('width: 100%;'):
            with ui.column().style('flex-grow: 1; height: calc(100vh - 182px); width: 100%;'):
                with ui.row().style('width:100%; height: calc(100vh - 182px);') as main_area:
                    with ui.column().style('width: 40%') as left_column:
                        ser_nr_input = ui.input(placeholder='Nutzen sorszám...') \
                            .style('width: 85%; margin: 10px; flex: none; font-size: 15px') \
                            .props('outlined dense')
                        print_button = ui.button('Nyomtatás', icon='print').style('margin-left: 10px; flex: none').props('push')
                    with ui.column().style('margin: 10px; width: 55%; height: 100%;') as right_column:
                        with ui.row():
                            ui.button(icon='description', on_click=lambda: display_db_data(TYPE_DATA, data_area, 'description', 'Típus adatok')).props('flat round color=primary')
                            ui.button(icon='view_kanban', on_click=lambda: display_db_data(IND_LABEL_DATA, data_area, 'view_kanban', 'Címke adatok')).props('flat round color=primary')
                            ui.button(icon='edit_note', on_click=lambda: display_label_file(IND_LABEL_DATA, data_area)).props('flat round color=primary')
                            ui.button(icon='edit_note', on_click=lambda: show_pdf(data_area)).props('flat round color=primary')
                        with ui.column().style('width: 100%; height: 100%;') as data_area:
                            ui.label('')
            with ui.row().style('display: flex; justify-content: space-around; align-items: center; width: 100%'):
                error_label = ui.label('Hibaüzenet helye') \
                    .style('border: 1px solid yellow; border-radius: 6px; padding: 8px; background-color: #333;')
                error_label.visible = False

    # Jobb oldali sáv
    with ui.column().style('width: 180px; height: 100%; flex-shrink: 0; background-color: #333; color: white; ' \
        'flex-direction: column; justify-content: flex-end; gap: 0px;'):
        # Ide jöhet az oldalsáv tartalma
        with ui.column().style('width: 96%; margin-right: 10px; gap: 0px'):
            clock_label = ui.label('12:14:25').classes('text-right w-full').style('font-size: 25px;')
            uptime_label = ui.label('Uptime: 0d 0h 00m').classes('text-right w-full').style('font-size: 12px')

# Az aktuális idő kiírása
def update_clock():
    current_time = time.strftime('%H:%M:%S')
    clock_label.text = current_time

# Kiválasztott termék adatainak kilistázása
def display_db_data(data_source: dict, target_area, icon, caption):
    target_area.clear()
    with target_area:
        with ui.row().style('font-size: 20px'):
            ui.icon(icon)
            ui.label(caption)
        for key, value in data_source.items():
            with ui.row().classes('items-center').style('gap: 12px;'):
                ui.label(f'{key}:').style('font-weight: bold; min-width: 100px;')
                ui.label(str(value))

# ZPL szerkesztő megjelenítése
def display_label_file(data_source: dict, target_area):
    target_area.clear()
    fila_name = rf"{ZPL_DIR}\{IND_LABEL_DATA['label_file']}"
    with target_area:
        with ui.row().style('font-size: 20px'):
            ui.icon('edit_note')
            ui.label('Címke szerkesztése')
        # Szövegmező létrehozása
        text_area = ui.textarea(label=fila_name, placeholder='Fájl betöltése folyamatban...')
        text_area.props('rows=15 outlined spellcheck=false')
        text_area.style('width: 100%;')

        # Fájl betöltése
        if len(fila_name) > 5:
            try:
                with open(fila_name, 'r', encoding='utf-8') as f:
                    tartalom = f.read()
                    text_area.set_value(tartalom)
            except FileNotFoundError:
                text_area.set_value('Nincs ilyen fájl!')

        ui.button('Mentés', icon='save', on_click=lambda: save_file(fila_name, text_area)).style('margin-left: 10px; flex: none').props('push')

# Fájl mentése
def save_file(file_path: str, new_text):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_text.value)
    ui.notify('Mentve!')

dialog = ui.dialog().style('widt: 100%').props('backdrop-filter="blur(8px) brightness(40%)"')
def show_pdf(target_area):
    ser_nr_input.visible=False
    print_button.visible=False
    left_column.style('flex: none; width: 0%;')
    right_column.style('flex: none; width: 100%;')

    target_area.clear()
    with target_area:
        ui.html('''
            <iframe src="/pdf/test.pdf" width="100%" height="100%" style="border: none;"></iframe>
            ''').style('width: 100%; height: 100%')
        ui.button('Bezár', on_click=lambda: close_pdf()).classes('w-full')

def close_pdf():
    ser_nr_input.visible=True
    print_button.visible=True
    left_column.style('flex: none; width: 40%;')
    right_column.style('flex: none; width: 55%;')

    display_db_data(TYPE_DATA, data_area, 'description', 'Típus adatok')

# Háttérszál: olvassa a soros portot, és beírja a queue-ba
def serial_reader():
    try:
        with serial.Serial(SERIALPORT_DATA["port"], SERIALPORT_DATA["baudrate"], timeout=0.1) as ser:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    SERIALPORT_DATA["data_queue"].put(line)
    except Exception as e:
        error_label.text = f'Hiba a soros porton: {e}'
        error_label.visible = True

# Beolvasott vonalkód feldolgozása
def proc_serial_data(serial_data: str):
    error_label.visible = False
    code_Id = serial_data[2:3]
    bc = serial_data[4:-1]
    if (len(bc) == 10) & (code_Id == 'C'):
        proc_user_barcode(bc)
    else:
        proc_prod_barcode(bc)

# User vonalkód feldolgozása
def proc_user_barcode(user_bc: str):
    USER_DATA = fn.get_user_data(user_bc)
    if USER_DATA['id'] > 0:
        input_user_name.value = USER_DATA['name']
        fn.log_to_file(f"User logged in: {USER_DATA['name']} ({USER_DATA['id']})", LOG_DIR)

# Termék vonalkód feldolgozása
def proc_prod_barcode(prod_bc: str):
    ser_nr_input.value = prod_bc
    if prod_bc[1:4] != TYPE_DATA['log_nr']:
        error_label.text = 'E101 - Log szám eltérés!'
        error_label.visible = True

# Típusváltás
def type_change(selected_type):
    global TYPE_DATA, IND_LABEL_DATA
    if selected_type.value != '--- Válassz típust ---':
        type_code = selected_type.value.split(' - ')[0]
        TYPE_DATA = fn.get_type_data(type_code)
        if TYPE_DATA['id'] > 0:
            IND_LABEL_DATA = fn.get_label_data(TYPE_DATA['id'], 1)
            fn.log_to_file(f"Type selected: {selected_type.value} ({TYPE_DATA["id"]})", LOG_DIR)
            display_db_data(IND_LABEL_DATA, data_area)

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
