(function(){
  const root = document.getElementById('app-root');

  const STAGES = ['entrada','comida_salida','comida_entrada','salida'];
  const TYPE_LABEL = {entrada:'Entrada', comida_salida:'Salida a comer', comida_entrada:'Regreso de comer', salida:'Salida'};
  const CATEGORY_LABEL = {practicante:'Practicante', trabajador:'Trabajador', administrador:'Administrador'};

  let state = {
    view: 'clock', // clock | admin-login | admin-recover | admin
    pin: '',
    activeEmployee: null,
    todayDone: {},

    adminPass: '',
    adminTab: 'registros',
    employees: [],
    categories: [],
    reportRows: [],
    reportPeriod: 'dia',
    filterDate: '',
    filterEmp: 'all',
    lunchMinutes: '90',
    recoveryCode: '',
    deviceAlerts: [],
    absences: [],
    justifications: [],
    calendarEmployeeId: '',
    calendarYear: new Date().getFullYear(),
    calendarMonth: new Date().getMonth()+1,
    calendarDays: [],
    editTarget: null,
  };

  function fmtTime(d){ return d.toLocaleTimeString('es-MX', {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false}); }
  function fmtDate(d){ return d.toLocaleDateString('es-MX', {weekday:'long', day:'numeric', month:'long'}); }

  function toast(msg){
    let t = document.getElementById('toastel');
    if(!t){ t = document.createElement('div'); t.id='toastel'; t.className='toast'; document.body.appendChild(t); }
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(()=>t.classList.remove('show'), 2400);
  }

  async function api(path, opts){
    opts = opts || {};
    opts.headers = Object.assign({'Content-Type':'application/json'}, opts.headers||{});
    if(state.adminPass) opts.headers['X-Admin-Pass'] = state.adminPass;
    const res = await fetch(path, opts);
    return res.json();
  }

  // ---------------- PIN ----------------
  function addDigit(d){
    if(state.pin.length>=4) return;
    state.pin += d;
    if(state.pin.length===4){
      setTimeout(async ()=>{
        const r = await api('/api/verify-pin', {method:'POST', body: JSON.stringify({pin: state.pin})});
        state.pin = '';
        if(r.ok){
          state.activeEmployee = r.employee;
          await refreshToday();
        } else {
          toast('PIN no encontrado');
        }
        render();
      }, 150);
    }
    render();
  }
  function backspace(){ state.pin = state.pin.slice(0,-1); render(); }
  function clearInput(){ state.pin=''; render(); }

  async function refreshToday(){
    if(!state.activeEmployee) return;
    const r = await api('/api/today?employeeId='+encodeURIComponent(state.activeEmployee.id));
    state.todayDone = r.done || {};
  }

  async function doPunch(type){
    const emp = state.activeEmployee;
    if(!emp) return;
    const r = await api('/api/punch', {method:'POST', body: JSON.stringify({employeeId: emp.id, employeeName: emp.name, type})});
    if(r.ok){
      toast(TYPE_LABEL[type] + ' registrada — ' + r.time);
    } else {
      toast(r.error || 'No se pudo registrar');
    }
    state.activeEmployee = null;
    state.todayDone = {};
    render();
  }

  // ---------------- Render root ----------------
  function render(){
    if(state.view==='clock') return renderClock();
    if(state.view==='admin-login') return renderAdminLogin();
    if(state.view==='admin-recover') return renderAdminRecover();
    if(state.view==='admin') return renderAdmin();
  }

  function renderClock(){
    const now = new Date();
    let body = '';

    if(!state.activeEmployee){
      const dots = Array.from({length:4}).map((_,i)=> `<div class="pin-dot ${i<state.pin.length?'filled':''}"></div>`).join('');
      body = `
        <div class="field-label">Ingresa tu PIN</div>
        <div class="pin-dots">${dots}</div>
        <div class="keypad">
          ${[1,2,3,4,5,6,7,8,9].map(n=>`<button data-key="${n}">${n}</button>`).join('')}
          <button data-key="clear" class="wide">Borrar</button>
          <button data-key="0">0</button>
          <button data-key="back" class="wide">←</button>
        </div>
      `;
    } else {
      const emp = state.activeEmployee;
      const done = state.todayDone;
      const nextStage = STAGES.find(s => !done[s]);
      const doneCount = STAGES.filter(s => done[s]).length;
      const stageDots = STAGES.map(s => `<div class="pin-dot ${done[s]?'filled':''}"></div>`).join('');

      if(!nextStage){
        body = `
          <div class="greet">
            <div class="name">Hola, ${emp.name.split(' ')[0]}</div>
            <div class="sub">Ya completaste tu registro de hoy</div>
          </div>
          <div class="pin-dots" style="margin-top:16px;">${stageDots}</div>
          <div class="stub-list">
            ${STAGES.map(s=>`
              <div class="stub">
                <span>${TYPE_LABEL[s]}</span>
                <span>${new Date(done[s]).toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})}</span>
              </div>`).join('')}
          </div>
          <button class="back-link" id="btn-back-emp">Cambiar de empleado</button>
        `;
      } else {
        body = `
          <div class="greet">
            <div class="name">Hola, ${emp.name.split(' ')[0]}</div>
            <div class="sub">Paso ${doneCount+1} de 4</div>
          </div>
          <div class="pin-dots" style="margin-top:6px;margin-bottom:22px;">${stageDots}</div>
          <button class="stage-btn" id="btn-next-stage">Marcar ${TYPE_LABEL[nextStage]}</button>
          <button class="back-link" id="btn-back-emp">Cambiar de empleado</button>
        `;
      }
    }

    root.innerHTML = `
      <div class="wrap">
        <div class="topbar"><div class="brand"><img src="/static/logo-icon.png" alt="ValeExpress" />Reloj checador</div><button class="admin-link" id="btn-goadmin">Admin</button></div>
        <div class="card">
          <div class="clockpanel"><div class="date">${fmtDate(now)}</div><div class="time" id="livetime">${fmtTime(now)}</div></div>
          <div class="body-pad">${body}</div>
        </div>
      </div>
    `;

    document.getElementById('btn-goadmin').onclick = ()=>{ state.view='admin-login'; render(); };

    if(!state.activeEmployee){
      root.querySelectorAll('[data-key]').forEach(btn=>{
        btn.onclick = ()=>{ const k=btn.getAttribute('data-key'); if(k==='clear') clearInput(); else if(k==='back') backspace(); else addDigit(k); };
      });
    } else {
      const nextBtn = document.getElementById('btn-next-stage');
      if(nextBtn){
        nextBtn.onclick = ()=>{
          const nextStage = STAGES.find(s => !state.todayDone[s]);
          if(nextStage) doPunch(nextStage);
        };
      }
      document.getElementById('btn-back-emp').onclick = ()=>{ state.activeEmployee=null; state.todayDone={}; render(); };
    }
  }

  function renderAdminLogin(){
    root.innerHTML = `
      <div class="wrap">
        <div class="topbar"><div class="brand"><img src="/static/logo-icon.png" alt="ValeExpress" />Reloj checador</div></div>
        <div class="card body-pad">
          <div class="field-label" style="text-align:left;">Acceso de administrador</div>
          <input type="password" id="adminpw" placeholder="Contraseña" style="margin-bottom:10px;" />
          <div class="row">
            <button class="btn" id="btn-login" style="flex:1;">Entrar</button>
            <button class="btn ghost" id="btn-cancel" style="flex:1;">Volver</button>
          </div>
          <button class="back-link" id="btn-forgot">¿Olvidaste tu contraseña?</button>
        </div>
      </div>
    `;
    document.getElementById('btn-cancel').onclick = ()=>{ state.view='clock'; render(); };
    document.getElementById('btn-forgot').onclick = ()=>{ state.view='admin-recover'; render(); };
    document.getElementById('btn-login').onclick = async ()=>{
      const v = document.getElementById('adminpw').value;
      const r = await api('/api/admin/login', {method:'POST', body: JSON.stringify({password:v})});
      if(r.ok){ state.adminPass = v; state.view='admin'; state.adminTab='registros'; await loadAdminTab(); render(); }
      else toast('Contraseña incorrecta');
    };
  }

  function renderAdminRecover(){
    root.innerHTML = `
      <div class="wrap">
        <div class="topbar"><div class="brand"><img src="/static/logo-icon.png" alt="ValeExpress" />Reloj checador</div></div>
        <div class="card body-pad">
          <div class="field-label" style="text-align:left;">Recuperar contraseña</div>
          <div class="note" style="margin-top:-8px;margin-bottom:14px;">Pide el código de recuperación a quien tenga acceso a la computadora donde corre el sistema (se muestra en la terminal al arrancar, o en Config una vez adentro).</div>
          <input type="text" id="recoverycode" placeholder="Código de recuperación" style="margin-bottom:10px;text-transform:uppercase;" />
          <input type="password" id="newpassrecover" placeholder="Nueva contraseña" style="margin-bottom:10px;" />
          <div class="row">
            <button class="btn secondary" id="btn-do-recover" style="flex:1;">Restablecer</button>
            <button class="btn ghost" id="btn-cancel-recover" style="flex:1;">Volver</button>
          </div>
        </div>
      </div>
    `;
    document.getElementById('btn-cancel-recover').onclick = ()=>{ state.view='admin-login'; render(); };
    document.getElementById('btn-do-recover').onclick = async ()=>{
      const code = document.getElementById('recoverycode').value.trim();
      const newPass = document.getElementById('newpassrecover').value.trim();
      const r = await api('/api/admin/recover', {method:'POST', body: JSON.stringify({recoveryCode: code, newPassword: newPass})});
      if(r.ok){ toast('Contraseña restablecida, ya puedes entrar'); state.view='admin-login'; render(); }
      else toast(r.error || 'No se pudo restablecer');
    };
  }

  async function loadAdminTab(){
    if(state.adminTab==='registros'){
      const q = `?period=${state.reportPeriod}&date=${state.filterDate}&emp=${encodeURIComponent(state.filterEmp)}`;
      const r = await api('/api/admin/records'+q);
      state.reportRows = r.rows || [];
      const ra = await api('/api/admin/device-alerts');
      state.deviceAlerts = ra.alerts || [];
      const rb = await api('/api/admin/absences'+q);
      state.absences = rb.absences || [];
      if(state.employees.length===0){
        const r2 = await api('/api/admin/employees');
        state.employees = r2.employees || [];
      }
    } else if(state.adminTab==='empleados'){
      const r = await api('/api/admin/employees');
      state.employees = r.employees || [];
      if(state.categories.length===0){
        const rc = await api('/api/admin/employee-categories');
        state.categories = rc.categories || [];
      }
    } else if(state.adminTab==='permisos'){
      const r = await api('/api/admin/justifications');
      state.justifications = r.justifications || [];
      if(state.employees.length===0){
        const r2 = await api('/api/admin/employees');
        state.employees = r2.employees || [];
      }
    } else if(state.adminTab==='calendario'){
      if(state.employees.length===0){
        const r2 = await api('/api/admin/employees');
        state.employees = r2.employees || [];
      }
      if(state.calendarEmployeeId){
        const r = await api(`/api/admin/calendar?employeeId=${encodeURIComponent(state.calendarEmployeeId)}&year=${state.calendarYear}&month=${state.calendarMonth}`);
        state.calendarDays = r.days || [];
      }
    } else if(state.adminTab==='config'){
      const r = await api('/api/admin/config');
      state.lunchMinutes = r.lunchMinutes || '90';
      state.recoveryCode = r.recoveryCode || '';
    }
  }

  function renderAdmin(){
    const tabs = ['registros','empleados','permisos','calendario','qr','config'];
    const labels = {registros:'Registros', empleados:'Empleados', permisos:'Permisos', calendario:'Calendario', qr:'Código QR', config:'Config'};
    let content = '';

    if(state.adminTab==='registros'){
      const rows = state.reportRows;
      const missing = rows.filter(r=>r.missing).slice(0,8);
      const totalHrs = rows.reduce((s,r)=>s+r.hours,0);
      const totalExtra = rows.reduce((s,r)=>s+r.extraHrs,0);
      const lateCount = rows.filter(r=>r.retardoMin>0).length;
      const missingCount = rows.filter(r=>r.missing).length;
      const periods = [['dia','Día'],['semana','Semana'],['mes','Mes']];

      let editPanel = '';
      if(state.editTarget){
        const t = state.editTarget;
        editPanel = `
          <div class="edit-panel">
            <div class="field-label" style="text-align:left;margin-bottom:8px;">Editar horario · ${t.employeeName} — ${t.dateLabel}</div>
            <div class="row">
              <div style="flex:1;"><label>Entrada</label><input type="time" id="edit-entrada" value="${t.entrada||''}" /></div>
              <div style="flex:1;"><label>Salida a comer</label><input type="time" id="edit-comida_salida" value="${t.comida_salida||''}" /></div>
            </div>
            <div class="row">
              <div style="flex:1;"><label>Regreso de comer</label><input type="time" id="edit-comida_entrada" value="${t.comida_entrada||''}" /></div>
              <div style="flex:1;"><label>Salida</label><input type="time" id="edit-salida" value="${t.salida||''}" /></div>
            </div>
            <div class="row">
              <div style="flex:1;"><label>Nota (opcional)</label><input type="text" id="edit-note" value="${(t.note||'').replace(/"/g,'&quot;')}" placeholder="Ej. permiso para retirarse temprano" /></div>
            </div>
            <div class="row">
              <button class="btn secondary" id="btn-save-edit" style="flex:1;">Guardar</button>
              <button class="btn ghost" id="btn-cancel-edit" style="flex:1;">Cancelar</button>
            </div>
          </div>
        `;
      }

      content = `
        ${missing.length ? `<div class="alert-banner">⚠ ${missing.length} registro(s) con entrada o salida faltante: ${missing.map(r=>r.employeeName+' ('+new Date(r.date+'T00:00:00').toLocaleDateString('es-MX',{day:'2-digit',month:'short'})+')').join(', ')}</div>` : ''}
        ${(()=>{ const unjustified = state.absences.filter(a=>!a.justified); return unjustified.length ? `<div class="alert-banner" style="background:#FBEAEA;border-color:#EFC7C0;color:#7A2E1E;">🚫 ${unjustified.length} falta(s) sin justificar: ${unjustified.map(a=>a.employeeName+' ('+new Date(a.date+'T00:00:00').toLocaleDateString('es-MX',{day:'2-digit',month:'short'})+')').join(', ')}</div>` : ''; })()}
        ${state.deviceAlerts.length ? `<div class="alert-banner" style="background:#FBEAEA;border-color:#EFC7C0;color:#7A2E1E;">
          ${state.deviceAlerts.map(a=>`
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:3px 0;">
              <span>⚠ Posible dispositivo compartido: <b>${a.emp1_name}</b> y <b>${a.emp2_name}</b> marcaron entrada desde el mismo aparato con pocos minutos de diferencia (${new Date(a.emp1_time).toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})} / ${new Date(a.emp2_time).toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})}).</span>
              <button class="edit-icon" style="color:#7A2E1E;white-space:nowrap;" data-resolve-alert="${a.id}">Marcar revisado</button>
            </div>`).join('')}
        </div>` : ''}
        <div class="period-tabs">
          ${periods.map(([val,label])=>`<button class="tab-btn ${state.reportPeriod===val?'active':''}" data-period="${val}">${label}</button>`).join('')}
        </div>
        <div class="row">
          <input type="date" id="f-date" value="${state.filterDate}" />
          <select id="f-emp">
            <option value="all">Todos</option>
            ${state.employees.map(e=>`<option value="${e.name}" ${state.filterEmp===e.name?'selected':''}>${e.name}</option>`).join('')}
          </select>
        </div>
        <div class="stat-row">
          <div class="stat-box"><div class="n">${totalHrs.toFixed(1)}</div><div class="l">Horas</div></div>
          <div class="stat-box ok"><div class="n">${totalExtra.toFixed(1)}</div><div class="l">Extra</div></div>
          <div class="stat-box warn"><div class="n">${lateCount}</div><div class="l">Retardos</div></div>
          <div class="stat-box bad"><div class="n">${missingCount}</div><div class="l">Sin marca</div></div>
        </div>
        ${editPanel}
        <div class="row"><button class="btn secondary" id="btn-export" style="flex:1;">Exportar CSV</button></div>
        <div class="table-scroll">
          <table>
            <thead><tr><th>Empleado</th><th>Fecha</th><th>Ent.</th><th>S.Comer</th><th>R.Comer</th><th>Sal.</th><th>Hrs</th><th>Estado</th><th></th></tr></thead>
            <tbody>
            ${rows.length? rows.map(r=>`
              <tr>
                <td>${r.employeeName}</td>
                <td>${new Date(r.date+'T00:00:00').toLocaleDateString('es-MX',{day:'2-digit',month:'short'})}</td>
                <td>${r.entrada || '—'}</td>
                <td>${r.comida_salida || '—'}</td>
                <td>${r.comida_entrada || '—'}</td>
                <td>${r.salida || '—'}</td>
                <td>${r.hours.toFixed(2)}</td>
                <td>
                  ${r.missing? '<span class="badge-mini bad">Falta</span>' : ''}
                  ${r.retardoMin>0? `<span class="badge-mini warn">+${r.retardoMin}m</span>` : ''}
                  ${r.extraHrs>0? `<span class="badge-mini ok">+${r.extraHrs.toFixed(1)}h</span>` : ''}
                  ${r.lunchLateMin>0? `<span class="badge-mini warn">comida +${r.lunchLateMin}m</span>` : ''}
                  ${r.note? `<div style="font-size:10.5px;color:var(--muted);margin-top:2px;">📝 ${r.note}</div>` : ''}
                </td>
                <td><button class="edit-icon" data-edit='${JSON.stringify({employeeId:r.employeeId, employeeName:r.employeeName, dateStr:r.date, dateLabel:new Date(r.date+'T00:00:00').toLocaleDateString('es-MX',{day:'2-digit',month:'short'}), entrada:r.entrada, comida_salida:r.comida_salida, comida_entrada:r.comida_entrada, salida:r.salida, note:r.note})}'>✎</button></td>
              </tr>`).join('') : '<tr><td colspan="9" class="msg-empty">Sin registros en este periodo</td></tr>'}
            </tbody>
          </table>
        </div>
      `;
    } else if(state.adminTab==='empleados'){
      content = `
        <div class="row"><input type="text" id="newname" placeholder="Nombre del empleado" /></div>
        <div class="row">
          <input type="text" id="newpin" placeholder="PIN de 4 dígitos" maxlength="4" />
        </div>
        <div class="row">
          <select id="newcategory">
            ${state.categories.map(c=>`<option value="${c.value}" ${c.value==='trabajador'?'selected':''}>${c.label}</option>`).join('')}
          </select>
        </div>
        <div class="row">
          <div style="flex:1;"><label style="font-size:11px;color:var(--muted);">Entrada esperada</label><input type="time" id="newschedin" /></div>
          <div style="flex:1;"><label style="font-size:11px;color:var(--muted);">Salida esperada</label><input type="time" id="newschedout" /></div>
        </div>
        <div class="row">
          <div style="flex:1;"><label style="font-size:11px;color:var(--muted);">Minutos para comer</label><input type="number" id="newlunchmin" min="0" /></div>
        </div>
        <div class="note" style="margin-top:-4px;">Los horarios y minutos de comida se llenan solos según la categoría — puedes ajustarlos si este empleado es distinto.</div>
        <div class="row" style="margin-top:10px;"><button class="btn" id="btn-addemp" style="flex:1;">Agregar empleado</button></div>
        <div style="margin-top:6px;">
          ${state.employees.length? state.employees.map(e=>`
            <div class="emp-item">
              <span>${e.name}
                <span class="cat-badge ${e.category||'trabajador'}">${CATEGORY_LABEL[e.category]||'Trabajador'}</span>
                <br/><span class="pin">${e.sched_in}–${e.sched_out} · comida ${e.lunch_minutes||90} min</span>
              </span>
              <span style="display:flex;align-items:center;gap:12px;">
                <span class="pin">PIN ${e.pin}</span>
                <button class="small-btn" data-del="${e.id}">Eliminar</button>
              </span>
            </div>`).join('') : '<div class="msg-empty">Aún no hay empleados</div>'}
        </div>
      `;
    } else if(state.adminTab==='permisos'){
      const typeLabels = {medica:'Médica / fuerza mayor', personal:'Personal', permiso_economico:'Permiso económico', vacaciones:'Vacaciones'};
      const statusLabels = {pendiente:'Pendiente', aprobada:'Aprobada', rechazada:'Rechazada'};
      const statusClass = {pendiente:'warn', aprobada:'ok', rechazada:'bad'};
      content = `
        <div class="field-label" style="text-align:left;">Registrar permiso, incapacidad o vacaciones</div>
        <div class="row">
          <select id="just-emp">
            <option value="">Selecciona empleado…</option>
            ${state.employees.map(e=>`<option value="${e.id}" data-name="${e.name}">${e.name}</option>`).join('')}
          </select>
        </div>
        <div class="row">
          <div style="flex:1;"><label style="font-size:11px;color:var(--muted);">Desde</label><input type="date" id="just-start" /></div>
          <div style="flex:1;"><label style="font-size:11px;color:var(--muted);">Hasta</label><input type="date" id="just-end" /></div>
        </div>
        <div class="row">
          <select id="just-type">
            <option value="vacaciones">Vacaciones</option>
            <option value="medica">Médica / fuerza mayor</option>
            <option value="personal">Personal</option>
            <option value="permiso_economico">Permiso económico</option>
          </select>
          <select id="just-status">
            <option value="aprobada">Aprobada</option>
            <option value="pendiente">Pendiente</option>
            <option value="rechazada">Rechazada</option>
          </select>
        </div>
        <div class="row"><input type="text" id="just-note" placeholder="Nota (opcional)" /></div>
        <div class="row"><button class="btn" id="btn-addjust" style="flex:1;">Guardar</button></div>
        <div class="note">Esto reemplaza la bitácora de WhatsApp: cuando apruebes un permiso aquí, los días dentro del rango dejan de contar como falta sin justificar en Registros.</div>

        <div style="margin-top:18px;">
          ${state.justifications.length? state.justifications.map(j=>`
            <div class="emp-item" style="align-items:flex-start;">
              <span style="flex:1;">
                <b>${j.employee_name}</b><br/>
                <span style="font-size:11px;color:var(--muted);">
                  ${new Date(j.date_start+'T00:00:00').toLocaleDateString('es-MX',{day:'2-digit',month:'short'})}
                  ${j.date_end!==j.date_start? ' al '+new Date(j.date_end+'T00:00:00').toLocaleDateString('es-MX',{day:'2-digit',month:'short'}) : ''}
                  — ${typeLabels[j.type]||j.type}
                  ${j.note? ' · '+j.note : ''}
                </span>
              </span>
              <span style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
                <span class="badge-mini ${statusClass[j.status]}">${statusLabels[j.status]||j.status}</span>
                <span style="display:flex;gap:6px;">
                  ${j.status!=='aprobada'? `<button class="small-btn" style="color:var(--accent);" data-just-status="${j.id}" data-status="aprobada">Aprobar</button>` : ''}
                  ${j.status!=='rechazada'? `<button class="small-btn" data-just-status="${j.id}" data-status="rechazada">Rechazar</button>` : ''}
                  <button class="small-btn" data-just-del="${j.id}">Eliminar</button>
                </span>
              </span>
            </div>`).join('') : '<div class="msg-empty">Aún no hay permisos registrados</div>'}
        </div>
      `;
    } else if(state.adminTab==='calendario'){
      const monthNames = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
      const dowLabels = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
      let grid = '';
      if(state.calendarEmployeeId && state.calendarDays.length){
        const firstWeekday = state.calendarDays[0].weekday === 6 ? 0 : state.calendarDays[0].weekday + 1;
        const leadingBlanks = Array.from({length:firstWeekday}).map(()=>'<div class="cal-day empty"></div>').join('');
        const dayCells = state.calendarDays.map(d=>`<div class="cal-day ${d.status}" title="${d.date}">${d.day}</div>`).join('');
        grid = `
          <div class="cal-header">
            <button class="cal-nav" id="cal-prev">‹</button>
            <span class="label">${monthNames[state.calendarMonth-1]} ${state.calendarYear}</span>
            <button class="cal-nav" id="cal-next">›</button>
          </div>
          <div class="cal-grid">
            ${dowLabels.map(l=>`<div class="cal-dow">${l}</div>`).join('')}
            ${leadingBlanks}${dayCells}
          </div>
          <div class="cal-legend">
            <div class="cal-legend-item"><span class="cal-legend-dot" style="background:var(--accent);"></span>Asistió</div>
            <div class="cal-legend-item"><span class="cal-legend-dot" style="background:var(--danger);"></span>Falta</div>
            <div class="cal-legend-item"><span class="cal-legend-dot" style="background:var(--warn);"></span>Permiso justificado</div>
            <div class="cal-legend-item"><span class="cal-legend-dot" style="background:#E5E7EB;"></span>No laboral</div>
          </div>
        `;
      } else {
        grid = '<div class="msg-empty">Elige un empleado para ver su calendario</div>';
      }
      content = `
        <div class="field-label" style="text-align:left;">Selecciona un empleado</div>
        <div class="row">
          <select id="cal-emp">
            <option value="">Elige empleado…</option>
            ${state.employees.map(e=>`<option value="${e.id}" ${state.calendarEmployeeId===e.id?'selected':''}>${e.name}</option>`).join('')}
          </select>
        </div>
        ${grid}
      `;
    } else if(state.adminTab==='qr'){
      content = `
        <div class="field-label">Este es el enlace que deben escanear los empleados</div>
        <div class="qr-box">
          <div id="qrcanvas"></div>
          <div class="note" style="text-align:center;font-family:var(--mono);">${window.location.origin}</div>
          <div class="note">Imprime este código y colócalo donde los empleados puedan escanearlo con su celular al llegar. Deben estar conectados a la misma red WiFi que esta computadora.</div>
        </div>
      `;
    } else if(state.adminTab==='config'){
      content = `
        <div class="field-label" style="text-align:left;">Minutos permitidos para comer</div>
        <div class="row">
          <input type="number" id="lunchmin" value="${state.lunchMinutes}" min="0" />
          <button class="btn secondary" id="btn-savelunch">Guardar</button>
        </div>
        <div class="note">Si alguien tarda más de este tiempo entre "salida a comer" y "regreso de comer", se marcará en el reporte.</div>

        <div class="field-label" style="text-align:left;margin-top:22px;">Cambiar contraseña de administrador</div>
        <div class="row">
          <input type="password" id="newpass" placeholder="Nueva contraseña" />
          <button class="btn" id="btn-savepass">Guardar</button>
        </div>

        <div class="field-label" style="text-align:left;margin-top:22px;">Código de recuperación</div>
        <div class="summary-card" style="text-align:center;">
          <div class="summary-total" style="letter-spacing:0.08em;font-size:19px;">${state.recoveryCode || '—'}</div>
        </div>
        <div class="row"><button class="btn ghost" id="btn-newrecovery" style="flex:1;">Generar código nuevo</button></div>
        <div class="note">Guárdalo en un lugar seguro fuera del sistema (una nota, tu teléfono). Si olvidas la contraseña de administrador, este código es lo único que permite restablecerla desde la pantalla de acceso.</div>
      `;
    }

    root.innerHTML = `
      <div class="wrap">
        <div class="admin-header">
          <h2>Panel de administración</h2>
          <button class="admin-link" id="btn-exit">Salir</button>
        </div>
        <div class="tabs">
          ${tabs.map(t=>`<button class="tab-btn ${state.adminTab===t?'active':''}" data-tab="${t}">${labels[t]}</button>`).join('')}
        </div>
        <div class="card body-pad">${content}</div>
      </div>
    `;

    document.getElementById('btn-exit').onclick = ()=>{ state.view='clock'; render(); };
    root.querySelectorAll('[data-tab]').forEach(b=>{
      b.onclick = async ()=>{ state.adminTab = b.getAttribute('data-tab'); state.editTarget=null; await loadAdminTab(); render(); };
    });

    if(state.adminTab==='registros'){
      document.getElementById('f-date').onchange = async (e)=>{ state.filterDate=e.target.value; await loadAdminTab(); render(); };
      document.getElementById('f-emp').onchange = async (e)=>{ state.filterEmp=e.target.value; await loadAdminTab(); render(); };
      root.querySelectorAll('[data-period]').forEach(b=>{
        b.onclick = async ()=>{ state.reportPeriod = b.getAttribute('data-period'); await loadAdminTab(); render(); };
      });
      root.querySelectorAll('[data-resolve-alert]').forEach(b=>{
        b.onclick = async ()=>{
          await api('/api/admin/device-alerts/resolve', {method:'POST', body: JSON.stringify({id: b.getAttribute('data-resolve-alert')})});
          await loadAdminTab();
          render();
        };
      });
      document.getElementById('btn-export').onclick = ()=>{
        const q = `?period=${state.reportPeriod}&date=${state.filterDate}&emp=${encodeURIComponent(state.filterEmp)}`;
        const url = '/api/admin/export.csv'+q;
        fetch(url, {headers:{'X-Admin-Pass': state.adminPass}}).then(r=>r.blob()).then(blob=>{
          const link = document.createElement('a');
          link.href = URL.createObjectURL(blob);
          link.download = 'registros_asistencia.csv';
          link.click();
        });
      };
      root.querySelectorAll('[data-edit]').forEach(b=>{
        b.onclick = ()=>{ state.editTarget = JSON.parse(b.getAttribute('data-edit')); render(); };
      });
      const saveEdit = document.getElementById('btn-save-edit');
      if(saveEdit) saveEdit.onclick = async ()=>{
        const t = state.editTarget;
        const edits = {
          entrada: document.getElementById('edit-entrada').value,
          comida_salida: document.getElementById('edit-comida_salida').value,
          comida_entrada: document.getElementById('edit-comida_entrada').value,
          salida: document.getElementById('edit-salida').value,
        };
        const note = document.getElementById('edit-note').value;
        await api('/api/admin/manual-edit', {method:'POST', body: JSON.stringify({employeeId:t.employeeId, employeeName:t.employeeName, dateStr:t.dateStr, edits, note})});
        state.editTarget = null;
        toast('Horario actualizado');
        await loadAdminTab();
        render();
      };
      const cancelEdit = document.getElementById('btn-cancel-edit');
      if(cancelEdit) cancelEdit.onclick = ()=>{ state.editTarget=null; render(); };
    }

    if(state.adminTab==='empleados'){
      const catSelect = document.getElementById('newcategory');
      const applyCategoryDefaults = ()=>{
        const cat = state.categories.find(c=>c.value===catSelect.value);
        if(cat){
          document.getElementById('newschedin').value = cat.schedIn;
          document.getElementById('newschedout').value = cat.schedOut;
          document.getElementById('newlunchmin').value = cat.lunchMinutes;
        }
      };
      if(catSelect){ catSelect.onchange = applyCategoryDefaults; applyCategoryDefaults(); }

      document.getElementById('btn-addemp').onclick = async ()=>{
        const name = document.getElementById('newname').value.trim();
        const pin = document.getElementById('newpin').value.trim();
        const category = document.getElementById('newcategory').value;
        const schedIn = document.getElementById('newschedin').value;
        const schedOut = document.getElementById('newschedout').value;
        const lunchMinutes = document.getElementById('newlunchmin').value;
        const r = await api('/api/admin/employees', {method:'POST', body: JSON.stringify({name, pin, category, schedIn, schedOut, lunchMinutes})});
        if(r.ok){ await loadAdminTab(); render(); } else { toast(r.error || 'Error'); }
      };
      root.querySelectorAll('[data-del]').forEach(b=>{
        b.onclick = async ()=>{
          await api('/api/admin/employees/'+b.getAttribute('data-del'), {method:'DELETE'});
          await loadAdminTab();
          render();
        };
      });
    }

    if(state.adminTab==='permisos'){
      document.getElementById('btn-addjust').onclick = async ()=>{
        const sel = document.getElementById('just-emp');
        const empId = sel.value;
        const empName = sel.selectedOptions[0] ? sel.selectedOptions[0].getAttribute('data-name') : '';
        const dateStart = document.getElementById('just-start').value;
        const dateEnd = document.getElementById('just-end').value || dateStart;
        const type = document.getElementById('just-type').value;
        const status = document.getElementById('just-status').value;
        const note = document.getElementById('just-note').value;
        if(!empId || !dateStart){ toast('Selecciona empleado y fecha de inicio'); return; }
        const r = await api('/api/admin/justifications', {method:'POST', body: JSON.stringify({employeeId:empId, employeeName:empName, dateStart, dateEnd, type, status, note})});
        if(r.ok){ toast('Permiso guardado'); await loadAdminTab(); render(); } else { toast(r.error || 'Error'); }
      };
      root.querySelectorAll('[data-just-status]').forEach(b=>{
        b.onclick = async ()=>{
          await api('/api/admin/justifications/status', {method:'POST', body: JSON.stringify({id:b.getAttribute('data-just-status'), status:b.getAttribute('data-status')})});
          await loadAdminTab();
          render();
        };
      });
      root.querySelectorAll('[data-just-del]').forEach(b=>{
        b.onclick = async ()=>{
          await api('/api/admin/justifications/'+b.getAttribute('data-just-del'), {method:'DELETE'});
          await loadAdminTab();
          render();
        };
      });
    }

    if(state.adminTab==='calendario'){
      document.getElementById('cal-emp').onchange = async (e)=>{
        state.calendarEmployeeId = e.target.value;
        await loadAdminTab();
        render();
      };
      const prevBtn = document.getElementById('cal-prev');
      const nextBtn = document.getElementById('cal-next');
      if(prevBtn) prevBtn.onclick = async ()=>{
        state.calendarMonth -= 1;
        if(state.calendarMonth < 1){ state.calendarMonth = 12; state.calendarYear -= 1; }
        await loadAdminTab();
        render();
      };
      if(nextBtn) nextBtn.onclick = async ()=>{
        state.calendarMonth += 1;
        if(state.calendarMonth > 12){ state.calendarMonth = 1; state.calendarYear += 1; }
        await loadAdminTab();
        render();
      };
    }

    if(state.adminTab==='qr'){
      const box = document.getElementById('qrcanvas');
      if(box){ box.innerHTML=''; try{ new QRCode(box, {text: window.location.origin, width:190, height:190, colorDark:'#1F2937', colorLight:'#ffffff'}); }catch(e){} }
    }

    if(state.adminTab==='config'){
      document.getElementById('btn-savelunch').onclick = async ()=>{
        const v = document.getElementById('lunchmin').value;
        await api('/api/admin/config', {method:'POST', body: JSON.stringify({lunchMinutes:v})});
        state.lunchMinutes = v; toast('Guardado');
      };
      document.getElementById('btn-savepass').onclick = async ()=>{
        const v = document.getElementById('newpass').value.trim();
        if(v.length<4){ toast('Usa al menos 4 caracteres'); return; }
        await api('/api/admin/config', {method:'POST', body: JSON.stringify({password:v})});
        state.adminPass = v;
        toast('Contraseña actualizada');
        document.getElementById('newpass').value='';
      };
      document.getElementById('btn-newrecovery').onclick = async ()=>{
        const r = await api('/api/admin/config', {method:'POST', body: JSON.stringify({generateRecovery:true})});
        state.recoveryCode = r.recoveryCode || '';
        toast('Código de recuperación regenerado');
        render();
      };
    }
  }

  function init(){ render(); }
  init();
  setInterval(()=>{
    const el = document.getElementById('livetime');
    if(el) el.textContent = fmtTime(new Date());
  }, 1000);
})();
