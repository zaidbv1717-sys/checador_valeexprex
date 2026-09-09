"""Verifica que cada hallazgo P0/P1 de AUDITORIA.md quedo corregido.

Cada prueba reproduce el ataque o el error original y exige el comportamiento
nuevo. Correr con el stack levantado:

    python3 scripts/verifica_arreglos.py
"""

import json
import subprocess
import sys
import time

B = "http://localhost:18000"     # backend directo
F = "http://localhost:18080"     # a traves de nginx
ADMIN = ["-H", "X-Admin-Pass: 1234"]
FOTO = "reloj_checador.ico"

fallos = []
pasadas = []


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
        ["docker", "exec", "reloj_checador_postgres", "psql", "-U", "reloj",
         "-d", "reloj_checador", "-t", "-c", sql],
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
    ["docker", "exec", "reloj_checador_backend", "date", "+%H"],
    capture_output=True, text=True).stdout.strip()
check("host y contenedor comparten hora", hora_host == hora_cont,
      f"host={hora_host} cont={hora_cont}")

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
check("la hora guardada es local", hora_bd == hora_host, f"bd={hora_bd} host={hora_host}")

print("\nP0-4  Rate limiting")
# Cada bloque usa su propia IP simulada: el limite es por IP, asi que reutilizar
# una ya bloqueada por el bloque anterior daria un 429 enganoso.
codigos = [curl("-X", "POST", f"{F}/api/verify-pin", "-H", "X-Forwarded-For: 10.1.0.1",
                "-H", "Content-Type: application/json",
                "-d", f'{{"pin":"9{i:03d}"}}', status=True) for i in range(8)]
check("verify-pin bloquea tras varios fallos", "429" in codigos, f"codigos={codigos}")

codigos = [curl("-X", "POST", f"{F}/api/admin/login", "-H", "X-Forwarded-For: 10.1.0.2",
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
    ["docker", "exec", "reloj_checador_postgres", "psql", "-U", "reloj", "-d", "reloj_checador",
     "-c", f"INSERT INTO records (id,employee_id,employee_name,type,timestamp) "
           f"VALUES ('dup1','{emp_id}','Ana Torres','entrada',now());"],
    capture_output=True, text=True)
check("la BD rechaza dos marcas del mismo tipo el mismo dia",
      "duplicate key" in (dup.stderr + dup.stdout), (dup.stderr or dup.stdout)[:80])

print("\nSeguridad de datos")
cfg = jcurl(f"{B}/api/admin/config", *ADMIN)
check("config ya no expone el codigo de recuperacion", "recoveryCode" not in cfg, str(cfg)[:90])
logs = subprocess.run(["docker", "logs", "reloj_checador_backend"],
                      capture_output=True, text=True)
check("los logs no imprimen el codigo de recuperacion",
      "recuperación de contraseña" not in (logs.stdout + logs.stderr))
# Desde otra IP, para no chocar con el bloqueo que dejaron las pruebas de fuerza
# bruta de arriba (el rate limit es por IP, y eso es justo lo que se quiere).
login = jcurl("-X", "POST", f"{F}/api/admin/login", "-H", "X-Forwarded-For: 10.0.0.9",
              "-H", "Content-Type: application/json", "-d", '{"password":"1234"}')
check("avisa que la contrasena es la de fabrica",
      login.get("usingDefaultPassword") is True, str(login)[:90])
check("el bloqueo de fuerza bruta es por IP, no global",
      login.get("ok") is True, "una IP bloqueada no debe afectar a las demas")

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
