/* UI only. Authentication and media handlers remain unchanged. */
(() => {
 const header=document.querySelector('.site-topbar');
 if(header){const session=document.createElement('div');session.className='header-session';session.setAttribute('aria-label','Account');header.querySelectorAll('.nav-login,[data-logout]').forEach(el=>session.append(el));header.append(session);}
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
   let contact=card.querySelector('[data-plan-contact]');
   if(!contact){contact=document.createElement('a');contact.className='small-button whatsapp-plan';contact.dataset.planContact=key;contact.target='_blank';contact.rel='noopener noreferrer';contact.textContent='Contact on WhatsApp';card.append(contact);}
   contact.href='https://wa.me/923211618331?text='+encodeURIComponent('Hello VELAUR LABS, I am interested in the Velaur Media Studio '+(plan.name||key)+' plan ('+(yearly?'yearly':'monthly')+'). Please share the details.');
   const active=!!profile?.access.enabled && profile.access.plan===key;
   const canTrial=key==='creator' && !!eligible && !yearly && !active;
   let status=card.querySelector('[data-active-plan]');
   if(!status){status=document.createElement('button');status.type='button';status.disabled=true;status.className='small-button active-plan-button';status.dataset.activePlan=key;status.textContent='Your Active Plan';card.append(status);}
   status.hidden=!active;
   contact.hidden=active||canTrial;
   if(key==='creator'){
    const trial=document.getElementById('creatorTrial');if(trial)trial.hidden=!canTrial;
    line.classList.toggle('trial-crossed',canTrial);
    const offer=document.getElementById('trialOffer');if(offer)offer.hidden=!canTrial;
    const badge=document.getElementById('trialLabel');if(badge&&active)badge.textContent=profile.access.access_kind==='trial'?'YOUR ACTIVE TRIAL':'YOUR ACTIVE PLAN';else if(badge&&yearly)badge.textContent='YEARLY CREATOR';
   }else card.querySelectorAll('button.small-button:not([data-active-plan])').forEach(b=>b.hidden=true);
   card.classList.toggle('is-active-plan',active);

  }
  const note=document.getElementById('pricingNote');if(note)note.textContent='Monthly Creator trial: no card required, no automatic renewal. Contact us on WhatsApp for paid plan details.';
 }
 window.addEventListener('velaur:pricing',e=>paint(e.detail));
 window.VelaurAccount?.ready.then(()=>window.dispatchEvent(new Event('velaur:refresh-pricing'))).catch(()=>{});
})();
