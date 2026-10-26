/* Geometry only. Do not replace existing help toggle or media handlers. */
(()=>{
 const wraps=[...document.querySelectorAll('.help-wrap')];
 function place(wrap){
  const button=wrap.querySelector('button'),tip=wrap.querySelector('.help-tooltip');if(!button||!tip)return;
  const width=Math.min(300,window.innerWidth-40);
  const rect=button.getBoundingClientRect(),origin=wrap.getBoundingClientRect();
  const left=Math.max(20,Math.min(rect.left+rect.width/2-width/2,window.innerWidth-width-20));
  tip.style.setProperty('--help-width',width+'px');
  tip.style.setProperty('--help-left',(left-origin.left)+'px');
  const height=tip.getBoundingClientRect().height;
  const below=rect.bottom+10;
  const above=rect.top-height-10;
  const top=below+height<=window.innerHeight-12||above<12?below:above;
  tip.style.setProperty('--help-top',(top-origin.top)+'px');
 }
 const update=()=>wraps.forEach(place);
 for(const wrap of wraps){
  for(const type of ['pointerenter','focusin'])wrap.addEventListener(type,()=>{wrap.classList.remove('is-dismissed');place(wrap);});
  wrap.addEventListener('click',()=>{const button=wrap.querySelector('button');wrap.classList.toggle('is-dismissed',button?.getAttribute('aria-expanded')==='false');place(wrap);});
 }
 function dismiss(wrap){wrap.classList.remove('is-open');wrap.classList.add('is-dismissed');const button=wrap.querySelector('button');button?.setAttribute('aria-expanded','false');button?.blur();}
 document.addEventListener('keydown',event=>{if(event.key==='Escape')wraps.forEach(dismiss);});
 document.addEventListener('click',event=>wraps.filter(wrap=>!wrap.contains(event.target)).forEach(dismiss));
 window.addEventListener('resize',update,{passive:true});
 window.addEventListener('scroll',update,{passive:true,capture:true});
 document.fonts?.ready.then(update);update();
})();
