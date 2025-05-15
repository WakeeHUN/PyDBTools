import mysql.connector
import os


DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "10.180.8.23"),
    "user":     os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_DATABASE", "traceability")
}


def _execute_select_query(query, params=None, fetchone=False):
    """
    Végrehajt egy SELECT SQL lekérdezést az adatbázisban és visszaadja az eredményt.
    Használja a 'with' statement-et a kapcsolat és a kurzor automatikus kezelésére.

    Args:
        query (str): Az SQL SELECT lekérdezés. Használj '%s' placeholder-eket a paraméterekhez.
        params (tuple/list, optional): A lekérdezésben használt paraméterek tuple vagy listaként. Defaults to None.
                                       Fontos a biztonságos lekérdezésekhez (SQL injection megelőzés).
        fetchone (bool, optional): Ha True, csak az első eredményt adja vissza (dict formában).
                                   Ha False, az összes eredményt listaként adja vissza (dict-ek listája). Defaults to False.

    Returns:
        list[dict] | dict | None: Az eredmény(ek) dictionary(k) listájaként (ha fetchone=False)
                                  vagy egyetlen dictionary-ként (ha fetchone=True).
                                  None-t ad vissza hiba esetén.
    """
    try:
        # Létrehoz egy adatbázis kapcsolatot a DB_CONFIG szótárban megadott adatokkal.
        # A 'with' statement biztosítja, hogy a kapcsolat automatikusan bezáródjon,
        # akár sikeres volt a művelet, akár hiba történt.
        with mysql.connector.connect(**DB_CONFIG) as mydb:
            # Létrehoz egy kurzor objektumot a lekérdezések végrehajtásához.
            # A 'dictionary=True' beállítás miatt a lekérdezés eredményének sorai
            # dictionary formában lesznek, ahol a kulcsok az oszlopnevek. Kényelmesebb feldolgozni.
            # A 'with' statement itt is biztosítja a kurzor automatikus bezárását.
            with mydb.cursor(dictionary=True) as mycursor:
                mycursor.execute(query, params)
                if fetchone:
                    # Visszaadja az első (vagy következő) sor eredményét dictionary-ként.
                    # Ha nincs több sor, None-t ad vissza.
                    return mycursor.fetchone()
                else:
                    # Visszaadja az összes hátralévő sor eredményét dictionary-k listájaként.
                    # Ha nincs eredmény, üres listát ad vissza.
                    return mycursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Hiba az adatbázis művelet során: {err}")
        # Hiba esetén None-t ad vissza.
        return None


def _execute_modify_query(query, params=None):
    """
    Végrehajt egy INSERT, UPDATE vagy DELETE SQL utasítást az adatbázisban.
    Véglegesíti a változtatásokat (commit), vagy visszavonja (rollback) hiba esetén.

    Args:
        query (str): Az SQL utasítás (INSERT, UPDATE, DELETE).
        params (tuple/list, optional): Az utasításban használt paraméterek tuple vagy listaként. Defaults to None.

    Returns:
        bool: True, ha a művelet sikeres volt, False hiba esetén.
        int: Sikeres INSERT esetén a beszúrt sor ID-ja, ha van auto-increment oszlop (vagy -1, ha nincs/sikertelen).
              Sikeres UPDATE/DELETE esetén az érintett sorok száma (vagy -1, ha nincs/sikertelen).
    """
    conn = None # Azért definiáljuk itt None-ként, hogy a finally blokkban ellenőrizhessük
    cursor = None
    lastrowid = -1 # Az utolsó beszúrt sor ID-ja
    affected_rows = -1 # Az érintett sorok száma UPDATE/DELETE esetén

    try:
        # Adatbázis csatlakozás
        # dictionary=True itt nem kell, mert nem SELECT eredményt várunk
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # SQL utasítás végrehajtása paraméterekkel
        cursor.execute(query, params)

        # Ha INSERT volt, lekérdezhetjük az utolsó beszúrt sor ID-ját (auto-increment oszlop esetén)
        if query.strip().upper().startswith("INSERT"):
             lastrowid = cursor.lastrowid
        else:
             # UPDATE vagy DELETE esetén lekérdezhetjük az érintett sorok számát
             affected_rows = cursor.rowcount

        # Változtatások véglegesítése
        conn.commit()

        # Sikeres volt
        if query.strip().upper().startswith("INSERT"):
            return True, lastrowid
        else:
            return True, affected_rows # UPDATE/DELETE esetén érintett sorok száma

    except mysql.connector.Error as err:
        print(f"Adatbázis hiba az SQL végrehajtása során: {err}")
        # Hiba esetén visszavonjuk a tranzakciót
        if conn and conn.is_connected():
            conn.rollback()
        # Sikertelen volt
        return False, -1
    
    except Exception as e:
        print(f"Váratlan hiba az adatbázis művelet során: {e}")
        if conn and conn.is_connected():
            conn.rollback()
        return False, -1

    finally:
        # Erőforrások lezárása minden esetben
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()  

# SELECT ---
def get_users():
    query = "SELECT userId, userName, primeNr FROM users WHERE userStatus = %s"
    results = _execute_select_query(query, (True,))
    return results
    
def get_user_datas(prime_nr: str):
    query = "SELECT userId, userName, language, roleId FROM users WHERE primeNr = %s"
    result = _execute_select_query(query, (prime_nr,), fetchone=True)
    return result

def get_type_datas(product_id: int, station_group: int):
    query = """
    SELECT product_process_steps.product_code, products.productName, products.logNr, products.customerId,
    products.traySize, products.boxSize, products.palletSize, products.active, products.arraySize,
    products.arrayDimension, products.baseTypeId, products.params
    FROM product_process_steps INNER JOIN products ON product_process_steps.product_id = products.productId
    WHERE (((product_process_steps.station_group_id) = %s)
    AND ((product_process_steps.product_id) = %s))
    """
    result = _execute_select_query(query, (station_group, product_id, ), fetchone=True)
    return result

def get_label_datas(product_id: int, entry_nr: int):
    query = """
    SELECT lastSn, hwswIndex, bomNr, labelCode, foilType, labelFile, snFormat,
    snResetType, copies FROM labels WHERE productId = %s AND entryNr = %s
    """
    result = _execute_select_query(query, (product_id, entry_nr,), fetchone=True)
    return result

def get_order_details(order_nr: str):
    query = """
    SELECT order_details.productId, order_details.orderType, order_details.quantity, order_details.discount,
    order_details.closeDate, order_details.routing, order_details.matnr
    FROM order_details
    WHERE (((order_details.orderNumber) = %s ))
    """
    result = _execute_select_query(query, (order_nr, ), fetchone=True)
    return result

def get_product_datas(ser_nr: str, product_id: int):
    query = """
    SELECT recnrsernr.recNr, recnrsernr.lastStation, recnrsernr.changeDate, recnrsernr.customerSn, recnrsernr.devParam
    FROM recnrsernr
    WHERE (((recnrsernr.serNr) = %s) AND ((recnrsernr.productId) = %s))
    """
    result = _execute_select_query(query, (ser_nr, product_id, ), fetchone=True)
    return result

def get_array_datas(ser_nr: str, product_id: int):
    query = """
    SELECT arrayId, createDate, changeDate, lastStation, unGrouped
    FROM arrayofpcba WHERE arraySerNr = %s AND arrayProductId = %s
    """
    result = _execute_select_query(query, (ser_nr, product_id, ), fetchone=True)
    return result

def get_product_wi_ids(product_id: int, work_group: int):
    query = """
    SELECT work_instruction_product.work_instruction_id, work_instruction_product.station_list
    FROM work_instruction_product INNER JOIN work_instructions ON
    work_instruction_product.work_instruction_id = work_instructions.work_instruction_id
    WHERE (((work_instruction_product.product_id) = %s) AND ((work_instruction_product.work_center) = %s)
    AND ((work_instructions.folder) <> 'R') AND ((work_instructions.active) IS TRUE)
    AND ((work_instruction_product.line_config) IS NULL) )
    """
    result = _execute_select_query(query, (product_id, work_group,))
    return result

def get_global_wi_ids(work_group: int):
    query = """
    SELECT work_instruction_station.work_instruction_id, work_instruction_station.station_list
    FROM work_instruction_station
    WHERE work_instruction_station.station_group_id = %s
    """
    result = _execute_select_query(query, (work_group,))
    return result
    
def get_wi_datas(workinstruction_id: int):
    query = """
    SELECT work_instructions.work_instruction_name, work_instructions.current_revision,
    work_instructions.folder, work_instructions.active, work_instructions.global, work_instructions.global_area
    FROM work_instructions
    WHERE ((work_instructions.work_instruction_id) = %s)
    """
    result = _execute_select_query(query, (workinstruction_id, ), fetchone=True)
    return result

# INSERT ---
# --- Példa használat INSERT-re ---

# Feltételezve, hogy van egy táblád pl. 'serial_data'
# oszlopok: id (auto-increment), order_number (INT), serial_number (VARCHAR), change_date (DATETIME)

# SQL utasítás az INSERT-hez. Fontos a %s használata a paraméterezéshez!
# Több sor beszúrásához (pl. egy fájl összes sorozatszámához) a cursor.executemany() hatékonyabb
INSERT_SERIAL_SQL = """
INSERT INTO serial_data (order_number, serial_number, change_date)
VALUES (%s, %s, %s)
"""

# Adatok előkészítése (pl. a fájlfeldolgozásból nyert adatok)
# Tételezzük fel, hogy a process_recent_files_and_extract_data függvényből kaptad ezt:
sample_order_number = 1340417
sample_serial_numbers = ['784901324181', '784901324182', '784901324183', '784901324184']
processing_time = datetime.datetime.now() # Az aktuális idő, vagy amikor feldolgoztad a fájlt

# Hogyan tudod ezt beírni az adatbázisba?
# Minden sorozatszám egy külön sor lesz az adatbázisban, de ugyanazzal a megrendelés számmal és dátummal.

# Készítsük elő az adatokat a cursor.executemany() számára (ajánlott több sor esetén)
data_to_insert = []
for ser_nr in sample_serial_numbers:
    data_to_insert.append((sample_order_number, ser_nr, processing_time))

# Most hívjuk meg a beszúró függvényt
if data_to_insert: # Csak ha van adat
     # A query a single INSERT SQL, az executemany fogja ismételni a data_to_insert minden elemére
     success, affected_or_lastid = execute_insert_query(INSERT_SERIAL_SQL, data_to_insert)

     if success:
         logging.info(f"Adatbázis INSERT művelet sikeres.")
         # affected_or_lastid itt az érintett sorok száma (ami megegyezik len(data_to_insert)-tel executemany esetén)
         logging.info(f"Érintett sorok száma: {affected_or_lastid}")

     else:
         logging.error("Adatbázis INSERT művelet sikertelen.")
else:
    logging.info("Nincs beszúrandó adat.")