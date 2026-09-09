"""Verifica que cada hallazgo P0/P1 de AUDITORIA.md quedo corregido.

Cada prueba reproduce el ataque o el error original y exige el comportamiento
nuevo. Correr con el stack levantado:

    python3 scripts/verifica_arreglos.py

Los valores por defecto son los del stack de desarrollo (puertos 18000/18080,
contenedores reloj_checador_*, contrasena de fabrica). Para correrlo contra otro
entorno, por ejemplo el VPS de staging, todo se ajusta por variables de entorno
sin tocar este archivo:

    CHECADOR_BACKEND=http://127.0.0.1:18001 \
    CHECADOR_FRONT=http://127.0.0.1:18085 \
    CHECADOR_ADMIN_PASS='...' \
    CHECADOR_PG_CONTAINER=checador_staging_postgres \
    CHECADOR_BACKEND_CONTAINER=checador_staging_backend \
    CHECADOR_PG_USER=reloj CHECADOR_PG_DB=reloj_checador \
    python3 scripts/verifica_arreglos.py

Estaba clavado a los nombres de la oficina, asi que en staging fallaba entero
aunque el sistema estuviera bien: `docker exec reloj_checador_postgres` no
existe ahi. Un verificador que no se puede apuntar al entorno real no verifica
el entorno real.
"""

import json
import os
import subprocess
import sys
import time

B = os.environ.get("CHECADOR_BACKEND", "http://localhost:18000")   # backend directo
F = os.environ.get("CHECADOR_FRONT", "http://localhost:18080")     # a traves de nginx
ADMIN_PASS = os.environ.get("CHECADOR_ADMIN_PASS", "1234")
ADMIN = ["-H", f"X-Admin-Pass: {ADMIN_PASS}"]
PG_CONTAINER = os.environ.get("CHECADOR_PG_CONTAINER", "reloj_checador_postgres")
BACKEND_CONTAINER = os.environ.get("CHECADOR_BACKEND_CONTAINER", "reloj_checador_backend")
PG_USER = os.environ.get("CHECADOR_PG_USER", "reloj")
PG_DB = os.environ.get("CHECADOR_PG_DB", "reloj_checador")
# La contrasena de fabrica se sigue comprobando, pero solo tiene sentido donde
# de verdad se uso: en staging el compose exige una propia y ese aviso no aplica.
ESPERA_PASS_DE_FABRICA = ADMIN_PASS == "1234"
FOTO = os.environ.get("CHECADOR_FOTO", "reloj_checador.ico")

fallos = []
pasadas = []

# IPs SIMULADAS UNICAS POR CORRIDA.
#
# El rate limit vive en memoria del proceso y dura 5 minutos (rate_limit.py:
# WINDOW_SECONDS=300). Con IPs fijas, la segunda corrida dentro de esa ventana
# arranca contra un cubo que la primera dejo lleno: el primer login devuelve 429
# en vez de 401 y la prueba "login fallido devuelve 401" falla aunque el sistema
# este perfecto. Es un falso negativo del verificador, y de los peores, porque
# aparece justo cuando uno repite la prueba por desconfianza.
#
# Derivar el ultimo octeto del PID da una IP distinta en cada corrida sin
# necesidad de esperar los 5 minutos.
_OCTETO = os.getpid() % 250 + 2
IP_PIN = f"10.1.{_OCTETO}.1"
IP_LOGIN = f"10.1.{_OCTETO}.2"
IP_LIMPIA = f"10.1.{_OCTETO}.9"


def curl(*args, status=False):
    cmd = ["curl", "-s"]
    if status:
        cmd += ["-o", "/dev/null", "-w", "%{http_code}"]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def jcurl(*args):
    raw = curl(*args)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}


def check(nombre, condicion, detalle=""):
    if condicion:
        pasadas.append(nombre)
        print(f"  OK   {nombre}")
    else:
        fallos.append(f"{nombre}: {detalle}")
        print(f"  FALLA {nombre}  {detalle}")


def psql(sql):
    return subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", PG_USER,
         "-d", PG_DB, "-t", "-c", sql],
        capture_output=True, text=True,
    ).stdout.strip()


print("Preparando: un empleado de prueba\n")
psql("DELETE FROM records; DELETE FROM device_alerts; DELETE FROM employees;")
curl("-X", "POST", f"{B}/api/admin/employees", *ADMIN,
     "-F", "name=Ana Torres", "-F", "pin=1111", "-F", "category=trabajador",
     "-F", f"photo=@{FOTO};type=image/png")
emp = jcurl(f"{B}/api/admin/employees", *ADMIN)["employees"][0]
emp_id = emp["id"]

print("P0-1  Zona horaria")
hora_host = subprocess.run(["date", "+%H"], capture_output=True, text=True).stdout.strip()
hora_cont = subprocess.run(
    ["docker", "exec", BACKEND_CONTAINER, "date", "+%H"],
    capture_output=True, text=True).stdout.strip()
# En la PC de la oficina el host ya corre en hora local y comparar contra el
# contenedor basta. En un servidor en UTC (el VPS de staging) esa comparacion
# FALLA aunque todo este bien, porque el contenedor debe ir 7 horas atras del
# host a proposito. Lo que importa en ambos casos es que el contenedor este en
# la hora de la OFICINA, asi que se compara contra OFFICE_TZ, no contra el host.
hora_oficina = subprocess.run(
    ["docker", "exec", BACKEND_CONTAINER, "python", "-c",
     "from app import clock; print(f'{clock.now():%H}')"],
    capture_output=True, text=True).stdout.strip()
check("el contenedor corre en la hora de la oficina", hora_cont == hora_oficina,
      f"date={hora_cont} clock.now()={hora_oficina}")

print("\nP0-2  Suplantacion: marcar por otro sin su PIN")
r = jcurl("-X", "POST", f"{B}/api/punch",
          "-F", f"employeeId={emp_id}", "-F", "employeeName=Ana Torres",
          "-F", "type=entrada", "-F", f"photo=@{FOTO};type=image/png")
check("punch sin PIN es rechazado", r.get("ok") is False, str(r)[:90])
check("no se creo el registro", psql("SELECT count(*) FROM records;") == "0")

print("\nP0-3  Marcar con el PIN correcto si funciona")
r = jcurl("-X", "POST", f"{B}/api/punch", "-F", "pin=1111",
          "-F", "type=entrada", "-F", f"photo=@{FOTO};type=image/png")
check("punch con PIN valido es aceptado", r.get("ok") is True, str(r)[:90])
check("quedo registrado", psql("SELECT count(*) FROM records;") == "1")
hora_bd = psql("SELECT to_char(timestamp,'HH24') FROM records LIMIT 1;").strip()
check("la hora guardada es local", hora_bd == hora_oficina,
      f"bd={hora_bd} oficina={hora_oficina} host={hora_host}(UTC en el VPS)")

print("\nP0-4  Rate limiting")
# Cada bloque usa su propia IP simulada: el limite es por IP, asi que reutilizar
# una ya bloqueada por el bloque anterior daria un 429 enganoso.
codigos = [curl("-X", "POST", f"{F}/api/verify-pin", "-H", f"X-Forwarded-For: {IP_PIN}",
                "-H", "Content-Type: application/json",
                "-d", f'{{"pin":"9{i:03d}"}}', status=True) for i in range(8)]
check("verify-pin bloquea tras varios fallos", "429" in codigos, f"codigos={codigos}")

codigos = [curl("-X", "POST", f"{F}/api/admin/login", "-H", f"X-Forwarded-For: {IP_LOGIN}",
                "-H", "Content-Type: application/json",
                "-d", f'{{"password":"malo{i}"}}', status=True) for i in range(8)]
check("login fallido devuelve 401 (no 200)", codigos[0] == "401", f"primero={codigos[0]}")
check("login bloquea tras varios fallos", "429" in codigos, f"codigos={codigos}")

print("\nP1  Los 500 de manual-edit")
casos = [
    ("fecha invalida", '{"employeeId":"%s","dateStr":"no-es-fecha","edits":{"entrada":"09:00"}}' % emp_id),
    ("hora 99:99", '{"employeeId":"%s","dateStr":"2026-09-08","edits":{"entrada":"99:99"}}' % emp_id),
    ("tipo invalido", '{"employeeId":"%s","dateStr":"2026-09-08","edits":{"inventado":"09:00"}}' % emp_id),
    ("empleado inexistente", '{"employeeId":"FANTASMA","dateStr":"2026-09-08","edits":{"entrada":"09:00"}}'),
]
for nombre, payload in casos:
    code = curl("-X", "POST", f"{B}/api/admin/manual-edit", *ADMIN,
                "-H", "Content-Type: application/json", "-d", payload, status=True)
    check(f"manual-edit {nombre} no da 500", code != "500", f"HTTP {code}")

print("\nP1  Limite de subida")
subprocess.run(["dd", "if=/dev/urandom", "of=/tmp/grande.png", "bs=1M", "count=20"],
               capture_output=True)
code = curl("-X", "POST", f"{B}/api/punch", "-F", "pin=1111", "-F", "type=comida_salida",
            "-F", "photo=@/tmp/grande.png;type=image/png", status=True)
check("foto de 20 MB es rechazada", code == "413", f"HTTP {code}")

print("\nP1  Indices y unicidad")
idx = psql("SELECT count(*) FROM pg_indexes WHERE tablename='records';")
check("records tiene indices", int(idx) >= 4, f"{idx} indices")
dup = subprocess.run(
    ["docker", "exec", PG_CONTAINER, "psql", "-U", PG_USER, "-d", PG_DB,
     "-c", f"INSERT INTO records (id,employee_id,employee_name,type,timestamp) "
           f"VALUES ('dup1','{emp_id}','Ana Torres','entrada',now());"],
    capture_output=True, text=True)
check("la BD rechaza dos marcas del mismo tipo el mismo dia",
      "duplicate key" in (dup.stderr + dup.stdout), (dup.stderr or dup.stdout)[:80])

print("\nSeguridad de datos")
cfg = jcurl(f"{B}/api/admin/config", *ADMIN)
check("config ya no expone el codigo de recuperacion", "recoveryCode" not in cfg, str(cfg)[:90])
logs = subprocess.run(["docker", "logs", BACKEND_CONTAINER],
                      capture_output=True, text=True)
check("los logs no imprimen el codigo de recuperacion",
      "recuperación de contraseña" not in (logs.stdout + logs.stderr))
# Desde otra IP, para no chocar con el bloqueo que dejaron las pruebas de fuerza
# bruta de arriba (el rate limit es por IP, y eso es justo lo que se quiere).
login = jcurl("-X", "POST", f"{F}/api/admin/login", "-H", f"X-Forwarded-For: {IP_LIMPIA}",
              "-H", "Content-Type: application/json",
              "-d", json.dumps({"password": ADMIN_PASS}))
if ESPERA_PASS_DE_FABRICA:
    check("avisa que la contrasena es la de fabrica",
          login.get("usingDefaultPassword") is True, str(login)[:90])
check("el bloqueo de fuerza bruta es por IP, no global",
      login.get("ok") is True, "una IP bloqueada no debe afectar a las demas")

print("\nEndurecimiento para internet (staging/produccion)")
docs = curl(f"{B}/docs", status=True)
openapi = curl(f"{B}/openapi.json", status=True)
if os.environ.get("CHECADOR_ESPERA_DOCS_CERRADOS") == "1":
    check("/docs esta cerrado", docs == "404", f"HTTP {docs}")
    check("/openapi.json esta cerrado", openapi == "404", f"HTTP {openapi}")
else:
    print(f"  (informativo) /docs -> HTTP {docs}, /openapi.json -> HTTP {openapi}")

print("\nIP real detras del proxy")
psql("DELETE FROM records; DELETE FROM device_alerts;")
curl("-X", "POST", f"{F}/api/admin/employees", *ADMIN,
     "-F", "name=Beto Ruiz", "-F", "pin=2222", "-F", "category=trabajador",
     "-F", f"photo=@{FOTO};type=image/png")
for pin, ip in (("1111", "192.168.1.50"), ("2222", "192.168.1.77")):
    curl("-X", "POST", f"{F}/api/punch", "-H", f"X-Forwarded-For: {ip}",
         "-F", f"pin={pin}", "-F", "type=entrada", "-F", f"photo=@{FOTO};type=image/png")
    time.sleep(0.2)
ips = psql("SELECT DISTINCT source_ip FROM records;").split()
check("se guarda la IP real del celular, no la de nginx",
      "192.168.1.50" in ips and "192.168.1.77" in ips, f"ips={ips}")
alerts = jcurl(f"{F}/api/admin/device-alerts", *ADMIN).get("alerts", [])
check("no hay falso positivo de dispositivo compartido", len(alerts) == 0,
      f"{len(alerts)} alerta(s)")

print(f"\n{'='*54}")
print(f"  {len(pasadas)} pasadas, {len(fallos)} fallas")
for f in fallos:
    print(f"   - {f}")
sys.exit(1 if fallos else 0)
