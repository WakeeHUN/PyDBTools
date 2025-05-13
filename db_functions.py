from dataclasses import dataclass, field
from typing import List
import db_queries as ds
import db_field_mappings as fm

# User data:
@dataclass
class UserData:
    id: int = -1,
    name: str = '-',
    prime_nr: str = '',
    language: str = '',
    role_id: int =  -1

def get_user_data(prime_nr: str) -> UserData:
    user_data = UserData()

    if prime_nr != '-':
        sql_datas = ds.get_user_datas(prime_nr)

        if sql_datas:
            mapped_values = {}
            for sql_key, field_name in fm.USER_DATA_MAP.items():
                 if sql_key in sql_datas:
                     mapped_values[field_name] = sql_datas[sql_key]

            user_data = UserData(**mapped_values)
            user_data.prime_nr = prime_nr

    return user_data

# Type data:
@dataclass
class TypeData:
    id: int = -1
    code: str = ''
    name: str = ''
    log_nr: str = ''

def get_type_data(product_code: str) -> TypeData:
    type_data = TypeData()

    if product_code != '-':
        sql_datas = ds.get_type_datas(product_code)

        if sql_datas:
            mapped_values = {}
            for sql_key, field_name in fm.PRODUCT_DATA_MAP.items():
                 if sql_key in sql_datas:
                     mapped_values[field_name] = sql_datas[sql_key]

            type_data = TypeData(**mapped_values)
            type_data.code = product_code

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

def get_label_data(product_id: int, entry_nr: int) -> LabelData:
    label_data = LabelData()

    if product_id > 0:
        sql_datas = ds.get_label_datas(product_id, entry_nr)

        if sql_datas:
            mapped_values = {}
            for sql_key, field_name in fm.LABEL_DATA_MAP.items():
                 if sql_key in sql_datas:
                     mapped_values[field_name] = sql_datas[sql_key]

            label_data = LabelData(**mapped_values)

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

def get_order_data(order_nr: str) -> OrderData:
    order_data = OrderData()

    if order_nr:
        sql_datas = ds.get_order_details(order_nr)

        if sql_datas:
            mapped_values = {}
            for sql_key, field_name in fm.ORDER_DATA_MAP.items():
                 if sql_key in sql_datas:
                     mapped_values[field_name] = sql_datas[sql_key]

            order_data = OrderData(**mapped_values)
            order_data.order_nr = order_nr

    return order_data

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
            mapped_values = {}
            for sql_key, field_name in fm.WORK_INSTRUCTION_MAP.items():
                if sql_key in instruction_data_dict:
                    mapped_values[field_name] = instruction_data_dict[sql_key]

            wi_instance = WorkInstructionData(**mapped_values)

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

                mapped_values.clear
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
    