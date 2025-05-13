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
SERVICE_NAME = "MySimpleTimeService"
# A szolgáltatás felhasználóbarát neve
SERVICE_DISPLAY_NAME = "My Simple Python Time Service"
# A szolgáltatás leírása
SERVICE_DESCRIPTION = "Writes current timestamp to a file every 10 seconds."

# A fájl elérési útja, ahova az időt írjuk
# Cseréld le ezt egy létező útvonalra, ahova a felhasználónak, aki a service-t futtatja, van írási joga!
# Példa: C:\ServiceLogs\timestamp_log.txt (Ehhez lehet, hogy manuálisan létre kell hozni a C:\ServiceLogs mappát)
# Most használjunk egy egyszerűbb utat, ami a szkript mellé kerülhetne, de service esetén fix út jobb:
# WINDOWS_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timestamp_log.txt")
# Vagy egy fix, jól elérhető hely:
WINDOWS_LOG_FILE = r"C:\Temp\simple_service_log.txt" # Használj raw stringet (r"...") vagy dupla backslash-t (C:\\Temp\\...)!

# Az írás gyakorisága másodpercben
INTERVAL_SECONDS = 10

# --- Logolás beállítása ---
# A szolgáltatás logolásához ajánlott fájlba írni, mivel nincs konzol kimenet
LOG_FILE = r"C:\Temp\simple_service_internal.log" # Ide a szolgáltatás saját belső logjait írja
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

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

        # Ellenőrizzük és ha szükséges, hozzuk létre a log fájl könyvtárát
        log_dir = os.path.dirname(WINDOWS_LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
             try:
                 os.makedirs(log_dir)
                 logging.info(f"Létrehozva a log könyvtár: {log_dir}")
             except Exception as e:
                 logging.error(f"Hiba a log könyvtár létrehozásakor ({log_dir}): {e}")
                 # Lehet, hogy itt le is kellene állni, ha nem tudunk írni

        # A szolgáltatás fő ciklusa
        while self.is_running:
            # 1. Végezd el a feladatot: írd be az időt a fájlba
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"Aktuális idő: {current_time}\n"

            try:
                # Fájl megnyitása hozzáfűzés módra ('a') és írás
                # 'with' statement biztosítja, hogy a fájl be is záródjon
                with open(WINDOWS_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(log_message)
                logging.info(f"Idő beírva a fájlba: {current_time}")
            except Exception as e:
                logging.error(f"Hiba a fájlba íráskor ({WINDOWS_LOG_FILE}): {e}")
                # Ha hiba van az íráskor, leállíthatod a service-t, vagy próbálkozhatsz újra

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


# --- A szkript futtatása parancssorból ---
# Ez a rész teszi lehetővé, hogy a szkriptet parancssorból telepítsd, indítsd,
# leállítsd és töröld Windows service-ként.
if __name__ == '__main__':
    # Ha a szkript paraméterek nélkül fut, alapértelmezettként szolgáltatásként próbál indulni
    # Ha paraméterekkel fut (install, start, stop, remove), akkor a win32serviceutil kezeli
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MySimpleTimeService)
        # Ez a hívás nem tér vissza, amíg a service fut
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # win32serviceutil kezeli a parancssori argumentumokat (install, start, stop, remove stb.)
        win32serviceutil.HandleCommandLine(MySimpleTimeService)