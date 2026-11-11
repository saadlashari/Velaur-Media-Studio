/* Public plan comparison; verified Google members submit an admin-reviewed request. */
(() => {
 const prices={creator:1,pro:2,studio:3};
 const billing=()=>document.querySelector('[data-billing][aria-pressed="true"]')?.dataset.billing||'monthly';
 const message=document.createElement('p');
 message.className='pricing-note';
 message.setAttribute('role','status');
 message.style.margin='18px auto';
 message.style.maxWidth='760px';
 document.querySelector('.pricing-grid')?.after(message);
 for(const key of Object.keys(prices)){
  const card=document.getElementById(key+'Price')?.closest('.price-card');
  if(!card)continue;
  const old=card.querySelector('#creatorTrial');
  if(old)old.hidden=true;
  const btn=document.createElement('button');
  btn.type='button';btn.className='small-button request-plan-button';
  btn.dataset.planRequest=key;
  btn.textContent='Request '+key[0].toUpperCase()+key.slice(1);
  card.append(btn);
  btn.addEventListener('click',async()=>{
   const A=window.VelaurAccount;
   try{await A.ready;}catch(e){message.textContent='Account service unavailable. Please retry.';return;}
   if(!A.profile||A.profile.user.role==='guest'){
    try{sessionStorage.setItem('velaur:pricing-intent',key+':'+billing());}catch{}
    location.href='/login';return;
   }
   btn.disabled=true;
   try{
    const result=await A.request('/api/me/plan-request',{method:'POST',
      body:JSON.stringify({plan:key,billing:billing()})});
    message.textContent=result.message||'Request submitted. Await admin approval.';
    message.scrollIntoView({block:'nearest',behavior:'smooth'});
   }catch(e){message.textContent=e.message;}
   finally{btn.disabled=false;}
  });
 }
 const note=document.getElementById('pricingNote');
 if(note)note.textContent='Annual plans cost 10 months for 12 months of access. No online checkout or automatic charge. Approval is manual.';
 for(const [key,price] of Object.entries(prices)){
  const card=document.getElementById(key+'Price')?.closest('.price-card');
  const trial=card?.querySelector('#trialOffer');
  if(trial)trial.hidden=true;
 }
 const A=window.VelaurAccount;
 A?.ready.then(()=>{
  if(A.profile?.user?.role==='guest')return;
  const selected=sessionStorage.getItem('velaur:pricing-intent');
  if(selected){
   const [plan,interval]=selected.split(':');
   sessionStorage.removeItem('velaur:pricing-intent');
   if(plan in prices){
    const switcher=document.querySelector('[data-billing="'+interval+'"]');
    switcher?.click();
    const btn=document.querySelector('[data-plan-request="'+plan+'"]');
    btn?.scrollIntoView({block:'center'});
    message.textContent='Your '+plan+' plan is selected. Click Request to submit for admin approval.';
   }
  }
 }).catch(()=>{});
})();
