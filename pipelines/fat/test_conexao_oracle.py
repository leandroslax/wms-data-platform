from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

host = os.environ["ORACLE_HOST"]
port = int(os.environ["ORACLE_PORT"])
user = os.environ["ORACLE_USER"]
password = os.environ["ORACLE_PASSWORD"]
service_name = os.environ["ORACLE_SERVICE_NAME"]
sid = os.environ["ORACLE_SID"]

print("Teste 1: service_name")
try:
    dsn = oracledb.makedsn(host, port, service_name=service_name)
    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("select sys_context('USERENV','DB_NAME') from dual")
            print("OK service_name ->", cur.fetchone()[0])
except Exception as e:
    print("ERRO service_name ->", e)

print("\nTeste 2: SID")
try:
    dsn = oracledb.makedsn(host, port, sid=sid)
    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("select sys_context('USERENV','DB_NAME') from dual")
            print("OK sid ->", cur.fetchone()[0])
except Exception as e:
    print("ERRO sid ->", e)
