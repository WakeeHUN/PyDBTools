import socket
import os
import sys

def send_zpl_to_zebra_network_printer(printer_ip, printer_port, zpl_file_path):
    """
    Elküld egy ZPL fájlt egy Zebra hálózati nyomtatóra TCP/IP kapcsolaton keresztül.

    Args:
        printer_ip (str): A nyomtató IP címe vagy hálózati neve.
        printer_port (int): A nyomtató port száma (tipikusan 9100 a raw TCP/IP nyomtatáshoz).
        zpl_file_path (str): A küldendő ZPL fájl elérési útja.

    Returns:
        bool: True, ha sikeres volt a küldés, False hiba esetén.
    """
    sock = None # Inicializáljuk a socket változót None-ra

    try:
        # Ellenőrizzük, hogy a fájl létezik-e
        if not os.path.exists(zpl_file_path):
            print(f"Hiba: A ZPL fájl nem található: {zpl_file_path}", file=sys.stderr)
            return False

        # Olvassuk be a ZPL fájl tartalmát bináris módban.
        # Fontos binárisan olvasni, mivel a ZPL kódok tartalmazhatnak olyan karaktereket,
        # amiket szöveges módban hibásan kezelhet a rendszer.
        with open(zpl_file_path, 'rb') as f:
            zpl_data = f.read()

        if not zpl_data:
            print(f"Figyelem: A ZPL fájl üres: {zpl_file_path}", file=sys.stderr)
            return False

        # Létrehozunk egy TCP/IP socket-et
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Kapcsolódási és küldési időtúllépés beállítása másodpercben (opcionális, de ajánlott)
        sock.settimeout(10) 

        # Kapcsolódunk a nyomtatóhoz
        print(f"Kapcsolódás a nyomtatóhoz: {printer_ip}:{printer_port}...")
        sock.connect((printer_ip, printer_port))
        print("Kapcsolódás sikeres.")

        # Elküldjük a ZPL adatot a sendall() metódussal, ami kezeli a teljes adatküldést
        print(f"ZPL adat küldése ({len(zpl_data)} bájt)...")
        sock.sendall(zpl_data) 
        print("Adatküldés sikeres.")

        # Itt opcionálisan olvashatnál vissza a nyomtatótól, ha az valami állapotot küld vissza,
        # de a raw nyomtatásnál ez ritka.
        # response = sock.recv(1024) 

        return True # Sikeres volt a küldés

    except FileNotFoundError:
         print(f"Hiba: A ZPL fájl nem található: {zpl_file_path}", file=sys.stderr)
         return False
    except socket.timeout:
        print(f"Hiba: Időtúllépés kapcsolódáskor vagy adatküldéskor a nyomtatóhoz {printer_ip}:{printer_port}", file=sys.stderr)
        return False
    except socket.error as e:
        # Általános socket hiba (pl. kapcsolat elutasítva, hálózati probléma)
        print(f"Hiba a socket művelet közben: {e}", file=sys.stderr)
        print(f"Nem sikerült kapcsolódni vagy adatot küldeni a nyomtatóhoz {printer_ip}:{printer_port}.", file=sys.stderr)
        return False
    except Exception as e:
        # Minden egyéb váratlan hiba
        print(f"Váratlan hiba a nyomtatás közben: {e}", file=sys.stderr)
        return False
    finally:
        # Mindig zárjuk be a socket-et, ha létrejött
        if sock:
            sock.close()
            print("Socket bezárva.")

# --- Példa használat: ---
if __name__ == "__main__":
    # Ezeket az értékeket cseréld le a saját nyomtatódtól és ZPL fájlodtól függően
    printer_ip_address = '10.180.8.123' # A Zebra nyomtató IP címe vagy hálózati neve
    printer_port_number = 9100          # A tipikus port raw TCP/IP nyomtatáshoz
    zpl_file = 'cimke.zpl'              # A küldendő ZPL fájl elérési útja

    # --- Hozzon létre egy dummy cimke.zpl fájlt a teszthez, ha nem létezik ---
    # (Ez a rész csak a teszt szkript futtatásához kell, a fő programban nem)
    if not os.path.exists(zpl_file):
        # Egy egyszerű ZPL kód: ^XA = Start Format, ^FO = Field Origin, ^A0 = Font A, ^FD = Field Data, ^FS = Field Separator, ^XZ = End Format
        dummy_zpl_content = b'^XA\n^FO50,50^A0N,30,30^FDHello Zebra!^FS\n^XZ'
        try:
            with open(zpl_file, 'wb') as f:
                f.write(dummy_zpl_content)
            print(f"Létrehozva egy dummy ZPL fájl a teszthez: {zpl_file}")
        except Exception as e:
            print(f"Nem sikerült dummy ZPL fájlt létrehozni: {e}", file=sys.stderr)
    # --- Dummy fájl létrehozás vége ---


    # Hívjuk meg a függvényt a nyomtatáshoz
    success = send_zpl_to_zebra_network_printer(printer_ip_address, printer_port_number, zpl_file)

    if success:
        print("ZPL küldés sikeresen befejeződött (amennyire a küldés sikeressége megállapítható a socket szinten).")
    else:
        print("ZPL küldés sikertelen.")