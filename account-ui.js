// activity-outcomes-2
/* Same-origin session UI. No credentials or auth tokens in localStorage. */
window.VelaurAccount = (() => {
 let profile=null, csrf='', plans=null, yearly=false, refreshing=null, lastRefresh=0, accountFailure='';
 const $=id=>document.getElementById(id);
 function text(id,value){const e=$(id);if(e)e.textContent=value;if(id==='accountError')window.dispatchEvent(new CustomEvent('velaur:limit-status',{detail:{id,text:String(value||''),error:true}}));}
 function hours(seconds){return (Math.max(0,seconds||0)/3600).toFixed(1)+' hours';}
 function when(value){return value?new Date(value*1000).toLocaleString():'—';}
 async function request(path,options={}) {
  const method=options.method||'GET';
  const headers={...options.headers};
  if(!['GET','HEAD'].includes(method)){headers['X-CSRF-Token']=csrf;if(options.body)headers['Content-Type']='application/json';}
  const response=await fetch(path,{...options,headers,cache:'no-store',credentials:'same-origin'});
  let data;try{data=await response.json();}catch{throw new Error('Account service could not be reached.');}
  if(!response.ok){const err=new Error(typeof data.detail==='string'?data.detail:'Request failed ('+response.status+').');err.status=response.status;throw err;}
  return data;
 }
 function priceCards(){
  if(!plans)return;
  const eligible=plans.new_trials && !profile?.access.trial_used && !profile?.access.enabled;
  for(const [key,plan] of Object.entries(plans.plans)){
   text(key+'Price','$'+(yearly?plan.yearly:plan.monthly));
   text(key+'Interval',yearly?'/year':'/month');
   text(key+'Then',key==='creator'&&eligible?'Planned price after trial: $'+(yearly?plan.yearly+'/year':plan.monthly+'/month'):(yearly?'Monthly option: $'+plan.monthly+'/month':'Yearly option: $'+plan.yearly+'/year'));
   text(key+'Allowance',hours(plan.seconds)+' of exports / 30 days');
   text(key+'Daily',plan.exports+' exports + '+plan.previews+' previews/day');
   text(key+'Slots',plan.active+' active processing job'+(plan.active===1?'':'s'));
   text(key+'Upload',plan.upload_gb+' GB uploads · Up to '+(plan.height===2160?'4K':'1080p'));
  }
  if($('trialOffer'))$('trialOffer').hidden=!eligible;
  text('trialLabel',eligible?plans.trial_days+' days free':'Creator access');
  text('trialOffer',eligible?'$0 for your first '+plans.trial_days+' days':'$2/month or $20/year');
  text('creatorTrial',eligible?'Unlock free trial':profile?'View your account':'Continue with Google');
  const crossed=$('creatorPriceLine');if(crossed)crossed.classList.toggle('trial-crossed',eligible);
  text('pricingNote','No card required. Paid checkout is not available yet. Your trial does not renew automatically.');
  window.dispatchEvent(new CustomEvent("velaur:pricing", {detail:{plans:plans.plans,yearly,eligible}}));
  window.dispatchEvent(new CustomEvent("velaur:audio",{detail:{plans:plans.plans,profile}}));
 }
 function render(){
  window.dispatchEvent(new CustomEvent("velaur:usage",{detail:profile}));
  const member=!!profile;
  document.querySelectorAll('[data-member]').forEach(x=>x.hidden=!member);
  document.querySelectorAll('[data-guest]').forEach(x=>x.hidden=member);
  document.querySelectorAll('[data-access]').forEach(x=>x.hidden=!profile?.access.enabled);
  document.querySelectorAll('[data-no-access]').forEach(x=>x.hidden=!!profile?.access.enabled);

  text('accountLink',profile?'My dashboard':accountFailure?'Retry sign-in':'Continue with Google');
  if($('accountLink'))$('accountLink').href=profile?'/dashboard':'/login';
  document.querySelectorAll('[data-logout]').forEach(x=>x.hidden=!profile);
  document.querySelectorAll('[data-admin]').forEach(x=>x.hidden=profile?.user.role!=='admin');
  const studio=$('studio'),gate=$('studioAccessGate'),enabled=!!profile?.access.enabled;
  if(studio){studio.hidden=!enabled;studio.inert=!enabled;}
  if(gate){
   gate.hidden=enabled;
   const eligible=!!profile && !profile.access.trial_used && !!plans?.new_trials;
   text('studioGateTitle',accountFailure?'We could not verify your access':!profile?'Your studio starts with a sign-in.':eligible?'Unlock your creative space.':'Your studio needs active access.');
   text('studioGateMessage',accountFailure||(!profile?'Continue with Google to open your private studio, then unlock your 30-day Creator trial.':eligible?'Your account is ready. Activate your free trial to preview, trim and export.':'Check your trial status and current limits in your dashboard.'));
   $('studioGateLogin').hidden=!!profile;
   $('studioGateUnlock').hidden=!eligible;
   $('studioGateDashboard').hidden=!profile;
  }
  if(profile){
   text('accountLink','My dashboard');if($('accountLink'))$('accountLink').href='/dashboard';
   document.querySelectorAll('[data-logout]').forEach(x=>x.hidden=false);
   document.querySelectorAll('[data-admin]').forEach(x=>x.hidden=profile.user.role!=='admin');
   text('accountName',profile.user.name||profile.user.email);
   text('accountEmail',profile.user.email);
   text('accessTitle',profile.access.access_kind==='trial'?'Creator free trial':profile.access.plan?plans?.plans[profile.access.plan]?.name+' access':'Unlock your Creator trial');
   text('accessStatus',profile.access.enabled?'Active':profile.access.mode==='paused'?'Processing paused':profile.access.starts_at?'Access ended':'Trial not activated');
   text('usedDuration',hours(profile.usage.used_seconds)+' used'+(profile.usage.reserved_seconds?' + '+hours(profile.usage.reserved_seconds)+' processing':''));
   text('remainingDuration',hours(profile.usage.remaining_seconds)+' remaining');
   text('periodEnd',profile.access.mode==='open'?'No expiry while open access is enabled':when(profile.access.expires_at));
   text('allowanceReset',profile.access.enabled?when(profile.usage.period_ends_at):'-');
   text('dailyReset',when(profile.usage.daily_resets_at));
   text('dailyExports',profile.usage.exports_today+' / '+profile.access.limits.exports);
   text('dailyPreviews',profile.usage.previews_today+' / '+profile.access.limits.previews);
   text('activeJobs',profile.access.processing_slot_exempt?profile.usage.active_jobs+' active · Admin':profile.usage.active_jobs+' / '+profile.access.limits.active);
   if($('activeJobs'))$('activeJobs').title=profile.access.processing_slot_exempt?'No per-account processing cap. Jobs still share server processing capacity.':'Your plan limits simultaneous processing jobs.';
   const unlock=$('dashboardUnlock');if(unlock)unlock.hidden=profile.access.trial_used || profile.access.enabled || !plans?.new_trials;
  }
  document.querySelectorAll('[data-hero-note]').forEach(x=>x.textContent=profile?.access.enabled?'Your workspace is ready. Check your usage in your dashboard.':profile?'Your account is ready. Explore plans or activate an available trial.':'No card required. Activate your trial after sign-in.');
  priceCards();
 }
 async function refresh(){
  if(refreshing)return refreshing;
  refreshing=(async()=>{
   try{profile=await request('/api/me');csrf=profile.csrf;accountFailure='';}
   catch(error){profile=null;csrf='';accountFailure=error.status===401?'':error.message;render();if(error.status!==401)throw error;}
   render();
   if(!profile && ['/admin','/dashboard','/studio'].includes(location.pathname))location.replace('/login?expired=1');
   return profile;
  })();
  try{return await refreshing;}finally{refreshing=null;lastRefresh=Date.now();}
 }
 async function unlock(){
  try{await ready;}catch(e){text('accountError',e.message);return;}
  if(!profile){location.href='/login';return;}
  if(profile.access.trial_used || profile.access.enabled || !plans?.new_trials){location.href='/dashboard';return;}
  const button=$('creatorTrial')||$('dashboardUnlock');
  if(button)button.disabled=true;
  try{await request('/api/me/trial',{method:'POST'});location.href='/dashboard';}
  catch(e){text('accountError',e.message);}
  finally{if(button)button.disabled=false;}
 }
 async function logout(){
  try{await ready;await request('/auth/logout',{method:'POST'});localStorage.removeItem('velaurExportJobV3');location.href='/';}
  catch(e){text('accountError',e.message);}
 }
 async function jobs(){
  // dashboard-activity-ui-1
  if(!$('accountJobs')||!profile)return;
  const container=$('accountJobs');container.replaceChildren();
  const note=document.createElement('p');note.textContent='Recent activity, 25 records at a time. Preview and export results are shown separately.';container.append(note);
  const more=document.createElement('button');more.type='button';more.className='small-button';more.textContent='Load older activity';more.hidden=true;container.append(more);
  let next=null;
  async function load(offset){
   more.disabled=true;
   try{
    const data=await request('/api/me/jobs?offset='+offset);
    if(!data.jobs.length&&offset===0){const empty=document.createElement('p');empty.textContent='Your exports and previews will appear here.';container.insertBefore(empty,more);}
    for(const job of data.jobs){
     const item=document.createElement('div');item.className='history-row';
     const copy=document.createElement('div');copy.className='activity-copy';
     const status=document.createElement('strong');status.textContent=job.status_label||(job.kind==='preview'?'Preview ':'Export ')+job.state;copy.append(status);
     const detail=document.createElement('p');detail.textContent=(job.job_type||job.kind)+' · '+when(job.created);copy.append(detail);
     if(job.title&&job.title!=='Media job'){const media=document.createElement('p');media.textContent=job.title.length>140?job.title.slice(0,137)+'...':job.title;media.title=job.title;copy.append(media);}if(job.outcome_detail){const outcome=document.createElement('p');outcome.textContent=job.outcome_detail;copy.append(outcome);}
     if(job.last_download_request){const sent=document.createElement('p');sent.textContent='Download requested '+when(job.last_download_request)+'. This records the request, not completed delivery.';copy.append(sent);}
     if(job.error){const box=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Why it failed';box.append(summary);box.addEventListener('toggle',()=>{if(box.open&&!box.querySelector('pre')){const error=document.createElement('pre');error.textContent=job.error;box.append(error);}});copy.append(box);}
     item.append(copy);
     if(job.kind==='export'&&job.state==='done'&&job.file_ready){const link=document.createElement('a');link.href='/api/files/'+encodeURIComponent(job.id);link.textContent='Download '+(job.output_format||'file').toUpperCase();link.className='small-button';item.append(link);}
     container.insertBefore(item,more);
    }
    next=data.next_offset;more.hidden=next==null;
   }finally{more.disabled=false;}
  }
  more.addEventListener('click',()=>load(next).catch(e=>text('accountError',e.message)));
  await load(0);
 }

 const ready=(async()=>{
  try{
   let planError;
   try{plans=await request('/api/public/plans');}catch(e){planError=e;}
   await refresh();render();
   if(planError)text('accountError','Plan information could not be loaded. '+planError.message);
   if(location.search.includes('login_error=1'))text('accountError','Google sign-in was cancelled or could not be verified. Please try again.');
   await jobs();
  }catch(e){text('accountError',e.message);throw e;}
 })();
 ready.catch(()=>{});
 function refreshOnReturn(){
  ready.then(()=>{if(Date.now()-lastRefresh>15000)return refresh();}).catch(e=>text('accountError',e.message));
 }
 window.addEventListener('pageshow',event=>{if(event.persisted)refreshOnReturn();});
 window.addEventListener('focus',refreshOnReturn);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshOnReturn();});
 document.querySelectorAll('[data-logout]').forEach(x=>x.addEventListener('click',logout));
 document.querySelectorAll('[data-unlock]').forEach(x=>x.addEventListener('click',unlock));
 document.querySelectorAll('[data-billing]').forEach(button=>button.addEventListener('click',()=>{
  yearly=button.dataset.billing==='yearly';
  document.querySelectorAll('[data-billing]').forEach(x=>x.setAttribute('aria-pressed',String(x===button)));
  document.querySelectorAll('[data-hero-note]').forEach(x=>x.textContent=profile?.access.enabled?'Your workspace is ready. Check your usage in your dashboard.':profile?'Your account is ready. Explore plans or activate an available trial.':'No card required. Activate your trial after sign-in.');
  priceCards();
 }));
 window.addEventListener("velaur:refresh-pricing",priceCards);
 window.addEventListener("velaur:audio-refresh",priceCards);
 return {ready,request,refresh,get csrf(){return csrf;},get profile(){return profile;},when,hours};
})();

// inline-upgrade-events-1
