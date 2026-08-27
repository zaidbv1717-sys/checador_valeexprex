#!/usr/bin/env python3
"""
Reloj checador local (versión simple) — servidor único en Python estándar,
sin dependencias externas. Sin cámara y sin código de acceso dinámico.
Ejecutar con:  python3 server.py
Luego abre en tu navegador la URL que imprime en consola (tu IP local + :5000).
Esa misma URL es la que va en el código QR que escanean los empleados.
"""
import json
import os
import re
import sqlite3
import socket
import calendar
import uuid
import csv
import io
import random
import string
import shutil
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'attendance.db')
BACKUP_DIR = os.path.join(DATA_DIR, 'backups')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
PORT = 5000
MAX_BACKUPS = 30

os.makedirs(DATA_DIR, exist_ok=True)

TYPES = ('entrada', 'comida_salida', 'comida_entrada', 'salida')
TYPE_LABELS = {
    'entrada': 'Entrada',
    'comida_salida': 'Salida a comer',
    'comida_entrada': 'Regreso de comer',
    'salida': 'Salida',
}

JUSTIFICATION_TYPES = ('medica', 'personal', 'permiso_economico', 'vacaciones')
JUSTIFICATION_TYPE_LABELS = {
    'medica': 'Médica / fuerza mayor',
    'personal': 'Personal',
    'permiso_economico': 'Permiso económico',
    'vacaciones': 'Vacaciones',
}
JUSTIFICATION_STATUSES = ('pendiente', 'aprobada', 'rechazada')

EMPLOYEE_CATEGORIES = ('practicante', 'trabajador', 'administrador')
CATEGORY_LABELS = {
    'practicante': 'Practicante',
    'trabajador': 'Trabajador',
    'administrador': 'Administrador',
}
CATEGORY_DEFAULTS = {
    'practicante': {'schedIn': '10:00', 'schedOut': '18:00', 'lunchMinutes': 90},
    'trabajador': {'schedIn': '08:30', 'schedOut': '18:00', 'lunchMinutes': 90},
    'administrador': {'schedIn': '08:30', 'schedOut': '19:00', 'lunchMinutes': 90},
}


def gen_recovery_code():
    return '-'.join(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4)) for _ in range(2))


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute('''CREATE TABLE IF NOT EXISTS employees (
        id TEXT PRIMARY KEY, name TEXT, pin TEXT,
        sched_in TEXT DEFAULT '09:00', sched_out TEXT DEFAULT '18:00',
        category TEXT DEFAULT 'trabajador', lunch_minutes INTEGER
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY, employee_id TEXT, employee_name TEXT,
        type TEXT, timestamp TEXT, source_ip TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS device_alerts (
        id TEXT PRIMARY KEY, ip TEXT,
        emp1_name TEXT, emp1_time TEXT,
        emp2_name TEXT, emp2_time TEXT,
        created_at TEXT, resolved INTEGER DEFAULT 0
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS justifications (
        id TEXT PRIMARY KEY, employee_id TEXT, employee_name TEXT,
        date_start TEXT, date_end TEXT, type TEXT, status TEXT,
        note TEXT, created_at TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS day_notes (
        employee_id TEXT, date TEXT, note TEXT,
        PRIMARY KEY (employee_id, date)
    )''')
    conn.commit()
    # Migración: si la base ya existía sin la columna source_ip, se agrega ahora.
    cols = [r['name'] for r in conn.execute("PRAGMA table_info(records)").fetchall()]
    if 'source_ip' not in cols:
        conn.execute("ALTER TABLE records ADD COLUMN source_ip TEXT")
        conn.commit()
    # Migración: empleados creados antes de la categoría y minutos de comida propios.
    emp_cols = [r['name'] for r in conn.execute("PRAGMA table_info(employees)").fetchall()]
    if 'category' not in emp_cols:
        conn.execute("ALTER TABLE employees ADD COLUMN category TEXT DEFAULT 'trabajador'")
        conn.commit()
    if 'lunch_minutes' not in emp_cols:
        conn.execute("ALTER TABLE employees ADD COLUMN lunch_minutes INTEGER")
        conn.commit()
    if conn.execute("SELECT 1 FROM config WHERE key='password'").fetchone() is None:
        conn.execute("INSERT INTO config (key, value) VALUES ('password','1234')")
    if conn.execute("SELECT 1 FROM config WHERE key='lunch_minutes'").fetchone() is None:
        conn.execute("INSERT INTO config (key, value) VALUES ('lunch_minutes','90')")
    if conn.execute("SELECT 1 FROM config WHERE key='recovery_code'").fetchone() is None:
        conn.execute("INSERT INTO config (key, value) VALUES ('recovery_code', ?)", (gen_recovery_code(),))
    conn.commit()
    conn.close()


DEVICE_ALERT_WINDOW_MIN = 5  # minutos: si dos empleados distintos marcan entrada
                              # desde el mismo dispositivo dentro de esta ventana,
                              # se genera una alerta silenciosa para el administrador.



def get_config():
    conn = db()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}


def set_config(partial):
    conn = db()
    for k, v in partial.items():
        conn.execute("INSERT INTO config (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Respaldo automático
# ---------------------------------------------------------------------------
def backup_now():
    """Copia attendance.db a data/backups/ con fecha y hora, y conserva solo los últimos MAX_BACKUPS."""
    if not os.path.isfile(DB_PATH):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(BACKUP_DIR, f'attendance_{ts}.db')
    shutil.copy2(DB_PATH, dest)
    existing = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith('attendance_') and f.endswith('.db'))
    while len(existing) > MAX_BACKUPS:
        os.remove(os.path.join(BACKUP_DIR, existing.pop(0)))
    return dest


def backup_loop():
    while True:
        time.sleep(24 * 60 * 60)  # cada 24 horas
        try:
            backup_now()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Cálculo de reportes (retardos, horas extra, comida, faltantes)
# ---------------------------------------------------------------------------
def compute_report_rows(period, anchor_date_str, emp_filter):
    conn = db()
    employees = {r['id']: r for r in conn.execute("SELECT * FROM employees").fetchall()}
    default_lunch_minutes = int(get_config().get('lunch_minutes', '90') or 90)
    recs = conn.execute("SELECT * FROM records ORDER BY timestamp ASC").fetchall()
    notes = {(r['employee_id'], r['date']): r['note'] for r in conn.execute("SELECT * FROM day_notes").fetchall()}
    conn.close()

    by_key = {}
    for r in recs:
        ts = datetime.fromisoformat(r['timestamp'])
        day = ts.date()
        key = (r['employee_id'], day)
        if key not in by_key:
            by_key[key] = {'employee_id': r['employee_id'], 'employee_name': r['employee_name'], 'date': day,
                           'entrada': None, 'comida_salida': None, 'comida_entrada': None, 'salida': None}
        by_key[key][r['type']] = dict(r)

    today = datetime.now().date()
    start, end = period_range(period, anchor_date_str)

    rows = []
    for g in by_key.values():
        if not (start <= g['date'] <= end):
            continue
        if emp_filter and emp_filter != 'all' and g['employee_name'] != emp_filter:
            continue
        emp = employees.get(g['employee_id'])
        sched_in = emp['sched_in'] if emp else ''
        sched_out = emp['sched_out'] if emp else ''
        lunch_minutes = emp['lunch_minutes'] if (emp and emp['lunch_minutes'] is not None) else default_lunch_minutes

        hours = 0.0
        if g['entrada'] and g['salida']:
            t_in = datetime.fromisoformat(g['entrada']['timestamp'])
            t_out = datetime.fromisoformat(g['salida']['timestamp'])
            worked = (t_out - t_in).total_seconds() / 3600
            lunch_h = 0.0
            if g['comida_salida'] and g['comida_entrada']:
                lo = datetime.fromisoformat(g['comida_salida']['timestamp'])
                li = datetime.fromisoformat(g['comida_entrada']['timestamp'])
                lunch_h = max(0, (li - lo).total_seconds() / 3600)
            hours = max(0, worked - lunch_h)

        retardo_min = 0
        if g['entrada'] and sched_in:
            h, m = map(int, sched_in.split(':'))
            sched_dt = datetime.combine(g['date'], datetime.min.time()).replace(hour=h, minute=m)
            t_in = datetime.fromisoformat(g['entrada']['timestamp'])
            diff = (t_in - sched_dt).total_seconds() / 60
            if diff > 10:
                retardo_min = round(diff)

        lunch_late_min = 0
        if g['comida_salida'] and g['comida_entrada']:
            lo = datetime.fromisoformat(g['comida_salida']['timestamp'])
            li = datetime.fromisoformat(g['comida_entrada']['timestamp'])
            taken = (li - lo).total_seconds() / 60
            if taken > lunch_minutes + 5:
                lunch_late_min = round(taken - lunch_minutes)

        extra_hrs = 0.0
        if g['entrada'] and g['salida'] and sched_in and sched_out:
            h1, m1 = map(int, sched_in.split(':'))
            h2, m2 = map(int, sched_out.split(':'))
            sched_hrs = (h2 + m2 / 60) - (h1 + m1 / 60)
            if sched_hrs < 0:
                sched_hrs += 24
            diff_extra = hours - sched_hrs
            if diff_extra > 0.1:
                extra_hrs = diff_extra

        is_past = g['date'] != today
        missing = is_past and ((g['entrada'] and not g['salida']) or (not g['entrada'] and g['salida']))

        rows.append({
            'employeeId': g['employee_id'], 'employeeName': g['employee_name'],
            'date': g['date'].isoformat(),
            'entrada': fmt_hm(g['entrada']), 'comida_salida': fmt_hm(g['comida_salida']),
            'comida_entrada': fmt_hm(g['comida_entrada']), 'salida': fmt_hm(g['salida']),
            'hours': round(hours, 2), 'retardoMin': retardo_min, 'extraHrs': round(extra_hrs, 2),
            'lunchLateMin': lunch_late_min, 'missing': missing,
            'note': notes.get((g['employee_id'], g['date'].isoformat()), '') or '',
        })
    rows.sort(key=lambda r: r['date'], reverse=True)
    return rows


def fmt_hm(rec):
    if not rec:
        return None
    return datetime.fromisoformat(rec['timestamp']).strftime('%H:%M')


def compute_calendar(employee_id, year, month):
    """Estado de cada día del mes para un empleado: asistio, falta, justificado
    o no_laboral (domingo, o día de hoy/futuro sin marcar todavía)."""
    conn = db()
    days_in_month = calendar.monthrange(year, month)[1]
    today = datetime.now().date()
    days = []
    for day_num in range(1, days_in_month + 1):
        d = datetime(year, month, day_num).date()
        has_entry = conn.execute(
            "SELECT 1 FROM records WHERE employee_id=? AND type='entrada' AND date(timestamp)=?",
            (employee_id, d.isoformat())
        ).fetchone()
        if has_entry:
            status = 'asistio'
        elif d.weekday() == 6:
            status = 'no_laboral'
        elif d >= today:
            status = 'no_laboral'
        else:
            just = conn.execute(
                "SELECT type FROM justifications WHERE employee_id=? AND status='aprobada' "
                "AND date_start<=? AND date_end>=?",
                (employee_id, d.isoformat(), d.isoformat())
            ).fetchone()
            status = 'justificado' if just else 'falta'
        days.append({'day': day_num, 'date': d.isoformat(), 'weekday': d.weekday(), 'status': status})
    conn.close()
    return days


def compute_absences(period, anchor_date_str, emp_filter):
    """Días ya concluidos donde un empleado no registró NINGUNA entrada.
    Excluye domingos (no hay horario oficial ese día). Si el día cae dentro
    de un justificante aprobado (permiso, incapacidad, vacaciones), se marca
    como justificada en vez de como falta."""
    conn = db()
    employees = conn.execute("SELECT * FROM employees").fetchall()
    if emp_filter and emp_filter != 'all':
        employees = [e for e in employees if e['name'] == emp_filter]
    start, end = period_range(period, anchor_date_str)
    today = datetime.now().date()
    effective_end = min(end, today - timedelta(days=1))

    absences = []
    if effective_end >= start:
        d = start
        while d <= effective_end:
            if d.weekday() != 6:  # 6 = domingo
                for emp in employees:
                    has_entry = conn.execute(
                        "SELECT 1 FROM records WHERE employee_id=? AND type='entrada' AND date(timestamp)=?",
                        (emp['id'], d.isoformat())
                    ).fetchone()
                    if has_entry:
                        continue
                    just = conn.execute(
                        "SELECT type FROM justifications WHERE employee_id=? AND status='aprobada' "
                        "AND date_start<=? AND date_end>=?",
                        (emp['id'], d.isoformat(), d.isoformat())
                    ).fetchone()
                    absences.append({
                        'employeeId': emp['id'], 'employeeName': emp['name'], 'date': d.isoformat(),
                        'justified': bool(just),
                        'justificationType': JUSTIFICATION_TYPE_LABELS.get(just['type'], just['type']) if just else None,
                    })
            d += timedelta(days=1)
    conn.close()
    return absences


def period_range(period, anchor_date_str):
    if anchor_date_str:
        anchor = datetime.strptime(anchor_date_str, '%Y-%m-%d').date()
    else:
        anchor = datetime.now().date()
    if period == 'semana':
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        return start, end
    if period == 'mes':
        start = anchor.replace(day=1)
        if anchor.month == 12:
            end = anchor.replace(year=anchor.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = anchor.replace(month=anchor.month + 1, day=1) - timedelta(days=1)
        return start, end
    return anchor, anchor


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def uid():
    return uuid.uuid4().hex[:12]


def check_device_alert(ip, employee_id, employee_name, ts_iso):
    """Detección silenciosa: si otro empleado distinto marcó 'entrada' desde la
    misma IP hace pocos minutos, registra una alerta para el administrador.
    No se le informa nada al empleado en ningún caso."""
    if not ip:
        return
    conn = db()
    try:
        window_start = (datetime.fromisoformat(ts_iso) - timedelta(minutes=DEVICE_ALERT_WINDOW_MIN)).isoformat()
        recent = conn.execute(
            "SELECT employee_name, timestamp FROM records "
            "WHERE type='entrada' AND source_ip=? AND employee_id!=? AND timestamp>=? "
            "ORDER BY timestamp DESC LIMIT 1",
            (ip, employee_id, window_start)
        ).fetchone()
        if recent:
            conn.execute(
                "INSERT INTO device_alerts (id, ip, emp1_name, emp1_time, emp2_name, emp2_time, created_at, resolved) "
                "VALUES (?,?,?,?,?,?,?,0)",
                (uid(), ip, recent['employee_name'], recent['timestamp'], employee_name, ts_iso, datetime.now().isoformat())
            )
            conn.commit()
    finally:
        conn.close()


def build_csv(rows, period, date_str, emp_filter):
    period_label = {'dia': 'Día', 'semana': 'Semana', 'mes': 'Mes'}.get(period, period)
    emp_label = 'Todos' if (not emp_filter or emp_filter == 'all') else emp_filter
    anchor = date_str or datetime.now().strftime('%Y-%m-%d')

    conn = db()
    categories = {r['id']: r['category'] for r in conn.execute("SELECT id, category FROM employees").fetchall()}
    conn.close()

    dow_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['Reporte de Asistencia — Reloj Checador'])
    w.writerow([f'Periodo: {period_label}', f'Fecha de referencia: {datetime.strptime(anchor, "%Y-%m-%d").strftime("%d/%m/%Y")}', f'Empleado: {emp_label}', f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}'])
    w.writerow([])
    w.writerow(['Empleado', 'Categoría', 'Fecha', 'Entrada', 'Salida a comer', 'Regreso de comer', 'Salida', 'Horas trabajadas', 'Estado'])

    sorted_rows = sorted(rows, key=lambda r: (r['employeeName'], r['date']))
    current_emp = None
    emp_hours = emp_extra = 0.0
    emp_retardos = emp_missing = 0

    def flush_subtotal():
        if current_emp is not None:
            w.writerow([f'Subtotal {current_emp}', '', '', '', '', '', '',
                        f"{emp_hours:.2f} h",
                        f"{emp_retardos} retardo(s) · {emp_extra:.2f} h extra · {emp_missing} sin marca"])
            w.writerow([])

    for r in sorted_rows:
        if current_emp is not None and r['employeeName'] != current_emp:
            flush_subtotal()
            emp_hours = emp_extra = 0.0
            emp_retardos = emp_missing = 0
        current_emp = r['employeeName']
        emp_hours += r['hours']
        emp_extra += r['extraHrs']
        if r['retardoMin'] > 0:
            emp_retardos += 1
        if r['missing']:
            emp_missing += 1

        fecha_dt = datetime.strptime(r['date'], '%Y-%m-%d')
        fecha = f"{dow_names[fecha_dt.weekday()]} {fecha_dt.strftime('%d/%m/%Y')}"
        cat = CATEGORY_LABELS.get(categories.get(r['employeeId']), '')
        estado_parts = []
        if r['missing']:
            estado_parts.append('Sin marca')
        if r['retardoMin'] > 0:
            estado_parts.append(f"Retardo {r['retardoMin']} min")
        if r['extraHrs'] > 0:
            estado_parts.append(f"Extra {r['extraHrs']:.1f} h")
        if r['lunchLateMin'] > 0:
            estado_parts.append(f"Comida +{r['lunchLateMin']} min")
        estado = ' | '.join(estado_parts) if estado_parts else 'Normal'

        w.writerow([
            r['employeeName'], cat, fecha,
            r['entrada'] or '—', r['comida_salida'] or '—', r['comida_entrada'] or '—', r['salida'] or '—',
            f"{r['hours']:.2f} h", estado,
        ])
    flush_subtotal()

    total_hours = sum(r['hours'] for r in rows)
    total_extra = sum(r['extraHrs'] for r in rows)
    total_retardos = sum(1 for r in rows if r['retardoMin'] > 0)
    total_missing = sum(1 for r in rows if r['missing'])
    w.writerow(['TOTAL GENERAL', '', '', '', '', '', '',
                f"{total_hours:.2f} h",
                f"{total_retardos} retardo(s) · {total_extra:.2f} h extra · {total_missing} sin marca"])

    return ('\ufeff' + buf.getvalue()).encode('utf-8')


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silencioso en consola

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, content_type):
        if not os.path.isfile(path):
            self.send_json({'error': 'not found'}, 404)
            return
        with open(path, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return {}

    def require_admin(self):
        pw = self.headers.get('X-Admin-Pass', '')
        cfg = get_config()
        return pw == cfg.get('password', '1234')

    def do_GET(self):
        parts = urlsplit(self.path)
        path, query = parts.path, parse_qs(parts.query)

        if path == '/' or path == '/index.html':
            return self.send_file(os.path.join(STATIC_DIR, 'index.html'), 'text/html; charset=utf-8')
        if path == '/static/app.js':
            return self.send_file(os.path.join(STATIC_DIR, 'app.js'), 'application/javascript; charset=utf-8')
        if path == '/static/style.css':
            return self.send_file(os.path.join(STATIC_DIR, 'style.css'), 'text/css; charset=utf-8')
        if path == '/static/logo.png':
            return self.send_file(os.path.join(STATIC_DIR, 'logo.png'), 'image/png')
        if path == '/static/logo-icon.png':
            return self.send_file(os.path.join(STATIC_DIR, 'logo-icon.png'), 'image/png')

        if path == '/api/today':
            emp_id = query.get('employeeId', [''])[0]
            conn = db()
            today = datetime.now().date().isoformat()
            recs = conn.execute(
                "SELECT type, timestamp FROM records WHERE employee_id=? AND date(timestamp)=?",
                (emp_id, today)
            ).fetchall()
            conn.close()
            done = {r['type']: r['timestamp'] for r in recs}
            return self.send_json({'done': done})

        if path == '/api/admin/employees':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            conn = db()
            emps = [dict(r) for r in conn.execute("SELECT * FROM employees ORDER BY name").fetchall()]
            conn.close()
            return self.send_json({'employees': emps})

        if path == '/api/admin/employee-categories':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            cats = [
                {'value': c, 'label': CATEGORY_LABELS[c], **CATEGORY_DEFAULTS[c]}
                for c in EMPLOYEE_CATEGORIES
            ]
            return self.send_json({'categories': cats})

        if path == '/api/admin/records':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            period = query.get('period', ['dia'])[0]
            date_str = query.get('date', [''])[0]
            emp = query.get('emp', ['all'])[0]
            rows = compute_report_rows(period, date_str, emp)
            return self.send_json({'rows': rows})

        if path == '/api/admin/device-alerts':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            conn = db()
            alerts = [dict(r) for r in conn.execute(
                "SELECT * FROM device_alerts WHERE resolved=0 ORDER BY created_at DESC LIMIT 20"
            ).fetchall()]
            conn.close()
            return self.send_json({'alerts': alerts})

        if path == '/api/admin/absences':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            period = query.get('period', ['dia'])[0]
            date_str = query.get('date', [''])[0]
            emp = query.get('emp', ['all'])[0]
            absences = compute_absences(period, date_str, emp)
            return self.send_json({'absences': absences})

        if path == '/api/admin/calendar':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            employee_id = query.get('employeeId', [''])[0]
            now = datetime.now()
            year = int(query.get('year', [str(now.year)])[0])
            month = int(query.get('month', [str(now.month)])[0])
            if not employee_id:
                return self.send_json({'days': []})
            days = compute_calendar(employee_id, year, month)
            return self.send_json({'days': days})

        if path == '/api/admin/justifications':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            emp = query.get('emp', ['all'])[0]
            conn = db()
            q = "SELECT * FROM justifications"
            params = ()
            if emp and emp != 'all':
                q += " WHERE employee_name=?"
                params = (emp,)
            q += " ORDER BY date_start DESC"
            items = [dict(r) for r in conn.execute(q, params).fetchall()]
            conn.close()
            return self.send_json({'justifications': items})

        if path == '/api/admin/config':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            cfg = get_config()
            return self.send_json({'lunchMinutes': cfg.get('lunch_minutes', '90'), 'recoveryCode': cfg.get('recovery_code', '')})

        if path == '/api/admin/export.csv':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            period = query.get('period', ['mes'])[0]
            date_str = query.get('date', [''])[0]
            emp = query.get('emp', ['all'])[0]
            rows = compute_report_rows(period, date_str, emp)
            data = build_csv(rows, period, date_str, emp)
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename="registros_asistencia.csv"')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_json({'error': 'not found'}, 404)

    def do_POST(self):
        path = urlsplit(self.path).path
        body = self.read_json()

        if path == '/api/verify-pin':
            pin = str(body.get('pin', ''))
            conn = db()
            emp = conn.execute("SELECT * FROM employees WHERE pin=?", (pin,)).fetchone()
            conn.close()
            if emp:
                return self.send_json({'ok': True, 'employee': {'id': emp['id'], 'name': emp['name']}})
            return self.send_json({'ok': False})

        if path == '/api/punch':
            emp_id = body.get('employeeId', '')
            emp_name = body.get('employeeName', '')
            ptype = body.get('type', '')
            if ptype not in TYPES:
                return self.send_json({'ok': False, 'error': 'tipo inválido'}, 400)

            client_ip = self.client_address[0] if self.client_address else ''
            today = datetime.now().date().isoformat()
            ts = datetime.now().isoformat()
            conn = db()

            existing = conn.execute(
                "SELECT id FROM records WHERE employee_id=? AND type=? AND date(timestamp)=?",
                (emp_id, ptype, today)
            ).fetchone()
            if existing:
                conn.close()
                return self.send_json({'ok': False, 'error': 'Ese registro ya se marcó hoy. Solo el administrador puede modificarlo.'}, 400)

            step_index = TYPES.index(ptype)
            if step_index > 0:
                previous_type = TYPES[step_index - 1]
                done_previous = conn.execute(
                    "SELECT id FROM records WHERE employee_id=? AND type=? AND date(timestamp)=?",
                    (emp_id, previous_type, today)
                ).fetchone()
                if not done_previous:
                    conn.close()
                    return self.send_json({'ok': False, 'error': f'Primero debes marcar "{TYPE_LABELS[previous_type]}".'}, 400)

            conn.execute(
                "INSERT INTO records (id, employee_id, employee_name, type, timestamp, source_ip) VALUES (?,?,?,?,?,?)",
                (uid(), emp_id, emp_name, ptype, ts, client_ip)
            )
            conn.commit()
            conn.close()
            if ptype == 'entrada':
                check_device_alert(client_ip, emp_id, emp_name, ts)
            return self.send_json({'ok': True, 'time': datetime.now().strftime('%H:%M:%S')})

        if path == '/api/admin/login':
            pw = str(body.get('password', ''))
            cfg = get_config()
            return self.send_json({'ok': pw == cfg.get('password', '1234')})

        if path == '/api/admin/recover':
            code = str(body.get('recoveryCode', '')).strip().upper()
            new_pass = str(body.get('newPassword', '')).strip()
            cfg = get_config()
            if code != cfg.get('recovery_code', ''):
                return self.send_json({'ok': False, 'error': 'Código de recuperación incorrecto'}, 400)
            if len(new_pass) < 4:
                return self.send_json({'ok': False, 'error': 'La nueva contraseña debe tener al menos 4 caracteres'}, 400)
            set_config({'password': new_pass})
            return self.send_json({'ok': True})

        if path == '/api/admin/employees':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            name = str(body.get('name', '')).strip()
            pin = str(body.get('pin', '')).strip()
            category = body.get('category', 'trabajador')
            if category not in EMPLOYEE_CATEGORIES:
                category = 'trabajador'
            defaults = CATEGORY_DEFAULTS[category]
            sched_in = body.get('schedIn') or defaults['schedIn']
            sched_out = body.get('schedOut') or defaults['schedOut']
            lunch_minutes = body.get('lunchMinutes')
            lunch_minutes = int(lunch_minutes) if lunch_minutes not in (None, '') else defaults['lunchMinutes']
            if not name or not re.match(r'^\d{4}$', pin):
                return self.send_json({'ok': False, 'error': 'nombre y PIN de 4 dígitos requeridos'}, 400)
            conn = db()
            if conn.execute("SELECT 1 FROM employees WHERE pin=?", (pin,)).fetchone():
                conn.close()
                return self.send_json({'ok': False, 'error': 'ese PIN ya está en uso'}, 400)
            conn.execute(
                "INSERT INTO employees (id, name, pin, sched_in, sched_out, category, lunch_minutes) VALUES (?,?,?,?,?,?,?)",
                (uid(), name, pin, sched_in, sched_out, category, lunch_minutes)
            )
            conn.commit()
            conn.close()
            return self.send_json({'ok': True})

        if path == '/api/admin/device-alerts/resolve':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            alert_id = body.get('id', '')
            conn = db()
            conn.execute("UPDATE device_alerts SET resolved=1 WHERE id=?", (alert_id,))
            conn.commit()
            conn.close()
            return self.send_json({'ok': True})

        if path == '/api/admin/justifications':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            emp_id = body.get('employeeId', '')
            emp_name = body.get('employeeName', '')
            date_start = body.get('dateStart', '')
            date_end = body.get('dateEnd', '') or date_start
            jtype = body.get('type', '')
            status = body.get('status', 'aprobada')
            note = str(body.get('note', '') or '').strip()
            if not emp_id or not date_start or jtype not in JUSTIFICATION_TYPES or status not in JUSTIFICATION_STATUSES:
                return self.send_json({'ok': False, 'error': 'Faltan datos o son inválidos'}, 400)
            if date_end < date_start:
                return self.send_json({'ok': False, 'error': 'La fecha final no puede ser antes de la inicial'}, 400)
            conn = db()
            conn.execute(
                "INSERT INTO justifications (id, employee_id, employee_name, date_start, date_end, type, status, note, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (uid(), emp_id, emp_name, date_start, date_end, jtype, status, note, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            return self.send_json({'ok': True})

        if path == '/api/admin/justifications/status':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            jid = body.get('id', '')
            status = body.get('status', '')
            if status not in JUSTIFICATION_STATUSES:
                return self.send_json({'ok': False, 'error': 'Estado inválido'}, 400)
            conn = db()
            conn.execute("UPDATE justifications SET status=? WHERE id=?", (status, jid))
            conn.commit()
            conn.close()
            return self.send_json({'ok': True})

        if path == '/api/admin/manual-edit':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            emp_id = body.get('employeeId')
            emp_name = body.get('employeeName')
            date_str = body.get('dateStr')
            edits = body.get('edits', {})  # {type: "HH:MM"}
            conn = db()
            for ptype, hm in edits.items():
                if not hm or ptype not in TYPES:
                    continue
                h, m = map(int, hm.split(':'))
                ts = datetime.strptime(date_str, '%Y-%m-%d').replace(hour=h, minute=m).isoformat()
                existing = conn.execute(
                    "SELECT id FROM records WHERE employee_id=? AND type=? AND date(timestamp)=?",
                    (emp_id, ptype, date_str)
                ).fetchone()
                if existing:
                    conn.execute("UPDATE records SET timestamp=? WHERE id=?", (ts, existing['id']))
                else:
                    conn.execute(
                        "INSERT INTO records (id, employee_id, employee_name, type, timestamp) VALUES (?,?,?,?,?)",
                        (uid(), emp_id, emp_name, ptype, ts)
                    )
            if 'note' in body:
                note_val = str(body.get('note', '') or '').strip()
                if note_val:
                    conn.execute(
                        "INSERT INTO day_notes (employee_id, date, note) VALUES (?,?,?) "
                        "ON CONFLICT(employee_id, date) DO UPDATE SET note=excluded.note",
                        (emp_id, date_str, note_val)
                    )
                else:
                    conn.execute("DELETE FROM day_notes WHERE employee_id=? AND date=?", (emp_id, date_str))
            conn.commit()
            conn.close()
            return self.send_json({'ok': True})

        if path == '/api/admin/config':
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            partial = {}
            if 'password' in body and body['password']:
                partial['password'] = body['password']
            if 'lunchMinutes' in body and body['lunchMinutes']:
                partial['lunch_minutes'] = body['lunchMinutes']
            if body.get('generateRecovery'):
                partial['recovery_code'] = gen_recovery_code()
            set_config(partial)
            cfg = get_config()
            return self.send_json({'ok': True, 'recoveryCode': cfg.get('recovery_code', '')})

        self.send_json({'error': 'not found'}, 404)

    def do_DELETE(self):
        path = urlsplit(self.path).path
        m = re.match(r'^/api/admin/employees/(.+)$', path)
        if m:
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            conn = db()
            conn.execute("DELETE FROM employees WHERE id=?", (m.group(1),))
            conn.commit()
            conn.close()
            return self.send_json({'ok': True})
        m = re.match(r'^/api/admin/justifications/(.+)$', path)
        if m:
            if not self.require_admin():
                return self.send_json({'error': 'unauthorized'}, 401)
            conn = db()
            conn.execute("DELETE FROM justifications WHERE id=?", (m.group(1),))
            conn.commit()
            conn.close()
            return self.send_json({'ok': True})
        self.send_json({'error': 'not found'}, 404)


def main():
    init_db()
    ip = get_local_ip()
    cfg = get_config()
    backup_now()
    threading.Thread(target=backup_loop, daemon=True).start()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print('=' * 56)
    print(' Reloj checador (simple) — servidor iniciado')
    print(f' En esta computadora:   http://localhost:{PORT}')
    print(f' Para el QR (celulares): http://{ip}:{PORT}')
    print(' (los celulares deben estar en la misma red WiFi)')
    print(f' Código de recuperación de contraseña: {cfg.get("recovery_code","")}')
    print(' (guárdalo en un lugar seguro — sirve si olvidas la contraseña de admin)')
    print(f' Respaldo automático diario en: data/backups/ (se guardan los últimos {MAX_BACKUPS})')
    print(' Presiona Ctrl+C para detener el servidor.')
    print('=' * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')


if __name__ == '__main__':
    main()
