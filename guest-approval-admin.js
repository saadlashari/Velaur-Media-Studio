/* Admin-only manual email invitations. Uses existing authenticated CSRF API helper. */
(async()=>{
 const A=window.VelaurAccount;
 try{await A.ready}catch{return}
 if(A.profile?.user.role!=='admin')return;
 const users=document.querySelector('[data-admin-view="users"]');
 if(!users)return;
 const panel=document.createElement('article');
 panel.className='admin-panel';
 const title=document.createElement('h2');title.textContent='Approve verified-email access';
 const description=document.createElement('p');
 description.textContent='After a guest contacts you, approve the exact email they will verify using Google. Only that verified email can claim the assigned plan. No payment is collected.';
 const form=document.createElement('form');form.className='admin-form-grid';
 const email=document.createElement('input');email.type='email';email.required=true;email.maxLength=254;email.placeholder='user@example.com';email.autocomplete='off';
 const emailLabel=document.createElement('label');emailLabel.className='form-field';emailLabel.textContent='Approved email';emailLabel.append(email);
 const plan=document.createElement('select');for(const key of ['creator','pro','studio']){const opt=document.createElement('option');opt.value=key;opt.textContent=key[0].toUpperCase()+key.slice(1);plan.append(opt);}
 const planLabel=document.createElement('label');planLabel.className='form-field';planLabel.textContent='Access level';planLabel.append(plan);
 const days=document.createElement('input');days.type='number';days.min='1';days.max='366';days.value='30';days.required=true;
 const daysLabel=document.createElement('label');daysLabel.className='form-field';daysLabel.textContent='Days of access';daysLabel.append(days);
 const reason=document.createElement('textarea');reason.required=true;reason.minLength=3;reason.maxLength=300;reason.placeholder='Reason for this invitation';
 const reasonLabel=document.createElement('label');reasonLabel.className='form-field';reasonLabel.textContent='Audit reason';reasonLabel.append(reason);
 const submit=document.createElement('button');submit.type='submit';submit.className='admin-button primary';submit.textContent='Approve this email';
 const feedback=document.createElement('p');feedback.setAttribute('role','status');feedback.className='admin-muted';
 form.append(emailLabel,planLabel,daysLabel,reasonLabel,submit,feedback);
 const list=document.createElement('div');list.className='uc-rows';
 const h=document.createElement('h3');h.textContent='Recent invitations';
 panel.append(title,description,form,h,list);users.prepend(panel);
 async function refresh(){
  const result=await A.request('/api/admin/invitations');
  list.replaceChildren();
  for(const r of result.invitations){
   const item=document.createElement('p');
   item.textContent=r.email+' · '+r.plan+' · '+r.days+' days · '+r.status;
   list.append(item);
  }
  if(!result.invitations.length){const p=document.createElement('p');p.textContent='No invitations yet.';list.append(p);}
 }
 form.addEventListener('submit',async e=>{
  e.preventDefault();if(!form.reportValidity())return;
  submit.disabled=true;feedback.textContent='';
  try{
   const payload={email:email.value.trim().toLowerCase(),plan:plan.value,days:Number(days.value),reason:reason.value};
   await A.request('/api/admin/invitations',{method:'POST',body:JSON.stringify(payload)});
   feedback.textContent='Email approved. Ask the user to verify this exact email with Google at /login.';
   email.value='';reason.value='';
   await refresh();
  }catch(error){feedback.textContent=error.message}
  finally{submit.disabled=false}
 });
 refresh().catch(e=>{feedback.textContent=e.message});
})();
