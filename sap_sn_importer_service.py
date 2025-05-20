import win32serviceutil
import win32service
import win32event
import servicemanager
import logging
import os
import sys
import sap_sn_importer as importer
import functions as fn
import logging_setup


# --- Alap Service Konfiguráció (ezek felülíródhatnak a külső configból) ---
# Ezeket a külső configból olvassuk be futáskor, de definiálhatunk alapértelmezetteket
DEFAULT_ARCHIVE_PATH = "C:\\DefaultArchive"
DEFAULT_STATION_ID = 8888
DEFAULT_TIME_THRESHOLD_SECONDS = 60
DEFAULT_FILENAME_PATTERN = "S*F.dat"
DEFAULT_INTERVAL_SECONDS = 1

# A külső konfigurációs fájl elérési útja
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sap_sn_importer.json")


# --- A szolgáltatás osztály ---
class SAPImporterService(win32serviceutil.ServiceFramework):
    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True

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

        # Hívjuk a functions.py-ban lévő config betöltő függvényt
        self.instance_config = fn.load_service_instance_config(CONFIG_FILE_PATH, service_name)

        if self.instance_config is None:
             # Ha a konfiguráció betöltése sikertelen, logolunk (servicemanagerrel) és leállunk
             servicemanager.LogErrorMsg(f"HIBA: Nem sikerült betölteni a konfigurációt a service '{service_name}' számára. Leállás.")
             self.SvcStop() # Hívjuk a leállító metódust
             return # Kilépés a SvcDoRun-ból
        
        # *** Logolás Beállítása ***
        # Hívjuk a functions.py-ban lévő logolás beállító függvényt
        # Átadjuk neki a betöltött konfigurációt
        logging_setup.setup_service_logging(self.instance_config)

        # Ellenőrizzük, hogy legalább egy log handler sikeresen beállítódott-e (ha ez kritikus)
        # logging.getLogger().hasHandlers() ellenőrzés vagy a setup_service_logging return értéke alapján
        if not logging.getLogger().hasHandlers():
             servicemanager.LogErrorMsg(f"FATAL: Nincs log handler konfigurálva a '{service_name}' service-hez. Leállás.")
             self.SvcStop()
             return

        # --- Konfiguráció és Logolás Sikeresen Beállítva ---
        # Innentől használhatjuk a standard logging-ot a service üzeneteihez
        logging.info(f"Szolgáltatás '{service_name}' konfigurációja és logolása beállítva.")

        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        # Lekérdezzük a szükséges konfigurációs értékeket az aktuális konfigurációból
        archive_path     = self.instance_config.get("archive_path", DEFAULT_ARCHIVE_PATH)
        time_threshold   = self.instance_config.get("time_threshold_seconds", DEFAULT_TIME_THRESHOLD_SECONDS)
        filename_pattern = self.instance_config.get("filename_pattern", DEFAULT_FILENAME_PATTERN)
        station_id       = self.instance_config.get('station_id', DEFAULT_STATION_ID)
        interval_seconds = self.instance_config.get('interval_seconds', DEFAULT_INTERVAL_SECONDS)

        # A szolgáltatás fő ciklusa
        while self.is_running:
            # 1. Végezd el a feladatot:
            processed_files_count, error_msg = importer.process_recent_files(archive_path, time_threshold, filename_pattern, station_id)
            if error_msg != '':
                logging.error(error_msg)

            # 2. Várj az adott ideig VAGY amíg a leállási jelzést megkapod
            # win32event.WaitForSingleObject blokkol addig, amíg az esemény jelzést nem kap,
            # VAGY le nem telik az időtúllépés (timeout) ezredmásodpercben.
            # A return érték alapján tudjuk, hogy mi történt.
            wait_result = win32event.WaitForSingleObject(self.hWaitStop, interval_seconds * 1000)

            # Ellenőrizzük, hogy a várakozás miért fejeződött be
            if wait_result == win32event.WAIT_OBJECT_0:
                # Ha a return érték WAIT_OBJECT_0, az azt jelenti, hogy a self.hWaitStop esemény
                # kapott jelzést, vagyis a SvcStop metódus hívta meg a SetEvent-et.
                # Ekkor ki kell lépni a fő ciklusból.
                logging.info("Leállási jelzés érkezett, kilépés a fő ciklusból.")
                break # Kilépés a while True ciklusból

            # Ha a várakozás az időtúllépés miatt fejeződött be, a ciklus folytatódik
            logging.debug(f"Várakozás lejárt ({interval_seconds} mp), folytatás.")

        # A fő ciklus befejeződött (mert leállási jelzés érkezett)
        servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' fő ciklusa befejeződött.")


# --- Származtatott osztályok létrehozása ---
# Létrehozza a külön szervizeket
class SAP_SN_Importer_L2(SAPImporterService):
    _svc_name_         = "SAP_SN_Importer_L2"
    _svc_display_name_ = "SAP SN Importer L2"
    _svc_description_  = "Import SAP generated serialnumbers"

class SAP_SN_Importer_L5(SAPImporterService):
    _svc_name_         = "SAP_SN_Importer_L5"
    _svc_display_name_ = "SAP SN Importer L5"
    _svc_description_  = "Import SAP generated serialnumbers"

class SAP_SN_Importer_L6(SAPImporterService):
    _svc_name_         = "SAP_SN_Importer_L6"
    _svc_display_name_ = "SAP SN Importer L6"
    _svc_description_  = "Import SAP generated serialnumbers"


# --- Szkript futtatása parancssorból ---
# Ez a blokk kezeli a parancssori argumentumokat (install, start, stop, remove stb.)
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Használat: sap_sn_importer_service.py [install|start|...] <ServiceName>")
        sys.exit(1)

    service_name = sys.argv[2]  # pl. SAP_SN_Importer_L5
    service_class = globals().get(service_name)

    if not service_class:
        print(f"Nincs ilyen service osztály: {service_name}")
        sys.exit(1)

    sys.argv = [sys.argv[0]] + [sys.argv[1]]  # pl. ["script.py", "install", "MyService"]
    win32serviceutil.HandleCommandLine(service_class)