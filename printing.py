import subprocess
import os

def print_zpl_file(zpl_filepath, printer_port_name):
    """
    Egy ZPL fájlt küld ki a megadott Windows nyomtató portra a copy paranccsal.

    :param zpl_filepath: A ZPL fájl teljes elérési útja.
    :param printer_port_name: A nyomtató port neve a Windowsban (pl. 'USB001').
    :return: True, ha sikeres, False, ha hiba történt.
    """
    if not os.path.exists(zpl_filepath):
        print(f"Hiba: A fájl nem található: {zpl_filepath}")
        return False

    # A copy parancs összeállítása
    # /b opció bináris másoláshoz (elengedhetetlen a ZPL-hez)
    # A port nevét és a fájl elérési útját idézőjelbe tesszük a szóközök miatt
    command = f'copy /b "{zpl_filepath}" "{printer_port_name}"'

    print(f"Parancs futtatása: {command}")

    try:
        # A parancs futtatása a shellben
        # check=True: hibát dob, ha a parancs nem 0 kilépési kóddal tér vissza
        subprocess.run(command, shell=True, check=True)
        print("ZPL fájl sikeresen elküldve a nyomtatóra.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Hiba történt a nyomtatás közben: {e}")
        return False
    except FileNotFoundError:
         print(f"Hiba: A 'copy' parancs nem található. Biztosan Windows rendszert használsz?")
         return False
    except Exception as e:
        print(f"Váratlan hiba történt: {e}")
        return False

# Példa használat:
if __name__ == "__main__":
    # Cseréld le ezeket a saját adataidra!
    zpl_fajl_utvonala = "cimke.zpl"
    nyomtato_port_neve = "USB003" # Ezt a Portok fülön találtad meg

    if print_zpl_file(zpl_fajl_utvonala, nyomtato_port_neve):
        print("Nyomtatási feladat elküldve.")
    else:
        print("Nem sikerült elküldeni a nyomtatási feladatot.")