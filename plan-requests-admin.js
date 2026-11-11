/* Admin: manually review verified Google users' plan requests. */
(async()=>{
 const A=window.VelaurAccount;
 try{await A.ready;}catch{return;}
 if(A.profile?.user?.role!=='admin')return;
 const target=document.querySelector('[data-admin-view="users"]');
 if(!target)return;
 const panel=document.createElement('article');
 panel.className='admin-panel';
 const title=document.createElement('h2');title.textContent='Pending plan approvals';
 const hint=document.createElement('p');
 hint.textContent='These requests are from verified Google accounts. Approval grants access immediately. No online payment is collected.';
 const refreshButton=document.createElement('button');
 refreshButton.type='button';refreshButton.className='admin-button secondary';refreshButton.textContent='Refresh requests';
 const status=document.createElement('p');status.setAttribute('role','status');status.className='admin-muted';
 const queue=document.createElement('div');queue.className='uc-rows';
 panel.append(title,hint,refreshButton,status,queue);
 target.prepend(panel);
 async function refresh(){
  refreshButton.disabled=true;
  try{
   const r=await A.request('/api/admin/plan-requests');
   queue.replaceChildren();
   const pending=r.requests.filter(x=>x.status==='pending');
   status.textContent=pending.length+' pending request'+(pending.length===1?'':'s');
   if(!pending.length){const p=document.createElement('p');p.textContent='No pending plan requests.';queue.append(p);}
   for(const item of pending){
    const row=document.createElement('div');row.className='history-row';
    const details=document.createElement('p');
    details.textContent=item.email+' — '+item.plan.toUpperCase()+' — '+item.billing;
    const approve=document.createElement('button');approve.type='button';approve.className='admin-button primary';approve.textContent='Approve';
    const reject=document.createElement('button');reject.type='button';reject.className='admin-button secondary';reject.textContent='Reject';
    for(const [btn,decision] of [[approve,'approved'],[reject,'rejected']]){
     btn.addEventListener('click',async()=>{
      if(!confirm((decision==='approved'?'Approve':'Reject')+' the '+item.plan+' request for '+item.email+'?'))return;
      approve.disabled=true;reject.disabled=true;
      try{
       await A.request('/api/admin/plan-requests/'+encodeURIComponent(item.id)+'/decision',
        {method:'POST',body:JSON.stringify({decision})});
       status.textContent='Request '+decision+' for '+item.email+'.';
       await refresh();
      }catch(e){status.textContent=e.message;approve.disabled=false;reject.disabled=false;}
     });
    }
    row.append(details,approve,reject);
    queue.append(row);
   }
  }catch(e){status.textContent=e.message;}
  finally{refreshButton.disabled=false;}
 }
 refreshButton.addEventListener('click',refresh);
 await refresh();
})();
