/* Presence Attendance multi-tenant admin console — no third-party frontend dependencies. */
'use strict';
const ICONS = {
  shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  calendar:'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  alert:'<path d="m10.29 3.86-8.47 14.14A2 2 0 0 0 3.53 21h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4m0 4h.01"/>',
  monitor:'<rect x="2" y="3" width="20" height="15" rx="2"/><path d="M8 21h8M12 18v3"/>',
  clipboard:'<rect x="8" y="4" width="13" height="18" rx="2"/><path d="M16 4.5V3a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v1.5M3 8v12a2 2 0 0 0 2 2h3"/>',
  palette:'<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 22a10 10 0 1 1 10-10c0 1.1-.9 2-2 2h-2.5a2.5 2.5 0 0 0-2.5 2.5V18a4 4 0 0 1-4 4Z"/>',
  settings:'<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06-2.86 2.86-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.01 1.55V21h-4v-.06A1.7 1.7 0 0 0 8.99 19.4a1.7 1.7 0 0 0-1.87.34l-.06.06-2.86-2.86.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1.01H3v-4h.06A1.7 1.7 0 0 0 4.6 8.99a1.7 1.7 0 0 0-.34-1.87L4.2 7.06 7.06 4.2l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.54V3h4v.06a1.7 1.7 0 0 0 1.01 1.54 1.7 1.7 0 0 0 1.87-.34l.06-.06 2.86 2.86-.06.06A1.7 1.7 0 0 0 19.4 9a1.7 1.7 0 0 0 1.54 1.01H21v4h-.06A1.7 1.7 0 0 0 19.4 15Z"/>',
  check:'<path d="m20 6-11 11-5-5"/>',plus:'<path d="M12 5v14M5 12h14"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  logout:'<path d="M10 17l5-5-5-5m5 5H3m9-9h6a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3h-6"/>',
  download:'<path d="M12 3v12m-4-4 4 4 4-4M4 17v3h16v-3"/>',
  chevron:'<path d="m9 18 6-6-6-6"/>',
  search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
  lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  wifi:'<path d="M2 8.5a16 16 0 0 1 20 0M5 12a11 11 0 0 1 14 0m-11 3.5a6 6 0 0 1 8 0M12 19h.01"/>',
  arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5 9a8 8 0 0 1 14-2l1 5M4 12l1 5a8 8 0 0 0 14-2"/>',
  activity:'<path d="M3 12h4l3-7 4 14 3-7h4"/>',
};
function icon(name, size = 18) { return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.grid}</svg>`; }
function esc(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const $=(s,b=document)=>b.querySelector(s);
const PORTAL=document.querySelector('meta[name="presence-portal"]')?.content||'platform';
const COMPANY_URL='http://localhost:8082', PLATFORM_URL='http://localhost:8080', KIOSK_URL='http://localhost:8081';
const state={token:sessionStorage.getItem('presence_admin_token'),user:null,page:'dashboard',data:{},theme:'enterprise-dark',
  unread:0,counts:{},notifItems:[],lastNotif:null,calendarEmployee:null,calendarMonth:new Date().toISOString().slice(0,7),
  enabledSound:localStorage.getItem('presence_sound')==='on',busy:false};
const THEMES=[
  ['enterprise-dark','Enterprise Dark','Deep navy · mint','#0a1825','#2bdbb1'],
  ['clean-light','Clean Enterprise','Cloud white · blue','#f7f9fe','#2976e4'],
  ['modern-indigo','Modern Indigo','Violet · midnight','#15172e','#9476ff'],
  ['security-command','Security Command','Charcoal · crimson','#141a22','#f16571'],
  ['corporate-neutral','Corporate Neutral','Warm ivory · cocoa','#f9f6f1','#aa7755'],
  ['midnight-azure','Midnight Azure','Ocean ink · cyan','#071928','#27bded'],
  ['forest-pro','Forest Pro','Emerald · pine','#0d211e','#5ad9a0'],
  ['sandstone','Sandstone','Stone · amber','#f7f1e7','#bb7b3b'],
  ['ocean-blue','Ocean Blue','Blue · teal','#eaf5fa','#1689ad'],
  ['rose-quartz','Rose Quartz','Blush · wine','#fff5f5','#bd6378'],
  ['graphite','Graphite','Slate · ice','#14171d','#b1c7d5'],
  ['high-contrast','High Contrast','Black · bright gold','#090909','#ffdf33']
];
const COMPANY_NAV=[['dashboard','Dashboard','grid'],['employees','Employees','users'],['attendance','Attendance Records','calendar'],
  ['alerts','Security Alerts','alert'],['devices','Kiosk Fleet','monitor'],['audit','Audit Logs','clipboard'],
  ['themes','Theme Studio','palette'],['status','System Status','activity'],['billing','Subscription','clock'],['settings','Settings','settings']];
const SUPER_NAV=[['dashboard','Platform Overview','grid'],['companies','Companies','users'],['employees','All Employees','users'],['attendance','All Attendance','calendar'],
  ['orders','Orders & Payments','clipboard'],['alerts','Security Alerts','alert'],['audit','Audit Logs','activity'],
  ['backups','Backup Center','download'],['status','System Status','activity'],['themes','Theme Studio','palette'],['settings','Settings','settings']];
const isSuper=()=>state.user?.role==='superadmin';
const nav=()=>isSuper()?SUPER_NAV:COMPANY_NAV;
const root=()=>isSuper()?'/super':'/portal';
const correctRole=u=>u?.role===(PORTAL==='platform'?'superadmin':'company_admin');
const zone=()=>state.user?.company?.timezone||'Asia/Dubai';
function dateText(d){if(!d)return '—';return new Date(d).toLocaleString('en-AE',{timeZone:zone(),dateStyle:'medium',timeStyle:'short'});}
function shortDate(d){if(!d)return '—';return new Date(d).toLocaleDateString('en-AE',{timeZone:zone(),month:'short',day:'numeric'});}
async function api(path,options={}){
 const response=await fetch('/api'+path,{...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),
   ...(state.token?{'Authorization':'Bearer '+state.token}:{}),...(options.headers||{})}});
 const contentType=response.headers.get('content-type')||'';
 const data=contentType.includes('json')?await response.json():null;
 if(!response.ok){if(response.status===401 && !['/auth/login','/public/register'].includes(path)){logout(false);throw Error('Your session expired. Sign in again.');}
   throw Error(data?.detail||`Request failed (${response.status})`);}
 return data;
}
function applyTheme(theme,config={}){if(THEMES.some(t=>t[0]===theme)){state.theme=theme;document.body.dataset.theme=theme;}
 if(config.font_family)document.documentElement.style.setProperty('--ui-font',config.font_family);
 if(config.density)document.body.dataset.density=config.density;
 const a=config.accent_override;document.body.style.removeProperty('--accent');document.body.style.removeProperty('--accent-rgb');
 if(/^#[0-9a-fA-F]{6}$/.test(a||'')){document.body.style.setProperty('--accent',a);document.body.style.setProperty('--accent-rgb',[1,3,5].map(i=>parseInt(a.slice(i,i+2),16)).join(','));}}
function toast(message,error=false){$('#toast')?.remove();const node=document.createElement('div');node.id='toast';node.className='toast'+(error?' error':'');node.textContent=message;document.body.append(node);setTimeout(()=>node.remove(),5500);}
function logout(announce=true){state.token=null;state.user=null;state.lastNotif=null;clearInterval(state.poller);sessionStorage.removeItem('presence_admin_token');document.title='Presence Attendance';authScreen();if(announce)toast('Signed out.');}
function authScreen(mode='login'){
 const register=mode==='register'&&PORTAL==='company';$('#app').innerHTML=`<div class="auth-page"><section class="auth-card"><div class="auth-symbol">${icon('shield',28)}</div>
 <div class="eyebrow">PRESENCE ATTENDANCE · ${PORTAL==='platform'?'PLATFORM ADMIN':'COMPANY PORTAL'}</div><h1>${register?'Create your company workspace':'Welcome back'}</h1>
 <p class="top-desc">${register?'Register your business and choose how you want to get started.':PORTAL==='platform'?'Manage the platform, companies, subscriptions, and service operations.':'Manage your employees, attendance, and company devices.'}</p>
 <div id="login-error"></div>${register?`<form id="register-form" class="auth-form">
 <div class="form-field"><label>Company name</label><input class="input" name="company_name" required minlength="3" maxlength="160" placeholder="Kings Palace Real Estate"></div>
 <div class="form-field"><label>Company URL name (slug)</label><input class="input" name="slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" minlength="3" placeholder="kings-palace"></div>
 <div class="form-field"><label>Business email</label><input class="input" name="email" type="email" required placeholder="hr@example.com"></div>
 <div class="form-field"><label>Admin username</label><input class="input" name="username" required pattern="[A-Za-z0-9_.-]+" minlength="3" autocomplete="username"></div>
 <div class="form-field"><label>Password (12+ characters)</label><input class="input" type="password" name="password" required minlength="12" autocomplete="new-password"></div>
 <div class="form-field"><label>Plan</label><select name="plan" class="select"><option value="trial">Free trial — 7 days</option><option value="monthly">Monthly — AED 100 / 30 days</option><option value="annual">Annual — AED 1,000 / 365 days</option></select></div>
 <input type="hidden" name="timezone" value="Asia/Dubai"><button class="btn btn-primary full" type="submit">Create workspace ${icon('arrow',17)}</button></form>`:
 `<form id="login-form" class="auth-form"><div class="form-field"><label>Username</label><input class="input" name="username" autocomplete="username" required></div>
 <div class="form-field"><label>Password</label><input class="input" name="password" type="password" autocomplete="current-password" required></div>
 <button class="btn btn-primary full" type="submit">Sign in ${icon('arrow',17)}</button></form>`}
 <div class="auth-foot">${PORTAL==='company'?`${register?'Already registered?':'New company?'} <button type="button" class="mini-link" data-action="auth-${register?'login':'register'}">${register?'Sign in':'Register company'}</button>`:`Company administrator? <a class="mini-link" href="${COMPANY_URL}">Company Portal</a>`}</div></section></div>`;
}
function modal(title,description,contents){$('#dialog')?.remove();const b=document.createElement('div');b.id='dialog';b.className='modal-backdrop';b.innerHTML=`<div class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}"><h2>${esc(title)}</h2><p>${esc(description)}</p>${contents}</div>`;document.body.append(b);b.addEventListener('click',e=>{if(e.target===b)b.remove();});}
function closeModal(){$('#dialog')?.remove();}
function btn(label,action,id='',style=''){return `<button class="btn btn-sm ${style}" data-action="${action}" data-id="${esc(id)}">${label}</button>`;}
function pill(text,kind=''){return `<span class="badge ${kind}">${esc(text)}</span>`;}
function metric(label,value,detail,ic='activity'){return `<div class="metric-card"><div class="metric-icon">${icon(ic,22)}</div><div><div class="metric-title">${esc(label)}</div><div class="metric-value">${esc(value)}</div><div class="metric-sub">${esc(detail)}</div></div></div>`;}
function card(title,content,sub=''){return `<section class="card"><div class="card-header"><div><div class="card-title">${esc(title)}</div>${sub?`<div class="card-sub">${esc(sub)}</div>`:''}</div></div>${content}</section>`;}
function empty(msg='No records yet'){return `<div class="empty-state">${esc(msg)}</div>`;}
function table(headers,rows){return `<div class="table-wrap"><table class="data-table"><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr><td colspan="${headers.length}">${empty('No matching records')}</td></tr>`}</tbody></table></div>`;}
function tr(...cols){return `<tr>${cols.map(c=>`<td>${c}</td>`).join('')}</tr>`;}
function subscriptionBanner(){const s=state.user?.company?.subscription;if(!s)return '';
 if(['active','trial'].includes(s.status))return `<div class="subscription-strip">${icon('clock',16)} ${s.status==='trial'?'Free trial':'Subscription active'} · ${esc(s.days_remaining)} days remaining · Expires ${esc(shortDate(s.ends_at))} <button class="mini-link" data-page="billing">Manage plan</button></div>`;
 return `<div class="subscription-strip danger-strip">${icon('alert',17)} Access ${esc(s.status)}. Renew your subscription to enable attendance and enrollments. <button class="mini-link" data-page="billing">View plans</button></div>`;
}
const META={dashboard:['Dashboard','Live attendance and operational insights'],companies:['Registered Companies','Company workspaces, owners and subscriptions'],status:['System Status','Application availability, database, and active kiosk connections'],
 employees:['Employees','Register employees, review enrollment and monthly attendance'],attendance:['Attendance Records','All attendance transactions and verification methods'],
 alerts:['Security Alerts','Review rejected kiosk attempts'],devices:['Kiosk Fleet','Manage company terminals and building locations'],
 audit:['Audit Logs','Audit trail of attendance and administration'],themes:['Theme Studio','Customize your company portal and kiosks'],
 billing:['Billing & Subscriptions','Plans, checkout requests and renewal'],orders:['Subscription Orders','Review pending local checkout requests'],
 backups:['Backup Center','Encrypted database backups and cloud destinations'],settings:['Settings','Account access and notification preferences'],
 calendar:['Employee Attendance','Monthly check-in and check-out history']};
function shell(){const [title,originalSubtitle]=META[state.page]||META.dashboard;const subtitle=isSuper()&&state.page==='themes'?'Choose an appearance for the platform console':originalSubtitle;const username=state.user?.username||'Admin';
 $('#app').innerHTML=`<div class="app-shell"><aside class="sidebar"><div class="brand"><span class="brand-icon">${icon('shield',26)}</span><div><div class="brand-text">Presence<span>Attendance</span></div><div class="brand-sub">${isSuper()?'PLATFORM ADMIN':'COMPANY WORKSPACE'}</div></div></div>
 <div class="portal-quicklinks"><a href="${PLATFORM_URL}" ${PORTAL==='platform'?'aria-current="page"':''}>Platform</a><a href="${COMPANY_URL}" ${PORTAL==='company'?'aria-current="page"':''}>Company</a><a href="${KIOSK_URL}">Kiosk</a></div><div class="workspace-name">${esc(state.user?.company?.name||(isSuper()?'Platform Operations':'Workspace'))}</div>
 <nav class="nav-group" aria-label="Main navigation"><div class="nav-label">NAVIGATION</div>${nav().map(([id,label,symbol])=>`<button class="nav-btn ${state.page===id?'active':''}" data-page="${id}">${icon(symbol)}<span>${label}</span>${state.counts[id]?`<span class="nav-count">${state.counts[id]>99?'99+':state.counts[id]}</span>`:''}</button>`).join('')}</nav>
 <div class="nav-tail"><div class="tail-title">${icon('activity',16)} ${isSuper()?'Platform Overview':'Company Workspace'}</div><div class="tail-desc">${isSuper()?'Manage registered organizations and plans.':'Employee and kiosk access are managed within your company.'}</div></div></aside>
 <main class="main"><header class="topbar"><div><div class="crumb">PRESENCE ATTENDANCE / ${isSuper()?'PLATFORM':'COMPANY'} / ${esc(title.toUpperCase())}</div><h1 class="top-title">${esc(title)}</h1><div class="top-desc">${esc(subtitle)}</div></div>
 <div class="top-actions"><div class="date-pill">${icon('calendar',15)} ${new Date().toLocaleDateString('en-AE',{day:'numeric',month:'short',year:'numeric'})}</div>
 <div class="notifications-wrap"><button class="notification-bell" data-action="notifications" title="Notifications" aria-label="Notifications">${icon('alert',20)}<span id="bell-count" class="notification-count" ${!state.unread?'hidden':''}>${state.unread||''}</span></button><div id="notification-panel" class="notification-panel" hidden></div></div>
 <div class="profile-pill"><span class="avatar">${esc(username[0].toUpperCase())}</span><div class="profile-info">${esc(username)}<small>${isSuper()?'Super Admin':'Company Admin'}</small></div></div>
 <button class="icon-plain" data-action="logout" aria-label="Sign out" title="Sign out">${icon('logout',18)}</button></div></header>
 ${!isSuper()?subscriptionBanner():''}<div id="page-content">${renderPage()}</div></main></div>`;
 updateNotificationUI();
}
function rowsAttendance(data,superMode=false){return table(superMode?['Employee','Company','Time','Action','Method','Kiosk']:['Employee','Department','Time','Action','Method','Kiosk'],
 data.map(x=>tr(`<strong>${esc(x.full_name)}</strong><div class="cell-muted">${esc(x.employee_code)}</div>`,
   esc(superMode?x.company:x.department),esc(dateText(x.recorded_at)),
   pill(x.action==='check_in'?'Check-in':'Check-out',x.action==='check_in'?'good':'warn'),pill(x.method.toUpperCase()),esc(x.device))));}
function chartBars(values){const max=Math.max(1,...values.map(v=>v.count));return `<div class="bar-series">${values.map(v=>`<div class="bar-column" title="${esc(v.day)} · ${v.count} check-ins"><span>${v.count||''}</span><div class="bar-fill" style="height:${Math.max(5,Math.round(v.count/max*100))}%"></div><small>${esc(v.day.slice(5))}</small></div>`).join('')}</div>`;}
function dashboard(){const d=state.data.dashboard||{};if(isSuper())return `<div class="metrics">${metric('Companies',d.companies||0,'Registered organizations','users')}${metric('Active plans',d.active||0,'Trial and paid','check')}${metric('Employees',d.employees||0,'Across all workspaces','users')}${metric('Pending orders',d.pending_orders||0,'Awaiting review','clock')}</div>
 <div class="dashboard-grid">${card('Recent company registrations',table(['Company','Status','Plan'],(d.companies_recent||[]).map(c=>tr(`<strong>${esc(c.name)}</strong><div class="cell-muted">${esc(c.slug)}</div>`,pill(c.subscription.status,c.subscription.status==='active'?'good':'warn'),esc(c.subscription.plan||'—')))))}
 ${card('Activity at a glance',`<div class="summary-figure">${esc(d.events||0)}<span>Total attendance events</span></div><p class="top-desc">${esc(d.devices||0)} kiosks registered across ${esc(d.companies||0)} companies.</p><button class="btn" data-page="companies">Manage companies ${icon('arrow',15)}</button>`)}
 <div class="full-span">${card('Latest attendance',rowsAttendance(d.recent||[],true))}</div></div>`;
 return `<div class="metrics">${metric('Employees',d.total||0,'Active team members','users')}${metric('Checked in',d.present||0,'Currently clocked in','check')}${metric('Not checked in',d.absent_or_offsite||0,'Current check-in state','clock')}${metric('Kiosks',d.devices||0,'Registered terminals','monitor')}</div>
 <div class="dashboard-grid">${card('Attendance trend',chartBars(d.trend||[]),'Check-ins during the last 14 days')}
 ${card('Today’s overview',`<div class="donut-row"><div class="donut" style="--p:${d.total?Math.round(d.present/d.total*100):0};--q:0"><div class="donut-hole"><strong>${d.total?Math.round(d.present/d.total*100):0}%</strong><span>Checked in</span></div></div><div class="legend"><div class="legend-item">Checked in <strong>${d.present||0}</strong></div><div class="legend-item">Not checked in <strong>${d.absent_or_offsite||0}</strong></div><div class="legend-item">Events today <strong>${d.today_events||0}</strong></div></div></div>`)}
 <div class="full-span">${card('Recent activity',rowsAttendance(d.recent||[]))}</div></div>`;
}
function companiesPage(){const data=state.data.companies||[];return `<div class="section-head"><div class="toolbar"><div class="search">${icon('search',16)}<input class="input" id="table-search" placeholder="Search companies…"></div>${pill(`${data.length} organizations`)}</div><button class="btn btn-primary" data-action="super-register-company">${icon('plus',16)} Register Company</button></div>
 ${card('Company directory',`<div id="filterable">${table(['Company','Owner email','Staff','Kiosks','Subscription','Expiry','Actions'],data.map(c=>tr(`<strong>${esc(c.name)}</strong><div class="cell-muted">${esc(c.slug)}</div>`,esc(c.email),esc(c.employees),esc(c.devices),pill(c.subscription.status,['active','trial'].includes(c.subscription.status)?'good':'warn'),shortDate(c.subscription.ends_at),
 `<div class="row-actions">${btn('Reset admin password','company-admins',c.id)}${btn('Grant plan','grant',c.id)}${btn(c.enabled?'Suspend':'Enable','company-status',c.id,c.enabled?'btn-danger':'')}</div>`)))}</div>`)} `;}
function employeesPage(){const data=state.data.employees||[];if(isSuper())return `<div class="section-head"><div class="toolbar"><div class="search">${icon('search',16)}<input id="table-search" class="input" placeholder="Search employees…"></div>${pill(data.length+' employees')}</div></div>${card('Employees across companies',`<div id="filterable">${table(['Employee','Company','Department','Portal Account','Actions'],data.map(e=>tr(`<strong>${esc(e.full_name)}</strong><div class="cell-muted">${esc(e.employee_code)}</div>`,esc(e.company),esc(e.department),pill(e.portal_password_set?'Enabled':'Not set'),btn('Reset portal password','super-employee-password',e.id))))}</div>`)}`;return `<div class="section-head"><div class="toolbar"><div class="search">${icon('search',16)}<input id="table-search" class="input" placeholder="Search employees…"></div>${pill(data.length+' employees')}<a class="btn" href="${KIOSK_URL}/employee.html">Employee history sign-in</a></div><button class="btn btn-primary" data-action="new-employee">${icon('plus',17)} Add Employee</button></div>
 ${card('Employee directory',`<div id="filterable">${table(['Employee','Department','Status','Face enrollment','Attendance','Actions'],data.map(e=>tr(`<strong>${esc(e.full_name)}</strong><div class="cell-muted">${esc(e.employee_code)}</div>`,esc(e.department),pill(e.active?'Active':'Inactive',e.active?'good':'danger'),pill(e.biometric_enrolled?'Enrolled':'Not enrolled',e.biometric_enrolled?'good':''),
 btn('View month','calendar',e.id),`<div class="row-actions">${btn('Edit','edit-employee',e.id)}${btn('Reset PIN','reset-pin',e.id)}${btn('Reset portal password','employee-password',e.id)}${e.biometric_enrolled?btn('Remove Face','delete-face',e.id,'btn-danger'):''}</div>`)))}</div>`)} `;}
function attendancePage(){const rows=state.data.attendance||[];return `<div class="section-head"><div class="toolbar"><div class="search">${icon('search',16)}<input id="table-search" class="input" placeholder="Search attendance…"></div>${pill(rows.length+' recent events')}</div><button class="btn btn-primary" data-action="export-csv">${icon('download',16)} Export CSV</button></div>
 ${card('Attendance transactions',`<div id="filterable">${rowsAttendance(rows,isSuper())}</div>`)} `;}
function devicesPage(){const data=state.data.devices||[];return `<div class="section-head">${pill(data.length+' kiosks')}<button class="btn btn-primary" data-action="new-device">${icon('plus',16)} Register Kiosk</button></div>${card('Kiosk fleet',table(['Device','Location','Status','Last seen','Actions'],data.map(d=>tr(`<strong>${esc(d.name)}</strong>`,esc(d.location),pill(d.online?'Online':d.status,d.online?'good':d.status==='revoked'?'danger':''),dateText(d.last_seen),
 `<div class="row-actions">${d.status==='revoked'?'':btn('Pair code','pair-code',d.id)}${btn('Revoke','revoke',d.id,'btn-danger')}</div>`))))}`;}
function auditPage(){const rows=state.data.audit||[];return card('Audit events',table(isSuper()?['Actor','Action','Company ID','Details','Time']:['Actor','Action','Details','Time'],rows.map(x=>tr(esc(x.actor),esc(x.action),...(isSuper()?[esc(x.company_id||'Platform')]:[]),esc(x.detail),dateText(x.created_at)))));}
function alertsPage(){const rows=state.data.alerts||[];return card('Security events',table(isSuper()?['Type','Company ID','Detail','Time']:['Type','Detail','Time'],rows.map(x=>tr(pill(x.kind,'warn'),...(isSuper()?[esc(x.company_id||'Platform')]:[]),esc(x.detail),dateText(x.created_at)))));}
function themesPage(){return `<div class="theme-grid">${THEMES.map(([id,name,desc,bg,accent])=>`<button class="theme-tile ${state.theme===id?'chosen':''}" data-action="select-theme" data-id="${id}"><div class="theme-preview" style="background:${bg}"><i style="background:${accent}"></i><span style="background:${accent}"></span><div></div><div></div></div><strong>${esc(name)}</strong><small>${esc(desc)}</small>${state.theme===id?`<span class="badge good">Active</span>`:''}</button>`).join('')}</div>${isSuper()?'':card('Customize appearance',`<form id="customize-form" class="customize-form"><div class="form-field"><label>Accent color</label><input type="color" name="accent_override" value="${esc(state.data.themes?.accent_override||'#1adc9b')}"></div><div class="form-field"><label>Font</label><select class="select" name="font_family">${['Inter','Arial','Georgia','Verdana','Tahoma','system-ui'].map(f=>`<option value="${f}" ${state.data.themes?.font_family===f?'selected':''}>${f}</option>`).join('')}</select></div><div class="form-field"><label>Layout density</label><select class="select" name="density"><option value="comfortable" ${state.data.themes?.density!=='compact'?'selected':''}>Comfortable</option><option value="compact" ${state.data.themes?.density==='compact'?'selected':''}>Compact</option></select></div><button class="btn btn-primary" type="submit">Apply customization</button></form>`,'Overrides apply to this company and all its kiosks.')}`; }
function billingPage(){const d=state.data.billing||{subscription:state.user?.company?.subscription,orders:[]};const s=d.subscription||{status:'pending'};
 return `<div class="metrics plan-summary">${metric('Current status',(s.status||'pending').toUpperCase(),s.plan||'No active plan','check')}${metric('Days remaining',s.days_remaining||0,'Until subscription expires','clock')}${metric('Renewal date',s.ends_at?shortDate(s.ends_at):'—','Expiry checked on every request','calendar')}</div>
 <div class="pricing-grid"><div class="pricing-card"><div class="eyebrow">FREE TRIAL</div><h2>7 Days</h2><div class="price">AED 0</div><p>Automatically activated on first registration. One trial per workspace.</p></div>
 <div class="pricing-card featured"><div class="eyebrow">MONTHLY</div><h2>30 Days</h2><div class="price">AED 100</div><p>Attendance, employee and kiosk access for 30 days.</p><button class="btn btn-primary" data-action="cart" data-id="monthly">Add to cart</button></div>
 <div class="pricing-card"><div class="eyebrow">ANNUAL</div><h2>365 Days</h2><div class="price">AED 1,000</div><p>Annual subscription with continued company access.</p><button class="btn btn-primary" data-action="cart" data-id="annual">Add to cart</button></div></div>
 <div class="notice-inline">${icon('alert',17)} Local checkout demonstration: no card is charged. All subscription orders remain pending until the platform administrator manually approves them.</div>
 ${card('Your checkout history',table(['Reference','Plan','AED','Status','Submitted'],(d.orders||[]).map(o=>tr(esc(o.reference),esc(o.plan),esc(o.amount_aed),pill(o.status,o.status==='approved'?'good':'warn'),dateText(o.created_at)))))} `;}
function ordersPage(){const data=state.data.orders||[];return card('Local checkout requests',table(['Reference','Company','Plan','AED','Status','Created','Actions'],data.map(o=>tr(esc(o.reference),esc(o.company),esc(o.plan),esc(o.amount_aed),pill(o.status,o.status==='approved'?'good':'warn'),dateText(o.created_at),
 o.status==='pending'?`<div class="row-actions">${btn('Approve','order-approve',o.id,'btn-primary')}${btn('Reject','order-reject',o.id,'btn-danger')}</div>`:'—'))));}
function backupsPage(){const d=state.data.backups||{files:[]};return `<div class="metrics">${metric('Local backups',(d.files||[]).length,'Encrypted archive files','download')}${metric('Daily schedule',d.scheduled?'Configured':'Not configured','Use the scheduler described in README','clock')}${metric('Cloud destination',d.cloud_enabled?'S3 configured':'Off','Optional external storage','wifi')}</div>
 <div class="notice-inline">${icon('lock',18)} Backups are encrypted on the application host. To download to your PC, choose Download below. Automatic Windows local backups require the included scheduler script.</div>
 ${card('Encrypted SQL backup archives',table(['Archive','Size','Created','Download'],(d.files||[]).map(f=>tr(esc(f.name),(f.bytes/1024).toFixed(1)+' KB',dateText(f.modified_at),btn('Download','backup-download',f.name)))))} `;}
function statusPage(){const d=state.data.status||{};
 const row=(name,value)=>`<div class="status-row"><strong>${esc(name)}</strong>${pill(value,value==='operational'||value==='Online'||value==='Ready'?'good':'warn')}</div>`;
 return `<div class="metrics">${metric('API',d.api||'Unverified','Live status via authenticated API','activity')}${metric('MySQL',d.database||'Unverified','Database connection test','check')}${metric('Online kiosks',d.kiosks_online??'—',`${d.kiosks_registered??'—'} registered`,`monitor`)}${metric('Face models',d.face_matching_available?'Ready':'Unavailable','Matching models only; liveness is not validated','shield')}</div>
 ${card('Service health',`${row('SuperAdmin website',d.web_portals?.platform_portal||'unavailable')}${row('Company website',d.web_portals?.company_portal||'unavailable')}${row('Attendance website',d.web_portals?.attendance_portal||'unavailable')}${row('Application API',d.api||'unknown')}${row('Database',d.database||'unknown')}${row('Face recognition models',d.face_matching_available?'Ready':'Not installed')}${row('Anti-spoof / liveness','Not certified')}<p class="form-hint">Checks represent API/database connectivity and recent kiosk heartbeats, not biometric accuracy or external website uptime.</p><a class="btn" href="/status.html">Open public status page ${icon('arrow',15)}</a>`)} `;
}
function settingsPage(){return `<div class="settings-grid">${card('Update password',`<form id="password-form"><div class="form-field"><label>Current password</label><input class="input" name="current_password" type="password" required></div><div class="form-field"><label>New password (12+ characters)</label><input class="input" name="new_password" type="password" minlength="12" required></div><button class="btn btn-primary" type="submit">Update password</button></form>`)}
 ${card('Real-time notifications',`<p class="top-desc">The console checks for new attendance and security events every four seconds. Alerts appear in the navigation and browser tab.</p><div class="settings-action"><button class="btn" data-action="sound-toggle">${icon('alert',16)} ${state.enabledSound?'Disable':'Enable'} notification sound</button><button class="btn" data-action="browser-permission">Enable desktop notifications</button></div><p class="form-hint">Sound requires a click to enable. Desktop notifications require browser permission and a secure context.</p>`)} </div>`;}
function calendarPage(){const d=state.data.calendar;
 if(!d)return empty('Choose an employee to view attendance.');const days=d.days||[],first=days[0]?.weekday||0;
 const slots=[...Array(first).fill(null),...days];while(slots.length%7)slots.push(null);
 const labels=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];return `<div class="section-head"><button class="btn" data-page="employees">${icon('chevron',16)} Back to Employees</button><div class="toolbar"><button class="btn btn-sm" data-action="month-prev">← Previous</button><strong>${esc(d.month)}</strong><button class="btn btn-sm" data-action="month-next">Next →</button></div></div>
 ${card(`${d.employee.full_name} · ${d.employee.employee_code}`,`<div class="calendar-legend"><span class="legend-chip complete">Complete day</span><span class="legend-chip incomplete">Open check-in</span><span class="legend-chip no_record">No record</span><span class="legend-chip weekend">Weekend</span></div>
 <div class="month-grid">${labels.map(x=>`<div class="month-day-label">${x}</div>`).join('')}${slots.map(x=>x?`<div class="month-cell ${x.status}" title="${esc(x.date)} · ${esc(x.status)}"><strong>${x.date.slice(-2)}</strong>${x.check_in?`<small>In ${esc(x.check_in)}</small>`:''}${x.check_out?`<small>Out ${esc(x.check_out)}</small>`:''}${!x.check_in?`<small>${x.status==='no_record'?'No record':x.status==='weekend'?'Weekend':x.status==='future'?'Upcoming':'—'}</small>`:''}</div>`:'<div class="month-cell month-blank"></div>').join('')}</div>
 <div class="form-hint">Times use ${esc(d.timezone)}. “No record” does not distinguish approved leave, holidays or absences.</div>`)} `;}
function renderPage(){switch(state.page){case 'dashboard':return dashboard();case 'companies':return companiesPage();case 'employees':return employeesPage();case 'attendance':return attendancePage();case 'alerts':return alertsPage();case 'devices':return devicesPage();case 'audit':return auditPage();case 'themes':return themesPage();case 'billing':return billingPage();case 'orders':return ordersPage();case 'backups':return backupsPage();case 'status':return statusPage();case 'settings':return settingsPage();case 'calendar':return calendarPage();default:return empty('Page not found');}}
async function navigate(page,silent=false){if(!nav().some(n=>n[0]===page) && page!=='calendar')return;state.page=page;
 const path={status:'/system-status',dashboard:isSuper()?'/overview':'/summary',employees:'/employees',attendance:'/attendance',alerts:'/security',devices:'/devices',audit:'/audit',themes:'/theme',billing:'/billing',orders:'/orders',companies:'/companies',backups:'/backups'}[page];
 try{
  if(page==='calendar' && state.calendarEmployee){state.data.calendar=await api(`/portal/employees/${state.calendarEmployee}/calendar?month=${encodeURIComponent(state.calendarMonth)}`);}
  else if(path){if(page==='themes'&&isSuper())state.data.themes={theme:state.theme};else state.data[page]=await api((page==='themes'?'/portal':root())+path);}
  if(page==='themes')applyTheme(isSuper()?state.theme:state.data.themes.theme,state.data.themes);
  shell();
 }catch(err){if(!silent)toast(err.message,true);if(err.message.includes('session expired'))return; $('#page-content')&&( $('#page-content').innerHTML=`<div class="empty-state">${esc(err.message)}</div>`);}
}
function employeeForm(emp){const edit=Boolean(emp);modal(edit?'Edit Employee':'Add Employee',edit?'Update employee details and access.':'Create the employee before face enrollment at the kiosk.',
 `<form id="employee-form" data-id="${emp?.id||''}"><div class="form-grid"><div class="form-field"><label>Employee ID</label><input class="input" name="employee_code" value="${esc(emp?.employee_code||'')}" required minlength="2" maxlength="32" pattern="[A-Za-z0-9_-]+" ${edit?'disabled':''}></div>
 <div class="form-field"><label>Department</label><input class="input" name="department" value="${esc(emp?.department||'')}" required></div><div class="form-field wide"><label>Full name</label><input class="input" name="full_name" value="${esc(emp?.full_name||'')}" required></div>
 ${edit?`<div class="form-field wide"><label>Status</label><select class="select" name="active"><option value="true" ${emp.active?'selected':''}>Active</option><option value="false" ${emp.active?'':'selected'}>Inactive</option></select></div>`:`<div class="form-field wide"><label>One-time registration PIN (4–12 digits)</label><input class="input" name="pin" type="password" autocomplete="off" pattern="[0-9]{4,12}" required></div>`}</div>
 <div class="form-foot"><button type="button" class="btn" data-action="close">Cancel</button><button type="submit" class="btn btn-primary">${edit?'Save changes':'Create employee'}</button></div></form>`);}
function deviceForm(){modal('Register Kiosk','Choose the building and terminal to register.',`<form id="device-form"><div class="form-field"><label>Kiosk name</label><input class="input" name="name" required placeholder="Main Entrance"></div><div class="form-field"><label>Building / location</label><input class="input" name="location" required placeholder="Building A · Reception"></div><div class="form-foot"><button type="button" class="btn" data-action="close">Cancel</button><button type="submit" class="btn btn-primary">Register & Pair</button></div></form>`);}
function pairModal(code){modal('One-time pairing code','Enter this code on the kiosk at localhost:8081. Expires after 10 minutes.',`<div class="code-box" id="pair-code">${esc(code)}</div><div class="form-foot"><button class="btn" data-action="copy-code">Copy code</button><button class="btn btn-primary" data-action="close">Done</button></div>`);}
function grantModal(id){modal('Grant Subscription','Select a plan for this company. This grants access without payment.',`<div class="choice-row">${btn('7-day trial','grant-submit',id+':trial')}${btn('30 days · AED 100','grant-submit',id+':monthly')}${btn('365 days · AED 1,000','grant-submit',id+':annual')}</div><div class="form-foot"><button class="btn" data-action="close">Close</button></div>`);}
function cartModal(plan){const amount=plan==='annual'?1000:100;modal('Subscription checkout','Local order request — no online payment will be taken.',`<div class="checkout-box"><strong>${plan==='annual'?'Annual · 365 days':'Monthly · 30 days'}</strong><span>AED ${amount.toLocaleString('en-AE')}</span></div><p class="top-desc">When you submit, your order becomes pending. A platform administrator must approve it. No card number or payment details are collected.</p><div class="form-foot"><button class="btn" data-action="close">Cancel</button><button class="btn btn-primary" data-action="checkout" data-id="${plan}">Submit order</button></div>`);}
async function downloadCsv(){const res=await fetch('/api'+root()+'/attendance/export',{headers:{Authorization:'Bearer '+state.token}});if(!res.ok)throw Error('Export failed');downloadBlob(await res.blob(),'presence-attendance.csv');}
function downloadBlob(blob,name){const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),2000);}
async function downloadBackup(name){const res=await fetch('/api/super/backups/'+encodeURIComponent(name),{headers:{Authorization:'Bearer '+state.token}});if(!res.ok)throw Error('Backup download failed');downloadBlob(await res.blob(),name);}
function updateNotificationUI(){document.title=(state.unread?`(${state.unread}) `:'')+'Presence Attendance';const el=$('#bell-count');if(el){el.textContent=state.unread>99?'99+':state.unread;el.hidden=!state.unread;}
 nav().forEach(([id])=>{const b=$(`[data-page="${id}"] .nav-count`);if(b)b.textContent=state.counts[id]||'';});
}
function notificationPanel(){const panel=$('#notification-panel');if(!panel)return;panel.hidden=!panel.hidden;
 if(!panel.hidden){panel.innerHTML=`<div class="notify-head"><strong>Notifications</strong><button class="mini-link" data-action="notifications-read">Mark all read</button></div><div class="notify-list">${state.notifItems.length?state.notifItems.slice().reverse().map(n=>`<div class="notify-item"><strong>${esc(n.title)}</strong><span>${esc(n.message)}</span><small>${esc(dateText(n.created_at))}</small></div>`).join(''):empty('No recent notifications')}</div>`;}}
let audioContext=null;
function beep(){if(!state.enabledSound)return;try{audioContext=audioContext||new (window.AudioContext||window.webkitAudioContext)();if(audioContext.state==='suspended')audioContext.resume();const osc=audioContext.createOscillator(),gain=audioContext.createGain();osc.type='sine';osc.frequency.value=760;gain.gain.value=0.05;osc.connect(gain);gain.connect(audioContext.destination);osc.start();osc.stop(audioContext.currentTime+.16);}catch{}}
async function poll(){if(!state.token)return;try{const data=await api('/notifications?after='+(state.lastNotif??0));
  const initialized=state.lastNotif!==null;state.unread=data.unread_count;state.counts=data.counts;
  if(initialized&&data.items?.length){const items=data.items.filter(n=>n.id>state.lastNotif);if(items.length){state.notifItems=[...state.notifItems,...items].slice(-30);const newest=items[items.length-1];beep();toast(newest.title+' · '+newest.message);
    if('Notification' in window && Notification.permission==='granted' && document.hidden){new Notification(newest.title,{body:newest.message});}
    if(['dashboard','attendance','employees','devices','alerts','companies','orders','billing','audit'].includes(state.page))await navigate(state.page,true);
  }}else if(!initialized){state.notifItems=data.items||[];}
  state.lastNotif=data.latest_id;updateNotificationUI();
 }catch(err){/* Transient network errors do not log users out except on 401. */}}
async function loginSuccess(login){state.token=login.access_token;sessionStorage.setItem('presence_admin_token',state.token);state.user=await api('/auth/me');
 applyTheme(isSuper()?localStorage.getItem('presence_platform_theme')||'enterprise-dark':state.user?.company?.theme||'enterprise-dark',state.user?.company||{});state.page=isSuper()?'dashboard':(['expired','pending','suspended'].includes(state.user.company?.subscription.status)?'billing':'dashboard');
 state.lastNotif=null;await navigate(state.page);await poll();clearInterval(state.poller);state.poller=setInterval(poll,4000);
}
async function init(){if(!state.token){authScreen();return;}try{const user=await api('/auth/me');if(!correctRole(user)){logout(false);return;}state.user=user;applyTheme(isSuper()?localStorage.getItem('presence_platform_theme')||'enterprise-dark':user.company?.theme||'enterprise-dark',user.company||{});
  if(!isSuper()&&['pending','expired','suspended'].includes(user.company.subscription.status))state.page='billing';
  await navigate(state.page);await poll();state.poller=setInterval(poll,4000);}catch{logout(false);}}
// Delegated handlers work with dynamic screens without leaking listeners on re-render.
document.addEventListener('click',async e=>{
 const navEl=e.target.closest('[data-page]');if(navEl){await navigate(navEl.dataset.page);return;}
 const el=e.target.closest('[data-action]');if(!el)return;const act=el.dataset.action,id=el.dataset.id;
 try{
  if(act==='logout')return logout();if(act==='auth-register')return authScreen('register');if(act==='auth-login')return authScreen();
  if(act==='close')return closeModal();if(act==='notifications')return notificationPanel();
  if(act==='notifications-read'){await api('/notifications/read',{method:'POST',body:JSON.stringify({last_seen_id:state.lastNotif||0})});$('#notification-panel').hidden=true;await poll();return;}
  if(act==='super-register-company')return modal('Register a company','Create a company workspace and its first administrator.',`<form id="super-register-form" class="auth-form"><div class="form-field"><label>Company name</label><input class="input" name="company_name" minlength="3" maxlength="160" required></div><div class="form-field"><label>Company slug</label><input class="input" name="slug" placeholder="example-company" pattern="[a-z0-9]+(-[a-z0-9]+)*" required></div><div class="form-field"><label>Business email</label><input class="input" type="email" name="email" required></div><div class="form-field"><label>Company admin username</label><input class="input" name="username" pattern="[A-Za-z0-9_.-]+" required></div><div class="form-field"><label>Initial admin password (12+ characters)</label><input class="input" type="password" name="password" minlength="12" required autocomplete="new-password"></div><div class="form-field"><label>Subscription</label><select class="select" name="plan"><option value="trial">7-day trial</option><option value="monthly">Monthly · awaiting manual approval</option><option value="annual">Annual · awaiting manual approval</option></select></div><input type="hidden" name="timezone" value="Asia/Dubai"><div class="form-foot"><button class="btn btn-primary" type="submit">Register company</button></div></form>`);
  if(act==='company-admins'){const admins=await api(`/super/companies/${id}/admins`);if(!admins.length)throw Error('No company administrator accounts found');return modal('Reset company administrator password','Choose the company administrator whose access you need to reset.',`<div class="choice-row">${admins.map(a=>btn('Reset '+esc(a.username),'admin-password',id+':'+a.id)).join('')}</div>`);}
  if(act==='admin-password'||act==='super-employee-password'||act==='employee-password'){
   const endpoint=act==='admin-password'?`/super/companies/${id.split(':')[0]}/admins/${id.split(':')[1]}/reset-password`:act==='super-employee-password'?(()=>{const e=(state.data.employees||[]).find(x=>x.id===Number(id));return e?`/super/companies/${e.company_id}/employees/${e.id}/reset-password`:null;})():`/portal/employees/${id}/reset-password`;
   if(!endpoint)throw Error('Record not found');return modal('Reset portal password','A new employee or company admin password invalidates previous sessions. It does not change attendance PINs.',`<form id="reset-password-form" data-endpoint="${esc(endpoint)}"><div class="form-field"><label>New password (12+ characters)</label><input class="input" type="password" name="password" minlength="12" maxlength="128" required autocomplete="new-password"></div><div class="form-foot"><button class="btn btn-primary" type="submit">Reset password</button></div></form>`);
  }
  if(act==='new-employee')return employeeForm();
  if(act==='edit-employee')return employeeForm((state.data.employees||[]).find(x=>x.id===Number(id)));
  if(act==='reset-pin')return modal('Reset employee PIN','The employee can use this PIN for one-time enrollment or attendance fallback.',`<form id="pin-form" data-id="${esc(id)}"><div class="form-field"><label>New PIN (4–12 digits)</label><input class="input" name="pin" pattern="[0-9]{4,12}" type="password" required></div><div class="form-foot"><button type="submit" class="btn btn-primary">Update PIN</button></div></form>`);
  if(act==='delete-face'){if(!confirm('Remove this employee’s face enrollment?'))return;await api(`/portal/employees/${id}/biometrics`,{method:'DELETE'});await navigate('employees');return toast('Face enrollment removed');}
  if(act==='calendar'){state.calendarEmployee=Number(id);state.calendarMonth=new Date().toISOString().slice(0,7);return navigate('calendar');}
  if(act==='month-prev'||act==='month-next'){const [year,month]=state.calendarMonth.split('-').map(Number);const date=new Date(Date.UTC(year,month-1+(act==='month-next'?1:-1),1));state.calendarMonth=date.toISOString().slice(0,7);return navigate('calendar');}
  if(act==='new-device')return deviceForm();
  if(act==='pair-code'){const r=await api(`/portal/devices/${id}/pair-code`,{method:'POST'});pairModal(r.pairing_code);return;}
  if(act==='revoke'){if(!confirm('Revoke this kiosk permanently?'))return;await api(`/portal/devices/${id}/revoke`,{method:'POST'});await navigate('devices');return;}
  if(act==='copy-code'){await navigator.clipboard.writeText($('#pair-code').textContent);return toast('Pairing code copied');}
  if(act==='grant')return grantModal(id);
  if(act==='grant-submit'){const [company,plan]=id.split(':');if(!confirm(`Grant ${plan} plan to company #${company}?`))return;await api(`/super/companies/${company}/grant`,{method:'POST',body:JSON.stringify({plan})});closeModal();await navigate('companies');return toast('Subscription granted');}
  if(act==='company-status'){const c=(state.data.companies||[]).find(x=>x.id===Number(id));if(!c||!confirm(`${c.enabled?'Suspend':'Enable'} ${c.name}?`))return;await api(`/super/companies/${id}/status`,{method:'POST',body:JSON.stringify({enabled:!c.enabled})});await navigate('companies');return;}
  if(act==='order-approve'||act==='order-reject'){if(!confirm(act==='order-approve'?'Confirm manual approval? No payment is verified.':'Reject this order?'))return;await api(`/super/orders/${id}/${act==='order-approve'?'approve':'reject'}`,{method:'POST'});await navigate('orders');return;}
  if(act==='cart')return cartModal(id);
  if(act==='checkout'){await api('/portal/orders',{method:'POST',body:JSON.stringify({plan:id})});closeModal();await navigate('billing');return toast('Order submitted for manual approval');}
  if(act==='select-theme'){if(isSuper()){localStorage.setItem('presence_platform_theme',id);}else{await api('/portal/theme',{method:'PUT',body:JSON.stringify({theme:id})});}applyTheme(id,state.data.themes||{});await navigate('themes');return toast(isSuper()?'Platform console theme updated':'Theme updated for your company and its kiosks');}
  if(act==='export-csv')return downloadCsv();if(act==='backup-download')return downloadBackup(id);
  if(act==='sound-toggle'){state.enabledSound=!state.enabledSound;localStorage.setItem('presence_sound',state.enabledSound?'on':'off');if(state.enabledSound)beep();await navigate('settings');return;}
  if(act==='browser-permission'){if(!('Notification' in window))throw Error('Desktop notifications are not supported by this browser');const permission=await Notification.requestPermission();return toast(`Browser notification permission: ${permission}`);}
 }catch(err){toast(err.message,true);}
});
document.addEventListener('input',e=>{if(e.target.id==='table-search'){const q=e.target.value.toLocaleLowerCase();$('#filterable')?.querySelectorAll('tbody tr').forEach(row=>row.style.display=row.textContent.toLocaleLowerCase().includes(q)?'':'none');}});
document.addEventListener('submit',async e=>{
 const form=e.target;if(!['register-form','login-form','employee-form','device-form','pin-form','password-form','customize-form','reset-password-form','super-register-form'].includes(form.id))return;e.preventDefault();
 const submit=form.querySelector('[type=submit]');if(submit?.disabled)return;if(submit)submit.disabled=true;
 try{const value=Object.fromEntries(new FormData(form));
  if(form.id==='super-register-form'){await api('/public/register',{method:'POST',body:JSON.stringify(value)});closeModal();await navigate('companies');return toast('Company workspace registered.');}
  if(form.id==='reset-password-form'){await api(form.dataset.endpoint,{method:'POST',body:JSON.stringify(value)});closeModal();return toast('Portal password reset. Previous sessions revoked.');}
  if(form.id==='register-form'){await api('/public/register',{method:'POST',body:JSON.stringify(value)});authScreen();return toast('Workspace registered. Sign in to continue.');}
  if(form.id==='login-form'){const data=await api('/auth/login',{method:'POST',body:JSON.stringify(value)});if(!correctRole(data))throw Error(PORTAL==='platform'?'This is a company account. Use the Company Portal at localhost:8082.':'This is a platform account. Use SuperAdmin at localhost:8080.');await loginSuccess(data);return;}
  if(form.id==='employee-form'){if(form.dataset.id){delete value.employee_code;value.active=value.active==='true';await api(`/portal/employees/${form.dataset.id}`,{method:'PATCH',body:JSON.stringify(value)});}else await api('/portal/employees',{method:'POST',body:JSON.stringify(value)});closeModal();await navigate('employees');return toast('Employee saved');}
  if(form.id==='device-form'){const r=await api('/portal/devices',{method:'POST',body:JSON.stringify(value)});pairModal(r.pairing_code);state.data.devices=await api('/portal/devices');return;}
  if(form.id==='pin-form'){await api(`/portal/employees/${form.dataset.id}/reset-pin`,{method:'POST',body:JSON.stringify(value)});closeModal();return toast('PIN updated');}
  if(form.id==='customize-form'){await api('/portal/theme',{method:'PUT',body:JSON.stringify(value)});await navigate('themes');return toast('Appearance saved');}
  if(form.id==='password-form'){await api('/auth/change-password',{method:'POST',body:JSON.stringify(value)});logout(false);return toast('Password updated. Sign in again.');}
 }catch(err){if(form.id==='register-form'||form.id==='login-form')$('#login-error').innerHTML=`<div class="error-msg">${esc(err.message)}</div>`;else toast(err.message,true);}
 finally{if(submit?.isConnected)submit.disabled=false;}
});
init();
