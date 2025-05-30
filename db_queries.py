import mysql.connector
import psycopg2
import psycopg2.extras
import os
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import logging


# MySQL
MYSQL_DB_CONFIG = {
    "db_type":  "mysql",
    "host":     "10.180.8.23",
    "user":     os.environ.get("DB_USER_MYSQL", "importer_user"),
    "password": os.environ.get("DB_PASSWORD_MYSQL", "p4pAQ9qC"),
    "database": "traceability",
    "port":     3306
}

# MySQL Backup
MYSQL_BACKUP_DB_CONFIG = {
    "db_type":  "mysql",
    "host":     "srv14-db02",
    "user":     "admin",
    "password": "DgDAXcP22!",
    "database": "traceability",
    "port":     3306
}

# PostgreSQL
PSQL_DB_CONFIG = {
    "db_type":  "postgresql",
    "host":     "khudb01",
    "user":     "vargat",
    "password": "galaxys24",
    "database": "traceability",
    "port":     5432
}

DB_CONFIG = MYSQL_BACKUP_DB_CONFIG
DB_TYPE = "mysql"


# --- Adatbázis Kapcsolat Létrehozása ---
def _get_db_connection(db_config: Dict[str, Any]):
    """
    Létrehoz egy adatbázis kapcsolatot a megadott konfiguráció alapján.
    Dinamikusan választ MySQL és PostgreSQL között.
    """
    global DB_TYPE
    DB_TYPE  = db_config.get("db_type", "mysql").lower() # Alapértelmezés MySQL, ha nincs megadva
    host     = db_config.get("host")
    user     = db_config.get("user")
    password = db_config.get("password")
    database = db_config.get("database")
    port     = db_config.get("port")

    conn = None # Kapcsolat objektum

    try:
        if DB_TYPE == "mysql":
            conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port or 3306, # MySQL alapértelmezett portja
            )
        elif DB_TYPE == "postgresql":
            conn = psycopg2.connect(
                host=host,
                user=user,
                password=password,
                dbname=database, # PostgreSQL-ben 'dbname' a 'database' helyett
                port=port or 5432 # PostgreSQL alapértelmezett portja
            )
        else:
            raise ValueError(f"Nem támogatott adatbázis típus a konfigurációban: {DB_TYPE}")

        return conn
    except Exception as e:
        print(f"Nem sikerült kapcsolódni a(z) {DB_TYPE} adatbázishoz: {e}")
        logging.error(f"Nem sikerült kapcsolódni a(z) {DB_TYPE} adatbázishoz: {e}", exc_info=True)
        return None # Visszaadunk None-t, ha a kapcsolat sikertelen
    
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
        with _get_db_connection(DB_CONFIG) as conn:
            # --- JAVÍTÁS: Feltételes kurzor létrehozás a DB típus alapján ---
            if DB_TYPE == "mysql":
                # Feltételezzük, hogy a MySQL-nél is szótár-szerű eredményeket akarsz
                cursor = conn.cursor(dictionary=True) 
            elif DB_TYPE == "postgresql":
                # PostgreSQL-nél a DictCursor-t kell használni a szótár-szerű eredményekhez
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            else:
                raise ValueError(f"Nem támogatott adatbázis típus a kurzor létrehozásához: {DB_TYPE}")
            
            with cursor as mycursor:
                mycursor.execute(query, params)
                if fetchone:
                    # Visszaadja az első (vagy következő) sor eredményét dictionary-ként.
                    # Ha nincs több sor, None-t ad vissza.
                    return mycursor.fetchone()
                else:
                    # Visszaadja az összes hátralévő sor eredményét dictionary-k listájaként.
                    # Ha nincs eredmény, üres listát ad vissza.
                    return mycursor.fetchall()
                
    except conn.Error as err:
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
        with _get_db_connection(DB_CONFIG) as conn:
            cursor = conn.cursor()
            with cursor as mycursor:
                # SQL utasítás végrehajtása paraméterekkel
                mycursor.execute(query, params)

                # Ha INSERT volt, lekérdezhetjük az utolsó beszúrt sor ID-ját (auto-increment oszlop esetén)
                if query.strip().upper().startswith("INSERT"):
                    if DB_TYPE == "mysql":
                        lastrowid = mycursor.lastrowid
                    elif DB_TYPE == "postgresql":
                        lastrowid = mycursor.fetchone()[0]
                else:
                    # UPDATE vagy DELETE esetén lekérdezhetjük az érintett sorok számát
                    affected_rows = mycursor.rowcount

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
        if conn:
            conn.rollback()
        # Sikertelen volt
        return False, -1
    
    except Exception as e:
        print(f"Váratlan hiba az adatbázis művelet során: {e}")
        if conn:
            conn.rollback()
        return False, -1


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
    result = _execute_select_query(query, (station_group, product_id), fetchone=True)
    return result

def get_label_datas(product_id: int, entry_nr: int):
    query = """
    SELECT labels.lastSn, labels.hwswIndex, labels.bomNr, labels.labelCode, labels.foilType, labels.labelFile, labels.snFormat,
    labels.snResetType, labels.copies FROM labels WHERE labels.productId = %s AND labels.entryNr = %s
    """
    result = _execute_select_query(query, (product_id, entry_nr), fetchone=True)
    return result

def get_order_details(order_nr: str):
    query = """
    SELECT order_details.productId, order_details.orderType, order_details.quantity, order_details.discount,
    order_details.closeDate, order_details.routing, order_details.matnr
    FROM order_details
    WHERE order_details.orderNumber = %s
    """
    result = _execute_select_query(query, (order_nr,), fetchone=True)
    return result

def get_product_datas(ser_nr: str, product_id: int):
    query = """
    SELECT recnrsernr.recNr, recnrsernr.lastStation, recnrsernr.changeDate, recnrsernr.customerSn, recnrsernr.devParam
    FROM recnrsernr
    WHERE (((recnrsernr.serNr) = %s) AND ((recnrsernr.productId) = %s))
    """
    result = _execute_select_query(query, (ser_nr, product_id), fetchone=True)
    return result

def get_array_datas(ser_nr: str, product_id: int):
    query = """
    SELECT arrayofpcba.arrayId, arrayofpcba.createDate, arrayofpcba.changeDate, arrayofpcba.lastStation, arrayofpcba.unGrouped
    FROM arrayofpcba WHERE arrayofpcba.arraySerNr = %s AND arrayofpcba.arrayProductId = %s
    """
    result = _execute_select_query(query, (ser_nr, product_id), fetchone=True)
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
    result = _execute_select_query(query, (product_id, work_group))
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
    result = _execute_select_query(query, (workinstruction_id,), fetchone=True)
    return result


# INSERT ---
def insert_array_of_pcba(serial_nr: str, product_id: int, last_station: int) -> Tuple[bool, int]:
    insert_into_part = "INSERT INTO arrayofpcba"
    insert_columns   = "arraySerNr, arrayProductId, createDate, lastStation, unGrouped"
    values_part      = "VALUES (%s, %s, NOW(), %s, FALSE)"
    returning_part   = ''
    if DB_TYPE == "postgresql":
        returning_part = "RETURNING arrayid"

    query = f"{insert_into_part} ({insert_columns}) {values_part} {returning_part}"
    success, last_id = _execute_modify_query(query, (serial_nr, product_id, last_station))
    return success, last_id

def insert_rec_nr_ser_nr(product_id: int, serial_nr: str, customer_sn: str, dev_param: str, last_station: int, 
                         box_id: Optional[int] = None, create_date: Optional[datetime] = None) -> Tuple[bool, int]:
    insert_into_part = "INSERT INTO recnrsernr"
    insert_columns   = "productId, serNr, customerSn, devParam, lastStation, boxId, createDate, changeDate"
    
    if create_date is None:
        values_part = f"VALUES ({', '.join(['%s'] * 6)}, NOW(), NOW())"
        params = (product_id, serial_nr, customer_sn, dev_param, last_station, box_id)
    else:
        values_part = f"VALUES ({', '.join(['%s'] * 8)})"
        params = (product_id, serial_nr, customer_sn, dev_param, last_station, box_id, create_date, create_date)

    returning_part = ''
    if DB_TYPE == "postgresql":
        returning_part = "RETURNING recnr"

    query = f"{insert_into_part} ({insert_columns}) {values_part} {returning_part}"
    success, last_id = _execute_modify_query(query, params)
    return success, last_id

def insert_rec_nr_last_station(rec_nr: int, last_station: int, proc_state: bool, user_id: int, prod_order: str,
                              change_date: Optional[datetime] = None) -> Tuple[bool, int]:
    insert_into_part = "INSERT INTO recnrlaststation"
    insert_columns   = "lastStation, procState, userId, recNr, prodOrder, changeDate"

    if change_date is None:
        values_part = f"VALUES ({', '.join(['%s'] * 5)}, NOW())"
        params = (last_station, proc_state, user_id, rec_nr, prod_order)
    else:
        values_part = f"VALUES ({', '.join(['%s'] * 6)})"
        params = (last_station, proc_state, user_id, rec_nr, prod_order, change_date)
    
    returning_part = ''
    if DB_TYPE == "postgresql":
        returning_part = "RETURNING procid"

    query = f"{insert_into_part} ({insert_columns}) {values_part} {returning_part}"
    success, last_id = _execute_modify_query(query, params)
    return success, last_id

def insert_array_items(array_serial_nr: str, rec_nr: int, position: int, array_id: int) -> Tuple[bool, int]:
    insert_into_part = "INSERT INTO arrayitems"
    insert_columns   = "arraySerNr, recNr, position, arrayId"
    values_part      = f"VALUES ({', '.join(['%s'] * 4)})"
    returning_part   = ''
    if DB_TYPE == "postgresql":
        returning_part = "RETURNING arrayitemsid"

    query = f"{insert_into_part} ({insert_columns}) {values_part} {returning_part}"
    success, last_id = _execute_modify_query(query, (array_serial_nr, rec_nr, position, array_id))
    return success, last_id