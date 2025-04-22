import mysql.connector
import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "10.180.8.23"),
    "user": os.environ.get("DB_USER"),
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

def getUserName(primeNr):
    query = "SELECT userName FROM users WHERE primeNr = %s"
    result = execute_select_query(query, (primeNr,), fetchone=True)
    return result['userName'] if result and 'userName' in result else None

def getUsers():
    query = "SELECT userName, roleId FROM users WHERE userStatus = %s"
    results = execute_select_query(query, (True,))
    if results:
        users_data = []
        for row in results:
            users_data.append({'userName': row['userName'], 
                               'roleId': row['roleId']})
        return users_data
    else:
        return []
