from nicegui import ui
import threading
import webview
import time
import serial
import queue


SERIAL_PORT = 'COM6'
BAUDRATE = 9600


data_queue = queue.Queue()
status_label = ui.label('📡 Várakozás vonalkódra...').classes('text-h5 q-mt-lg')

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
    if not data_queue.empty():
        new_data = data_queue.get()
        status_label.set_text(f'📦 Beolvasva: {new_data}')
    ui.timer(0.05, update_gui, once=True)

# GUI szerver indítása külön szálon
def start_gui():
    ui.timer(0.5, update_gui, once=True)
    ui.run(host='127.0.0.1', port=8080, reload=False, show=False)

# Indítás
if __name__ == '__main__':
    threading.Thread(target=start_gui, daemon=True).start()
    threading.Thread(target=serial_reader, daemon=True).start()
    time.sleep(1)
    webview.create_window('Vonalkód olvasó app', 'http://127.0.0.1:8080', width=800, height=600)
    webview.start()
