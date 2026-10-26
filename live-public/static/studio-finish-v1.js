/* Approved pricing-card layout. Existing account/plan renderers remain authoritative. */
/* WhatsApp path: Font Awesome Free 6.7.2, Fonticons Inc., CC BY 4.0, https://fontawesome.com/license/free */
(()=>{
 const check='<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-8"/></svg>';
 const clock='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/></svg>';
 const whatsapp="<svg viewBox=\"0 0 448 512\" fill=\"currentColor\" aria-hidden=\"true\"><path d=\"M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-32.6-16.3-54-29.1-75.5-66-5.7-9.8 5.7-9.1 16.3-30.3 1.8-3.7.9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 35.2 15.2 49 16.5 66.6 13.9 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.6z\"/></svg>";
 document.body.classList.toggle('finish-pricing-page',location.pathname.replace(/\/$/,'')==='/pricing');
 const $=id=>document.getElementById(id);
 function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text)n.textContent=text;return n;}
 function feature(label){const li=el('li');li.innerHTML=check;li.append(el('span','',label));return li;}
 function hours(value){return Number(value/3600).toLocaleString(undefined,{maximumFractionDigits:1});}
 function sourceLimit(value){return value%3600===0?`Up to ${value/3600}-hour source videos`:`Up to ${Math.round(value/60)}-minute source videos`;}
 function render({plans,yearly,eligible}){
  const profile=window.VelaurAccount?.profile;
  for(const key of ['creator','pro','studio']){
   const p=plans?.[key],price=$(key+'Price'),card=price?.closest('.price-card');
   if(!p||!card||!Number.isFinite(p.seconds))continue;
   let head=card.querySelector('.card-heading-band');
   if(!head){head=el('div','card-heading-band');const copy=el('div'),title=card.querySelector('h3'),badge=card.querySelector('.price-badge');if(badge)copy.append(badge);if(title)copy.append(title);head.append(copy);card.prepend(head);}
   let planIcon=head.querySelector('.card-plan-icon');if(!planIcon){planIcon=el('span','card-plan-icon');head.append(planIcon);}planIcon.setAttribute('aria-hidden','true');
   const paths={creator:'M5 21v-3a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v3M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8',pro:'m13 2-9 12h7l-1 8 10-13h-7z',studio:'M4 7h16v14H4zM4 7V3h16v4M9 3l-2 4m8-4-2 4M10 11l5 3-5 3z'};
   planIcon.innerHTML='<svg viewBox="0 0 24 24"><path d="'+paths[key]+'"/></svg>';
   card.classList.add('glass-plan');card.dataset.plan=key;
   const active=!!profile?.access.enabled&&profile.access.plan===key;
   const free=key==='creator'&&!!eligible&&!yearly&&!active;
   card.classList.toggle('is-trial-offer',free);
   let promo=card.querySelector('.glass-trial-price');
   if(key==='creator'){
    if(!promo){promo=el('div','glass-trial-price');price.closest('.price-line').before(promo);}
    const raw=$('trialOffer')?.textContent||'',days=raw.match(/first\s+(\d+)\s+days/i)?.[1];
    promo.replaceChildren(el('strong','','$0'),el('small','',days?`first ${days} days`:'introductory trial'));promo.hidden=!free;
   }
   const badge=card.querySelector('.price-badge');
   if(badge&&key!=='creator')badge.textContent=active?'YOUR ACTIVE PLAN':key==='pro'?'MORE ROOM TO CREATE':'STUDIO ACCESS';
   const allowance=$(key+'Allowance');
   if(allowance){
    const icon=el('span','glass-hours-icon');icon.setAttribute('aria-hidden','true');icon.innerHTML=clock;
    const copy=el('span','glass-hours-copy');copy.append(el('strong','',hours(p.seconds)+' export hours'),el('small','','every 30 days'));allowance.replaceChildren(icon,copy);
   }
   let features=card.querySelector('.glass-feature-list');
   if(!features){features=el('ul','glass-feature-list');allowance?.after(features);}
   const height=p.height===2160?'4K':p.height+'p';
   features.replaceChildren(...[
    `${p.exports} MP4 exports / day`,p.mp3_exports===0?'Unlimited MP3 exports / day':`${p.mp3_exports} MP3 exports / day`,
    `${p.previews} previews / day`,`${p.upload_gb} GB upload \u00b7 ${height}`,`${p.active} active ${p.active===1?'job':'jobs'}`
   ].map(feature));
   let compact=card.querySelector('.glass-feature-compact');
   if(!compact){compact=el('ul','glass-feature-compact');features.after(compact);}
   compact.replaceChildren(...[
    `${p.exports} MP4 / day \u00b7 ${p.mp3_exports===0?'Unlimited MP3 / day':p.mp3_exports+' MP3 / day'}`,
    `${p.previews} previews / day`,`${p.upload_gb} GB \u00b7 ${height} \u00b7 ${p.active} active ${p.active===1?'job':'jobs'}`
   ].map(feature));
   let note=card.querySelector('.glass-source-note');
   if(!note){note=el('p','glass-source-note');features.after(note);}compact.after(note);note.textContent=sourceLimit(p.source_seconds);
   for(const paragraph of card.querySelectorAll(':scope > p:not([id]):not([data-audio-allowance]):not(.glass-source-note)')){
    if(/source videos/i.test(paragraph.textContent))paragraph.classList.add('legacy-source-note');
   }
   const contact=card.querySelector('[data-plan-contact]');
   if(contact){const icon=el('span','glass-whatsapp-icon');icon.setAttribute('aria-hidden','true');icon.innerHTML=whatsapp;contact.replaceChildren(icon,el('span','','Contact on WhatsApp'));}
  }
 }
 window.addEventListener('velaur:pricing',event=>render(event.detail));
 window.VelaurAccount?.ready.then(()=>window.dispatchEvent(new Event('velaur:refresh-pricing'))).catch(()=>{});
})();
