/* Decorative wrappers only: preserve all pricing IDs, buttons and handlers. */
(()=>{
 const paths={creator:'M4 5h16v14H4zM4 9h16M8 5v4m8-4v4M10 12l5 2-5 2z',pro:'M5 6h14v12H5zM2 9h3m14 0h3M8 2v4m8-4v4M8 18v4m8-4v4',studio:'M4 7h11v10H4zM15 10l5-3v10l-5-3'};
 function icon(path,cls){const span=document.createElement('span');span.className=cls;span.setAttribute('aria-hidden','true');span.innerHTML='<svg viewBox="0 0 24 24"><path d="'+path+'"/></svg>';return span;}
 for(const card of document.querySelectorAll('.price-card')){
  if(card.querySelector('.card-heading-band'))continue;
  const heading=card.querySelector('h3'),badge=card.querySelector('.price-badge');if(!heading)continue;
  const key=card.querySelector('#creatorPrice')?'creator':card.querySelector('#proPrice')?'pro':'studio';
  const band=document.createElement('div');band.className='card-heading-band';
  const text=document.createElement('div');if(badge)text.append(badge);text.append(heading);band.append(text,icon(paths[key],'card-plan-icon'));card.prepend(band);
 }
 const symbols=['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8','M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M8 12l3 3 5-6','M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4','M12 3v4m0 10v4M3 12h4m10 0h4M6 6l3 3m6 6 3 3M6 18l3-3m6-6 3-3'];
 document.querySelectorAll('.admin-stats article').forEach((card,i)=>{if(!card.querySelector('.card-summary-icon'))card.append(icon(symbols[i]||symbols[0],'card-summary-icon'));});
})();
