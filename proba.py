from nicegui import ui

with ui.column().style('height: 100vh; justify-content: flex-end;'):

    # 2️⃣ Tartalomrész, ami fentről indul — de külön konténerben!
    with ui.column().classes('items-start').style('flex-grow: 1; background-color: #f8f8f8; padding: 10px; width: 100%;'):
        ui.label('Ez fentről indul')
        ui.button('Felső gomb 1')
        ui.button('Felső gomb 2')

    # 1️⃣ Alsó "footer" rész
    with ui.row().classes('justify-end').style('background-color: #ddd; padding: 10px;'):
        ui.button('Lenti gomb 1')
        ui.button('Lenti gomb 2')

ui.run(host='127.0.0.1', port=8080, reload=False, show=False, dark=True)