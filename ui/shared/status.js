"use strict";
const checks=document.getElementById('check-list');
const checked=document.getElementById('last-checked');
function addRow(label,value,ok){const row=document.createElement('div');row.className='status-row';const title=document.createElement('strong');title.textContent=label;const result=document.createElement('span');result.className='badge '+(ok?'ok':'fail');result.textContent=value;row.append(title,result);checks.append(row);}
async function run(){checks.replaceChildren();addRow('This web portal','Accessible',true);
 try{const r=await fetch('/api/public/status',{cache:'no-store',signal:AbortSignal.timeout(6000)});
 if(!r.ok)throw Error('API response '+r.status);const data=await r.json();
 addRow('Attendance API',data.api||'Unknown',data.api==='operational');
 addRow('MySQL database',data.database||'Unknown',data.database==='operational');
 for(const [key,label] of [['platform_portal','SuperAdmin website'],['company_portal','Company website'],['attendance_portal','Attendance website']]){const value=data.web_portals?.[key]||'Unavailable';addRow(label,value,value==='operational');}
 addRow('Face recognition models',data.face_matching_available?'Available':'Not installed',!!data.face_matching_available);
 addRow('Verified anti-spoofing',data.liveness_certified?'Certified':'Not available',!!data.liveness_certified);
 }catch(error){addRow('Attendance API / Database','Unreachable',false);}checked.textContent='Last checked: '+new Date().toLocaleString();}
document.getElementById('refresh').addEventListener('click',run);run();setInterval(run,30000);
