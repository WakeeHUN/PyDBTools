from nicegui import ui, app
import threading
import webview
import time
import serial
import queue
from dataclasses import is_dataclass, asdict
import functions as fn
import db_functions as db
import element_props as ep
import print_usb
import print_tcp

app.add_static_files('/static', 'static')
app.add_static_files('/pdf', '//srv14-fs01/office/Quality/ISO_TS dokumentacio/Valid_Digital')

# A külső CSS fájl belinkelése
ui.add_head_html(f'<link rel="stylesheet" href="/static/style.css?{int(time.time())}">')
ui.add_head_html('<link rel="icon" type="image/x-icon" href="/static/Barcode.ico">')

COMPANY_NAME = "Katek Hungary Kft."
PROGRAM_VERSION = '1.0.1'
STATION_DATA = fn.get_station_data()

LOG_DIR = r'\\srv14-fs01\production\traceability\marking\ManualLabeling\Programs\Labeling\Log'
ZPL_DIR = r"\\srv14-fs01\production\traceability\marking\ManualLabeling\Labels\ZPL"
fn.log_to_file(f"IP: {STATION_DATA["ip"]}; MAC: {STATION_DATA["mac"]}", LOG_DIR)

SERIALPORT_DATA = fn.load_settings('settings.ini', 'SERIALPORT_DATA')
SERIALPORT_DATA["data_queue"] = queue.Queue()

PRINTER_DATA = fn.load_settings('settings.ini', 'PRINTER_DATA')

USER_DATA = db.get_user_data('-')
TYPE_DATA = db.get_type_data('-')
IND_LABEL_DATA = db.get_label_data(-1, 1)

PRODUCT_WORK_INSTRUCTIONS = db.get_product_workinstructions(2663, 23, 1)
print(PRODUCT_WORK_INSTRUCTIONS)
GLOBAL_WORK_INSTRUCTIONS  = db.get_global_workinstructions(23, 1)
print(GLOBAL_WORK_INSTRUCTIONS)

EO_TYPES = ['10000323 - TCM615 CA', 
            '13603089-01 - TCM515U']
            

def print_sn():
    if PRINTER_DATA["port"] == "USB":
        print_usb.send_zpl_to_usb_printer_windows(PRINTER_DATA['name'], "cimke.zpl")
    elif PRINTER_DATA["port"] == "TCP":
        print_tcp.send_zpl_to_zebra_network_printer(PRINTER_DATA["ip"], 9100, "cimke.zpl")
    else:
        print("Printer config error")

# Header
with ui.header().classes('app-header'): 
    ui.select(['ENOCEAN_LABELING',], value='ENOCEAN_LABELING') \
        .classes('header-element header-select-program') \
        .props(ep.HEADER_INPUT_PROPS)
    
    with ui.input(placeholder='Felhasználó...') \
        .classes('header-element header-input-user') \
        .props(ep.HEADER_INPUT_PROPS) as input_user_name:
        ui.button(color='orange-8', on_click=lambda: input_user_name.set_value(None), icon='logout') \
            .props('flat dense').bind_visibility_from(input_user_name, 'value')
        
    ui.input(placeholder='PO...') \
        .classes('header-element header-input-po') \
        .props(ep.HEADER_INPUT_PROPS)
    
    type_select = ui.select(EO_TYPES, value=None, on_change=lambda e: type_change(e)) \
        .classes('header-element header-select-type') \
        .props(ep.HEADER_TYPESELECT_PROPS)

# Footer
with ui.footer().classes('app-footer'):
    ui.label(STATION_DATA["mac"])
    ui.label(STATION_DATA["ip"])
    ui.label(STATION_DATA["id"])
    ui.label(STATION_DATA["name"])
    ui.label(STATION_DATA["host_name"])

# Fő tartalom a fejléc és lábléc nélkül
with ui.row().style('width: 100%; height: calc(100vh - 130px)'): 
    # Fő tartalom
    with ui.column().classes('main-content-container'):
        with ui.row().classes('main-layout-row') as data_row:  
            # Left column:
            with ui.column().classes('left-column') as left_column:
                ser_nr_input = ui.input(placeholder='Nutzen sorszám...') \
                    .classes('left-column-input') \
                    .props('outlined dense')
                print_button = ui.button('Nyomtatás', icon='print', on_click=lambda: print_sn()) \
                    .classes('print-button') \
                    .props('push')
            # Right column:
            with ui.column().classes('right-column') as right_column:
                with ui.row().classes('tool_buttons') as tool_bar:
                    tool_button_1 = ui.button(icon='description', on_click=lambda: display_db_data(TYPE_DATA, data_area, 'description', 'Típus adatok')) \
                        .props(ep.TOOL_BUTTON_PROPS)
                    tool_button_2 = ui.button(icon='view_kanban', on_click=lambda: display_db_data(IND_LABEL_DATA, data_area, 'view_kanban', 'Címke adatok')) \
                        .props(ep.TOOL_BUTTON_PROPS)
                    tool_button_3 = ui.button(icon='edit_note', on_click=lambda: display_label_file(IND_LABEL_DATA, data_area)) \
                        .props(ep.TOOL_BUTTON_PROPS)
                with ui.column().classes('data-display-area') as data_area:
                    ui.label('')
        # Alsó sor a hibaüzenetnek
        with ui.row().classes('bottom-status-row') as error_row:
            error_label = ui.label('Hibaüzenet helye') \
                .classes('error-message-label')
            error_label.visible = False

    # Jobb oldali sáv
    with ui.column().classes('right-sidebar'):
        with ui.column().classes('sidebar-inner-column'):
            with ui.column().classes('sidebar-instruction-area') as wi_area:
                ui.label('Munkautasítások')
                with ui.row():
                    ui.button('M-P-G-0022', on_click=lambda: dialog.open()) \
                        .classes('instruction-button-wide') \
                        .props(ep.WI_BUTTON_PROPS)
                    ui.button(icon='edit_note', on_click=lambda: show_pdf(data_area)) \
                        .props(ep.WIHISTORY_BUTTON_PROPS)
            clock_label = ui.label('00:00:00') \
                .classes('text-right w-full clock-text')
            uptime_label = ui.label('Uptime: 0d 0h 00m') \
                .classes('text-right w-full uptime-text')

# Az aktuális idő kiírása
def update_clock():
    current_time = time.strftime('%H:%M:%S')
    clock_label.text = current_time

    uptime = fn.get_windows_uptime()
    if uptime:
        uptime_label.text = f"Uptime: {uptime['days']}d {uptime['hours']}h {uptime['minutes']}m"
    else:
        uptime_label.text = "Uptime: -"

# Kiválasztott termék adatainak kilistázása
def display_db_data(data_source, target_area, icon, caption):
    target_area.clear()
    with target_area:
        with ui.row().style('font-size: 20px'):
            ui.icon(icon)
            ui.label(caption)

        data_to_display = {}

        # Ellenőrizzük, hogy a bejövő adat dataclass-e
        if is_dataclass(data_source):
            # Ha dataclass, alakítsuk át dictionary-vé
            data_to_display = asdict(data_source)
        elif isinstance(data_source, dict):
            # Ha már eleve dictionary, használjuk azt
            data_to_display = data_source
        else:
            # Ha sem dictionary, sem dataclass, jelezzünk hibát vagy térjünk vissza
            print(f"Warning: display_db_data unexpected data type: {type(data_source)}")
            return # Megállítjuk a függvény futását

        for key, value in data_to_display.items():
            with ui.row().classes('items-center').style('gap: 12px;'):
                ui.label(f'{key}:').style('font-weight: bold; min-width: 100px;')
                ui.label(str(value))

# ZPL szerkesztő megjelenítése
def display_label_file(label_data, target_area):
    global IND_LABEL_DATA
    target_area.clear()
    fila_name = rf"{ZPL_DIR}\{label_data.label_file}"
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

dialog = ui.dialog()
dialog.props('full-screen')
with dialog:
    with ui.card().classes('w-full h-full'):
        with ui.column().classes('w-full h-full items-center'):
            ui.html('''
                <iframe src="/pdf/test.pdf#toolbar=0" width="100%" height="100%" style="border: none;"></iframe>
                ''').style('width: 100%; height: 100%')
            ui.button('Bezár', on_click=lambda: close_pdf()).classes('w-full')

# Munkauti PDF megjelenítése
def show_pdf(target_area):
    error_label.visible = False
    error_row.style('height: 0px')

    ser_nr_input.visible = False
    print_button.visible = False
    left_column.style('width: 0%;')
    right_column.style('width: 100%;')

    tool_button_1.visible = False
    tool_button_2.visible = False
    tool_button_3.visible = False
    tool_bar.style('margin: 0px; height: 0px')

    data_row.style('height: 100%')

    target_area.clear()
    with target_area:
        ui.html('''
            <iframe src="/pdf/M-L-0011 Kiszállítás_rev01.pdf#toolbar=0" width="100%" height="100%" style="border: none;"></iframe>
            ''').style('width: 100%; height: 100%;')
        ui.button('Bezár', on_click=lambda: close_pdf()).classes('w-full')

# PDF bezárása
def close_pdf():
    error_row.style('height: 50px')

    ser_nr_input.visible = True
    print_button.visible = True
    left_column.style('width: 40%;')
    right_column.style('width: 60%;')

    tool_button_1.visible = True
    tool_button_2.visible = True
    tool_button_3.visible = True
    tool_bar.style('margin: 10px; height: 50px')

    data_row.style('height: calc(100vh - 160px)')

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
    global USER_DATA
    USER_DATA = db.get_user_data(user_bc)
    if USER_DATA.id > 0:
        input_user_name.value = USER_DATA.name
        fn.log_to_file(f"User logged in: {USER_DATA.name} ({USER_DATA.id})", LOG_DIR)

# Termék vonalkód feldolgozása
def proc_prod_barcode(prod_bc: str):
    ser_nr_input.value = prod_bc
    if prod_bc[1:4] != TYPE_DATA.log_nr:
        error_label.text = 'E101 - Log szám eltérés!'
        error_label.visible = True

# Típusváltás
def type_change(selected_type):
    global TYPE_DATA, IND_LABEL_DATA
    type_select.props(remove='label')
    type_code = selected_type.value.split(' - ')[0]
    TYPE_DATA = db.get_type_data(type_code)
    if TYPE_DATA.id > 0:
        IND_LABEL_DATA = db.get_label_data(TYPE_DATA.id, 1)
        fn.log_to_file(f"Type selected: {selected_type.value} ({TYPE_DATA.id})", LOG_DIR)
        display_db_data(IND_LABEL_DATA, data_area, 'view_kanban', 'Címke adatok')

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
    webview.create_window(f"Labeling {PROGRAM_VERSION} - {COMPANY_NAME}", 'http://127.0.0.1:8080', 
                          width=1200, 
                          height=710, 
                          )
    webview.start()
