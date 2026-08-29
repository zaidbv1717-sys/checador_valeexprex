# Reloj checador — versión simple (sin cámara, sin código de acceso)

Corre completo en la computadora del negocio. No necesita internet, no necesita
instalar nada más que Python (que ya viene en Mac y Linux; en Windows se instala
gratis desde la Microsoft Store buscando "Python"). No usa cámara ni código de
acceso dinámico, así que tampoco necesita HTTPS ni paquetes extra.

## Cómo arrancarlo (manual)

1. Copia esta carpeta completa a la computadora del negocio.
2. Abre una terminal dentro de la carpeta.
3. Ejecuta:

   ```
   python server.py
   ```

   (en Mac/Linux puede ser `python3 server.py`)

4. La terminal te muestra dos direcciones:
   - `http://localhost:5000` — para configurar todo desde esta computadora.
   - `http://<tu-ip-local>:5000` — la que va en el código QR para los celulares.

5. Deja la terminal abierta mientras el sistema esté en uso.

## Que arranque solo al prender la computadora (Windows)

Ya viene incluido el archivo `iniciar_reloj_checador.bat` en esta carpeta —
hace lo mismo que el paso manual, pero con doble click.

1. Presiona **Windows + R**, escribe `shell:startup` y da Enter — se abre la
   carpeta de Inicio de Windows.
2. Haz **click derecho** sobre `iniciar_reloj_checador.bat` (en la carpeta del
   sistema) → **Crear acceso directo**.
3. Arrastra ese acceso directo a la carpeta de Inicio que abriste en el paso 1
   (o cópialo y pégalo ahí).
4. Listo. La próxima vez que prendas la computadora y abras sesión, se va a
   abrir solo una ventana negra con el sistema ya corriendo.

**Notas:**
- Esa ventana negra debe quedarse abierta — es el servidor. Si la cierras, el
  sistema se detiene (pero puedes volver a abrirlo con el mismo acceso directo
  cuando quieras).
- Si prefieres que no aparezca ninguna ventana visible al iniciar, dime y te
  preparo una versión oculta — pero entonces no vas a poder leer el código de
  recuperación ni la IP directo de la pantalla; tendrías que verlos desde la
  pestaña Config una vez adentro.

## Primeros pasos

1. Entra a `http://localhost:5000/`, toca **Admin** (contraseña inicial `1234`,
   cámbiala en Config).
2. En **Empleados**, da de alta a cada trabajador con su PIN de 4 dígitos y su
   horario esperado (para calcular retardos y horas extra).
3. En **Código QR** copia/genera el QR con el enlace correcto para imprimir.
4. Los celulares deben estar en la misma red WiFi que esta computadora.

## Qué trae esta versión

- PIN de 4 dígitos para identificarse.
- Marcar por etapas, en orden fijo: Entrada → Salida a comer → Regreso de comer
  → Salida. El empleado solo ve el siguiente paso pendiente, uno a la vez, y
  el sistema regresa a la pantalla de PIN después de cada marca.
- Cada marca queda fija una vez hecha — si el empleado la vuelve a intentar, el
  sistema la rechaza. Solo el administrador puede corregir un registro
  (pestaña Registros → ícono ✎).
- Cálculo automático de retardos (10 min de tolerancia), horas extra y tiempo
  de comida excedido (90 min por defecto).
- Aviso de marcas faltantes (entrada sin salida o viceversa).
- Reportes por día, semana o mes, con exportación a CSV agrupada por empleado,
  con totales al final.
- Recuperación de contraseña desde la propia pantalla de acceso, usando un
  código de recuperación (visible en Config, y también impreso en la terminal
  cada vez que arrancas el servidor). Guárdalo en un lugar seguro.
- Respaldo automático de la base de datos al arrancar y cada 24 horas,
  conservando los últimos 30, en `data/backups/`.
- Detección silenciosa de dispositivo compartido: si dos empleados distintos
  marcan entrada desde el mismo aparato en menos de 5 minutos, el sistema
  genera una alerta que solo ve el administrador en Registros — el empleado
  nunca se entera de que quedó marcado.
- Aviso de faltas completas: si un empleado no registró ninguna entrada en un
  día ya concluido (excluyendo domingos), aparece como falta en Registros —
  a menos que ese día esté cubierto por un permiso aprobado.
- Permisos, incapacidades y vacaciones (pestaña Permisos): registra el
  resultado de lo que ya se resolvió por WhatsApp según tu política — médica,
  personal, permiso económico o vacaciones, con fecha de inicio y fin, y
  estado (pendiente/aprobada/rechazada). Un permiso aprobado hace que esos
  días dejen de contar como falta sin justificar.
- Nota opcional en cualquier día: desde Registros → editar, se puede agregar
  un comentario libre a la asistencia de un empleado en una fecha específica
  (por ejemplo, "llegó con permiso para retirarse temprano").
- Calendario visual por empleado (pestaña Calendario): elige a alguien y ve su
  mes completo en colores — verde (asistió), rojo (falta), amarillo (permiso
  justificado) y gris (día no laboral, o el día de hoy si aún no marca).
  Navega entre meses con las flechas.

## Respaldo de tus datos

**Automático (ya viene incluido):** cada vez que arrancas el servidor, y luego una
vez al día mientras sigue corriendo, el sistema copia tu base de datos a
`data/backups/` con la fecha y hora en el nombre. Guarda los últimos 30
respaldos y borra los más viejos solo. Esto te protege si la base de datos
principal se corrompe o alguien la borra sin querer.

**Manual (hazlo tú, de vez en cuando):** el respaldo automático vive en la
MISMA computadora — si la computadora se descompone, se pierde también. Para
estar realmente protegido, copia la carpeta `data/` completa a un USB o a una
carpeta de Google Drive/Dropbox una vez por semana (o con la frecuencia que
prefieras). Es tan simple como copiar y pegar la carpeta.

## Dónde viven tus datos

- `data/attendance.db` — base de datos con empleados y registros.
- `data/backups/` — respaldos automáticos diarios.
