"""Reloj del sistema, siempre en la zona horaria de la oficina.

Todo el codigo debe pedir la hora aqui y nunca llamar a `datetime.now()` directo:
un `datetime.now()` sin zona toma la del proceso, que dentro del contenedor es UTC
salvo que alguien recuerde poner `TZ`. Eso ya rompio la nomina una vez (las
jornadas que terminaban despues de las 17:00 cruzaban de dia en UTC y se
contabilizaban como cero horas trabajadas mas una falta falsa).

La oficina esta en Mazatlan (MST, -0700, sin horario de verano desde 2022), que
NO comparte hora con Ciudad de Mexico (CST, -0600). `OFFICE_TZ` es configurable
por si el checador se instala en otra plaza.

Los `datetime` que devuelven estas funciones son *naive* a proposito: las
columnas son `TIMESTAMP WITHOUT TIME ZONE` y mezclar naive con aware revienta al
compararlos. Lo que garantizamos es que ese naive representa hora local de la
oficina, no UTC.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .config import settings


def tz() -> ZoneInfo:
    return ZoneInfo(settings.office_tz)


def now() -> datetime:
    """Hora local de la oficina, naive (sin tzinfo) para guardar en la BD."""
    return datetime.now(tz()).replace(tzinfo=None)


def today() -> date:
    """Fecha de hoy en la oficina. Distinta de la fecha UTC despues de las 17:00."""
    return now().date()
