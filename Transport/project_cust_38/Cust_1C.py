#coding=cp1251
import pythoncom
import win32com.client

def connect_1c():
    V83_CONN_STRING = 'Srvr="novgorod";Ref="ERP";Usr="  ";Pwd="25012022";'
    pythoncom.CoInitialize()
    conn1c = win32com.client.Dispatch("V83.COMConnector").Connect(V83_CONN_STRING)
    return conn1c

def spis_rascroev(conn1c):
    catalog = getattr(conn1c.Documents, "").Select()
    spis = [['', ]]
    while catalog.Next():
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("ID", getattr(catalog, "ID"))
        try:
            print(".", getattr(getattr(catalog, "").GetObject(), ''))
        except:
            print(". ")
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("ID", getattr(catalog, "ID"))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print("", getattr(catalog, ""))
        print('=================================================')
