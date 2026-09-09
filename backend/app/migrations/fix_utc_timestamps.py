"""Corrige de una sola vez los timestamps que se guardaron en UTC.

Contexto: hasta el arreglo de zona horaria, el backend corria con `TZ` sin definir
dentro del contenedor (UTC) y llamaba a `datetime.now()` sin zona, asi que las
marcas quedaron guardadas 7 horas adelantadas respecto a la hora real de Mazatlan.
Efecto en nomina: las jornadas que terminaban despues de las 17:00 cruzaban de dia
y se contabilizaban como cero horas trabajadas mas una falta falsa.

Esta migracion resta ese desfase a las marcas anteriores al arreglo. Es idempotente
por marca de control en la tabla `config` (`tz_migration_done`): correrla dos veces
no vuelve a restar.

Uso:
    # 1. Ver que haria, sin tocar nada (SIEMPRE primero)
    docker exec reloj_checador_backend python -m app.migrations.fix_utc_timestamps --dry-run

    # 2. Aplicar
    docker exec reloj_checador_backend python -m app.migrations.fix_utc_timestamps --apply

Antes de aplicar se hace un respaldo automatico con pg_dump. El corte
(`--cutoff`) por defecto es el momento de correr la migracion: todo registro
anterior se considera escrito por el codigo con el bug.
"""

import argparse
import sys
from datetime import datetime, timedelta

from sqlalchemy import text

from .. import clock
from ..backup import backup_now
from ..database import SessionLocal

CONTROL_KEY = "tz_migration_done"

# Columnas afectadas: todo lo que se escribio con datetime.now() naive.
TARGETS = [
    ("records", "timestamp"),
    ("device_alerts", "created_at"),
    ("device_alerts", "emp1_time"),
    ("device_alerts", "emp2_time"),
    ("justifications", "created_at"),
]


def _offset_hours(reference: datetime) -> float:
    """Desfase real entre UTC y la oficina en esa fecha, positivo.

    Se calcula con la zona configurada en vez de fijar 7 horas, para que siga
    siendo correcto si el checador se instala en una plaza con horario de verano.
    """
    aware = reference.replace(tzinfo=clock.tz())
    utcoffset = aware.utcoffset()
    if utcoffset is None:
        raise RuntimeError("No se pudo determinar el desfase de la zona horaria")
    return -utcoffset.total_seconds() / 3600


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="solo reporta, no escribe")
    group.add_argument("--apply", action="store_true", help="aplica la correccion")
    parser.add_argument(
        "--cutoff",
        default=None,
        help="ISO datetime; solo se corrigen registros anteriores. Default: ahora",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="corre aunque la migracion ya se haya aplicado antes",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        already = db.execute(
            text("SELECT value FROM config WHERE key = :k"), {"k": CONTROL_KEY}
        ).scalar()
        if already and not args.force:
            print(f"La migracion ya se aplico el {already}. Usa --force para repetirla.")
            return 1

        cutoff = datetime.fromisoformat(args.cutoff) if args.cutoff else clock.now()
        offset = _offset_hours(cutoff)
        delta = timedelta(hours=offset)
        print(f"Zona de la oficina: {clock.tz()}  |  desfase a restar: {offset:g} h")
        print(f"Corte: registros con fecha < {cutoff:%Y-%m-%d %H:%M:%S}\n")

        total = 0
        for table, column in TARGETS:
            rows = db.execute(
                text(f"SELECT count(*) FROM {table} WHERE {column} IS NOT NULL AND {column} < :c"),
                {"c": cutoff},
            ).scalar() or 0
            total += rows
            print(f"  {table}.{column}: {rows} registro(s)")

        if total == 0:
            print("\nNo hay nada que corregir.")
            return 0

        # Muestra el efecto sobre las marcas reales, que es lo que le importa a nomina.
        sample = db.execute(
            text("SELECT employee_name, type, timestamp FROM records "
                 "WHERE timestamp < :c ORDER BY timestamp DESC LIMIT 5"),
            {"c": cutoff},
        ).all()
        if sample:
            print("\n  Ejemplo del cambio en records:")
            for name, ptype, ts in sample:
                print(f"    {name} {ptype}: {ts:%Y-%m-%d %H:%M} -> {ts - delta:%Y-%m-%d %H:%M}")

        if args.dry_run:
            print(f"\n[DRY-RUN] Se corregirian {total} registro(s). Nada fue modificado.")
            return 0

        print("\nRespaldando antes de escribir...")
        dest = backup_now()
        print(f"  respaldo: {dest or 'NO SE PUDO (pg_dump no disponible)'}")
        if not dest:
            print("  Abortado: no se aplica una migracion sin respaldo previo.")
            return 1

        for table, column in TARGETS:
            db.execute(
                text(f"UPDATE {table} SET {column} = {column} - :d "
                     f"WHERE {column} IS NOT NULL AND {column} < :c"),
                {"d": delta, "c": cutoff},
            )
        db.execute(
            text("INSERT INTO config (key, value) VALUES (:k, :v) "
                 "ON CONFLICT (key) DO UPDATE SET value = :v"),
            {"k": CONTROL_KEY, "v": clock.now().isoformat(timespec="seconds")},
        )
        db.commit()
        print(f"\nListo: {total} registro(s) corregidos.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
