import mysql.connector
import os


DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "10.180.8.23"),
    "user":     os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_DATABASE", "traceability")
}

def execute_select_query(query, params=None, fetchone=False):
    try:
        with mysql.connector.connect(**DB_CONFIG) as mydb:
            with mydb.cursor(dictionary=True) as mycursor: # dictionary=True a név szerinti eléréshez
                mycursor.execute(query, params)
                if fetchone:
                    return mycursor.fetchone()
                else:
                    return mycursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Hiba az adatbázis művelet során: {err}")
        return None
    

def get_users():
    query = "SELECT userId, userName, primeNr FROM users WHERE userStatus = %s"
    results = execute_select_query(query, (True,))
    return results
    
def get_user_datas(prime_nr: str):
    query = "SELECT userId, userName, language, roleId FROM users WHERE primeNr = %s"
    result = execute_select_query(query, (prime_nr,), fetchone=True)
    return result

def get_type_datas(type_code: str):
    query = "SELECT productId, productName, logNr FROM products WHERE productCode = %s"
    result = execute_select_query(query, (type_code,), fetchone=True)
    return result

def get_label_datas(product_id: int, entry_nr: int):
    query = "SELECT lastSn, hwswIndex, bomNr, labelCode, foilType, labelFile, snFormat, \
             snResetType, copies FROM labels WHERE productId = %s AND entryNr = %s"
    result = execute_select_query(query, (product_id, entry_nr,), fetchone=True)
    return result

def get_order_details(order_nr: str):
    query = "SELECT order_details.productId, order_details.orderType, order_details.quantity, order_details.discount, \
             order_details.closeDate, order_details.routing, order_details.matnr \
             FROM order_details \
             WHERE (((order_details.orderNumber) = %s ))"
    result = execute_select_query(query, (order_nr, ), fetchone=True)
    return result

def get_product_datas(ser_nr: str, product_id: int):
    query = "SELECT recnrsernr.recNr, recnrsernr.lastStation, recnrsernr.changeDate, recnrsernr.customerSn, recnrsernr.devParam \
             FROM recnrsernr \
             WHERE (((recnrsernr.serNr) = %s) AND ((recnrsernr.productId) = %s))"
    result = execute_select_query(query, (ser_nr, product_id, ), fetchone=True)
    return result

def get_product_wi_ids(product_id: int, work_group: int):
    query = "SELECT work_instruction_product.work_instruction_id, work_instruction_product.station_list \
             FROM work_instruction_product INNER JOIN work_instructions ON \
             work_instruction_product.work_instruction_id = work_instructions.work_instruction_id \
             WHERE (((work_instruction_product.product_id) = %s) AND ((work_instruction_product.work_center) = %s) \
             AND ((work_instructions.folder) <> 'R') AND ((work_instructions.active) IS TRUE) \
             AND ((work_instruction_product.line_config) IS NULL) )"
    result = execute_select_query(query, (product_id, work_group,))
    return result

def get_global_wi_ids(work_group: int):
    query = "SELECT work_instruction_station.work_instruction_id, work_instruction_station.station_list \
             FROM work_instruction_station \
             WHERE work_instruction_station.station_group_id = %s"
    result = execute_select_query(query, (work_group,))
    return result
    
def get_wi_datas(workinstruction_id: int):
    query = "SELECT work_instructions.work_instruction_name, work_instructions.current_revision, \
             work_instructions.folder, work_instructions.active, work_instructions.global, work_instructions.global_area \
             FROM work_instructions \
             WHERE ((work_instructions.work_instruction_id) = %s)"
    result = execute_select_query(query, (workinstruction_id, ), fetchone=True)
    return result