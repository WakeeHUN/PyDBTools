import os
import time
import fnmatch
import logging
import db_functions as db

# --- A feldolgozó függvény ---
def process_recent_files(archive_path, time_threshold, filename_pattern, station_id):
    """
    Végigmegy a megadott útvonalon található fájlokon,
    feldolgozza azokat, amelyek illeszkednek a mintára és
    nem régebbiek a megadott idő küszöbnél (létrehozás ideje alapján).
    """
    logging.info(f"Fájlok keresése itt: {archive_path}")
    current_time = time.time() # Aktuális idő lekérdezése timestamp formátumban
    processed_files_count = 0

    try:
        # Listázzuk a könyvtár tartalmát
        with os.scandir(archive_path) as entries:
            for entry in entries:
                
                # Ellenőrizzük, hogy fájl-e
                if not entry.is_file():
                    continue

                # Ellenőrizzük, hogy illeszkedik-e a fájlnév a mintára
                if not fnmatch.fnmatch(entry.name, filename_pattern): # entry.name a fájl neve
                    continue

                # Ellenőrizzük a fájl létrehozásának idejét
                try:
                    # entry.stat() adja vissza a stat objektumot cached infóval
                    # st_ctime a létrehozás ideje Windows-on
                    creation_time = entry.stat().st_birthtime
                    file_age = current_time - creation_time # Fájl kora másodpercben

                    # Ellenőrizzük, hogy a fájl elég friss-e
                    if file_age > time_threshold: continue

                    # --- Fájl tartalmának soronkénti kiolvasása ---
                    full_path = os.path.join(archive_path, entry.name)
                    order_number = None
                    serial_numbers = []

                    try:
                        # Fájl megnyitása olvasásra. Fontos az encoding beállítása!
                        # Az 'errors="ignore"' vagy 'errors="replace"' segíthet, ha ismeretlen karakterek vannak
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            # Fájl feldolgozása soronként:
                            for line_num, line in enumerate(f, 1): # Kezdjük a sorszámot 2-től
                                cleaned_line = line.strip()
                                if not cleaned_line: continue

                                parts = cleaned_line.split(';')
                                if not parts: continue

                                if line_num == 1:
                                    order_number = parts[0]
                                else:
                                    serial_number = parts[0]
                                    serial_numbers.append(serial_number)

                            processed_files_count += 1

                            # Adatbázis műveletek:
                            order_data = db.get_order_data(order_number)

                            # Megnézem, hogy létezik-e már a sorszám az adatbázisban
                            array_data = db.get_array_data(serial_numbers[0], order_data.product_id)              
                            if not array_data:
                                success, array_id = db.insert_array_of_pcba(serial_numbers[0], order_data.product_id, station_id)
                                if not success: continue

                                for array_pos, ser_nr in enumerate(serial_numbers, 1):
                                    success, rec_nr = db.insert_rec_nr_ser_nr(order_data.product_id, ser_nr, None, None, station_id)
                                    if not success: continue

                                    success, proc_id = db.insert_rec_nr_last_station(rec_nr, STATION_ID, True, -1, order_data.order_nr)
                                    if not success: continue

                                    success, array_items_id = db.insert_array_items(serial_numbers[0], rec_nr, array_pos, array_id)

                    except Exception as file_read_err:
                        print(f"Hiba a fájl olvasása vagy feldolgozása közben ({entry}): {file_read_err}")
                        # Itt döntheted el, hogy hogyan kezeled a hibás fájlokat (pl. áthelyezed egy hibás mappába)

                except Exception as file_info_err:
                    print(f"Hiba a fájl információk lekérdezésekor ({entry}): {file_info_err}")
                    # Ez akkor fordulhat elő, ha nincs jogod, vagy a fájl pillanatnyilag nem elérhető

    except FileNotFoundError:
        print(f"Hiba: Az útvonal nem található: {archive_path}")
    except PermissionError:
        print(f"Hiba: Nincs jogosultság a könyvtár eléréséhez: {archive_path}")
    except Exception as e:
        print(f"Váratlan hiba történt a könyvtár feldolgozása közben: {e}", exc_info=True)

    print(f"Fájlkeresés befejeződött. Feldolgozott friss fájlok száma: {processed_files_count}")
    return processed_files_count # Visszatérünk a feldolgozott fájlok számával


# --- Önálló teszteléshez (NEM service-ként futtatva) ---
# Ha csak ezt a fájlfeldolgozó részt akarod tesztelni anélkül, hogy service lenne:
if __name__ == "__main__":
    # --- Konfiguráció ---
    # A hálózati útvonal, ahol a fájlok vannak
    #ARCHIVE_PATH = r"\\service-smt\applications\PrinterStation_Laser_KHU4\if_Laser_KHU4\vonstation\archive" # Használj raw stringet (r"...")!
    #STATION_ID = 2005

    ARCHIVE_PATH = r"C:\Temp\archive" # Használj raw stringet (r"...")!
    STATION_ID = 8888

    # Az idő küszöb másodpercben (5 másodpercnél nem régebbi)
    TIME_THRESHOLD_SECONDS = 6000

    # A fájlnév minta (S*.dat)
    FILENAME_PATTERN = "S*F.dat"

    process_recent_files(ARCHIVE_PATH, TIME_THRESHOLD_SECONDS, FILENAME_PATTERN, STATION_ID)
