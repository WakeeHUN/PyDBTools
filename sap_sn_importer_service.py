import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import logging
import os
import sys

# --- Konfiguráció ---
# A szolgáltatás neve - ezzel fog megjelenni a Windows Szolgáltatások listájában
SERVICE_NAME = "SnImporter"
# A szolgáltatás felhasználóbarát neve
SERVICE_DISPLAY_NAME = "SAP serialnumber importer"
# A szolgáltatás leírása
SERVICE_DESCRIPTION = "Write SAP serialnumbers to the database."

# --- Logolás beállítása ---
# A szolgáltatás logolásához ajánlott fájlba írni, mivel nincs konzol kimenet
LOG_FILE = r"C:\Temp\sn_importer_internal.log" # Ide a szolgáltatás saját belső logjait írja
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

# Az írás gyakorisága másodpercben
INTERVAL_SECONDS = 1

# --- A szolgáltatás osztály ---
class MySimpleTimeService(win32serviceutil.ServiceFramework):
    # A service metadata beállítása
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args):
        # Alap osztály konstruktor hívása
        win32serviceutil.ServiceFramework.__init__(self, args)
        # Esemény objektum létrehozása a leállási jelzéshez
        # Amikor a Windows leállítja a service-t, ez az esemény "jelzést kap"
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True # Saját flag a fő ciklus vezérléséhez

    def SvcStop(self):
        """
        Ezt a metódust hívja a Windows, amikor leállítja a szolgáltatást.
        """
        servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' leállítása...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING) # Jelzés a Windows-nak: leállás folyamatban
        # Jelzés a SvcDoRun metódusnak a leállásról
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False # Beállítjuk a saját flag-et is

    def SvcDoRun(self):
        """
        Ezt a metódust hívja a Windows, amikor elindítja a szolgáltatást.
        Itt fut a szolgáltatás fő logikája.
        """
        servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' indult. Fő ciklus fut...")
        self.ReportServiceStatus(win32service.SERVICE_RUNNING) # Jelzés a Windows-nak: fut

        # A szolgáltatás fő ciklusa
        while self.is_running:
            # 1. Végezd el a feladatot: írd be az időt a fájlba
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"Aktuális idő: {current_time}\n"


            

            # 2. Várj az adott ideig VAGY amíg a leállási jelzést megkapod
            # win32event.WaitForSingleObject blokkol addig, amíg az esemény jelzést nem kap,
            # VAGY le nem telik az időtúllépés (timeout) ezredmásodpercben.
            # A return érték alapján tudjuk, hogy mi történt.
            wait_result = win32event.WaitForSingleObject(self.hWaitStop, INTERVAL_SECONDS * 1000)

            # Ellenőrizzük, hogy a várakozás miért fejeződött be
            if wait_result == win32event.WAIT_OBJECT_0:
                # Ha a return érték WAIT_OBJECT_0, az azt jelenti, hogy a self.hWaitStop esemény
                # kapott jelzést, vagyis a SvcStop metódus hívta meg a SetEvent-et.
                # Ekkor ki kell lépni a fő ciklusból.
                logging.info("Leállási jelzés érkezett, kilépés a fő ciklusból.")
                break # Kilépés a while True ciklusból

            # Ha a várakozás az időtúllépés miatt fejeződött be, a ciklus folytatódik
            logging.debug(f"Várakozás lejárt ({INTERVAL_SECONDS} mp), folytatás.")

        # A fő ciklus befejeződött (mert leállási jelzés érkezett)
        servicemanager.LogInfoMsg(f"Szolgáltatás '{self._svc_display_name_}' fő ciklusa befejeződött.")