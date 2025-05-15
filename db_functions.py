from dataclasses import dataclass, field
from typing import List, Dict, Any, Type, TypeVar, Optional
import datetime
import db_queries as ds
import db_field_mappings as fm


T_Dataclass = TypeVar('T_Dataclass', bound=dataclass)
def _map_sql_data_to_dataclass(sql_data: Dict[str, Any], mapping_dict: Dict[str, str],
                               dataclass_type: Type[T_Dataclass]) -> T_Dataclass:
    """
    Összerendeli az SQL eredmény dictionary kulcsait a dataclass mezőnevekkel
    egy térképező dictionary alapján, és létrehoz egy dataclass példányt.

    Args:
        sql_data (Dict[str, Any]): A dictionary, ami a SQL lekérdezés eredményét tartalmazza
                                   (pl. cursor(dictionary=True).fetchone() visszatérése).
                                   Feltételezzük, hogy nem üres vagy None, amikor ezt a függvényt hívjuk.
        mapping_dict (Dict[str, str]): A térképező dictionary, ahol a kulcsok a SQL oszlopnevek (string),
                                       az értékek pedig a dataclass mezőnevek (string).
        dataclass_type (Type[T_Dataclass]): A célszerinti dataclass típusa (pl. OrderData, ProductData).

    Returns:
        T_Dataclass: A megadott dataclass típusú példány, feltöltve a térképezett értékekkel.
                     Ha az sql_data üres volt (bár a hívónak ezt ellenőriznie kellene),
                     akkor egy alapértelmezett értékekkel rendelkező példányt ad vissza.
    """
    mapped_values = {}
    
    # Végigmegyünk a térképező dictionary elemein
    for sql_key, field_name in mapping_dict.items():
        # Ellenőrizzük, hogy az aktuális SQL oszlopnév (sql_key) létezik-e
        # a kapott SQL eredmény dictionary-ben (sql_data)
        if sql_key in sql_data:
            # Ha létezik, átmásoljuk az értéket
            mapped_values[field_name] = sql_data[sql_key]

    # Létrehozzuk a dataclass példányt a gyűjtött értékekkel.
    # A '**' operátor kicsomagolja a mapped_values dictionary-t kulcsszavas argumentumokként.
    # Pl. OrderData(rec_nr=123, ser_nr='ABC', ...)
    # Ha a mapped_values dictionary üres, akkor a dataclass az összes mezőhöz
    # az alapértelmezett értéket fogja használni (ha meg van adva).
    return dataclass_type(**mapped_values)


# User data:
@dataclass
class UserData:
    id: int = -1,
    name: str = '-',
    prime_nr: str = '',
    language: str = '',
    role_id: int =  -1

def get_user_data(prime_nr: str):
    user_data = UserData()

    if prime_nr != '-':
        sql_datas = ds.get_user_datas(prime_nr)

        if sql_datas:
            user_data = _map_sql_data_to_dataclass(sql_datas, fm.USER_DATA_MAP, UserData)
            user_data.prime_nr = prime_nr

    return user_data

# Type data:
@dataclass
class TypeData:
    id: int = -1
    code: str = ''
    name: str = ''
    log_nr: str = ''
    cust_id: int = -1
    tray_size: int = -1
    box_size: int = -1
    pallet_size: int = -1
    active: bool = True
    array_size: int = -1
    array_dim: str = ''
    base_type_id: int = -1
    params: str = ''

def get_type_data(product_id: int, station_group: int):
    type_data = TypeData()

    if product_id > 0:
        sql_datas = ds.get_type_datas(product_id, station_group)

        if sql_datas:
            type_data = _map_sql_data_to_dataclass(sql_datas, fm.TYPE_DATA_MAP, TypeData)
            type_data.id = product_id

    return type_data

# Label data:
@dataclass
class LabelData:
    last_sn: str = ''
    hwsw: int = -1
    bom: int = -1
    label_code: str = ''
    foil_type: str = ''
    label_file: str = ''
    sn_format: str = ''
    sn_reset: str = ''
    copies: int = -1

def get_label_data(product_id: int, entry_nr: int):
    label_data = LabelData()

    if product_id > 0:
        sql_datas = ds.get_label_datas(product_id, entry_nr)

        if sql_datas:
            label_data = _map_sql_data_to_dataclass(sql_datas, fm.LABEL_DATA_MAP, LabelData)

    return label_data

# Order data:
@dataclass
class OrderData:
    order_nr: str = ''
    product_id: int = -1
    order_type: str = ''
    quantity: int = -1
    mat_nr: str = ''
    group_id: int = -1

def get_order_data(order_nr: str):
    order_data = OrderData()

    if order_nr:
        sql_datas = ds.get_order_details(order_nr)

        if sql_datas:
            order_data = _map_sql_data_to_dataclass(sql_datas, fm.ORDER_DATA_MAP, OrderData)
            order_data.order_nr = order_nr

    return order_data

# Product data:
@dataclass
class ProductData:
    rec_nr: int = -1
    ser_nr: str = ''
    product_id: int = -1
    last_station: int = -1
    change_date: datetime.datetime = field(default_factory=datetime.datetime.now)
    cust_sn: str = ''
    dev_param: str = ''

def get_product_data(ser_nr: str, product_id: int):
    product_data = ProductData()

    if ser_nr != '':
        sql_datas = ds.get_product_datas(ser_nr, product_id)

        if sql_datas:
            product_data = _map_sql_data_to_dataclass(sql_datas, fm.PRODUCT_DATA_MAP, ProductData)
            product_data.ser_nr = ser_nr
            product_data.product_id = product_id

    return product_data

def get_array_data(ser_nr: str, product_id: int):
    if ser_nr != '':
        sql_datas = ds.get_array_datas(ser_nr, product_id)

    return sql_datas

# Workinstructions:
@dataclass
class WorkInstructionData:
    """Representál egy sort a work_instruction_product lekérdezés eredményéből."""
    id: int = -1
    station_list: str = ''
    short_name: str = ''
    rev: int = -1

def _get_workinstruction_datas(workinstruction_id: int):
    workinstruction_datas = ds.get_wi_datas(workinstruction_id)
    return workinstruction_datas

def _get_work_instructions(wi_dicts: List[dict], station_id: int):
    list_of_wi_dataclasses: List[WorkInstructionData] = [] 

    if wi_dicts is not None and wi_dicts:
        for instruction_data_dict in wi_dicts:
            wi_instance = _map_sql_data_to_dataclass(instruction_data_dict, fm.WORK_INSTRUCTION_MAP, WorkInstructionData)

            # Stationlist alapján kell-e ez a munkauti
            station_list_value = wi_instance.station_list

            is_valid_station_string = isinstance(station_list_value, str) and station_list_value.strip() != ''
            should_append = False 

            if not is_valid_station_string:
                should_append = True
            else:
                stations = [s.strip() for s in station_list_value.split(';') if s.strip()]
                if station_id in stations:
                    should_append = True

            # Ha kell, akkor lekérdezem az adatait és hozzáadom a listához
            if should_append:
                wi_datas = _get_workinstruction_datas(wi_instance.id)

                mapped_values = {}
                for sql_key, field_name in fm.WORK_INSTRUCTION_MAP.items():
                    if sql_key in wi_datas:
                        mapped_values[field_name] = wi_datas[sql_key]

                for key, value in mapped_values.items():
                    if hasattr(wi_instance, key):
                        setattr(wi_instance, key, value)

                list_of_wi_dataclasses.append(wi_instance)
    
    return list_of_wi_dataclasses

def get_product_workinstructions(product_id: int, work_group: int, station_id: int):
    list_of_work_instructions_dicts = ds.get_product_wi_ids(product_id, work_group)
    return _get_work_instructions(list_of_work_instructions_dicts, station_id)

def get_global_workinstructions(work_group: int, station_id: int):
    list_of_work_instructions_dicts = ds.get_global_wi_ids(work_group)
    return _get_work_instructions(list_of_work_instructions_dicts, station_id)

def insert_array_of_pcba(serial_nr: str, product_id: int, last_station: int):
    return ds.insert_array_of_pcba(serial_nr, product_id, last_station)

def insert_rec_nr_ser_nr(product_id: int, serial_nr: str, customer_sn: str, dev_param: str, last_station: int, 
                         box_id: Optional[int] = None, create_date: Optional[datetime.datetime] = None):
    return ds.insert_rec_nr_ser_nr(product_id, serial_nr, customer_sn, dev_param, last_station, box_id, create_date)

def insert_rec_nr_last_station(rec_nr: int, last_station: int, proc_state: bool, user_id: int, prod_order: str,
                              change_date: Optional[datetime.datetime] = None):
    return ds.insert_rec_nr_last_station(rec_nr, last_station, proc_state, user_id, prod_order, change_date)
    
def insert_array_items(array_serial_nr: str, rec_nr: int, position: int, array_id: int):
    return ds.insert_array_items(array_serial_nr, rec_nr, position, array_id)