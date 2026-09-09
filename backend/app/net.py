"""IP real del cliente, incluso detras del proxy.

`request.client.host` devuelve la IP de quien abrio la conexion TCP. En el
despliegue real el frontend va detras de nginx, asi que esa IP es SIEMPRE la del
contenedor de nginx y es identica para todos los empleados. Eso rompia dos cosas:

- La deteccion de dispositivo compartido generaba falsos positivos: dos empleados
  con celulares distintos aparecian marcando "desde el mismo aparato" y se
  levantaba una alerta de fraude contra gente honesta.
- El rate limiting por IP habria agrupado a toda la oficina en un solo cubo,
  dejando que un empleado bloqueara a los demas.

nginx ya envia `X-Forwarded-For` (ver frontend/nginx.conf). Tomamos la primera
entrada de la lista, que es el cliente original.

Nota de seguridad: confiar en `X-Forwarded-For` solo es correcto porque el
backend no deberia ser alcanzable directamente. Un cliente puede falsificar el
header, asi que esto sirve para distinguir dispositivos en una LAN de confianza,
no como control de seguridad fuerte.
"""

from fastapi import Request


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real
    return request.client.host if request.client else ""
