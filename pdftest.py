from nicegui import ui, app
import functions as fn

app.add_static_files('/pdf', 'D:/Temp')
ui.html('''
<iframe src="/pdf/test.pdf" width="100%" height="800px" style="border: none;"></iframe>
''')


ui.run()