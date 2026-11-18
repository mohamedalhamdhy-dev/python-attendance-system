/* Presence Attendance Kiosk v2: real face embeddings with explicit one-time enrollment.
 * Face identification is PILOT-ONLY. No reliable anti-spoof / liveness certification.
 */
'use strict';
const $=(selector,root=document)=>root.querySelector(selector);
const state={
 deviceId:localStorage.getItem('presence_device_id'),token:localStorage.getItem('presence_device_token'),
 device:null,theme:'enterprise-dark',lang:localStorage.getItem('presence_lang')||'en',
 mode:'face',screen:'idle',videoStream:null,cameraReady:false,cameraError:'',cameraDevices:[],previewPromise:null,
 selectedCameraId:localStorage.getItem('presence_camera_id')||'',result:null,error:'',errorAction:'',busy:false,
 biometrics:{available:false,liveness_verified:false,enrolled_count:0}
};
const AVAILABLE_THEMES=['enterprise-dark','clean-light','modern-indigo','security-command','corporate-neutral','midnight-azure','forest-pro','sandstone','ocean-blue','rose-quartz','graphite','high-contrast'];
const T={
 en:{brand:'ATTENDANCE TERMINAL',pairTitle:'Pair this terminal',pairHelp:'Register a device in Admin → Kiosk Fleet and enter its one-time pairing code.',pairCode:'One-time pairing code',pair:'Pair Terminal',paired:'Paired terminal',switch:'Switch building / Unpair',switchConfirm:'Disconnect this terminal and invalidate its pairing credential? Ask the administrator for a new code to connect another building.',language:'عربي',hello:'ATTENDANCE MADE SIMPLE',title:'Just look at the camera.',desc:'Enroll your face once using employee ID + PIN. After that, scan your face for attendance without typing credentials.',time:'DUBAI LOCAL TIME',cameraTitle:'Live attendance camera',cameraOff:'Camera is off',cameraHelp:'Enable the camera to enroll or verify your face.',enableCamera:'Turn on camera',disableCamera:'Turn off',scan:'Scan face for attendance',enroll:'One-time face enrollment',pin:'Use ID + PIN',face:'Face check-in',status:'Recognition status',available:'Recognition model ready',unavailable:'Recognition not configured',antiSpoof:'Liveness / anti-spoofing',notVerified:'Not installed (pilot only)',warning:'Important: Face matching is real, but photo/replay attacks are NOT reliably blocked. Do not use for high-security attendance yet.',warningOff:'To enable face matching, install the two OpenCV models, configure the encryption key and restart the API. PIN check-in remains available.',enrollTitle:'One-time face registration',enrollDesc:'Enter your ID + PIN once, consent to biometric enrollment, then the camera will take three photos. No photos are saved; the face template is encrypted.',employee:'Employee ID',privatePin:'Private PIN',consent:'I explicitly consent to creating and storing an encrypted face template for attendance.',enrollNow:'Capture & enroll face',cancel:'Back to face check-in',pinTitle:'Manual PIN attendance',pinDesc:'Fallback method while face recognition is being enrolled or tested.',checkIn:'Check in',checkOut:'Check out',working:'Processing camera image…',capturing:'Capturing face sample',success:'Attendance recorded',successOut:'Check-out recorded',enrollSuccess:'Face enrolled successfully',enrollSuccessDesc:'Next time, use “Scan face for attendance” with no employee ID or PIN.',again:'New attendance',retry:'Try again',failed:'Verification unsuccessful',method:'Method',faceMatched:'Face identity matched',pinMatched:'Employee PIN checked',noLiveness:'Anti-spoof/liveness NOT verified',errorCamera:'Camera access requires permission and a secure connection (localhost or HTTPS).',network:'Local backend',footer:'Camera frames are sent to the local server for face matching. Raw photos are not retained.',offline:'Server unavailable',online:'Server connected'},
 ar:{brand:'جهاز تسجيل الحضور',pairTitle:'ربط جهاز الحضور',pairHelp:'سجّل جهازاً في لوحة الإدارة ← أجهزة الحضور، وأدخل رمز الربط لمرة واحدة.',pairCode:'رمز الربط',pair:'ربط الجهاز',paired:'الجهاز المرتبط',switch:'تغيير المبنى / إلغاء الربط',switchConfirm:'هل تريد إلغاء ربط الجهاز وإبطال بيانات الربط الحالية؟ ستحتاج إلى رمز جديد من المسؤول.',language:'English',hello:'الحضور بكل سهولة',title:'انظر إلى الكاميرا فقط.',desc:'سجّل وجهك مرة واحدة برقم الموظف ورمزه السري، ثم سجّل حضورك بوجهك فقط.',time:'توقيت دبي',cameraTitle:'كاميرا الحضور المباشرة',cameraOff:'الكاميرا متوقفة',cameraHelp:'شغّل الكاميرا لتسجيل الوجه أو التحقق منه.',enableCamera:'تشغيل الكاميرا',disableCamera:'إيقاف الكاميرا',scan:'التحقق بالوجه وتسجيل الحضور',enroll:'تسجيل الوجه مرة واحدة',pin:'الرقم الوظيفي والرمز السري',face:'حضور بالوجه',status:'حالة التحقق',available:'النموذج جاهز',unavailable:'التعرف على الوجه غير مُعدّ',antiSpoof:'التحقق من الحيوية ومنع الانتحال',notVerified:'غير متوفر — نسخة تجريبية',warning:'تنبيه: تتم مطابقة الوجه فعلياً، لكن لم يتم توفير الحماية الموثوقة ضد الصور أو الفيديو. لا تستخدمه للحضور عالي الحساسية.',warningOff:'لتفعيل التعرف على الوجه، ثبّت نموذجي OpenCV ومفتاح التشفير ثم أعد تشغيل الخادم.',enrollTitle:'تسجيل الوجه لأول مرة',enrollDesc:'أدخل رقمك الوظيفي ورمزك السري مرة واحدة ووافق على التسجيل؛ تُلتقط ثلاث صور ولا تُحفظ الصور الأصلية.',employee:'رقم الموظف',privatePin:'الرمز السري',consent:'أوافق صراحةً على تخزين قالب مشفّر لوجهي لتسجيل الحضور.',enrollNow:'التقاط وتسجيل الوجه',cancel:'العودة إلى التعرف على الوجه',pinTitle:'الحضور بواسطة الرمز السري',pinDesc:'الطريقة البديلة أثناء إعداد التحقق بالوجه.',checkIn:'تسجيل دخول',checkOut:'تسجيل خروج',working:'تتم معالجة صورة الوجه…',capturing:'التقاط عينة الوجه',success:'تم تسجيل الحضور',successOut:'تم تسجيل الانصراف',enrollSuccess:'تم تسجيل الوجه بنجاح',enrollSuccessDesc:'يمكنك لاحقاً التسجيل بالوجه فقط دون رقم الموظف أو الرمز السري.',again:'عملية حضور جديدة',retry:'إعادة المحاولة',failed:'فشل التحقق',method:'الطريقة',faceMatched:'تمت مطابقة الوجه',pinMatched:'تم التحقق من الرمز السري',noLiveness:'لم يتم التحقق من الحيوية',errorCamera:'يلزم إذن الكاميرا واتصال آمن (localhost أو HTTPS).',network:'الخادم المحلي',footer:'تُرسل صور الكاميرا إلى الخادم المحلي للمطابقة، ولا تُحفظ الصور الخام.',offline:'الخادم غير متاح',online:'الخادم متصل'}
};
T.en.cameraSelect='Camera';T.en.cameraUnavailable='Camera preview unavailable';T.en.cameraNoFrames='Camera connected, but no video frames were received.';
T.en.cameraAllowed='Allow camera access in your browser and Windows privacy settings.';
T.en.faceMethod='Face attendance';T.en.enrollMethod='Enroll face biometric';T.en.pinMethod='ID + PIN fallback';
T.en.noFaces='No faces enrolled for this company. Register your face first.';
T.en.registerAction='Register face now';T.en.alreadyEnrolled='This employee already has a registered face. Use Face attendance; ask your company administrator to reset an existing enrollment if needed.';
T.ar.cameraSelect='الكاميرا';T.ar.cameraUnavailable='تعذر عرض الكاميرا';T.ar.cameraNoFrames='تم الاتصال بالكاميرا، لكن لم تصل إطارات فيديو.';
T.ar.cameraAllowed='اسمح بالوصول للكاميرا من المتصفح وإعدادات خصوصية ويندوز.';
T.ar.faceMethod='الحضور بالوجه';T.ar.enrollMethod='تسجيل البيانات الحيوية';T.ar.pinMethod='الرقم والرمز البديل';
T.ar.noFaces='لم يتم تسجيل أي وجه لهذه الشركة. يرجى تسجيل وجهك أولاً.';
T.ar.registerAction='تسجيل الوجه الآن';T.ar.alreadyEnrolled='تم تسجيل وجه هذا الموظف مسبقاً. استخدم الحضور بالوجه أو اطلب من مسؤول الشركة إعادة التسجيل.';
const paths={shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',camera:'<path d="m23 7-7 5 7 5V7Z"/><rect x="1" y="5" width="15" height="14" rx="2"/>',scan:'<path d="M4 8V5a2 2 0 0 1 2-2h3M15 3h3a2 2 0 0 1 2 2v3M20 16v3a2 2 0 0 1-2 2h-3M9 21H6a2 2 0 0 1-2-2v-3"/><circle cx="12" cy="11" r="3"/>',check:'<path d="m20 6-11 11-5-5"/>',alert:'<path d="m10.29 3.86-8.47 14.14A2 2 0 0 0 3.53 21h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4m0 4h.01"/>',lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',logout:'<path d="M10 17l5-5-5-5m5 5H3m9-9h6a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3h-6"/>',arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'};
const ico=(name,size=19)=>`<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.shield}</svg>`;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=k=>T[state.lang][k]||k;
const clock=()=>new Date().toLocaleTimeString(state.lang==='ar'?'ar-AE':'en-AE',{timeZone:state.device?.timezone||'Asia/Dubai',hour:'2-digit',minute:'2-digit',hour12:true});
const date=()=>new Date().toLocaleDateString(state.lang==='ar'?'ar-AE':'en-AE',{timeZone:state.device?.timezone||'Asia/Dubai',day:'2-digit',month:'short',year:'numeric'});
const deviceHeaders=()=>({'X-Device-Id':state.deviceId||'', 'X-Device-Token':state.token||''});
async function api(route,options={}){
 const headers={...(options.body?{'Content-Type':'application/json'}:{}),...(route==='/kiosk/pair'?{}:deviceHeaders()),...(options.headers||{})};
 const response=await fetch('/api'+route,{...options,headers});
 let data;try{data=await response.json();}catch{data={};}
 if(!response.ok){
  if(response.status===401&&route==='/kiosk/device'){clearLocalPairing();}
  const error=new Error(typeof data.detail==='string'?data.detail:`Request failed (${response.status})`);
  error.status=response.status;error.route=route;throw error;
 }
 return data;
}
function theme(t,settings={}){if(AVAILABLE_THEMES.includes(t)){state.theme=t;document.body.dataset.theme=t;}
 document.documentElement.style.setProperty('--ui-font',settings.font_family||'Inter');document.body.dataset.density=settings.density||'comfortable';
 const a=settings.accent_override;document.body.style.removeProperty('--accent');document.body.style.removeProperty('--accent-rgb');
 if(/^#[a-fA-F0-9]{6}$/.test(a||'')){document.body.style.setProperty('--accent',a);document.body.style.setProperty('--accent-rgb',[1,3,5].map(i=>parseInt(a.slice(i,i+2),16)).join(','));}}
function stopCamera(){
 const stream=state.videoStream;state.videoStream=null;state.cameraReady=false;state.previewPromise=null;
 if(stream)stream.getTracks().forEach(track=>track.stop());
}
function cameraFailure(error){
 const name=error?.name||'';
 if(name==='NotAllowedError'||name==='PermissionDeniedError'||name==='SecurityError')return tr('cameraAllowed');
 if(name==='NotFoundError'||name==='DevicesNotFoundError')return 'No usable camera found. Connect or enable a webcam and try again.';
 if(name==='NotReadableError'||name==='TrackStartError')return 'Camera is busy or blocked by another app. Close other camera apps and retry.';
 if(name==='OverconstrainedError')return 'This camera is unavailable. Choose another camera and try again.';
 if(name==='AbortError')return 'Camera initialization was interrupted. Try again.';
 return error?.message||tr('cameraUnavailable');
}
async function discoverCameras(){
 if(!navigator.mediaDevices?.enumerateDevices)return;
 try{
  const devices=await navigator.mediaDevices.enumerateDevices();
  state.cameraDevices=devices.filter(x=>x.kind==='videoinput'&&x.deviceId).map((x,i)=>({id:x.deviceId,label:x.label||`Camera ${i+1}`}));
  const picker=$('#camera-device');
  if(picker){picker.innerHTML=state.cameraDevices.map((d,i)=>`<option value="${esc(d.id)}">${esc(d.label||`Camera ${i+1}`)}</option>`).join('');picker.value=state.selectedCameraId||state.cameraDevices[0]?.id||'';}
 }catch{/* Enumeration is optional: the default camera can still work. */}
}
async function bindCameraPreview(video,stream){
 if(!video||!stream)return;
 try{
  video.srcObject=stream;
  const start=video.play();
  await Promise.race([start,new Promise((_,reject)=>setTimeout(()=>reject(new Error(tr('cameraNoFrames'))),7500))]);
  if(video.readyState<2||!video.videoWidth||!video.videoHeight){
   await Promise.race([new Promise((resolve,reject)=>{video.addEventListener('loadeddata',resolve,{once:true});video.addEventListener('error',()=>reject(new Error('Unable to decode camera video.')),{once:true});}),new Promise((_,reject)=>setTimeout(()=>reject(new Error(tr('cameraNoFrames'))),7500))]);
  }
  if(state.videoStream!==stream||$('#camera-video')!==video)return;
  if(!stream.getVideoTracks().some(track=>track.readyState==='live')||!video.videoWidth||!video.videoHeight)throw new Error(tr('cameraNoFrames'));
  state.cameraReady=true;state.cameraError='';
  const overlay=$('#cam-placeholder');if(overlay)overlay.hidden=true;
  const feedback=$('#camera-error');if(feedback)feedback.hidden=true;
 }catch(error){
  if(state.videoStream!==stream||$('#camera-video')!==video)return;
  state.cameraError=cameraFailure(error);stopCamera();
  const overlay=$('#cam-placeholder');if(overlay)overlay.hidden=false;
  const title=$('#cam-placeholder-title');if(title)title.textContent=tr('cameraUnavailable');
  const help=$('#cam-placeholder-help');if(help)help.textContent=state.cameraError;
  const toggle=$('[data-action="camera"]');if(toggle)toggle.textContent=tr('enableCamera');
  banner(state.cameraError,true);
 }
}
function cameraPicker(){
 if(state.cameraDevices.length<2)return '';
 return `<label class="camera-picker"><span>${tr('cameraSelect')}</span><select id="camera-device" aria-label="${tr('cameraSelect')}">${state.cameraDevices.map((d,i)=>`<option value="${esc(d.id)}" ${state.selectedCameraId===d.id?'selected':''}>${esc(d.label||`Camera ${i+1}`)}</option>`).join('')}</select></label>`;
}
function explainKioskError(error,mode){
 state.errorAction='';
 if(error.status===409){
  if(/already enrolled/i.test(error.message)){state.errorAction='face';return tr('alreadyEnrolled');}
  if(/no enrolled faces/i.test(error.message)){state.errorAction='enroll';return tr('noFaces');}
 }
 if(mode==='camera')return cameraFailure(error);
 return error.message||'Verification could not be completed.';
}

function clearLocalPairing(){stopCamera();localStorage.removeItem('presence_device_id');localStorage.removeItem('presence_device_token');state.deviceId=null;state.token=null;state.device=null;state.mode='face';state.screen='idle';state.result=null;}
function banner(message,error=false){const el=$('#inline-message');if(el){el.textContent=message;el.className=error?'inline-message is-error':'inline-message';}}
function brand(){return `<div class="brand"><div class="brand-icon">${ico('shield',27)}</div><div class="brand-name">Presence Attendance<small>${tr('brand')}</small></div><a class="employee-shortcut" href="/employee.html">Employee attendance history</a></div>`;}
function flowContent(){
 if(state.screen==='enrolled')return `<section class="panel result-panel"><div class="result-icon">${ico('check',40)}</div><h2>${tr('enrollSuccess')}</h2><p>${tr('enrollSuccessDesc')}</p><button class="btn btn-primary" data-action="back-face">${ico('scan')} ${tr('face')}</button></section>`;
 if(state.screen==='success'&&state.result){const r=state.result;return `<section class="panel result-panel"><div class="result-icon">${ico('check',40)}</div><h2>${r.action==='check_out'?tr('successOut'):tr('success')}</h2><div class="result-name">${esc(r.full_name)}</div><div class="result-sub">${esc(r.employee_code)} · ${esc(r.department)}</div><div class="result-time">${esc(new Date(r.recorded_at).toLocaleString(state.lang==='ar'?'ar-AE':'en-AE',{timeZone:state.device?.timezone||'Asia/Dubai',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}))}</div><p>${tr('method')}: ${r.method==='face'?tr('faceMatched'):tr('pinMatched')}</p>${r.method==='face'?`<p class="result-warning">${tr('noLiveness')}</p>`:''}<button class="btn btn-primary" data-action="new">${tr('again')} ${ico('arrow')}</button></section>`;}
 if(state.screen==='error')return `<section class="panel result-panel"><div class="result-icon error">${ico('alert',40)}</div><h2>${tr('failed')}</h2><p>${esc(state.error)}</p>${state.errorAction==='enroll'?`<button class="btn btn-primary" data-action="mode-enroll">${tr('registerAction')} ${ico('arrow')}</button>`:state.errorAction==='face'?`<button class="btn btn-primary" data-action="mode-face">${tr('faceMethod')} ${ico('arrow')}</button>`:`<button class="btn btn-primary" data-action="new">${tr('retry')} ${ico('arrow')}</button>`}</section>`;
 if(state.mode==='face')return `<section class="panel flow-panel"><div class="eyebrow">01 / ${tr('face')}</div><h2>${tr('title')}</h2><p class="panel-desc">${tr('desc')}</p><div class="kiosk-status ${state.biometrics.available?'ready':'not-ready'}">${ico(state.biometrics.available?'check':'alert',18)}<span>${state.biometrics.available?(state.biometrics.enrolled_count===0?tr('noFaces'):tr('available')):tr('unavailable')}</span></div><button type="button" class="btn btn-primary full-width" data-action="scan" ${state.busy||!state.biometrics.available||state.biometrics.enrolled_count===0?'disabled':''}>${ico('scan',20)} ${tr('scan')}</button><div class="policy-note">${tr(state.biometrics.available?'warning':'warningOff')}</div></section>`;
 if(state.mode==='enroll')return `<section class="panel flow-panel"><div class="eyebrow">02 / ${tr('enroll')}</div><h2>${tr('enrollTitle')}</h2><p class="panel-desc">${tr('enrollDesc')}</p><form id="enroll-form"><div class="field"><label for="enroll-id">${tr('employee')}</label><input class="input" id="enroll-id" name="employee_code" placeholder="EMP-001" required minlength="2" maxlength="32" autocomplete="off"></div><div class="field"><label for="enroll-pin">${tr('privatePin')}</label><input class="input" id="enroll-pin" name="pin" type="password" inputmode="numeric" pattern="[0-9]{4,12}" required autocomplete="off"></div><label class="consent-row"><input type="checkbox" name="consent" required><span>${tr('consent')}</span></label><button class="btn btn-primary full-width" type="submit" ${state.busy||!state.biometrics.available?'disabled':''}>${ico('camera')} ${tr('enrollNow')}</button></form><button class="link-btn mode-back" data-action="back-face">${tr('cancel')}</button></section>`;
 return `<section class="panel flow-panel"><div class="eyebrow">03 / ${tr('pin')}</div><h2>${tr('pinTitle')}</h2><p class="panel-desc">${tr('pinDesc')}</p><form id="pin-form"><div class="field"><label for="employee-id">${tr('employee')}</label><input class="input" id="employee-id" name="employee_code" placeholder="EMP-001" required minlength="2" maxlength="32" autocomplete="off"></div><div class="field"><label for="employee-pin">${tr('privatePin')}</label><input class="input" id="employee-pin" name="pin" type="password" inputmode="numeric" pattern="[0-9]{4,12}" required autocomplete="off"></div><div class="button-row"><button class="btn btn-primary" type="submit" name="action" value="check_in">${ico('check')} ${tr('checkIn')}</button><button class="btn" type="submit" name="action" value="check_out">${ico('logout')} ${tr('checkOut')}</button></div></form><button class="link-btn mode-back" data-action="back-face">${tr('cancel')}</button></section>`;
}
function draw(){
 document.documentElement.lang=state.lang;document.documentElement.dir=state.lang==='ar'?'rtl':'ltr';
 if(!state.token){
  $('#app').innerHTML=`<div class="kiosk-shell"><header class="kiosk-header">${brand()}<button class="lang-button" data-action="lang">${tr('language')}</button></header><main class="pair-shell"><div class="panel"><div class="eyebrow">INITIAL SETUP</div><h1>${tr('pairTitle')}</h1><p>${tr('pairHelp')}</p><form id="pair-form"><div class="field"><label for="pair-code">${tr('pairCode')}</label><input class="input" id="pair-code" name="code" minlength="8" maxlength="128" autocomplete="off" required></div><div id="inline-message" class="inline-message ${state.error?'is-error':''}">${esc(state.error)}</div><button class="btn btn-primary full-width" type="submit">${ico('lock')} ${tr('pair')}</button></form></div></main><footer class="terminal-footer">${tr('network')} <span>${tr('footer')}</span></footer></div>`;
  return;
 }
 $('#app').innerHTML=`<div class="kiosk-shell"><header class="kiosk-header">${brand()}<div class="header-tools"><span class="header-chip"><span class="dot" id="online-dot"></span><span id="network-label">${tr('online')}</span></span><span class="header-chip location-chip">${ico('shield',15)} ${esc(state.device?.company||'')} · ${esc(state.device?.name||'Kiosk')} · ${esc(state.device?.location||'')}</span><button class="lang-button" data-action="lang">${tr('language')}</button><button class="lang-button exit-button" data-action="switch">${ico('logout',16)} ${tr('switch')}</button></div></header><main class="kiosk-main"><section class="camera-area"><div class="panel camera-panel"><video id="camera-video" playsinline autoplay muted></video><div class="cam-placeholder" id="cam-placeholder"><div class="cam-placeholder-icon">${ico('scan',49)}</div><h2 id="cam-placeholder-title">${state.cameraError?tr('cameraUnavailable'):tr('cameraOff')}</h2><p id="cam-placeholder-help">${esc(state.cameraError||tr('cameraHelp'))}</p></div><div class="scan-frame"><span class="scan-corner tl"></span><span class="scan-corner tr"></span><span class="scan-corner bl"></span><span class="scan-corner br"></span></div><div class="cam-overlay-top"><span class="camera-label">${ico('camera',15)} ${tr('cameraTitle')}</span>${cameraPicker()}<span class="camera-label">${esc(date())}</span></div><div class="cam-overlay-bottom"><span class="cam-hint">${tr('time')} · ${esc(clock())}</span><button class="cam-toggle" data-action="camera">${state.videoStream?tr('disableCamera'):tr('enableCamera')}</button></div></div><div class="camera-info"><div class="info-tile">${ico('scan',19)}<div><strong>${tr('status')}</strong><span>${state.biometrics.available?tr('available'):tr('unavailable')}</span></div></div><div class="info-tile">${ico('alert',19)}<div><strong>${tr('antiSpoof')}</strong><span>${tr('notVerified')}</span></div></div></div></section><section class="flow-area"><div class="welcome-title"><div class="eyebrow">${tr('hello')}</div><div class="welcome-heading"><h1>Presence <em>Attendance.</em></h1><span id="live-clock" class="big-clock">${esc(clock())}</span></div><p>${tr('desc')}</p></div><nav class="method-switch" aria-label="Attendance method"><button type="button" data-action="mode-face" aria-pressed="${state.mode==='face'}" class="${state.mode==='face'?'selected':''}">${ico('scan',15)} ${tr('faceMethod')}</button><button type="button" data-action="mode-enroll" aria-pressed="${state.mode==='enroll'}" class="${state.mode==='enroll'?'selected':''}">${ico('camera',15)} ${tr('enrollMethod')}</button><button type="button" data-action="mode-pin" aria-pressed="${state.mode==='pin'}" class="${state.mode==='pin'?'selected':''}">${ico('lock',15)} ${tr('pinMethod')}</button></nav><div id="flow-slot">${flowContent()}</div><div id="inline-message" class="inline-message" role="status" aria-live="polite"></div></section></main><footer class="terminal-footer"><span><span class="dot"></span> ${tr('paired')}: <strong>${esc(state.device?.company||'')}</strong> · ${esc(state.device?.name||'—')} · ${esc(state.device?.location||'')}</span><span>${tr('footer')}</span></footer></div>`;
 const video=$('#camera-video');if(video&&state.videoStream)state.previewPromise=bindCameraPreview(video,state.videoStream);
}
async function heartbeat(){if(!state.token)return;try{await api('/kiosk/heartbeat',{method:'POST'});const t=await api('/kiosk/theme');theme(t.theme,t);if($('#online-dot'))$('#online-dot').classList.remove('offline');if($('#network-label'))$('#network-label').textContent=tr('online');}catch(e){if($('#online-dot'))$('#online-dot').classList.add('offline');if($('#network-label'))$('#network-label').textContent=tr('offline');}}
async function startCamera(){
 if(state.videoStream){
  if(state.previewPromise)await state.previewPromise;
  if(state.cameraReady)return;
  stopCamera();
 }
 if(!navigator.mediaDevices?.getUserMedia)throw new Error(tr('errorCamera'));
 try{
  const videoConstraint={width:{ideal:640},height:{ideal:480},facingMode:'user'};
  if(state.selectedCameraId)videoConstraint.deviceId={exact:state.selectedCameraId};
  let stream;
  try{stream=await navigator.mediaDevices.getUserMedia({video:videoConstraint,audio:false});}
  catch(error){
   if(!state.selectedCameraId||!['NotFoundError','OverconstrainedError'].includes(error?.name))throw error;
   state.selectedCameraId='';localStorage.removeItem('presence_camera_id');
   delete videoConstraint.deviceId;
   stream=await navigator.mediaDevices.getUserMedia({video:videoConstraint,audio:false});
  }
  state.videoStream=stream;state.cameraError='';
  for(const track of stream.getVideoTracks())track.addEventListener('ended',()=>{
   if(state.videoStream===stream){state.cameraError='Camera disconnected. Reconnect it and turn on the camera again.';stopCamera();draw();}
  });
  await discoverCameras();
  draw();
  if(state.previewPromise)await state.previewPromise;
  if(!state.cameraReady)throw new Error(state.cameraError||tr('cameraNoFrames'));
 }catch(error){
  state.cameraError=cameraFailure(error);stopCamera();draw();
  throw new Error(state.cameraError);
 }
}
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function frame(){
 const video=$('#camera-video');
 if(!video||!state.videoStream||!state.cameraReady||video.readyState<2||!video.videoWidth||!video.videoHeight)throw new Error(tr('cameraNoFrames'));
 const width=640,height=Math.max(240,Math.min(960,Math.round(video.videoHeight*640/video.videoWidth)));
 const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
 canvas.getContext('2d',{alpha:false}).drawImage(video,0,0,width,height);
 return canvas.toDataURL('image/jpeg',0.78).split(',')[1];
}
async function prepareCamera(){await startCamera();await wait(350);}
async function refreshBio(){try{state.biometrics=await api('/kiosk/biometric-status');}catch(e){state.biometrics={available:false,liveness_verified:false,enrolled_count:0};}}
function resultScreen(result){state.result=result;state.screen='success';state.error='';draw();}
async function initialize(){if(state.token){try{state.device=await api('/kiosk/device');const settings=await api('/kiosk/theme');theme(settings.theme,settings);await refreshBio();}catch(e){if(!state.token)state.error='Previous pairing expired or revoked. Ask the administrator for another code.';else state.error=e.message;}}draw();}
document.addEventListener('click',async e=>{
 const btn=e.target.closest('[data-action]');if(!btn||state.busy)return;
 const action=btn.dataset.action;
 try{
  if(action==='lang'){state.lang=state.lang==='en'?'ar':'en';localStorage.setItem('presence_lang',state.lang);draw();}
  if(action==='camera'){if(state.videoStream){stopCamera();draw();}else await startCamera();}
  if(action==='mode-enroll'||action==='mode-pin'||action==='mode-face'||action==='back-face'){state.mode=action==='mode-enroll'?'enroll':action==='mode-pin'?'pin':'face';state.screen='idle';state.error='';state.errorAction='';draw();}
  if(action==='new'){state.screen='idle';state.error='';state.errorAction='';await refreshBio();draw();}
  if(action==='switch'){
   if(!confirm(tr('switchConfirm')))return;
   state.busy=true;
   try{await api('/kiosk/unpair',{method:'POST'});clearLocalPairing();draw();}
   finally{state.busy=false;}
  }
  if(action==='scan'){
   state.busy=true;
   try{await prepareCamera();banner(tr('working'));const image=await frame();const r=await api('/kiosk/biometric/identify',{method:'POST',body:JSON.stringify({image})});resultScreen(r);}
   finally{state.busy=false;}
  }
 }catch(err){state.error=explainKioskError(err,action==='camera'?'camera':'other');if(action==='camera'){banner(state.error,true);}else{state.screen='error';draw();}}
});
document.addEventListener('change',async event=>{
 if(event.target.id!=='camera-device'||state.busy)return;
 const id=event.target.value;
 if(id===state.selectedCameraId)return;
 state.selectedCameraId=id;localStorage.setItem('presence_camera_id',id);
 const wasRunning=Boolean(state.videoStream);stopCamera();draw();
 if(wasRunning){try{await startCamera();}catch(error){banner(cameraFailure(error),true);}}
});
document.addEventListener('submit',async e=>{
 if(!['pair-form','pin-form','enroll-form'].includes(e.target.id))return;
 e.preventDefault();if(state.busy)return;
 const form=e.target;state.busy=true;
 try{
  if(form.id==='pair-form'){
   const code=String(new FormData(form).get('code')||'').trim();
   const data=await api('/kiosk/pair',{method:'POST',body:JSON.stringify({code})});
   state.deviceId=String(data.device_id);state.token=data.device_token;
   localStorage.setItem('presence_device_id',state.deviceId);localStorage.setItem('presence_device_token',state.token);
   state.device=await api('/kiosk/device');{const preferences=await api('/kiosk/theme');theme(preferences.theme,preferences);}await refreshBio();state.error='';state.screen='idle';draw();
  }else if(form.id==='pin-form'){
   const formData=new FormData(form),action=e.submitter?.value||'check_in';
   resultScreen(await api('/kiosk/attendance',{method:'POST',body:JSON.stringify({employee_code:formData.get('employee_code'),pin:formData.get('pin'),action})}));
  }else{
   const formData=new FormData(form);
   if(!formData.get('consent'))throw new Error('Explicit biometric enrollment consent is required');
   const code=String(formData.get('employee_code')),pin=String(formData.get('pin'));
   await prepareCamera();const images=[];
   for(let i=0;i<3;i++){banner(`${tr('capturing')} ${i+1}/3`);await wait(850);images.push(await frame());}
   await api('/kiosk/biometric/enroll',{method:'POST',body:JSON.stringify({employee_code:code,pin,consent:true,images})});
   await refreshBio();state.mode='face';state.screen='enrolled';draw();
  }
 }catch(err){state.error=explainKioskError(err,form.id);state.screen=form.id==='pair-form'?'idle':'error';draw();}
 finally{state.busy=false;}
});
setInterval(()=>{if($('#live-clock'))$('#live-clock').textContent=clock();},1000);
setInterval(heartbeat,60000);
window.addEventListener('beforeunload',stopCamera);
initialize();
