import os
import time
import fnmatch
import logging
import db_functions as db

# --- Konfiguráció ---
# A hálózati útvonal, ahol a fájlok vannak
ARCHIVE_PATH = r"\\service-smt\applications\PrinterStation_Laser_KHU5\if_Laser_KHU5\vonstation\archive" # Használj raw stringet (r"...")!

# Az idő küszöb másodpercben (5 másodpercnél nem régebbi)
TIME_THRESHOLD_SECONDS = 60

# A fájlnév minta (S*.dat)
FILENAME_PATTERN = "S*F.dat"

# --- Logolás beállítása ---
# A szolgáltatás logolásához ajánlott fájlba írni, mivel nincs konzol kimenet
LOG_FILE = r"C:\Temp\sap_sn_importer_internal.log" # Ide a szolgáltatás saját belső logjait írja
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

# --- A feldolgozó függvény ---
def process_recent_files(archive_path, time_threshold, filename_pattern):
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
                
                # Ellenőrizzük, hogy fájl-e (hatékonyabban)
                if not entry.is_file():
                    logging.debug(f"Kihagyva (nem fájl): {entry.name}") # entry.name helyett entry_name-t használtam korábban
                    continue

                # Ellenőrizzük, hogy illeszkedik-e a fájlnév a mintára
                if not fnmatch.fnmatch(entry.name, filename_pattern): # entry.name a fájl neve
                    logging.debug(f"Kihagyva (nem illeszkedik a mintára '{filename_pattern}'): {entry.name}")
                    continue

                # Ellenőrizzük a fájl létrehozásának idejét
                try:
                    # entry.stat() adja vissza a stat objektumot cached infóval
                    # st_ctime a létrehozás ideje Windows-on
                    creation_time = entry.stat().st_birthtime
                    file_age = current_time - creation_time # Fájl kora másodpercben

                    # Ellenőrizzük, hogy a fájl elég friss-e
                    if file_age <= time_threshold:
                        logging.info(f"Talált friss fájl feldolgozásra: {entry} (kora: {file_age:.2f} mp)")

                        # --- Fájl tartalmának soronkénti kiolvasása ---
                        full_path = os.path.join(archive_path, entry.name)
                        order_number = None
                        serial_numbers = []

                        try:
                            # Fájl megnyitása olvasásra. Fontos az encoding beállítása!
                            # Az 'errors="ignore"' vagy 'errors="replace"' segíthet, ha ismeretlen karakterek vannak
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                logging.info(f"Fájl megnyitva olvasásra: {entry}")

                                # Fájl feldolgozása soronként:
                                for line_num, line in enumerate(f, 1): # Kezdjük a sorszámot 2-től
                                    cleaned_line = line.strip()
                                    if cleaned_line:
                                        parts = cleaned_line.split(';')
                                        if parts:
                                            if line_num == 1:
                                                order_number = parts[0]
                                            else:
                                                serial_number = parts[0]
                                                serial_numbers.append(serial_number)

                                logging.info(f"Fájl olvasása befejeződött: {entry}")
                                processed_files_count += 1

                                # Adatbázis műveletek:
                                order_data = db.get_order_data(order_number)

                                # Megnézem, hogy létezik-e már a sorszám az adatbázisban
                                array_data = db.get_array_data(serial_numbers[0], order_data.product_id)                            
                                if not array_data:
                                    type_data = db.get_type_data(order_data.product_id, 1)
                                    product_data = db.get_product_data(serial_numbers[0], order_data.product_id)
                                else:
                                    print(array_data)

                        except Exception as file_read_err:
                            logging.error(f"Hiba a fájl olvasása vagy feldolgozása közben ({entry}): {file_read_err}", exc_info=True)
                            # Itt döntheted el, hogy hogyan kezeled a hibás fájlokat (pl. áthelyezed egy hibás mappába)

                    else:
                        logging.debug(f"Kihagyva (túl régi): {entry} (kora: {file_age:.2f} mp)")

                except Exception as file_info_err:
                    logging.error(f"Hiba a fájl információk lekérdezésekor ({entry}): {file_info_err}", exc_info=True)
                    # Ez akkor fordulhat elő, ha nincs jogod, vagy a fájl pillanatnyilag nem elérhető

    except FileNotFoundError:
        logging.error(f"Hiba: Az útvonal nem található: {archive_path}")
    except PermissionError:
         logging.error(f"Hiba: Nincs jogosultság a könyvtár eléréséhez: {archive_path}")
    except Exception as e:
        logging.error(f"Váratlan hiba történt a könyvtár feldolgozása közben: {e}", exc_info=True)

    logging.info(f"Fájlkeresés befejeződött. Feldolgozott friss fájlok száma: {processed_files_count}")
    return processed_files_count # Visszatérünk a feldolgozott fájlok számával

# --- Hogyan használd a service SvcDoRun metódusában ---

# A korábbi simple_timeservice.py szkript SvcDoRun metódusában,
# a fő 'while self.is_running:' cikluson belül, a várakozás (WaitForSingleObject) előtt
# vagy után hívhatod meg ezt a függvényt.

# Példa a SvcDoRun ciklusában:
# class MySimpleTimeService(...):
#     # ... __init__, SvcStop metódusok ...

#     def SvcDoRun(self):
#         servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' indult. Fő ciklus fut...")
#         self.ReportServiceStatus(win32service.SERVICE_RUNNING)

#         # Ellenőrizzük és ha szükséges, hozzuk létre a log fájl könyvtárát (ez már benne van)
#         # ...

#         while self.is_running:
#             # Itt hívjuk meg a fájlfeldolgozó függvényt
#             try:
#                 logging.info("Fájlfeldolgozási ciklus indítása...")
#                 processed_count = process_recent_files(ARCHIVE_PATH, TIME_THRESHOLD_SECONDS, FILENAME_PATTERN)
#                 logging.info(f"Fájlfeldolgozási ciklus befejezve. Feldolgozott fájlok: {processed_count}")

#                 # Ide kerülhetne a feldolgozott sorozatszámok adatbázisba írása is

#             except Exception as task_err:
#                  logging.error(f"Hiba történt a fájlfeldolgozási feladat közben: {task_err}", exc_info=True)

#             # Várakozás a következő futtatásig vagy leállítási jelre
#             # Ez a WaitForSingleObject a ciklus végén van, ahogy korábban is volt
#             wait_result = win32event.WaitForSingleObject(self.hWaitStop, INTERVAL_SECONDS * 1000)

#             if wait_result == win32event.WAIT_OBJECT_0:
#                 logging.info("Leállási jelzés érkezett, kilépés a fő ciklusból.")
#                 break

#         servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' fő ciklusa befejeződött.")


# --- Önálló teszteléshez (NEM service-ként futtatva) ---
# Ha csak ezt a fájlfeldolgozó részt akarod tesztelni anélkül, hogy service lenne:
if __name__ == "__main__":
    # Állítsd be a logolást, ha külön futtatod
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
    logging.info("Fájlfeldolgozó szkript indítása teszt módban...")

    # Hozd létre a teszthez szükséges könyvtárat, ha nem hálózati utat használsz
    # test_dir = "./test_archive"
    # if not os.path.exists(test_dir):
    #     os.makedirs(test_dir)
    #     print(f"Létrehozva a teszt könyvtár: {test_dir}")
    # # Ideiglenesen állítsd be a teszt könyvtárat
    # ARCHIVE_PATH = test_dir

    # Hívd meg a feldolgozó függvényt
    process_recent_files(ARCHIVE_PATH, TIME_THRESHOLD_SECONDS, FILENAME_PATTERN)

    logging.info("Fájlfeldolgozó szkript befejezve.")