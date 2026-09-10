# Auditoría de código — Reloj Checador

**Fecha:** 2026-09-09
**Repo:** `github.com/Capitalcontinental/Checador` (rama `main`, commit `032e351`)
**Contraste:** `stack-capitalcontinental/03_STACK_TECNICO.md` y `capitalcontinental/AGENTS.md`
**Método:** lectura de los 1,451 LOC de backend y 2,112 LOC de frontend, más pruebas
ejecutadas contra el stack levantado en Docker (puertos 18000/18080/55432 para no chocar
con el Postgres local).

Todo lo marcado como "verificado" trae el comando y la salida real que lo demuestra.

---

## Veredicto

El código está **bien escrito y bien organizado** (módulos chicos, nombres claros,
comentarios en español que explican el porqué). El problema no es el estilo, son dos cosas:

1. **El reporte de nómina no sirve hoy.** Por un bug de zona horaria, toda jornada que
   termine después de las 17:00 se contabiliza como **0 horas trabajadas** y genera una
   falta falsa. Verificado contra el sistema: una jornada real de 9.5 h se paga como 0 h.
2. **La seguridad del checador es aparente, no real.** Cualquier empleado puede marcar por
   otro sin conocer su PIN, verificado con una sola llamada HTTP.

Reproducir el punto 1: `python3 scripts/prueba_bug_zona_horaria.py` con el stack levantado.

| Dimensión | Estado |
|---|---|
| Organización y legibilidad | Bien |
| Alineación al stack de la empresa | Diverge (Python/FastAPI vs Node/Express) |
| Seguridad | **Insuficiente para producción** |
| Corrección de datos | **Bug P0 activo (zona horaria)** |
| Pruebas y CI | Inexistentes |
| Operación (backups, arranque) | Aceptable para el alcance |


---

## Estado: corregido el 2026-09-09 (commit `1a9f926`)

Los hallazgos P0 y los P1 mas graves quedaron arreglados y verificados. Lo que
sigue en este documento es el diagnostico original, que se conserva como
referencia de por que se hizo cada cambio.

| # | Hallazgo | Estado |
|---|---|---|
| 1 | Zona horaria | Corregido: `app/clock.py` + `TZ`/`OFFICE_TZ` + migracion de datos |
| 2 | Marcar por otro sin PIN | Corregido: el empleado se deriva del PIN en el servidor |
| 3 | PIN sin limite de intentos | Corregido: rate limit en `verify-pin` y `punch` |
| 4 | `rate_limit.py` sin usar | Corregido: activo en `verify-pin`, `login` y `recover` |
| 5 | 500 en `manual-edit` | Corregido: validacion Pydantic real (`date`, `Literal`, patron HH:MM) |
| 6 | Fotos huerfanas | Corregido: se borra la foto si el insert falla |
| 7 | Subidas sin limite | Corregido: 8 MB en el backend, 10 MB en nginx |
| 8 | Sin indices | Corregido: tres indices en `records` |
| 9 | Sin UNIQUE por marca diaria | Corregido: indice unico sobre `(employee_id, type, date)` |
| 11 | `/config` filtraba el codigo de recuperacion | Corregido: solo se muestra al generarlo |
| 12 | Login devolvia 200 al fallar | Corregido: 401 |
| 16 | El aviso de contrasena por defecto nunca salia | Corregido: se compara contra el hash |
| 17 | Falsos positivos de dispositivo compartido | Corregido: `app/net.py` lee `X-Forwarded-For` |
| 18 | `npm install`, sin cabeceras en nginx | Corregido: `npm ci`, cabeceras y gzip |
| 20 | `api<T = any>` y errores de red sin manejar | Corregido: el cliente ya no cuelga la UI |

Verificacion: `python3 scripts/verifica_arreglos.py` (22 de 22 desde base limpia).

**Sigue abierto:** el PIN se guarda en texto plano (#3, parte de almacenamiento),
sesion admin sin JWT con bcrypt en cada request (#10), N+1 en los reportes (#8),
migraciones sin Alembic (#14), sin tests ni CI (#15), contrasena por defecto
`1234` (#16), `/docs` publico (#18), retencion de fotos (#7), `on_event`
deprecado y `except Exception: pass` (#20).

---

## P0 — Rompe los datos hoy

### 1. Zona horaria: todas las horas están corridas 7 horas

El contenedor corre en UTC y el código usa `datetime.now()` sin zona horaria (12 usos, y
cero menciones de `ZoneInfo`, `timezone` o `tzinfo` en todo el backend).
Una entrada real de las **14:03 hora de México** se guarda y se reporta como **21:03**.

Verificado:

```
$ date                                  # host
mié 09 sep 2026 14:04:15 MST
$ docker exec reloj_checador_backend date
Wed Sep  9 21:04:15 UTC 2026

$ curl -s "$B/api/admin/records?period=dia" -H 'X-Admin-Pass: 1234'
"entrada": "21:03",
"retardoMin": 754,
"hours": 0.02,
```

**754 minutos de retardo inventados** sobre un empleado con entrada esperada 08:30.

Pero el daño caro no es el retardo: entre las 17:00 y las 23:59 hora local, `date(timestamp)`
cae en el **día siguiente** en UTC, y como `rows.py` agrupa por `(employee_id, date)`, la
entrada y la salida de una misma jornada caen en **dos filas distintas**, cada una sin su
pareja, cada una con 0 horas.

Verificado inyectando en la base una jornada tal como la guarda el código con el bug
(8 sep, 08:30 a 18:00 hora local = 9.5 h reales) y pidiendo el reporte de nómina:

```
A) CON EL BUG (timestamps en UTC naive):
  2026-09-09  ent=--     sal=01:00  horas=0.0  sin_marca=False
  2026-09-08  ent=15:30  sal=--     horas=0.0  sin_marca=True
  TOTAL HORAS PAGADAS: 0.0

B) CON TZ CORRECTA (timestamps en hora local):
  2026-09-08  ent=08:30  sal=18:00  horas=9.5  sin_marca=False
  TOTAL HORAS PAGADAS: 9.5

VEREDICTO: el bug paga 0.0 h de una jornada de 9.5 h.
```

Es decir: **toda jornada que termine después de las 17:00 se paga como cero horas** y además
genera una falta falsa. Con salida a las 18:00, eso es todos los días de todos los empleados.

Archivos: `app/routers/public.py:78`, `app/routers/records.py:61`, `app/alerts.py:24`,
`app/reports/rows.py:31`, `app/reports/absences.py:15`, `app/reports/calendar.py:12`,
`app/backup.py:16`, `app/main.py`.

**Arreglo verificado.** La zona correcta es **`America/Mazatlan`**, no `America/Mexico_City`:
la computadora donde corre el checador está en `America/Mazatlan` (MST, -0700), y CDMX está
en CST (-0600), así que poner CDMX dejaría el reloj **una hora adelantado**. Confirmado:

```
$ timedatectl
  Time zone: America/Mazatlan (MST, -0700)

# con TZ: America/Mazatlan en el servicio backend
host: 14:11:28 MST
cont: 14:11:28 MST          <- coinciden

$ curl -X POST $B/api/punch ...
{"ok":true,"time":"14:11:29"}
$ curl "$B/api/admin/records?period=dia"
"entrada": "14:11",  "retardoMin": 341     <- correcto (08:30 a 14:11 = 341 min)
```

Parche inmediato: `TZ: America/Mazatlan` en el `environment:` del backend en
`docker-compose.yml`. **Antes de aplicarlo hay que confirmar en qué ciudad opera la oficina**,
porque si es CDMX la respuesta es otra y el reloj del host es el que está mal.
Arreglo de fondo: `datetime.now(ZoneInfo(...))` con columnas `TIMESTAMPTZ`.

### 2. Cualquiera puede marcar por cualquiera (sin PIN)

`POST /api/punch` **no valida ninguna credencial**. Recibe `employeeId` y `employeeName`
como campos de formulario y confía en ellos. El PIN se verifica en un endpoint aparte
(`/api/verify-pin`) cuyo resultado vive solo en el estado de React, así que la validación
es puramente de fachada.

Verificado (marca de asistencia falsa, sin conocer el PIN):

```
$ curl -X POST $B/api/punch -F "employeeId=07874851d861" \
    -F 'employeeName=Juan Perez' -F 'type=entrada' -F 'photo=@foto.png'
{"ok":true,"time":"21:03:36"}
```

Un empleado que abra las DevTools o que copie el `employeeId` de un compañero marca por él
desde su casa. La foto obligatoria no lo impide: el endpoint acepta cualquier imagen,
incluida una guardada previamente.

**Arreglo:** exigir el PIN en el mismo `POST /api/punch` y verificarlo del lado del
servidor antes de insertar, o emitir un token de un solo uso y corta duración desde
`/verify-pin`.

### 3. El PIN es la contraseña y se guarda y se muestra en texto plano

`Employee.pin = Column(String(4))` sin hash. El endpoint de administración lo devuelve
tal cual y la UI lo imprime en pantalla (`EmployeesTab.tsx:157`, `PIN {e.pin}`).

```
$ curl -s $B/api/admin/employees -H 'X-Admin-Pass: 1234'
{"employees":[{"id":"07874851d861","name":"Juan Perez","pin":"1111",...}]}
```

Además `verify-pin` no tiene límite de intentos: **10,000 combinaciones posibles y ningún
freno**. Verificado, 10 intentos consecutivos, todos HTTP 200 en menos de un segundo.

Peor: el PIN es `unique` en toda la tabla, así que el espacio real se reduce conforme se
dan de alta empleados, y `verify-pin` devuelve **nombre e id del empleado** al acertar, lo
que convierte la fuerza bruta en un enumerador de plantilla.

### 4. `rate_limit.py` existe pero nadie lo llama

El módulo está completo y correcto (ventana de 5 minutos, 5 intentos, con `Lock`). No hay
una sola importación. El commit `142af30` lo desactivó "por ahora" y quedó así.

```
$ grep -rn "rate_limit\|is_locked" --include="*.py" .
./backend/app/rate_limit.py:12:def is_locked(...)     # solo su propia definición
```

Consecuencia verificada: 20 intentos de login de admin, ningún 429.

Sin rate limit, la contraseña de admin (mínimo 4 caracteres, default `1234`) y el código de
recuperación de 8 caracteres son ataques de minutos, no de años.

---

## P1 — Falla o corrompe bajo condiciones normales

### 5. `manual-edit` responde 500 con entradas inválidas

Ninguna validación de formato. Tres casos probados, tres 500:

```
dateStr:"no-es-fecha"        -> HTTP 500   (ValueError de strptime)
edits:{"entrada":"99:99"}    -> HTTP 500   (hour must be in 0..23)
employeeId:"FANTASMA"        -> HTTP 500   (ForeignKeyViolation)
```

El problema de fondo: los schemas Pydantic **desactivan la validación** que Pydantic da
gratis. Todos los campos son `str = ""` sin restricciones, así que las peticiones inválidas
pasan el borde y explotan en la capa de base de datos. `ManualEditRequest.dateStr` debería
ser un `date`, y `edits` un `dict[Literal[...], time]`.

### 6. `/api/punch` deja archivos huérfanos al fallar

La foto se escribe en disco **antes** del `db.commit()` (`public.py:109-116`). Si el insert
falla, el archivo queda. Verificado: `hacker_anonimo_entrada_...png` (109 KB) quedó en
`data/punch_photos/` de un punch que terminó en 500.

Además no hay transacción: `check_device_alert` hace su propio `commit` después
(`public.py:119`), así que un fallo ahí deja el registro sin su alerta.

### 7. Subidas sin límite de tamaño

`photo.read()` carga el archivo completo en RAM y lo escribe sin verificar tamaño ni que
sea realmente una imagen (solo se confía en el `Content-Type`, que lo pone el cliente).

Verificado, 60 MB aceptados sin queja:

```
$ head -c 60000000 /dev/urandom > big.png
$ curl -X POST $B/api/punch ... -F 'photo=@big.png;type=image/png'
HTTP 200
-rw-r--r-- 1 root root 60000000 juan_perez_comida_entrada_...png
```

Nginx tampoco pone tope (`client_max_body_size` ausente). Con 15 empleados marcando 4 veces
al día, un disco lleno es cuestión de subir archivos grandes a propósito, o de un mes de
fotos sin rotación (**no hay política de retención para las fotos**, solo para los .sql).

### 8. Sin índices: la base escanea todo en cada consulta

Solo existen las llaves primarias y el `unique` del PIN. Verificado con `\di`. No hay
índice en `records.timestamp`, `records.employee_id` ni `records.type`, que son exactamente
las tres columnas por las que se filtra en cada reporte.

Junto a eso, tres consultas N+1 reales:

- `reports/rows.py:17` carga **la tabla `records` completa** en memoria en cada petición,
  y filtra por periodo en Python.
- `reports/absences.py:24,31` hace 2 queries por (empleado × día). Un mes con 15 empleados
  son ~900 queries por carga de la pestaña.
- `reports/calendar.py:16,28` hace hasta 2 queries por día del mes.
- `reports/photo_log.py:15` carga todos los registros con foto y filtra en Python.

Hoy con pocos registros no se nota. A un año de operación, la pestaña Registros se cae sola.

### 9. Falta constraint de unicidad en `records`

La regla "una marca de cada tipo por día" se aplica solo en código (`public.py:81-90`) con
un patrón consultar-luego-insertar. La prueba de concurrencia con dos peticiones
simultáneas pasó por suerte de timing, no por diseño: no hay `UNIQUE(employee_id, type,
date(timestamp))` que lo garantice.

### 10. `require_admin` corre bcrypt en cada petición

La contraseña viaja en el header `X-Admin-Pass` en **cada llamada** y se verifica con
bcrypt cada vez. Costo medido: **220 ms por petición**.

```
$ for i in 1 2 3 4 5; do curl -o /dev/null -w "%{time_total}s " $B/api/admin/employees -H 'X-Admin-Pass: 1234'; done
0.222713s 0.222856s 0.221447s 0.224385s 0.220355s
```

La pestaña Registros hace 4 llamadas al cargar, es decir ~900 ms solo en hashing. Y la
contraseña queda almacenada en memoria del navegador durante toda la sesión y se
retransmite constantemente sobre **HTTP sin cifrar**. El estándar de la casa usa JWT
(`03_STACK_TECNICO.md`, sección Seguridad); aquí no hay sesión ni expiración ni revocación.

### 11. `/admin/config` filtra el código de recuperación

```
$ curl -s $B/api/admin/config -H 'X-Admin-Pass: 1234'
{"lunchMinutes":"90","recoveryCode":"OHMG-UX62"}
```

Quien ya tenga la contraseña puede ver el código que sirve para restablecerla, lo que anula
su propósito como segundo factor de recuperación. También se imprime en los logs de arranque
del contenedor (`main.py:81`), donde queda visible con un `docker logs`.

### 12. `login` devuelve 200 en credenciales incorrectas

`{"ok": false}` con HTTP 200. Rompe la semántica HTTP, impide que un proxy o un WAF cuente
fallos de autenticación, y obliga al cliente a inspeccionar el cuerpo. Lo correcto es 401.

---

## P2 — Buenas prácticas y alineación con el stack

### 13. Divergencia de stack

| Capa | Estándar Capital Continental | Checador |
|---|---|---|
| Backend | Node 20 + Express 5 + TS + Prisma | **Python + FastAPI + SQLAlchemy** |
| Validación | Zod | Pydantic (sin usar sus validaciones) |
| Migraciones | `prisma migrate` | **`create_all` + `ALTER TABLE` a mano** |
| Auth | JWT + 2FA + RBAC | Header con contraseña en claro |
| Logs | Winston | **`print()`** |
| CI/CD | GitHub Actions + gitleaks | **Nada** |
| Frontend | React 19 + Vite + TanStack Query + Zustand | React 19 + Vite + `fetch` crudo |

FastAPI está bien elegido para el alcance y no vale la pena reescribirlo. Pero conviene
decidirlo de forma explícita y documentarlo, porque hoy es la única app de la empresa que
nadie más del equipo sabe operar. El frontend sí está alineado.

### 14. Migraciones improvisadas

`main.py:54-58` hace `create_all` y luego dos `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
en crudo, en cada arranque. Funciona hoy, pero no hay historial, no hay rollback y no hay
forma de saber en qué versión está una base. Con SQLAlchemy ya instalado, **Alembic** es la
respuesta estándar y son 20 minutos de configuración.

### 15. Sin tests ni CI

Cero archivos de prueba, cero workflows de GitHub Actions, sin `.gitattributes` (el
estándar lo exige tras el problema de CRLF/LF documentado en el diagnóstico interno) y sin
gitleaks. Los cinco cálculos de `reports/` (horas trabajadas, retardos, comida tardía,
faltas, quincenas) son lógica de nómina que produce números que alguien va a cobrar, y no
hay una sola prueba que los cubra. Un caso obvio sin cubrir: `period_range` con `quincena`
y `anchor.day == 31` en meses de 30 días.

### 16. Contraseña por defecto `1234` que nunca caduca

`config.py:13` y `.env.example`. Existe un banner que avisa, pero la lógica que lo activa
está mal: `usingDefaultPassword` es `stored_hash is None`, y como el arranque **siempre**
siembra el hash, el valor es siempre `false` aunque la contraseña siga siendo `1234`.

```
$ curl -X POST $B/api/admin/login -d '{"password":"1234"}'
{"ok":true,"usingDefaultPassword":false}     # <- debería ser true
```

El aviso nunca aparece. `auth.py:22`.

### 17. `X-Forwarded-For` ignorado: la detección de dispositivo compartido no sirve

`public.py:77` usa `request.client.host`. Detrás de nginx eso es siempre la IP del
contenedor de nginx, idéntica para todos los empleados. Verificado en la base:

```
 juan_perez | entrada       | 172.20.0.1   <- directo al backend
 juan_perez | comida_salida | 172.20.0.4   <- vía nginx (IP del proxy)
```

Nginx sí envía `X-Forwarded-For` (`nginx.conf:12`), pero el backend no lo lee. Resultado: en
el uso real, **todos los empleados comparten IP**. Verificado provocando el falso positivo:
dos empleados distintos, marcando desde dos celulares distintos (con `X-Forwarded-For`
diferente), a través de nginx:

```
 Ana_Torres    | 172.20.0.4        <- misma IP
 Beto_Ruiz     | 172.20.0.4        <- misma IP (la de nginx)

$ curl -s $F/api/admin/device-alerts -H 'X-Admin-Pass: 1234'
  1 alerta(s)
   FALSO POSITIVO: Ana_Torres vs Beto_Ruiz ip 172.20.0.4
```

No es que la función "no sirva": **acusa de fraude a empleados honestos**. En una oficina
donde varios llegan a la misma hora, genera una alerta por cada par. El arreglo es leer
`X-Forwarded-For` (nginx ya lo envía) y configurar `ProxyHeadersMiddleware` de uvicorn.

### 18. Detalles de infraestructura

- **`npm install` en el Dockerfile** (`frontend/Dockerfile:4`) ignora el lockfile. Debe ser
  `npm ci` para builds reproducibles.
- **Contenedores como root**: ningún `USER` en los dos Dockerfiles.
- **Sin headers de seguridad en nginx**: no hay `X-Frame-Options`, `X-Content-Type-Options`
  ni CSP. Sin `gzip` tampoco.
- **CORS abierto**: `allow_origins=["*"]` con todos los métodos (`main.py:20`).
- **`/docs` y `/openapi.json` públicos**: HTTP 200 sin autenticación. Todo el mapa de la API
  regalado.
- **Backend expuesto en `0.0.0.0:8000`**: correcto haber cerrado Postgres a `127.0.0.1`
  (commit `fe89bf5`), pero el backend sigue accesible desde toda la red WiFi, saltándose
  nginx y quedando fuera de cualquier control que se ponga en el proxy.

### 19. Backups: mejor que el estándar, pero no probados

El respaldo automático diario con `pg_dump` está bien hecho y verificado funcionando
(5,651 bytes de SQL válido). Es más de lo que tiene el monorepo principal, donde los
backups manuales son el riesgo P0 abierto.

Faltan tres cosas: la **restauración nunca se probó**, las copias viven en el **mismo disco**
que la base, y `backup_loop` usa `time.sleep(86400)` que se desfasa con cada reinicio (si la
computadora se apaga cada noche, el respaldo puede no correr nunca en su ciclo diario, solo
en el de arranque).

### 20. Deuda menor

- `@app.on_event("startup")` está deprecado en FastAPI; usar `lifespan`.
- `except Exception: pass` en `backup.py:39` traga cualquier error del respaldo en silencio.
- `tsconfig.app.json` **no activa `strict`**. Es el default de Vite y nadie lo revisó.
- 7 warnings de oxlint, todos `set-state-in-effect` (`EmployeesTab.tsx`, `RecordsTab.tsx`,
  `PhotoModal.tsx`, `EmployeePhoto.tsx`).
- `api<T = any>` en `client.ts:11` desactiva el chequeo de tipos en cada llamada, y **ningún
  error de red se maneja**: un `fetch` fallido lanza una excepción no capturada que deja la
  UI colgada sin mensaje.
- `key={i}` por índice en `RecordsTab.tsx:199`.
- Commits en inglés; el estándar de la casa exige español y Conventional Commits con ticket
  (`AGENTS.md`, regla 5). Sin `.gitattributes`.
- Las etiquetas de categorías y tipos de marca están triplicadas: `routers/employees.py`,
  `reports/common.py` y `utils/format.ts`.
- `legacy/` son 39 KB de código muerto en la raíz del repo; su lugar es una etiqueta de git.

---

## Qué haría primero

| # | Acción | Esfuerzo |
|---|---|---|
| 1 | `TZ: America/Mazatlan` en el backend (confirmar antes la ciudad de la oficina), y decidir qué hacer con los datos ya corridos | 10 min + decisión |
| 2 | Exigir el PIN dentro de `POST /api/punch` y verificarlo en el servidor | 1 h |
| 3 | Reactivar `rate_limit` en `/verify-pin`, `/admin/login` y `/admin/recover` | 30 min |
| 4 | Validación real en los schemas Pydantic (`date`, `time`, `Literal`) para matar los 500 | 1 h |
| 5 | Índices en `records(employee_id, type, timestamp)` y `UNIQUE` por marca diaria | 30 min |

Después: hashear el PIN, límite de tamaño de subida, Alembic, tests de `reports/`, y CI con
gitleaks.
