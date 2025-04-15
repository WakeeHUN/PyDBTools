from nicegui import ui
import threading
import webview
import time
import webbrowser


# Böngésző megnyitásának blokkolása
webbrowser.open = lambda *args, **kwargs: None

# Ez lesz az első státusz szöveg
status_label = ui.label('📡 Várakozás vonalkódra...').classes('text-h5 q-mt-lg')

# NiceGUI szerver indítása külön szálon
def start_nicegui():
    ui.run(host='127.0.0.1', port=8080, reload=False)

# PyWebview ablakindítás
if __name__ == '__main__':
    threading.Thread(target=start_nicegui, daemon=True).start()
    time.sleep(1)  # kis késleltetés, hogy elinduljon a szerver
    webview.create_window('Vonalkód olvasó app', 'http://127.0.0.1:8080', width=800, height=600)
    webview.start()