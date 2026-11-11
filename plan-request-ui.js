/* One visible control per plan: request -> requested -> active. Manual WhatsApp payment. */
(() => {
 const prices={creator:1,pro:2,studio:3};
 const names={creator:'Creator',pro:'Pro',studio:'Studio'};
 const whatsappNumber='923211618331';
 const A=window.VelaurAccount;
 const billing=()=>document.querySelector('[data-billing][aria-pressed="true"]')?.dataset.billing||'monthly';
 const amount=(plan,term)=>prices[plan]*(term==='yearly'?10:1);
 const message=document.createElement('p');
 message.className='pricing-note';message.setAttribute('role','status');
 document.querySelector('.pricing-grid')?.after(message);
 let pending=null,active=null,loggedIn=false,working=false;
 const buttons={};
 const dialog=document.createElement('dialog');dialog.className='velaur-payment-dialog';
 dialog.setAttribute('aria-labelledby','paymentTitle');
 dialog.innerHTML='<div class="velaur-payment-panel"><button type="button" class="velaur-payment-close" aria-label="Close">×</button><span class="velaur-payment-kicker">MANUAL PAYMENT</span><h2 id="paymentTitle">Complete your plan request</h2><p id="paymentDetails"></p><p class="velaur-payment-note">Payment is arranged directly with VELAUR LABS over WhatsApp. Do not pay until you have verified the recipient and payment instructions. Sending a request does not confirm payment or activate a plan.</p><p id="paymentFeedback" role="status"></p><div class="velaur-payment-actions"><button type="button" id="paymentConfirm" class="small-button">Request &amp; Continue to WhatsApp</button><button type="button" id="paymentCancel" class="small-button">Cancel</button></div></div>';
 document.body.append(dialog);
 const close=()=>dialog.close();
 dialog.querySelector('.velaur-payment-close').addEventListener('click',close);
 dialog.querySelector('#paymentCancel').addEventListener('click',close);
 dialog.addEventListener('click',e=>{if(e.target===dialog)close();});
 let chosen=null;
 function whatsappUrl(plan,term,email){
  const total=amount(plan,term);
  const msg='Hello VELAUR LABS, I requested the '+names[plan]+' plan for VELAUR Media Studio. Billing: '+term+'. Amount: USD $'+total+'. Verified Google email: '+email+'. Please share manual payment instructions and confirm my payment before activating access.';
  return 'https://wa.me/'+whatsappNumber+'?text='+encodeURIComponent(msg);
 }
 function render(){
  for(const [plan,button] of Object.entries(buttons)){
   const isActive=active===plan;
   const requested=!!pending && pending.status==='pending' && pending.plan===plan && !active;
   button.replaceChildren();
   button.textContent=isActive?'Your Active Plan':requested?'Requested':'Request Plan';
   button.classList.toggle('is-plan-status',isActive||requested);
   button.disabled=working||isActive||requested||!!active||!!(pending?.status==='pending');
   button.setAttribute('aria-disabled',String(button.disabled));
   button.style.cursor=button.disabled?'default':'pointer';
   button.style.opacity=isActive||requested?'1':'';
   button.setAttribute('aria-label',isActive?'Your active '+names[plan]+' plan':requested?names[plan]+' plan requested': 'Request '+names[plan]+' plan');
   const card=button.closest('.price-card');
   if(card)card.classList.toggle('is-active-plan',isActive);
  }
 }
 for(const plan of Object.keys(prices)){
  const card=document.getElementById(plan+'Price')?.closest('.price-card');
  if(!card)continue;
  card.querySelectorAll('[data-active-plan],[data-plan-contact],.request-plan-button').forEach(e=>e.remove());
  const trial=card.querySelector('#creatorTrial');if(trial)trial.hidden=true;
  const button=document.createElement('button');
  button.type='button';button.className='small-button request-plan-button';
  button.dataset.planRequest=plan;buttons[plan]=button;card.append(button);
  button.addEventListener('click',()=>{
   if(button.disabled)return;
   if(!loggedIn){
    try{sessionStorage.setItem('velaur:pricing-intent',plan+':'+billing());}catch{}
    location.href='/login';return;
   }
   chosen={plan,term:billing()};
   const total=amount(plan,chosen.term);
   dialog.querySelector('#paymentDetails').textContent=names[plan]+' — '+(chosen.term==='yearly'?'Yearly (12 months, pay for 10)':'Monthly')+' — USD $'+total+'.';
   dialog.querySelector('#paymentFeedback').textContent='';
   dialog.showModal();
  });
 }
 dialog.querySelector('#paymentConfirm').addEventListener('click',async()=>{
  if(!chosen||working)return;
  const {plan,term}=chosen;
  const submit=dialog.querySelector('#paymentConfirm');
  working=true;submit.disabled=true;render();
  try{
   const result=await A.request('/api/me/plan-request',{method:'POST',body:JSON.stringify({plan,billing:term})});
   pending={plan,billing:term,status:'pending'};
   message.textContent=result.message||'Request recorded. Please contact VELAUR LABS for manual payment.';
   dialog.querySelector('#paymentFeedback').textContent='Your request is recorded as Pending. Opening WhatsApp for payment instructions.';
   const link=whatsappUrl(plan,term,A.profile?.user?.email||'');
   // User-initiated click opens the payment conversation; no payment is taken by the website.
   const tab=window.open(link,'_blank','noopener,noreferrer');
   if(!tab){
    const a=document.createElement('a');a.href=link;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Open WhatsApp payment chat';a.className='small-button';
    dialog.querySelector('#paymentFeedback').append(' ',a);
   }
   render();
  }catch(e){dialog.querySelector('#paymentFeedback').textContent=e.message;}
  finally{working=false;submit.disabled=false;render();}
 });
 const note=document.getElementById('pricingNote');
 if(note)note.textContent='Yearly: pay for 10 months, receive 12. Manual WhatsApp payment. Request remains pending until admin approves.';
 async function sync(){
  try{
   await A.ready;
   loggedIn=!!A.profile && A.profile.user.role!=='guest';
   active=A.profile?.access?.enabled && loggedIn ? A.profile.access.plan:null;
   if(loggedIn){
    const data=await A.request('/api/me/plan-request');
    pending=data.request?.status==='pending'?data.request:null;
   }else pending=null;
   render();
   if(loggedIn){
    let selection=null;
    try{selection=sessionStorage.getItem('velaur:pricing-intent');sessionStorage.removeItem('velaur:pricing-intent');}catch{}
    if(selection){
     const [plan,term]=selection.split(':');
     if(plan in prices){
      document.querySelector('[data-billing="'+term+'"]')?.click();
      message.textContent='Your '+names[plan]+' plan is selected. Click Request Plan to see the payment instructions.';
     }
    }
   }
  }catch(e){message.textContent='Could not verify plan status. Refresh and try again.';}
 }
 window.addEventListener('velaur:pricing',()=>render());
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();});
 sync();
})();
