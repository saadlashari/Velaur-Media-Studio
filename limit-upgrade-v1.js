/* WhatsApp SVG path: Font Awesome Free 6.7.2, Fonticons Inc., CC BY 4.0; https://fontawesome.com/license/free */
/* Velaur quota popup v2. Presentation only; backend quotas remain authoritative. */
(()=>{
 if(window.VelaurQuotaPopup)return;
 let dialog,lastFocus=null,currentKey='',lastProfile=null,scheduled=false;
 const dismissed=new Set();
 const whatsapp="<svg viewBox=\"0 0 448 512\" fill=\"currentColor\" aria-hidden=\"true\"><path d=\"M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-32.6-16.3-54-29.1-75.5-66-5.7-9.8 5.7-9.1 16.3-30.3 1.8-3.7.9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 35.2 15.2 49 16.5 66.6 13.9 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.6z\"/></svg>";
 const planIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18M7 15h4"/></svg>';
 const gauge='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 17a9 9 0 1 1 16 0M12 12l5-4M7 17h10"/><circle cx="12" cy="12" r="1.5"/></svg>';
 function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text)e.textContent=text;return e;}
 function storageKey(key){return 'velaur:quota-popup:2:'+key;}
 function wasDismissed(key){if(dismissed.has(key))return true;try{return sessionStorage.getItem(storageKey(key))==='1';}catch{return false;}}
 function markDismissed(key){if(!key)return;dismissed.add(key);try{sessionStorage.setItem(storageKey(key),'1');}catch{}}
 function ensure(){
  if(dialog)return;
  dialog=node('dialog','quota-dialog');dialog.id='quotaDialog';dialog.setAttribute('aria-labelledby','quotaTitle');dialog.setAttribute('aria-describedby','quotaDescription');
  const header=node('div','quota-head'),brand=node('div','quota-brand'),image=node('img');image.src='/static/brand-wordmark.webp';image.alt='VELAUR Media Studio';brand.append(image,node('span','','YOUR CREATIVE SPACE'));
  const close=node('button','quota-close');close.type='button';close.setAttribute('aria-label','Close limit options');close.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg>';close.addEventListener('click',()=>dialog.close());header.append(brand,close);
  const body=node('div','quota-body'),symbol=node('div','quota-symbol');symbol.setAttribute('aria-hidden','true');symbol.innerHTML=gauge;
  const title=node('h2');title.id='quotaTitle';const description=node('p','quota-description');description.id='quotaDescription';const list=node('ul','quota-list');list.id='quotaItems';const reset=node('p','quota-reset');reset.id='quotaReset';body.append(symbol,node('span','quota-eyebrow','PLAN ALLOWANCE'),title,description,list,reset);
  const footer=node('div','quota-actions'),buttons=node('div','quota-buttons');
  const plans=node('a','quota-button quota-plans');plans.href='/pricing';plans.innerHTML=planIcon;plans.append(node('span','','View plans'));
  const contact=node('a','quota-button quota-whatsapp');contact.href='https://wa.me/923211618331';contact.target='_blank';contact.rel='noopener noreferrer';contact.innerHTML=whatsapp;contact.append(node('span','','Chat on WhatsApp'));
  buttons.append(plans,contact);footer.append(buttons,node('p','quota-footnote','Compare plan limits, or ask us about more access.'));
  dialog.append(header,body,footer);document.body.append(dialog);
  dialog.addEventListener('keydown',event=>{
   if(event.key!=='Tab')return;
   const controls=[...dialog.querySelectorAll('button:not(:disabled),a[href]')].filter(e=>e.getClientRects().length);
   const first=controls[0],last=controls.at(-1);
   if(!first){event.preventDefault();return;}
   if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
   else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  });
  dialog.addEventListener('close',()=>{document.documentElement.classList.remove('quota-modal-open');markDismissed(currentKey);if(lastFocus?.isConnected&&!lastFocus.disabled)lastFocus.focus({preventScroll:true});});
  dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});
 }
 function show(options,automatic=false){
  if(automatic&&(wasDismissed(options.key)||dialog?.open))return;
  ensure();currentKey=options.key||'';
  dialog.querySelector('#quotaTitle').textContent=options.title;
  dialog.querySelector('#quotaDescription').textContent=options.description;
  const list=dialog.querySelector('#quotaItems');list.replaceChildren();
  for(const item of options.items||[]){const li=node('li');li.append(node('strong','',item.label),node('span','',item.value||''));list.append(li);}
  const reset=dialog.querySelector('#quotaReset');reset.textContent=options.reset||'';reset.hidden=!options.reset;
  if(!dialog.open){lastFocus=(options.focusId&&document.getElementById(options.focusId))||document.activeElement;dialog.showModal();document.documentElement.classList.add('quota-modal-open');}
 }
 function time(value){return value?new Date(value*1000).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'';}
 function dailyReset(p){return p?.usage?.daily_resets_at>Date.now()/1000?'Daily allowance resets '+time(p.usage.daily_resets_at)+'.':'Daily allowances reset at midnight UTC.';}
 function signature(p,codes){return [p?.user?.id||'member',p?.access?.plan||'',p?.access?.starts_at||'',p?.access?.expires_at||'',p?.usage?.daily_resets_at||'',codes.join(',')].join(':');}
 function errorOptions({id,text,error}){
  if(!error||!['previewStatus','exportStatus','accountError'].includes(id))return null;
  const p=window.VelaurAccount?.profile||lastProfile;let title,description,reset='',item;
  if(/free trial has already been used on this network or browser/i.test(text)){title='A trial has already been used here.';description='Another free trial cannot be activated on this network or browser. Use your original account, or contact us about access.';}
  else if(/daily MP3 export allowance/i.test(text)){title="Today's MP3 limit is reached.";description='You can wait for your daily reset, or compare plans for more MP3 exports.';reset=dailyReset(p);item={label:'MP3 exports today',value:p?.usage?.mp3_limit!=null?(p.usage.mp3_exports_today>=p.usage.mp3_limit?`${p.usage.mp3_exports_today} / ${p.usage.mp3_limit}`:`${p.usage.mp3_limit} / day`):'Reached'};}
  else if(/daily (processing|preview|export) allowance/i.test(text)){const preview=id==='previewStatus';title=preview?"Today's preview limit is reached.":"Today's MP4 limit is reached.";description='You can wait for your daily reset, or compare the allowances in other plans.';reset=dailyReset(p);item={label:preview?'Preview preparations':'MP4 exports',value:p?`${preview?p.access.limits.previews:p.access.limits.exports} / day`:'Reached'};}
  else if(/export-duration allowance|remaining export-duration|duration allowance has been used/i.test(text)){title='This request needs more export hours.';description='Your allowance is used, or this clip is longer than the hours remaining. Try a shorter clip or review your plan options.';reset=p?.usage?.period_ends_at?'Allowance period ends '+time(p.usage.period_ends_at)+'.':'';}
  else if(/processing slot is busy|active processing.*limit/i.test(text)){title='Your processing slot is busy.';description='Wait for your current preview or export to finish. You can also compare plans with more simultaneous processing slots.';}
  else if(/maximum source duration/i.test(text)){title='This source video is too long.';description='Use a shorter source video. Check plan details or contact us before choosing a different plan.';}
  else if(/plan.*(file.size|upload|resolution|height).*limit|upload exceeds.*limit|resolution exceeds|resolution is not included in your plan|account file-size limit|plan allows uploads up to|exceeds your plan/i.test(text)){title='This media exceeds a plan limit.';description='Try a smaller file or a lower resolution, or compare the upload and quality limits in our plans.';}
  else if(/access has ended|access is no longer active|needs active access|unlock your trial, or/i.test(text)){title='Your access has ended.';description='View the available plans or chat with us to continue preparing previews and exports.';}
  else return null;
  return {title,description,reset,items:item?[item]:[],key:signature(p,[title]),focusId:id==='previewStatus'?'previewBtn':id==='exportStatus'?'exportBtn':null};
 }
 window.addEventListener('velaur:limit-status',event=>{const options=errorOptions(event.detail||{});if(options)show(options);});
 function reached(p){
  if(!p||p.user?.role==='admin')return [];
  const a=p.access,v=p.usage,l=a.limits,items=[];
  if(!a.enabled&&a.trial_used&&a.mode!=='paused')return [{id:'accessStatus',code:'access',label:'Access period',value:'Ended'}];
  if(!a.enabled)return [];
  if(v.exports_today>=l.exports)items.push({id:'dailyExports',code:'mp4',label:'MP4 exports today',value:`${v.exports_today} / ${l.exports}`});
  if(v.previews_today>=l.previews)items.push({id:'dailyPreviews',code:'previews',label:'Previews today',value:`${v.previews_today} / ${l.previews}`});
  if(v.mp3_limit!=null&&v.mp3_exports_today>=v.mp3_limit)items.push({id:'audioUsageRow',code:'mp3',label:'MP3 exports today',value:`${v.mp3_exports_today} / ${v.mp3_limit}`});
  if(v.remaining_seconds<=0)items.push({id:'remainingDuration',code:'hours',label:'Export-hour allowance',value:'No hours remaining'});
  return items;
 }
 function summary(p,items){return {title:items[0]?.code==='access'?'Your access has ended.':'Your plan limit is reached.',description:items[0]?.code==='access'?'Review your plan options or chat with us to continue.':'These allowances are currently used. Wait for the relevant reset, or compare plan options for more access.',items,key:signature(p,items.map(i=>i.code)),reset:items.some(i=>['mp4','mp3','previews'].includes(i.code))?dailyReset(p):items.some(i=>i.code==='hours')&&p.usage.period_ends_at?'Allowance period ends '+time(p.usage.period_ends_at)+'.':''};}
 function hints(p,items){
  const active=new Set(items.map(i=>i.id));
  document.querySelectorAll('.quota-details-trigger').forEach(button=>{button.hidden=!active.has(button.dataset.limit);if(button.parentElement.classList.contains('quota-trigger-slot'))button.parentElement.hidden=button.hidden;});
  for(const item of items){const stat=document.getElementById(item.id);if(!stat)continue;let button=document.getElementById('quota-trigger-'+item.id);
   if(!button){button=node('button','quota-details-trigger','Limit reached ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· View options');button.id='quota-trigger-'+item.id;button.dataset.limit=item.id;button.type='button';button.setAttribute('aria-haspopup','dialog');const row=stat.closest('.usage-list > div');if(row){const dd=node('dd','quota-trigger-slot');dd.append(button);row.append(dd);}else stat.after(button);button.addEventListener('click',()=>show(summary(lastProfile,reached(lastProfile).filter(i=>i.id===button.dataset.limit))));}
   button.hidden=false;if(button.parentElement.classList.contains('quota-trigger-slot'))button.parentElement.hidden=false;
  }
 }
 function usage(p){if(p)lastProfile=p;if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;const p=lastProfile;if(!p)return;const items=reached(p);hints(p,items);if(items.length&&['/studio','/dashboard'].includes(location.pathname))show(summary(p,items),true);});}
 window.addEventListener('velaur:usage',e=>usage(e.detail));window.addEventListener('velaur:audio',()=>usage(window.VelaurAccount?.profile));
 window.VelaurAccount?.ready.then(()=>usage(window.VelaurAccount.profile)).catch(()=>{});
 window.VelaurQuotaPopup={showForStatus:detail=>{const options=errorOptions(detail);if(options)show(options);}};
})();
