/* UI only. Authentication and media handlers remain unchanged. */
(() => {
 const header=document.querySelector('.site-topbar');
 // Keep account actions inside the shared navigation. CSS positions them at the right edge.
 const money=v=>'$'+Number(v).toLocaleString('en-US',{maximumFractionDigits:2});
 function paint({plans,yearly,eligible}){
  // pricing-buttons-1: derive active/expired state from the backend account.
  const profile=window.VelaurAccount?.profile;
  for(const [key,plan] of Object.entries(plans)){
   const price=document.getElementById(key+'Price'),card=price?.closest('.price-card');if(!card)continue;
   const line=price.closest('.price-line');let original=card.querySelector('.annual-original');
   if(!original){original=document.createElement('div');original.className='annual-original';line.before(original);}
   original.replaceChildren();
   const annual=Number(plan.monthly)*12,saving=annual-Number(plan.yearly);
   original.hidden=!yearly||saving<=0;
   if(yearly&&saving>0){const del=document.createElement('del');del.textContent=money(annual)+'/year';const badge=document.createElement('span');badge.textContent='Save '+money(saving);original.append(del,badge);}
   // Plan purchase requests are reviewed in /admin, not handled by a checkout.
   const contact=card.querySelector('[data-plan-contact]');
   if(contact)contact.remove();
   const active=!!profile?.access.enabled && profile.access.plan===key;
   const canTrial=false;
   // Active-plan status is rendered only for an authenticated, actually active plan.
   let status=card.querySelector('[data-active-plan]');
   if(!active){if(status)status.remove();}
   else {if(!status){status=document.createElement('span');status.className='active-plan-status';status.dataset.activePlan=key;card.append(status);}status.textContent='Your Active Plan';}
   if(key==='creator'){
    const trial=document.getElementById('creatorTrial');if(trial)trial.hidden=!canTrial;
    line.classList.toggle('trial-crossed',canTrial);
    const offer=document.getElementById('trialOffer');if(offer)offer.hidden=!canTrial;
    const badge=document.getElementById('trialLabel');if(badge&&active)badge.textContent=profile.access.access_kind==='trial'?'YOUR ACTIVE TRIAL':'YOUR ACTIVE PLAN';else if(badge&&yearly)badge.textContent='YEARLY CREATOR';
   }
   card.classList.toggle('is-active-plan',active);

  }
  const note=document.getElementById('pricingNote');if(note)note.textContent='Select a plan to request admin approval. Annual plans cost 10 months for 12 months of access. No checkout or automatic payment is enabled.';
 }
 window.addEventListener('velaur:pricing',e=>paint(e.detail));
 window.VelaurAccount?.ready.then(()=>window.dispatchEvent(new Event('velaur:refresh-pricing'))).catch(()=>{});
})();
