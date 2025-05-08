from dataclasses import dataclass, field
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
    label_code: str = '',
    foil_type: str = '',
    label_file: str = '',
    sn_format: str = '',
    sn_reset: str = '',
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