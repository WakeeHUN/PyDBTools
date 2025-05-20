import logging
import logging.handlers
import os
from typing import Dict, Any
# import smtplib # Általában nem kell közvetlenül itt


# --- Default Konfigurációs Konstansok (Ha a külső configból hiányzik valami) ---
# Ezeket is érdemes ide tenni
DEFAULT_LOG_DIR = r"C:\Logs\Default"
DEFAULT_LOG_FILENAME_BASE = "service.log"
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = '%(asctime)s %(levelname)s:%(message)s'
DEFAULT_LOG_BACKUP_COUNT = 7
# Alapértelmezett SMTP config részek (ha szükséges)
# DEFAULT_SMTP_MAILHOST = None
# ...stb.


# --- Logolás Beállító Függvény ---
# Ez a függvény kapja meg a load_instance_config által visszaadott dictionary-t
def setup_service_logging(config: Dict[str, Any]):
    """
    Beállítja a logolást TimedRotatingFileHandler és opcionális SMTPHandler-rel
    a megadott konfiguráció alapján. Hozzáadja a handlereket a root loggerhez.
    Használja a servicemanager-t a beállítás korai hibáira, és a logging-et a sikerről.
    """
    # A servicemanager csak a service környezetben érhető el!

    # Logolás konfigurációs értékek lekérése a 'config' dictionary-ből (alapértelmezésekkel)
    log_dir = config.get("log_dir", DEFAULT_LOG_DIR)
    log_filename_base = config.get("log_filename_base", DEFAULT_LOG_FILENAME_BASE)
    log_file_path = os.path.join(log_dir, log_filename_base)
    log_level_str = config.get("log_level", "INFO").upper()
    # logging szint string konvertálása logging konstanssá
    log_level = getattr(logging, log_level_str, logging.INFO) # getattr megpróbálja lekérni a logging modulból a nevét (pl. logging.INFO)

    log_format = config.get("log_format", DEFAULT_LOG_FORMAT)
    backup_count = config.get("log_backup_count", DEFAULT_LOG_BACKUP_COUNT)

    # Győződj meg róla, hogy a log könyvtár létezik (servicemanager a korai hibákhoz)
    try:
        log_file_dir = os.path.dirname(log_file_path)
        if log_file_dir and not os.path.exists(log_file_dir):
             os.makedirs(log_file_dir)
             print(f"Log könyvtár létrehozva: {log_file_dir}")
    except Exception as e:
        print(f"ERROR: Nem sikerült létrehozni a log könyvtárat ({log_file_dir}) a logoláshoz: {e}")

    # Logger objektum lekérése (root logger)
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Távolítsd el minden korábbi handlert (nagyon fontos!)
    if logger.hasHandlers():
        # servicemanager.LogInfoMsg("Eltávolításra kerülnek a korábbi log handlerek.")
        logger.handlers.clear()

    # Hozd létre és konfiguráld a TimedRotatingFileHandler-t
    try:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file_path, when='midnight', interval=1, backupCount=backup_count, encoding='utf-8'
        )
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        # Innentől a logging hívások már használhatják a fájl handlert
        logging.info(f"Fájl logolás konfigurálva ide: {log_file_path} (Szint: {log_level_str})")

    except Exception as e:
        print(f"ERROR: Nem sikerült konfigurálni a Fájl logolást ide {log_file_path}: {e}")
        # Ha ez a handler nem működik, a service lehet, hogy nem tud megfelelően logolni

    # --- SMTPHandler (email küldés) beállítása ---
    smtp_config = config.get("smtp_config", None)
    if smtp_config:
        try:
            # SMTP konfigurációs értékek lekérése (mailhost, fromaddr, toaddrs, subject, credentials, secure, level)
            # Hiba kezelése, ha hiányoznak kötelező kulcsok (pl. KeyError)
            mailhost = smtp_config["mailhost"] # Kötelezőnek tekintjük
            fromaddr = smtp_config["fromaddr"] # Kötelezőnek tekintjük
            toaddrs = smtp_config["toaddrs"]   # Kötelezőnek tekintjük
            subject = smtp_config.get("subject", "Service Alert") # Opcionális
            
            credentials = smtp_config.get("credentials", None) # Opcionális
            if isinstance(credentials, dict): credentials = (credentials.get("user"), credentials.get("pass"))
            elif isinstance(credentials, list) and len(credentials) == 2: credentials = tuple(credentials)
            else: credentials = None # Biztos, ami biztos, ha nem megfelelő formátum

            secure = smtp_config.get("secure", None) # Opcionális TLS/SSL config

            email_level_str = smtp_config.get("level", "ERROR").upper()
            email_level = getattr(logging, email_level_str, logging.ERROR)

            # SMTPHandler létrehozása
            smtp_handler = logging.handlers.SMTPHandler(
                mailhost=mailhost, fromaddr=fromaddr, toaddrs=toaddrs,
                subject=subject, credentials=credentials, secure=secure
            )

            # Beállítjuk az SMTPHandler szintjét!
            smtp_handler.setLevel(email_level)
            smtp_handler.setFormatter(file_formatter) # Ugyanazt a formátumot használhatod

            # Add hozzá az SMTPHandlert a Loggerhez
            logger.addHandler(smtp_handler)

            logging.info(f"SMTP email logolás konfigurálva. Címzettek: {', '.join(toaddrs)} (Szint: {email_level_str})")

        except KeyError as ke:
            print(f"ERROR: Hiányzó kötelező SMTP konfigurációs kulcs: {ke}")
        except Exception as e:
            print(f"ERROR: Nem sikerült konfigurálni az SMTP email logolást: {e}")
