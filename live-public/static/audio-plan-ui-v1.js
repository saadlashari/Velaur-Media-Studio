/* Audio quota display; limits are enforced by the backend. */
(()=>{
 function render({plans,profile}){
  for(const [key,plan] of Object.entries(plans)){
   const price=document.getElementById(key+'Price'),card=price?.closest('.price-card');if(!card)continue;
   let p=card.querySelector('[data-audio-allowance]');
   if(!p){p=document.createElement('p');p.dataset.audioAllowance=key;const control=card.querySelector('button,a.small-button');control?control.before(p):card.append(p);}
   p.textContent=plan.mp3_exports===0?'Unlimited MP3 exports/day':plan.mp3_exports+' MP3 exports/day';
   p.title='MP3 and MP4 use your shared export-duration allowance. Failed jobs release their reservation.';
  }
  if(!profile)return;
  const list=document.querySelector('.usage-list');
  if(list){
   let row=document.getElementById('audioUsageRow');if(!row){row=document.createElement('div');row.id='audioUsageRow';row.innerHTML='<dt>MP3 exports</dt><dd></dd>';list.append(row);}
   const limit=profile.usage.mp3_limit;
   row.querySelector('dd').textContent=(profile.usage.mp3_exports_today||0)+' / '+(limit==null?'Unlimited':limit);
   const video=document.getElementById('dailyExports')?.closest('div')?.querySelector('dt');if(video)video.textContent='MP4 exports';
  }
 }
 window.addEventListener('velaur:audio',e=>render(e.detail));
 window.VelaurAccount?.ready.then(()=>window.dispatchEvent(new Event('velaur:audio-refresh'))).catch(()=>{});
})();
