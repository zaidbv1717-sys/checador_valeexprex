"""Demuestra el bug P0 de zona horaria contra el sistema real.

Inyecta en la base una jornada de 9.5 horas guardada de las dos formas posibles
(como la guarda el codigo hoy, en UTC naive, y como deberia guardarla en hora
local) y pide el reporte de nomina en cada caso.

Requiere el stack levantado y la contrasena de admin por defecto. Ajusta B si
usas otro puerto. ATENCION: borra la tabla `records`, correr solo contra una
base de pruebas.

Salida esperada mientras el bug siga vivo:
    A) CON EL BUG    -> TOTAL HORAS PAGADAS: 0.0
    B) CON TZ CORRECTA -> TOTAL HORAS PAGADAS: 9.5
Sale con codigo 0 si el bug se reproduce, 1 si ya esta arreglado.
"""

import json
import subprocess
import sys

B = "http://localhost:18000"
H = ["-H", "X-Admin-Pass: 1234"]


def psql(sql):
    subprocess.run(
        ["docker", "exec", "reloj_checador_postgres",
         "psql", "-U", "reloj", "-d", "reloj_checador", "-q", "-c", sql],
        check=True, capture_output=True,
    )


def reporte():
    out = subprocess.run(
        ["curl", "-s", f"{B}/api/admin/records?period=mes", *H],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)["rows"]


def muestra(titulo, rows):
    print(titulo)
    if not rows:
        print("  (sin filas)")
    for r in rows:
        print(f"  {r['date']}  ent={r['entrada'] or '--'}  sal={r['salida'] or '--'}"
              f"  horas={r['hours']}  sin_marca={r['missing']}")
    print(f"  TOTAL HORAS PAGADAS: {sum(r['hours'] for r in rows)}")
    print()


emp = json.loads(subprocess.run(
    ["curl", "-s", f"{B}/api/admin/employees", *H],
    check=True, capture_output=True, text=True,
).stdout)["employees"][0]["id"]

print("Jornada real del empleado: 8 sep, 08:30 -> 18:00 = 9.5 horas\n")

# Caso A: como lo guarda el codigo con el bug (instante convertido a UTC, naive)
psql("DELETE FROM records;")
psql(f"""INSERT INTO records (id, employee_id, employee_name, type, timestamp) VALUES
 ('bug1','{emp}','Ana Torres','entrada','2026-09-08 15:30:00'),
 ('bug2','{emp}','Ana Torres','salida', '2026-09-09 01:00:00');""")
rows_bug = reporte()
muestra("A) CON EL BUG (timestamps en UTC naive):", rows_bug)

# Caso B: mismos instantes reales, guardados en hora local
psql("DELETE FROM records;")
psql(f"""INSERT INTO records (id, employee_id, employee_name, type, timestamp) VALUES
 ('ok1','{emp}','Ana Torres','entrada','2026-09-08 08:30:00'),
 ('ok2','{emp}','Ana Torres','salida', '2026-09-08 18:00:00');""")
rows_ok = reporte()
muestra("B) CON TZ CORRECTA (timestamps en hora local):", rows_ok)

pagadas_bug = sum(r["hours"] for r in rows_bug)
pagadas_ok = sum(r["hours"] for r in rows_ok)
print(f"VEREDICTO: el bug paga {pagadas_bug} h de una jornada de {pagadas_ok} h.")
print(f"Filas 'Sin marca' falsas generadas por el bug: "
      f"{sum(1 for r in rows_bug if r['missing'])} (correcto: "
      f"{sum(1 for r in rows_ok if r['missing'])})")

sys.exit(0 if pagadas_bug != pagadas_ok else 1)
