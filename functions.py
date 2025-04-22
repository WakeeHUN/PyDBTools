from datetime import datetime
import os


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
        