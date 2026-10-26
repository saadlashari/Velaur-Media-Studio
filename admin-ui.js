// audit-light-render-1
(async()=>{
 const A=window.VelaurAccount,$=id=>document.getElementById(id);
 let settings=null,userOffset=0,auditOffset=0,action=null,busy=false;
 const error=e=>{$('accountError').textContent=e.message;};
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
 const views={overview:['Studio overview','A clear view of your accounts, activity and access settings.'],users:['User accounts','Find an account, review usage and manage access.'],trial:['Trial settings','Decide how users start and keep access to the studio.'],plans:['Plan limits','Set the processing allowance for Creator, Pro and Studio.'],audit:['Audit history','A record of administrative changes and the reason behind each one.']};
 let currentView='overview',selectedPlan='creator';
 function menu(open){const mobile=matchMedia('(max-width:800px)').matches,wasOpen=document.body.classList.contains('menu-open');document.body.classList.toggle('menu-open',open);$('adminMenu').setAttribute('aria-expanded',String(open));$('sidebarShade').hidden=!open;$('adminSidebar').inert=mobile&&!open;document.querySelector('.admin-body').inert=mobile&&open;if(mobile&&open)$('adminSidebar').querySelector('[aria-current]')?.focus();else if(mobile&&wasOpen)$('adminMenu').focus();}
 function showView(view,updateHash=true){
  if(!views[view])view='overview';currentView=view;
  document.querySelectorAll('[data-admin-view]').forEach(x=>x.hidden=x.dataset.adminView!==view);
  document.querySelectorAll('[data-view]').forEach(x=>{if(x.dataset.view===view)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current');});
  $('settingsActions').hidden=!['trial','plans'].includes(view);
  $('adminPageTitle').textContent=views[view][0];$('adminPageDescription').textContent=views[view][1];
  $('adminBreadcrumb').textContent=document.querySelector('[data-view="'+view+'"]').textContent.trim();
  if(updateHash)history.replaceState(null,'','#'+view);menu(false);
 }
 function showPlan(key){selectedPlan=key;document.querySelectorAll('[data-plan-panel]').forEach(x=>x.hidden=x.dataset.planPanel!==key);document.querySelectorAll('[data-plan]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.plan===key)));}
 document.querySelectorAll('[data-view],[data-open-view]').forEach(x=>x.addEventListener('click',()=>showView(x.dataset.view||x.dataset.openView)));
 $('adminMenu').addEventListener('click',()=>menu(!document.body.classList.contains('menu-open')));
 $('sidebarShade').addEventListener('click',()=>menu(false));
 document.addEventListener('keydown',e=>{if(e.key==='Escape')menu(false);});
 window.addEventListener('resize',()=>menu(false));
 window.addEventListener('hashchange',()=>showView(location.hash.slice(1),false));
 showView(location.hash.slice(1)||'overview',false);
 async function loadOverview(){
  const d=await A.request('/api/admin/overview');
  for(const [id,key]of [['overviewUsers','users'],['overviewActive','active'],['overviewBlocked','blocked'],['overviewExports','exports_today'],['overviewJobs','active_jobs']])$(id).textContent=d[key];
 }
 function overviewSettings(){
  $('overviewMode').textContent={timed:'Timed access',open:'Open access',paused:'Processing paused'}[settings.mode];
  $('overviewTrials').textContent=settings.new_trials?'Enabled':'Disabled';$('overviewTrialDays').textContent=settings.trial_days+' days';
 }
 const fields=[
 ['mp3_exports','MP3 exports/day (0 = unlimited)',0,10000],['exports','MP4 exports/day',1,1000],['previews','Preview preparations/day',1,2000],
 ['active','Active processing jobs',1,4],['upload_gb','Maximum upload (GB)',1,8],
 ['seconds','Export duration / 30 days (hours)',1,1000],['source_seconds','Maximum source (hours)',1,3]
 ];
 function renderSettings(){
  $('trialMode').value=settings.mode;$('trialDays').value=settings.trial_days;$('newTrials').value=String(settings.new_trials);
  const container=$('planControls');container.replaceChildren();$('planTabs').replaceChildren();overviewSettings();
  for(const [key,p] of Object.entries(settings.plans)){
   const tab=el('button',p.name);tab.type='button';tab.dataset.plan=key;tab.addEventListener('click',()=>showPlan(key));$('planTabs').append(tab);
   const group=el('section',undefined,'admin-plan-panel');group.dataset.planPanel=key;group.append(el('h3',p.name));group.append(el('p','$'+p.monthly+'/month or $'+p.yearly+'/year. Paid checkout is not enabled.'));
   const grid=el('div',undefined,'admin-form-grid');
   for(const [field,label,min,max] of fields){
    const wrap=el('label',label,'form-field');const input=document.createElement('input');
    input.type='number';input.min=min;input.max=max;input.required=true;input.step='1';
    input.id=key+'-'+field;input.value=field==='seconds'||field==='source_seconds'?p[field]/3600:p[field];
    wrap.append(input);grid.append(wrap);
   }
   const wrap=el('label','Maximum resolution','form-field'),select=document.createElement('select');select.id=key+'-height';
   for(const [value,text] of [[720,'720p'],[1080,'1080p'],[2160,'4K']]){const option=el('option',text);option.value=value;select.append(option);}
   select.value=p.height;wrap.append(select);grid.append(wrap);group.append(grid);container.append(group);
  }
  showPlan(selectedPlan);$('saveAdminSettings').disabled=false;
 }
 async function loadUsers(reset=false){
  if(reset){userOffset=0;$('adminUsers').replaceChildren();}
  const data=await A.request('/api/admin/users?q='+encodeURIComponent($('searchUsers').value)+'&offset='+userOffset+'&status='+encodeURIComponent($('userStatus').value));
  if(reset&&!data.users.length)$('adminUsers').textContent='No matching users.';
  for(const record of data.users){
   const u=record.user,usage=record.usage,access=record.access;
   const card=el('article',undefined,'user-card'),title=el('div',undefined,'user-title');
   const identity=el('div',undefined,'user-identity'),avatar=el('span',(u.name||u.email).trim().split(/\s+/).slice(0,2).map(v=>v[0]).join('').toUpperCase(),'user-avatar');
   const names=el('div');names.append(el('strong',u.name||'Studio user'),el('p',u.email));identity.append(avatar,names);title.append(identity);
   const badges=el('div',undefined,'user-badges');badges.append(el('span',u.role==='admin'?'Administrator':'User','status-badge'),el('span',u.status==='active'?'Active':'Blocked','status-badge '+(u.status==='blocked'?'blocked':'')));title.append(badges);card.append(title);
   const details=el('div',undefined,'user-detail-grid');
   for(const [label,value]of [['Signed up',A.when(u.created)],['Last login',A.when(u.last_login)],['Access',(access.plan||'Not activated')+' / '+(access.access_kind||'No access')],['Usage',A.hours(usage.used_seconds)+' exported']]){const line=el('div');line.append(el('span',label),el('strong',value));details.append(line);}
   card.append(el('p','MP3 today: '+(usage.mp3_exports_today||0)+' / '+(usage.mp3_limit==null?'Unlimited':usage.mp3_limit),'user-meta'));card.append(details);card.append(el('p','Access ends '+A.when(access.expires_at)+' · '+usage.exports_today+' exports today · '+usage.previews_today+' previews today','user-meta'));
   const actions=el('div',undefined,'user-actions');
   const inspect=el('button','Open user details','admin-button primary');inspect.type='button';inspect.dataset.inspectUser=u.id;actions.append(inspect);
   for(const [kind,label]of [['grant','Manage access'],...(u.role==='admin'?[]:[[u.status==='blocked'?'unblock':'block',u.status==='blocked'?'Unblock account':'Block account']])]){
    const button=el('button',label,'admin-button '+(kind==='block'?'danger':kind==='grant'?'primary':'secondary'));button.type='button';button.disabled=kind==='grant'&&u.status==='blocked';button.addEventListener('click',()=>openAction(kind,{...u,plan:access.plan}));actions.append(button);
   }
   card.append(actions);$('adminUsers').append(card);
  }
  $('userCount').textContent=(data.total??data.users.length)+' matching account'+((data.total??data.users.length)===1?'':'s');
  userOffset=data.next_offset;$('loadMoreUsers').hidden=userOffset===null;
 }
 async function loadAudit(reset=false){
  if(reset){auditOffset=0;$('adminAudit').replaceChildren();}
  const data=await A.request('/api/admin/audit-logs?offset='+auditOffset);
  if(reset&&!data.logs.length)$('adminAudit').append(el('p','No administrative changes recorded yet.','admin-empty'));
  for(const log of data.logs){
   const line=el('div',undefined,'audit-entry');
   const labels={'user.limits.update':'Personal limits updated','user.sessions.revoke':'User sessions ended','user.access.extend':'Access extended','user.block':'Account blocked','user.unblock':'Account unblocked','access.grant':'Access granted','settings.update':'Studio settings updated','admin.promote':'Administrator granted','trial.activate':'Trial activated','auth.logout':'Signed out'};
   line.append(el('strong',labels[log.action]||log.action),el('time',A.when(log.created)));
   line.append(el('div','By '+(log.actor_email||log.actor||'Server')+' · '+(log.target_email||'Studio settings'),'audit-details'));
   const details=JSON.parse(log.details);if(details.reason)line.append(el('div','Reason: '+details.reason,'audit-details'));
   if(details.before||details.after){
    const detail=document.createElement('details');detail.append(el('summary','View settings change'));
    detail.addEventListener('toggle',()=>{if(detail.open&&!detail.querySelector('pre'))detail.append(el('pre',JSON.stringify(details,null,2)));});detail.style.whiteSpace='pre-wrap';line.append(detail);
   }
   $('adminAudit').append(line);
  }
  auditOffset+=25;$('moreAudit').hidden=data.logs.length<25;
 }
 function openAction(kind,u){
  action={kind,user:u};$('actionReason').value='';
  $('actionTitle').textContent=kind==='grant'?'Manage access':kind==='block'?'Block account':'Unblock account';$('actionEmail').textContent=u.email;$('dialogError').textContent='';$('confirmUserAction').textContent=kind==='grant'?'Grant access':kind==='block'?'Block account':'Unblock account';$('confirmUserAction').className='admin-button '+(kind==='block'?'danger':'primary');$('grantDays').required=kind==='grant';$('grantPlan').value=u.plan||'creator';
  $('grantPlanLabel').hidden=$('grantDaysLabel').hidden=kind!=='grant';
  $('actionExplanation').textContent=kind==='grant'?'Starts a new access period with a fresh plan allowance. This does not record or collect a payment.':
   kind==='block'?'Existing sessions will be revoked. Subsequent media requests will be denied.':'The user can sign in again; their previous access dates and usage remain.';
  $('userActionDialog').showModal();
 }
 $('cancelUserAction').addEventListener('click',()=>$('userActionDialog').close());
 $('userActionForm').addEventListener('submit',async e=>{
  e.preventDefault();if(busy)return;busy=true;
  const button=e.submitter;if(button)button.disabled=true;
  try{
   const body={reason:$('actionReason').value};
   if(action.kind==='grant'){body.plan=$('grantPlan').value;body.days=Number($('grantDays').value);}
   await A.request('/api/admin/users/'+encodeURIComponent(action.user.id)+'/'+(action.kind==='grant'?'trial':action.kind),
    {method:action.kind==='grant'?'PATCH':'POST',body:JSON.stringify(body)});
   $('userActionDialog').close();await Promise.all([loadUsers(true),loadAudit(true),loadOverview()]);
  }catch(e){$('dialogError').textContent=e.message;}
  finally{busy=false;if(button)button.disabled=false;}
 });
 $('userSearch').addEventListener('submit',e=>{e.preventDefault();loadUsers(true).catch(error);});
 $('userStatus').addEventListener('change',()=>loadUsers(true).catch(error));
 $('loadMoreUsers').addEventListener('click',()=>loadUsers().catch(error));
 $('moreAudit').addEventListener('click',()=>loadAudit().catch(error));
 $('settingsForm').addEventListener('submit',async e=>{
  e.preventDefault();if(busy||!settings)return;
  const invalid=[...$('settingsForm').querySelectorAll('input,select,textarea')].find(x=>!x.checkValidity());
  if(invalid){const panel=invalid.closest('[data-admin-view]');if(panel)showView(panel.dataset.adminView);const plan=invalid.closest('[data-plan-panel]');if(plan)showPlan(plan.dataset.planPanel);invalid.reportValidity();return;}
  busy=true;
  const button=e.submitter;if(button)button.disabled=true;
  try{
   const next=structuredClone(settings);next.mode=$('trialMode').value;next.trial_days=Number($('trialDays').value);next.new_trials=$('newTrials').value==='true';
   for(const key of Object.keys(next.plans)){
    for(const [field]of fields){
     const value=Number($(key+'-'+field).value);
     next.plans[key][field]=field==='seconds'||field==='source_seconds'?Math.round(value*3600):value;
    }
    next.plans[key].height=Number($(key+'-height').value);
   }
   await A.request('/api/admin/settings/trial',{method:'PATCH',body:JSON.stringify({settings:next,reason:$('settingsReason').value})});
   settings=next;overviewSettings();$('settingsReason').value='';$('settingsFeedback').textContent='Settings saved. New limits are effective.';
   await loadAudit(true);
  }catch(e){error(e);}
  finally{busy=false;if(button)button.disabled=false;}
 });
 $('refreshAdmin').addEventListener('click',async()=>{
  const button=$('refreshAdmin');button.disabled=true;
  try{await A.refresh();if(A.profile?.user.role!=='admin')throw new Error('Sign in again with your administrator account.');await Promise.all([loadUsers(true),loadAudit(true),loadOverview()]);$('accountError').textContent='';}
  catch(e){error(e);}finally{button.disabled=false;}
 });
 try{
  await A.ready;
  if(A.profile?.user.role!=='admin'){error(new Error('Administrator access is required.'));return;}
  settings=await A.request('/api/admin/settings/trial');renderSettings();
  await Promise.all([loadUsers(true),loadAudit(true),loadOverview()]);$('adminContent').setAttribute('aria-busy','false');
 }catch(e){error(e);}
})();
