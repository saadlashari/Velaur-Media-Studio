/* Contextual navigation: current page links are omitted in the HTML. */
(() => {
 const button=document.getElementById('siteMenu');
 const header=document.querySelector('.site-topbar');
 if(!button||!header)return;
 function menu(open){header.classList.toggle('menu-open',open);button.setAttribute('aria-expanded',String(open));button.setAttribute('aria-label',open?'Close navigation':'Open navigation');}
 button.addEventListener('click',()=>menu(!header.classList.contains('menu-open')));
 document.addEventListener('click',e=>{if(!header.contains(e.target))menu(false);});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&header.classList.contains('menu-open')){menu(false);button.focus();}});
 header.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',()=>menu(false)));
 window.addEventListener('resize',()=>menu(false));
 const help=document.getElementById('faqHelp');
 if(help&&!document.getElementById('studio')){
  const wrap=help.closest('.help-wrap');
  help.addEventListener('click',()=>{const open=!wrap.classList.contains('is-open');wrap.classList.toggle('is-open',open);help.setAttribute('aria-expanded',String(open));});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){wrap.classList.remove('is-open');help.setAttribute('aria-expanded','false');help.blur();}});
 }
})();
