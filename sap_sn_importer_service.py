import win32serviceutil
import win32service
import win32event
import servicemanager
import logging
import logging.handlers
import os
import sys
import json
from typing import Any, Dict
import sap_sn_importer as importer


# --- Alap Service Konfiguráció (ezek felülíródhatnak a külső configból) ---
# Ez a _svc_name_ lesz az alapértelmezett név, ha telepítéskor nem adsz meg más nevet
DEFAULT_SERVICE_NAME = "Default_SAP_SN_Importer"
# Ezeket a külső configból olvassuk be futáskor, de definiálhatunk alapértelmezetteket
DEFAULT_ARCHIVE_PATH = "C:\\DefaultArchive"
DEFAULT_STATION_ID = 8888
DEFAULT_LOG_DIR = "C:\\Logs\\Default"
DEFAULT_LOG_FILENAME_BASE = "service.log"
DEFAULT_LOG_BACKUP_COUNT = 7
DEFAULT_TIME_THRESHOLD_SECONDS = 60
DEFAULT_FILENAME_PATTERN = "S*F.dat"
DEFAULT_INTERVAL_SECONDS = 1

# A külső konfigurációs fájl elérési útja
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sap_sn_import.json")

# A betöltött teljes konfiguráció
ALL_CONFIGS: Dict[str, Any] = {}
# Az aktuális service példány konfigurációja
CURRENT_CONFIG: Dict[str, Any] = {}

# --- Konfiguráció betöltése (service indulásakor fut le) ---
def load_service_config(service_name: str) -> bool:
    """
    Betölti az összes konfigurációt a fájlból, és kiválasztja az aktuális service-hez tartozót.
    """
    global ALL_CONFIGS, CURRENT_CONFIG # Globális változók módosítása

    if not os.path.exists(CONFIG_FILE_PATH):
        servicemanager.LogErrorMsg(f"HIBA: Konfigurációs fájl nem található: {CONFIG_FILE_PATH}")
        return False # Jelzi, hogy a konfiguráció betöltése sikertelen volt

    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            ALL_CONFIGS = json.load(f)
            servicemanager.LogInfoMsg(f"Konfigurációs fájl sikeresen betöltve: {CONFIG_FILE_PATH}")
            # servicemanager.LogInfoMsg(f"Összes konfiguráció: {ALL_CONFIGS}") # Túl sok infó lehet

    except Exception as e:
        servicemanager.LogErrorMsg(f"HIBA: Nem sikerült betölteni a konfigurációt a fájlból ({CONFIG_FILE_PATH}): {e}")
        return False # Hiba a fájl olvasásakor/értelmezésekor

    if service_name not in ALL_CONFIGS:
        servicemanager.LogErrorMsg(f"HIBA: Nincs konfiguráció '{service_name}' nevű service-hez a fájlban.")
        return False # Nincs konfiguráció az adott nevű service-hez

    # Kiválasztjuk az aktuális service konfigurációját
    CURRENT_CONFIG = ALL_CONFIGS.get(service_name, {}) # Vagy adjunk vissza üres dict-et hibára
    servicemanager.LogInfoMsg(f"Aktuális service '{service_name}' konfigurációja betöltve.")
    servicemanager.LogInfoMsg(f"Aktuális konfiguráció: {CURRENT_CONFIG}") # Túl sok infó lehet

    return True # Konfiguráció betöltése sikeres volt

# --- Logolás beállítása (most már a betöltött konfiguráció alapján) ---
# Ezt a függvényt a service SvcDoRun metódusában hívjuk meg, MIUTÁN betöltöttük a configot
def setup_service_logging(config: Dict[str, Any]):
    """
    Beállítja a logolást TimedRotatingFileHandler-rel a megadott konfiguráció alapján.
    """
    log_dir = config.get("log_dir", DEFAULT_LOG_DIR) # Mappa a configból, vagy alapértelmezett
    log_filename_base = config.get("log_filename_base", DEFAULT_LOG_FILENAME_BASE) # Fájlnév configból
    log_file_path = os.path.join(log_dir, log_filename_base) # Teljes elérési út

    log_level_str = config.get("log_level", "INFO").upper() # Log szint string a configból
    # String log szint konvertálása logging konstanssá
    log_level = getattr(logging, log_level_str, logging.INFO)

    log_format = config.get("log_format", '%(asctime)s %(levelname)s:%(message)s') # Formátum configból
    backup_count = config.get("log_backup_count", DEFAULT_LOG_BACKUP_COUNT) # Backup count configból

    # Hozd létre a log könyvtárat, ha nem létezik
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            # Itt már a servicemanager.LogInfoMsg is jó, mert a service kontextusban vagyunk
            servicemanager.LogInfoMsg(f"Log könyvtár létrehozva: {log_dir}")
        except Exception as e:
            servicemanager.LogErrorMsg(f"HIBA: Nem sikerült létrehozni a log könyvtárat ({log_dir}): {e}")
            # Itt hibát jelezhetünk vissza, hogy a logolás nem fog működni

    # Logger objektum lekérése (root logger)
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Távolíts el minden korábbi handlert
    if logger.hasHandlers():
        # servicemanager.LogInfoMsg("Eltávolításra kerülnek a korábbi log handlerek.")
        logger.handlers.clear()

    # Hozd létre és konfiguráld a TimedRotatingFileHandler-t
    try:
        handler = logging.handlers.TimedRotatingFileHandler(
            log_file_path,
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        servicemanager.LogInfoMsg(f"Logolás beállítva: {log_file_path} (Szint: {log_level_str})")

    except Exception as e:
        servicemanager.LogErrorMsg(f"HIBA: Nem sikerült beállítani a TimedRotatingFileHandler-t ({log_file_path}): {e}")
        # Ha itt hiba van, a service nem fog tudni fájlba logolni a custom handlerrel!
        # Fontos ezt észrevenni az eseménynaplóban.


# --- A szolgáltatás osztály ---
class SAPImporterService(win32serviceutil.ServiceFramework):
    # Az alapértelmezett service név
    _svc_name_ = DEFAULT_SERVICE_NAME
    _svc_display_name_ = f"Python Importer ({DEFAULT_SERVICE_NAME})"
    _svc_description_ = "Processes files from a configured directory."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True
        # Az args tartalmazhat argumentumokat, de a configot inkább fájlból olvassuk

    def SvcStop(self):
        """
        Ezt a metódust hívja a Windows, amikor leállítja a szolgáltatást.
        """
        servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' leállítása...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """
        Ezt a metódust hívja a Windows, amikor elindítja a szolgáltatást.
        Itt fut a szolgáltatás fő logikája.
        """
        service_name = self._svc_name_ # Lekérdezzük a service aktuális nevét
        servicemanager.LogInfoMsg(f"Szolgáltatás '{service_name}' indult. Konfiguráció betöltése...")

        if not load_service_config(service_name):
             # Ha a konfiguráció betöltése sikertelen, logolunk (servicemanagerrel) és leállunk
             servicemanager.LogErrorMsg(f"HIBA: Nem sikerült betölteni a konfigurációt a service '{service_name}' számára. Leállás.")
             self.SvcStop() # Hívjuk a leállító metódust
             return # Kilépés a SvcDoRun-ból

        # *** Konfiguráció sikeresen betöltve, most beállítjuk a logolást a példány specifikus mappába ***
        setup_service_logging(CURRENT_CONFIG)
        # servicemanager már az új log fájlba logol innen

        logging.info(f"Szolgáltatás '{service_name}' fő ciklusa fut. Feldolgozási útvonal: {CURRENT_CONFIG.get('archive_path', 'N/A')}")
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        # Lekérdezzük a szükséges konfigurációs értékeket az aktuális konfigurációból
        archive_path = CURRENT_CONFIG.get("archive_path", DEFAULT_ARCHIVE_PATH)
        time_threshold = CURRENT_CONFIG.get("time_threshold_seconds", DEFAULT_TIME_THRESHOLD_SECONDS)
        station_id = CURRENT_CONFIG.get('station_id', DEFAULT_STATION_ID)

        # A szolgáltatás fő ciklusa
        while self.is_running:
            # 1. Végezd el a feladatot:
            importer.process_recent_files(archive_path, time_threshold, DEFAULT_FILENAME_PATTERN, station_id)

            # 2. Várj az adott ideig VAGY amíg a leállási jelzést megkapod
            # win32event.WaitForSingleObject blokkol addig, amíg az esemény jelzést nem kap,
            # VAGY le nem telik az időtúllépés (timeout) ezredmásodpercben.
            # A return érték alapján tudjuk, hogy mi történt.
            wait_result = win32event.WaitForSingleObject(self.hWaitStop, DEFAULT_INTERVAL_SECONDS * 1000)

            # Ellenőrizzük, hogy a várakozás miért fejeződött be
            if wait_result == win32event.WAIT_OBJECT_0:
                # Ha a return érték WAIT_OBJECT_0, az azt jelenti, hogy a self.hWaitStop esemény
                # kapott jelzést, vagyis a SvcStop metódus hívta meg a SetEvent-et.
                # Ekkor ki kell lépni a fő ciklusból.
                logging.info("Leállási jelzés érkezett, kilépés a fő ciklusból.")
                break # Kilépés a while True ciklusból

            # Ha a várakozás az időtúllépés miatt fejeződött be, a ciklus folytatódik
            logging.debug(f"Várakozás lejárt ({DEFAULT_INTERVAL_SECONDS} mp), folytatás.")

        # A fő ciklus befejeződött (mert leállási jelzés érkezett)
        servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' fő ciklusa befejeződött.")


# --- Szkript futtatása parancssorból ---
# Ez a blokk kezeli a parancssori argumentumokat (install, start, stop, remove stb.)
if __name__ == '__main__':
    # Ha a szkript paraméterek nélkül indul, az SCM indítja service-ként.
    # Ha paraméterekkel indul (pl. install FileProcessorService_PathA),
    # a win32serviceutil kezeli.
    # A win32serviceutil.HandleCommandLine() hívás második argumentuma
    # az a service osztály, amit kezelni kell. Az első argumentum a szkript neve.
    # A Hivatalos service neve (amit a Windows lát) a parancssorban megadott név lesz,
    # vagy a _svc_name_ ha nincs név a parancssorban.

    # Példa használat parancssorból (rendszergazdaként):
    # python file_processor_service.py install FileProcessorService_PathA
    # python file_processor_service.py start FileProcessorService_PathA
    # python file_processor_service.py stop FileProcessorService_PathA
    # python file_processor_service.py remove FileProcessorService_PathA

    # python file_processor_service.py install FileProcessorService_PathB
    # python file_processor_service.py start FileProcessorService_PathB
    # ... stb.

    # Telepítés a DEFAULT_SERVICE_NAME névvel:
    # python file_processor_service.py install

    # A sys.argv-ban lévő argumentumok közé a service neve is bekerül, ha megadják
    # A win32serviceutil.HandleCommandLine() ezt kezeli a háttérben.
    # Amikor az SCM indítja a service-t, a SvcDoRun fut le.
    # A SvcDoRun metóduson belül a self._svc_name_ attribútum tartalmazza a
    # telepítéskor használt service nevet (pl. FileProcessorService_PathA).

    if len(sys.argv) == 1:
        # Ha nincs parancssori argumentum (azaz az SCM indította),
        # Inicializáljuk a servicemanager-t és felkészítjük a service futtatásra.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SAPImporterService)
        servicemanager.StartServiceCtrlDispatcher() # Blokkol, amíg a service fut/leáll
    else:
        # Ha vannak parancssori argumentumok (install, start stb.)
        # A win32serviceutil kezeli a parancsokat a megadott service osztályra.
        # A megadott service név (ha van) automatikusan a self._svc_name_ lesz.
        win32serviceutil.HandleCommandLine(SAPImporterService)