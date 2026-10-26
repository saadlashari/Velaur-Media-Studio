/* Decorative login icon only. Existing sign-in links and handlers stay attached. */
(()=>{
 for(const link of document.querySelectorAll('.site-topbar .nav-login')){
  if(link.querySelector('.nav-login-icon'))continue;
  const icon=document.createElementNS('http://www.w3.org/2000/svg','svg');
  icon.setAttribute('class','nav-login-icon');icon.setAttribute('viewBox','0 0 24 24');icon.setAttribute('aria-hidden','true');icon.setAttribute('focusable','false');
  icon.innerHTML='<path d="M14 5h5v14h-5M10 8l4 4-4 4M14 12H3"/>';
  link.prepend(icon);
 }
})();
