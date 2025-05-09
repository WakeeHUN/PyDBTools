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
    
def get_user_datas(prime_nr):
    query = "SELECT userId, userName, language, roleId FROM users WHERE primeNr = %s"
    result = execute_select_query(query, (prime_nr,), fetchone=True)
    return result

def get_type_datas(type_code):
    query = "SELECT productId, productName, logNr FROM products WHERE productCode = %s"
    result = execute_select_query(query, (type_code,), fetchone=True)
    return result

def get_label_datas(product_id, entry_nr):
    query = "SELECT lastSn, hwswIndex, bomNr, labelCode, foilType, labelFile, snFormat, \
             snResetType, copies FROM labels WHERE productId = %s AND entryNr = %s"
    result = execute_select_query(query, (product_id, entry_nr,), fetchone=True)
    return result

def get_product_wi_ids(product_id, work_group):
    query = "SELECT work_instruction_product.work_instruction_id, work_instruction_product.station_list \
             FROM work_instruction_product INNER JOIN work_instructions ON \
             work_instruction_product.work_instruction_id = work_instructions.work_instruction_id \
             WHERE (((work_instruction_product.product_id) = %s) AND ((work_instruction_product.work_center) = %s) \
             AND ((work_instructions.folder) <> 'R') AND ((work_instructions.active) IS TRUE) \
             AND ((work_instruction_product.line_config) IS NULL) )"
    result = execute_select_query(query, (product_id, work_group,))
    return result
    