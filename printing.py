import win32print


def print_zpl(ser_nr: str):
    print(ser_nr)
    printer_name = "ZDesigner GK420t (1. másolat)"
    hPrinter = win32print.OpenPrinter(printer_name)

    zpl_text = '''
    ^XA
    ^LH320,0
    ^FO0,50^A0N,25,20^FD$$SERNR$$^FS
    ^XZ
    '''
    zpl_text = zpl_text.replace('$$SERNR$$', ser_nr)
    print(zpl_text)

    try:
        win32print.StartDocPrinter(hPrinter, 1, ("Zebra Címke", None, "RAW"))
        win32print.StartPagePrinter(hPrinter)
        win32print.WritePrinter(hPrinter, zpl_text.encode('utf-8'))
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
        print('ok')
    finally:
        win32print.ClosePrinter(hPrinter)
        

if __name__ == "__main__":
    print_zpl('111122333333')