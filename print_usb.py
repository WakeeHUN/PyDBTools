import win32print
import win32api
import os
import sys

def send_zpl_to_usb_printer_windows(printer_name, zpl_file_path):
    """
    Elküld egy ZPL fájlt egy Windows alá telepített (pl. USB-s) Zebra nyomtatóra
    a win32print API használatával RAW módban.

    Args:
    printer_name (str): A Windowsban telepített nyomtató pontos neve.
    zpl_file_path (str): A küldendő ZPL fájl elérési útja.

    Returns:
    bool: True, ha sikeres volt a küldés (az adatok elküldve a spoolernek), False hiba esetén.
    """
    p_handle = None # Inicializáljuk a nyomtató fogantyút None-ra
    job_id = 0 # Inicializáljuk a job ID-t

    try:
        # Ellenőrizzük, hogy a fájl létezik-e
        if not os.path.exists(zpl_file_path):
            print(f"Hiba: A ZPL fájl nem található: {zpl_file_path}", file=sys.stderr)
            return False

        # Olvassuk be a ZPL fájl tartalmát bináris módban
        with open(zpl_file_path, 'rb') as f:
            zpl_data = f.read()

        if not zpl_data:
            print(f"Figyelem: A ZPL fájl üres: {zpl_file_path}", file=sys.stderr)
            return False

        # Megnyitjuk a nyomtatót a Windows nyomtatási alrendszerében
        print(f"Megnyitás a nyomtatóhoz: '{printer_name}'...")
        # PRINTER_ACCESS_USE = Alap hozzáférés nyomtatási munkákhoz
        p_handle = win32print.OpenPrinter(printer_name, {"DesiredAccess": win32print.PRINTER_ACCESS_USE})
        print("Nyomtató fogantyú megnyitva.")

        # Nyomtatási munka indítása RAW adattípussal
        # A StartDocPrinter visszatér egy Job ID-vel, ha sikeres
        # Az 1-es flag azt jelenti, hogy az adatok fájlból jönnek (bár mi memóriából küldjük)
        # A harmadik elem a tuple-ben ("RAW") jelzi, hogy nyers adatot küldünk, nem dokumentumot
        job_id = win32print.StartDocPrinter(p_handle, 1, ("ZPL Raw Job", None, "RAW"))
        print(f"Nyomtatási munka indítva. Job ID: {job_id}")

        if job_id:
            # Oldal indítása (gyakran szükséges RAW adathoz is az API szerint)
            win32print.StartPagePrinter(p_handle)

            # Adatok küldése a nyomtatóra
            print(f"ZPL adat küldése ({len(zpl_data)} bájt)...")
            # A WritePrinter várja a bájtokat
            bytes_written = win32print.WritePrinter(p_handle, zpl_data)
            print(f"Elküldött bájtok száma: {bytes_written}")

            # Ellenőrizzük, hogy minden bájtot elküldtünk-e
            if bytes_written != len(zpl_data):
                 print(f"Figyelem: Nem minden adat került elküldésre! Elküldve: {bytes_written}, Összesen: {len(zpl_data)}", file=sys.stderr)
                 # Dönthetsz, hogy itt hibát jelzel vagy folytatod

            # Oldal befejezése
            win32print.EndPagePrinter(p_handle)

            # Nyomtatási munka befejezése
            win32print.EndDocPrinter(p_handle)
            print("Nyomtatási munka befejezve.")

        return True # Sikeres volt a küldés a spoolernek

    except FileNotFoundError:
        print(f"Hiba: A ZPL fájl nem található: {zpl_file_path}", file=sys.stderr)
        return False
    except win32api.error as e:
        # win32print specifikus hibák (pl. nyomtató nem található, hozzáférési hiba, spooler hiba)
        # A hiba kód és üzenet a kivétel objektumban van
        print(f"Win32 API hiba a nyomtatás közben: {e}", file=sys.stderr)
        print(f"Nem sikerült nyomtatni a(z) '{printer_name}' nyomtatóra.", file=sys.stderr)
        return False
    except Exception as e:
        # Minden egyéb váratlan hiba
        print(f"Váratlan hiba a nyomtatás közben: {e}", file=sys.stderr)
        return False
    finally:
        # Mindig zárjuk be a nyomtató fogantyút, ha megnyitottuk
        if p_handle:
            win32print.ClosePrinter(p_handle)
            print("Nyomtató fogantyú bezárva.")

# --- Példa használat: ---
if __name__ == "__main__":
    send_zpl_to_usb_printer_windows("ZDesigner GK420t (1. másolat)", "cimke.zpl")