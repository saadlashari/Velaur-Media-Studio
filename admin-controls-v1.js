// activity-outcomes-2
// activity-labels-1
/* Velaur administration: per-user detail workspace. All writes use the existing CSRF client. */
(()=>{
 const A=window.VelaurAccount,$=id=>document.getElementById(id);
 const make=(tag,text,cls)=>{const el=document.createElement(tag);if(text!=null)el.textContent=text;if(cls)el.className=cls;return el;};
 const when=v=>v?new Date(v*1000).toLocaleString(): 'Not recorded';
 const fields=[['exports','MP4 exports / day',1,1000,1],['mp3_exports','MP3 exports / day',0,10000,1],['previews','Previews / day',1,2000,1],['active','Active jobs',1,4,1],['upload_gb','Upload size (GB)',1,8,1],['seconds','Export hours / 30 days',1/60,1000,3600],['source_seconds','Source length (hours)',1/60,3,3600],['height','Maximum resolution',720,2160,1]];
 let uid=null,record=null,tab='summary',version=0,jobsOffset=null,sessionsOffset=null;
 const users=document.querySelector('[data-admin-view="users"]');if(!users)return;
 const list=users.querySelector('.admin-panel');
 const workspace=make('article',null,'uc-workspace');workspace.hidden=true;workspace.innerHTML='<div class="uc-heading"><div><span class="admin-eyebrow">USER WORKSPACE</span><h2 id="ucName"></h2><a id="ucEmail"></a></div><div class="uc-actions"><button type="button" class="admin-button secondary" id="ucRefresh">Refresh user</button><button type="button" class="admin-button secondary" id="ucBack">Back to users</button></div></div><p id="ucFeedback" role="status" aria-live="polite"></p><div class="uc-tabs" role="tablist" aria-label="User details"></div><section id="ucBody" class="uc-body" role="tabpanel"></section>';
 users.append(workspace);
 const labels={summary:'Overview',access:'Access & plan',limits:'Personal limits',sessions:'Sessions',jobs:'Media activity'};
 for(const [key,label] of Object.entries(labels)){const b=make('button',label);b.type='button';b.id='ucTab-'+key;b.setAttribute('role','tab');b.setAttribute('aria-controls','ucBody');b.dataset.ucTab=key;workspace.querySelector('.uc-tabs').append(b);b.addEventListener('click',()=>show(key));}
 workspace.querySelector('.uc-tabs').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const keys=Object.keys(labels),i=keys.indexOf(tab),n=e.key==='Home'?0:e.key==='End'?keys.length-1:(i+(e.key==='ArrowRight'?1:-1)+keys.length)%keys.length;show(keys[n]);$('ucTab-'+keys[n]).focus();});
 function endpoint(path=''){return '/api/admin/users/'+encodeURIComponent(uid)+path;}
 function feedback(message,error=false){$('ucFeedback').textContent=message;$('ucFeedback').className=error?'uc-notice error':'uc-notice';}
 async function refresh(){const target=uid;const d=await A.request(endpoint('/detail'));if(uid!==target)return;record=d;$('ucName').textContent=d.user.name||'Studio user';$('ucEmail').textContent=d.user.email;$('ucEmail').href='mailto:'+d.user.email;return d;}
 async function open(id){uid=id;version++;workspace.hidden=false;list.hidden=true;feedback('Loading user details...');try{await refresh();feedback('');await show('summary');workspace.scrollIntoView({block:'start',behavior:'instant'});}catch(e){feedback(e.message,true);}}
 function close(){uid=null;version++;workspace.hidden=true;list.hidden=false;}
 document.addEventListener('click',e=>{const button=e.target.closest('[data-inspect-user]');if(button)open(button.dataset.inspectUser);});
 $('ucBack').addEventListener('click',close);
 $('ucRefresh').addEventListener('click',async()=>{try{await refresh();await show(tab);feedback('User details refreshed.');}catch(e){feedback(e.message,true);}});
 document.querySelectorAll('[data-view],[data-open-view]').forEach(b=>b.addEventListener('click',close));
 function stat(parent,label,value,note){const card=make('div',null,'uc-stat');card.append(make('span',label),make('strong',value));if(note)card.append(make('small',note));parent.append(card);}
 function paragraph(text){return make('p',text,'uc-muted');}
 function formReason(form,id){const label=make('label','Reason for this change','form-field');const area=make('textarea');area.id=id;area.name='reason';area.required=true;area.minLength=3;area.maxLength=300;area.placeholder='Explain the change for the audit history.';label.append(area);form.append(label);}
 function button(text,cls='primary'){const b=make('button',text,'admin-button '+cls);b.type='submit';return b;}
 async function mutate(form,path,body,success){if(form.dataset.busy)return;if(!form.reportValidity())return;form.dataset.busy='1';const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);try{await A.request(endpoint(path),{method:path==='/limits'||path==='/trial'||path==='/access-end'?'PATCH':'POST',body:JSON.stringify({...body,reason:form.querySelector('[name="reason"]').value})});await refresh();await show(tab);feedback(success);}catch(e){feedback(e.message,true);}finally{delete form.dataset.busy;buttons.forEach(b=>b.disabled=false);}}
 async function show(next){
  if(!record||!uid)return;tab=next;const generation=++version;
  workspace.querySelectorAll('[data-uc-tab]').forEach(b=>{const selected=b.dataset.ucTab===next;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;});
  const body=$('ucBody');body.replaceChildren();body.setAttribute('aria-labelledby','ucTab-'+next);body.setAttribute('aria-busy','true');
  try{
   if(next==='summary')summary(body);if(next==='access')access(body);if(next==='limits')limits(body);
   if(next==='sessions')await sessions(body,generation);if(next==='jobs')await jobs(body,generation);
  }catch(e){if(generation===version)feedback(e.message,true);}finally{if(generation===version)body.setAttribute('aria-busy','false');}
 }
 function summary(body){
  const d=record,grid=make('div',null,'uc-stats');
  stat(grid,'Account',d.user.status,d.access.plan||'No plan');stat(grid,'Access',d.access.enabled?'Active':'Inactive',d.access.access_kind||'No access period');stat(grid,'Signed up',when(d.user.created));stat(grid,'Last login',when(d.user.last_login));stat(grid,'Last activity',when(d.last_activity),'Session activity timestamps may lag by up to 5 minutes.');stat(grid,'Access ends',when(d.access.expires_at));stat(grid,'Export allowance',A.hours(d.usage.remaining_seconds)+' remaining',A.hours(d.usage.used_seconds)+' used; '+A.hours(d.usage.reserved_seconds)+' reserved');stat(grid,'Active sessions',d.active_sessions);
  body.append(grid,paragraph('Personal limits override this account only. Access & plan manages the access period. Media activity shows preparation results and recorded download requests.'));
  const usage=make('div',null,'uc-usage');for(const [label,value] of [['MP4 today',d.usage.exports_today+' / '+d.access.limits.exports],['MP3 today',d.usage.mp3_exports_today+' / '+(d.usage.mp3_limit==null?'Unlimited':d.usage.mp3_limit)],['Previews today',d.usage.previews_today+' / '+d.access.limits.previews],['Active jobs',d.usage.active_jobs]])stat(usage,label,value);body.append(usage);
 }
 function access(body){
  const d=record;body.append(make('h3','Plan and access period'),paragraph('Granting access starts a new allowance period. Existing usage history is retained. Personal limit overrides stay in effect until you reset them.'));
  const form=make('form',null,'uc-form'),grid=make('div',null,'uc-form-grid');
  const planLabel=make('label','Assigned plan','form-field'),plan=make('select');for(const key of ['creator','pro','studio']){const opt=make('option',key[0].toUpperCase()+key.slice(1));opt.value=key;plan.append(opt);}plan.value=d.access.plan||'creator';planLabel.append(plan);
  const daysLabel=make('label','Access days','form-field'),days=make('input');days.type='number';days.min=1;days.max=366;days.value=30;days.required=true;daysLabel.append(days);grid.append(planLabel,daysLabel);form.append(grid);
  const ack=make('label',null,'uc-check'),check=make('input');check.type='checkbox';check.required=true;ack.append(check,make('span','I understand this starts a new access/allowance period.'));form.append(ack);formReason(form,'ucGrantReason');form.append(button('Grant plan access'));form.addEventListener('submit',e=>{e.preventDefault();mutate(form,'/trial',{plan:plan.value,days:Number(days.value)},'Plan access updated.');});body.append(form);
  if(d.access.starts_at){
   const extend=make('form',null,'uc-form uc-separated');extend.append(make('h3','Extend access without resetting usage'),paragraph('Adds days to the current expiry, or from today if access expired. Keeps the same plan, usage history and personal limits.'));
   const label=make('label','Additional days','form-field'),extra=make('input');extra.type='number';extra.min=1;extra.max=366;extra.value=30;extra.required=true;label.append(extra);extend.append(label);formReason(extend,'ucExtendReason');extend.append(button('Extend access','secondary'));extend.addEventListener('submit',e=>{e.preventDefault();mutate(extend,'/access-end',{days:Number(extra.value)},'Access extended; usage history preserved.');});body.append(extend);
  }
  if(d.user.role!=='admin'){
   const control=make('form',null,'uc-form uc-separated');control.append(make('h3',d.user.status==='blocked'?'Unblock account':'Block account'),paragraph(d.user.status==='blocked'?'Allows this user to sign in again. Existing access expiry still applies.':'Revokes the user sessions and prevents subsequent authenticated requests.'));formReason(control,'ucBlockReason');control.append(button(d.user.status==='blocked'?'Unblock account':'Block account',d.user.status==='blocked'?'secondary':'danger'));control.addEventListener('submit',e=>{e.preventDefault();mutate(control,d.user.status==='blocked'?'/unblock':'/block',{},'Account status updated.');});body.append(control);
  }
 }
 function limits(body){
  body.append(make('h3','Limits for this user'),paragraph('Check a setting to override the plan default. Leave it unchecked to follow the global plan. Changes do not reset usage, and wait until this user has no active jobs. MP3 0 means unlimited count; duration limits still apply.'));
  const form=make('form',null,'uc-form'),grid=make('div',null,'uc-form-grid'),inputs=[];
  for(const [key,title,min,max,scale] of fields){
   const box=make('div',null,'uc-limit'),label=make('label',null,'uc-check'),toggle=make('input');toggle.type='checkbox';toggle.checked=Object.hasOwn(record.overrides,key);toggle.setAttribute('aria-label','Override '+title);label.append(toggle,make('span',title));box.append(label);
   const input=make(key==='height'?'select':'input');input.id='ucLimit-'+key;input.setAttribute('aria-label',title);input.disabled=!toggle.checked;
   if(key==='height'){for(const h of [720,1080,2160]){const option=make('option',h+'p');option.value=h;input.append(option);}}
   else{input.type='number';input.min=min;input.max=max;input.step=scale===3600?'any':'1';input.required=true;}
   input.value=(record.access.limits[key]||0)/scale;
   box.append(input,make('small','Plan default: '+(record.base_limits[key]===0&&key==='mp3_exports'?'Unlimited':record.base_limits[key]/scale)));
   toggle.addEventListener('change',()=>{input.disabled=!toggle.checked;if(!toggle.checked)input.value=record.base_limits[key]/scale;});inputs.push({key,input,toggle,scale});grid.append(box);
  }
  form.append(grid);formReason(form,'ucLimitsReason');const actions=make('div',null,'uc-actions'),save=button('Save personal limits'),reset=make('button','Reset to plan defaults','admin-button secondary');reset.type='button';reset.addEventListener('click',()=>{if(!form.querySelector('[name="reason"]').reportValidity())return;mutate(form,'/limits',{limits:{}},'Personal overrides removed. Plan defaults restored.');});actions.append(save,reset);form.append(actions);form.addEventListener('submit',e=>{e.preventDefault();const values={};for(const {key,input,toggle,scale} of inputs)if(toggle.checked)values[key]=Math.round(Number(input.value)*scale);mutate(form,'/limits',{limits:values},'Personal limits saved. Usage history is unchanged.');});body.append(form);
 }
 async function sessions(body,generation){
  body.append(make('h3','Sign-in sessions'),paragraph('Started, last authenticated activity and expiry are recorded. Browser/device names were not stored for older sessions. Session tokens are never displayed.'));
  const data=await A.request(endpoint('/sessions'));if(generation!==version)return;
  const form=make('form',null,'uc-form');formReason(form,'ucSessionReason');const canRevoke=record.user.role!=='admin';
  if(canRevoke){const all=button('End all user sessions','danger');form.append(all);form.addEventListener('submit',e=>{e.preventDefault();mutate(form,'/sessions/revoke',{session:'all'},'User sessions ended.');});body.append(form);}
  else body.append(paragraph('Use Sign out for your own session. Other administrator sessions are managed from the server.'));
  const list=make('div',null,'uc-rows');body.append(list);
  function append(rows){for(const s of rows){const row=make('article',null,'uc-row');row.append(make('strong',s.current?'This administrator session':s.active?'Active session':'Expired session'),paragraph('Started '+when(s.created)+' · Last activity '+when(s.seen)+' · Expires '+when(s.expires)));if(canRevoke){const b=make('button','End this session','admin-button secondary');b.type='button';b.addEventListener('click',()=>{if(form.reportValidity())mutate(form,'/sessions/revoke',{session:s.id},'Selected session ended.');});row.append(b);}list.append(row);}}
  append(data.sessions);if(!data.sessions.length)list.append(paragraph('No stored sessions for this user.'));
  let offset=data.next_offset;const more=make('button','Load more sessions','admin-button secondary');more.type='button';more.hidden=offset==null;more.addEventListener('click',async()=>{more.disabled=true;try{const result=await A.request(endpoint('/sessions?offset='+offset));if(generation!==version)return;append(result.sessions);offset=result.next_offset;more.hidden=offset==null;}catch(e){feedback(e.message,true);}finally{more.disabled=false;}});body.append(more);
 }
 async function jobs(body,generation){
  body.append(make('h3','Media processing and delivery'),paragraph('File ready means processing succeeded. Download requested means a browser requested the export; it does not confirm the whole file reached the device. Request tracking starts with this update.'));
  const label=make('label','Filter jobs','form-field'),filter=make('select');for(const [value,text]of [['all','All jobs'],['done','Completed'],['error','Failed'],['running','Running'],['queued','Queued']]){const o=make('option',text);o.value=value;filter.append(o);}label.append(filter);body.append(label);
  const list=make('div',null,'uc-rows'),more=make('button','Load more jobs','admin-button secondary');more.type='button';more.hidden=true;body.append(list,more);let offset=null,requestVersion=0;
  function append(rows){for(const j of rows){const row=make('article',null,'uc-job'),head=make('div',null,'uc-row-head');head.append(make('strong',j.title),make('span',j.status_label||j.state,'uc-state '+j.state));row.append(head,paragraph((j.job_type||(j.kind==='export'?(j.output_format||'export').toUpperCase()+' export':'Preview'))+' · '+(j.source_host||'Uploaded file')+' · '+when(j.created)),paragraph(j.outcome_detail||j.stage||j.status_label));
   const details=make('details'),summary=make('summary','Processing details');details.append(summary,paragraph('Job '+j.id),paragraph('Updated '+when(j.updated)),paragraph('Processed duration: '+Math.round(j.seconds||0)+' seconds'));
   if(j.last_completed)details.append(paragraph('Full file sent by server '+when(j.last_completed)));
   if(j.kind==='export')details.append(paragraph(j.last_download_request?'Download requested '+when(j.last_download_request)+' ('+j.download_requests+' requests)':'No download request recorded. Older downloads may not have tracking.'));
   if(j.state==='done')details.append(paragraph(j.file_ready?'Export file is currently available.':'File may have expired or this preview uses a streamed source.'));
   if(j.source_url){const link=make('a','Open original source','admin-button secondary');link.href=j.source_url;link.target='_blank';link.rel='noopener noreferrer';details.append(link);}
   if(j.error)details.append(make('pre',j.error,'uc-job-error'));row.append(details);list.append(row);}}
  async function load(reset){const current=++requestVersion;more.disabled=true;try{const r=await A.request(endpoint('/jobs?state='+filter.value+'&offset='+(reset?0:offset)));if(current!==requestVersion||generation!==version)return;if(reset)list.replaceChildren();append(r.jobs);if(!r.jobs.length&&reset)list.append(paragraph('No jobs match this filter.'));offset=r.next_offset;more.hidden=offset==null;}catch(e){feedback(e.message,true);}finally{more.disabled=false;}}
  filter.addEventListener('change',()=>load(true));more.addEventListener('click',()=>load(false));await load(true);
 }
})();
