/* Non-invasive navigation consistency and hero icon polish */
(()=>{const here=location.pathname.replace(/\/$/,'')||'/';document.querySelectorAll('.site-topbar .site-nav a[href]').forEach(a=>{const path=new URL(a.href,location.origin).pathname.replace(/\/$/,'')||'/';if(path===here)a.setAttribute('aria-current','page')});const primary=document.querySelector('.hero-actions .action.primary');const use=primary?.querySelector('svg use');if(use)use.setAttribute('href','#i-sparkles')})();

/* Mobile navigation geometry only: keep the original account controls and styling. */
(()=>{
 const header=document.querySelector('.web-shell>.site-topbar');
 const nav=header?.querySelector('.site-nav');
 const toggle=header?.querySelector('.site-menu');
 if(!header||!nav||!toggle)return;
 const auth=[...nav.querySelectorAll(':scope > .nav-login, :scope > .nav-signout')];
 if(!auth.length)return;
 const mobile=window.matchMedia('(max-width:760px)');
 function sync(){
  if(mobile.matches){
   auth.forEach(el=>{if(el.parentElement!==header)header.appendChild(el)});
  }else{
   auth.forEach(el=>{if(el.parentElement!==nav)nav.appendChild(el)});
   header.classList.remove('menu-open');
   toggle.setAttribute('aria-expanded','false');
   toggle.setAttribute('aria-label','Open navigation');
  }
 }
 sync();
 if(mobile.addEventListener)mobile.addEventListener('change',sync);
 else mobile.addListener(sync);
})();
