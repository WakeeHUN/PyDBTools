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

# Workinstructions:
@dataclass
class WorkInstructionData:
    """Representál egy sort a work_instruction_product lekérdezés eredményéből."""
    work_instruction_id: int = -1
    station_list: str = ''

    stations: List[str] = field(default_factory=list, init=False, repr=False) 
    # init=False: ne kelljen megadni a konstruktorban, repr=False: ne jelenjen meg a repr-ben

    # Ez a metódus automatikusan lefut a dataclass példány létrehozása UTÁN
    def __post_init__(self):
        if isinstance(self.station_list, str) and self.station_list:
            # Feldaraboljuk a stringet vessző mentén, eltávolítjuk a szóközöket és a lehetséges üres elemeket
            self.stations = [s.strip() for s in self.station_list.split(';') if s.strip()]
        else:
            self.stations = [] # Üres listát állítunk be, ha a string üres vagy nem string

def get_work_instructions(product_id: int, work_group: int):
    # 1. Lekérjük az adatokat (szótárak listája vagy None)
    list_of_work_instructions_dicts = ds.get_product_wi_ids(product_id, work_group)

    # 2. Létrehozunk egy üres listát a WorkInstructionData példányok számára
    list_of_wi_dataclasses: List[WorkInstructionData] = [] 

    # 3. Ellenőrizzük az eredményt és alakítjuk át
    if list_of_work_instructions_dicts is None:
        print("Adatbázis hiba történt a munka utasítások lekérésekor.")
        # A list_of_wi_dataclasses üres marad, ami helyes hiba vagy nincs találat esetén

    elif not list_of_work_instructions_dicts: # Ellenőrzi, hogy a lista üres-e (azaz nincs találat)
        print(f"Nincs találat erre a termék ({product_id}) és munkacsoport ({work_group}) kombinációra.")
        # A list_of_wi_dataclasses üres marad

    else:
        # Ha idáig eljutunk, a lista nem üres, vannak szótárak benne
        print(f"Találatok száma (szótárként): {len(list_of_work_instructions_dicts)}")
        
        # Végigmegyünk a szótárak listáján
        for instruction_data_dict in list_of_work_instructions_dicts:
            # Létrehozunk egy WorkInstructionData példányt az aktuális szótárból
            # A ** instruction_data_dict kicsomagolja a szótárat, ahol a kulcsok
            # a WorkInstructionData konstruktorának paraméternevei (mezőnevek)
            # Pl. WorkInstructionData(work_instruction_id=instruction_data_dict['work_instruction_id'], station_list=instruction_data_dict['station_list'])
            wi_instance = WorkInstructionData(**instruction_data_dict)

            # Hozzáadjuk az elkészült dataclass példányt az új listához
            list_of_wi_dataclasses.append(wi_instance)

        print(f"Átalakítva {len(list_of_wi_dataclasses)} WorkInstructionData példánnyá.")

    # --- Most már használhatod a list_of_wi_dataclasses listát ---
    # Ez a lista WorkInstructionData objektumokat tartalmaz
    print("\nWorkInstructionData objektumok listája:")
    if list_of_wi_dataclasses:
        for i, wi_item in enumerate(list_of_wi_dataclasses):
            # Hozzáférés a mezőkhöz a könnyen olvasható dot notációval
            print(f"  Elem {i+1}:")
            print(f"    WI ID: {wi_item.work_instruction_id}") 
            print(f"    Állomáslista (nyers string): {wi_item.station_list}")
            # Ha használtad a __post_init__ metódust a stations listához:
            print(f"    Állomások (feldolgozott lista): {wi_item.stations}")
            print("-" * 10)
    else:
        print("A dataclass lista üres (nincs találat vagy hiba történt).")

    # --- Innen tovább tudsz dolgozni a list_of_wi_dataclasses listával ---
    # Pl. megjelenítheted a UI-ban, kiválaszthatsz belőle elemeket, stb.
    