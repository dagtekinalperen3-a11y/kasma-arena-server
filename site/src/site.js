/* EvolveArena sitesi — ortak kod. Veri: window.GD (assets/data.js, tools/build_site.py üretir). */
(function(){
'use strict';
const GD=window.GD||null;
const API=(/onrender\.com$/.test(location.hostname)||location.hostname==='localhost'||location.hostname==='127.0.0.1')?'':'https://kasma-arena-server-wir3.onrender.com';
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const PAGE=document.body.dataset.page||'';
function esc(t){return String(t==null?'':t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function num(n){return Number(n||0).toLocaleString('tr-TR');}
function img(u){return /^data:image\/(png|webp);base64,[A-Za-z0-9+/=]+$/.test(u||'')?u:'';}
function pct(v){return '%'+String(v).replace('.',',');}
const yil=$('#yil');if(yil)yil.textContent=new Date().getFullYear();

/* ---------- menü ---------- */
const burger=$('#burger'),nav=$('#nav');
if(burger)burger.onclick=()=>{const o=nav.classList.toggle('open');burger.setAttribute('aria-expanded',o);};

/* ---------- pencereler ---------- */
function openModal(id){$(id).classList.add('on');}
function closeAll(){$$('.modal.on').forEach(m=>m.classList.remove('on'));}
$$('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m||e.target.closest('[data-close]'))m.classList.remove('on');}));
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeAll();closeDrawer();}});
function info(html,wide){const b=$('#mInfoBox');b.className='mbox'+(wide?'':' sm');b.innerHTML='<button class="mclose" data-close aria-label="Kapat">×</button>'+html;openModal('#mInfo');}

/* ---------- ortak kart ---------- */
function card(o){
  return '<article class="card" tabindex="0" role="button" style="--c:'+esc(o.c)+(o.uc?';--uc:'+esc(o.uc):'')+'" data-t="'+esc(o.t)+'" data-k="'+esc(o.k)+'">'+
    (o.badges?'<div class="badges">'+o.badges+'</div>':'')+
    '<div class="stage"><img loading="lazy" alt="'+esc(o.n)+'" src="'+img(o.img)+'"></div>'+
    '<h3>'+esc(o.n)+'</h3>'+(o.meta?'<div class="meta'+(o.metaC?' c':'')+'">'+o.meta+'</div>':'')+
    (o.foot?'<div class="foot">'+o.foot+'</div>':'')+'</article>';
}
function detail(o){
  return '<div class="detail" style="--c:'+esc(o.c)+'"><div class="art"><img alt="" src="'+img(o.img)+'"></div><div class="info">'+
    (o.badges||'')+'<h2>'+esc(o.n)+'</h2>'+(o.desc?'<p class="desc">'+esc(o.desc)+'</p>':'')+'<div class="dl">'+o.body+'</div></div></div>';
}
function row(h,p){return '<div class="row"><h4>'+esc(h)+'</h4>'+p+'</div>';}
function ul(items){return '<ul class="list">'+items.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>';}
function tabs(sel,fn){$$(sel+' button').forEach(t=>t.onclick=()=>{$$(sel+' button').forEach(x=>x.setAttribute('aria-selected','false'));t.setAttribute('aria-selected','true');fn(t.dataset.c);});}

/* ---------- karakterler ---------- */
const NEW=GD?GD.new:[];
function skinPrice(s){
  if(s.premium)return '<span class="price p">'+esc(s.price||'Premium')+' · Mağaza</span>';
  if(!s.cost)return '<span class="price f">Ücretsiz</span>';
  return '<span class="price">💎 '+num(s.cost)+'</span>';
}
function skinCard(s){
  return card({t:'skin',k:s.id,c:s.color,uc:s.ult&&s.ult.color,n:s.name,img:s.img,
    badges:(NEW.includes(s.id)?'<span class="tag new">Yeni</span>':'')+(s.premium?'<span class="tag prem">Premium</span>':''),
    meta:s.ult?esc(s.ult.name)+' · '+Math.round(s.ult.cd)+' sn':'',metaC:true,foot:skinPrice(s)});
}
const STYLE_N=['Saldırı','Savunma','Hareket','Kazanç'];
function skinDetail(s){
  const bars=s.style&&s.style.length?'<div class="bars">'+s.style.map((v,i)=>'<div class="bar">'+STYLE_N[i]+'<i><b style="width:'+Math.round(v*100)+'%"></b></i></div>').join('')+'</div>':'';
  return detail({c:s.color,img:s.img,n:s.name,desc:s.desc,
    badges:(NEW.includes(s.id)?'<span class="tag new">Yeni</span> ':'')+(s.premium?'<span class="tag prem">Premium</span>':''),
    body:(s.ult?'<div class="ultbox" style="--uc:'+esc(s.ult.color)+'"><h4>⚡ '+esc(s.ult.name)+' · '+Math.round(s.ult.cd)+' sn</h4><p>'+esc(s.ult.desc)+'</p></div>':'')+
      row('Kalıcı özellikler',ul(s.perks))+(bars?row('Oyun tarzı',bars):'')+row('Fiyat','<p>'+skinPrice(s)+'</p>')});
}
function renderSkins(f){
  const el=$('#skinGrid');if(!el)return;
  const L=GD.skins.filter(s=>f==='all'||(f==='new'&&NEW.includes(s.id))||(f==='free'&&!s.premium&&!s.cost)||(f==='gem'&&!s.premium&&s.cost)||(f==='prem'&&s.premium));
  el.innerHTML=L.map(skinCard).join('');
}

/* ---------- silahlar ---------- */
function weaponDetail(w){
  const ev=GD.evos.find(e=>e.key===w.key);
  return detail({c:w.color,img:w.img,n:w.name,desc:w.desc,
    badges:w.timed?'<span class="tag soft">Döngü</span>':(w.passive?'<span class="tag soft">Sürekli</span>':''),
    body:(w.up?row('Seviye atlayınca','<p>'+esc(w.up)+'</p>'):'')+
      row('Nasıl açılır','<p>'+esc(w.how||w.unlock)+'</p>'+(w.reqs.length>1?ul(w.reqs):''))+
      (ev?row('Evrim','<p><b style="color:'+esc(ev.tiers[0].color)+'">'+esc(ev.tiers.map(t=>t.name).join(' › '))+'</b><br>Eş kitap: '+esc(ev.book)+' · <a href="evrimler.html#'+esc(w.key)+'" style="color:var(--gold)">Evrimleri gör ›</a></p>'):'')+
      row('En yüksek seviye','<p>Lv '+esc(w.max)+'</p>')});
}

/* ---------- kitaplar ---------- */
function bookDetail(b){
  return detail({c:b.color,img:b.img,n:b.name,desc:b.desc,badges:b.rare?'<span class="tag rare">Nadir</span>':'',
    body:row('Nasıl açılır',b.reqs.length?ul(b.reqs):'<p>'+esc(b.unlock)+'</p>')+
      (b.rare?row('Nadir kitap','<p>Seviye atlamaz; koşu başına yalnızca 1 nadir kitap taşınır. Her 5 seviyede bir nadir kart gelir.</p>'):row('En yüksek seviye','<p>Lv '+esc(b.max)+'</p>'))+
      (b.pairs.length?row('Eşi olduğu silahlar','<p>'+esc(b.pairs.join(', '))+' · <a href="evrimler.html" style="color:var(--gold)">Evrimler ›</a></p>'):'')});
}

/* ---------- kostümler ---------- */
function cosPrice(c){
  if(c.slot==='pet')return '<span class="price p">'+esc(c.price||'Mağaza')+' · Mağaza</span>';
  if(c.wheel)return '<span class="price w">Şans Çarkı</span>';
  return '<span class="price">💎 '+num(c.cost)+'</span>';
}
function cosDetail(c){
  return detail({c:c.color,img:c.img,n:c.name,desc:c.desc,
    body:(c.perk&&c.slot!=='pet'?row('Bonus','<p>'+esc(c.perk)+'</p>'):row('Bonus','<p>Yalnız görünüş; peşinden gelen küçük bir dost.</p>'))+row('Fiyat','<p>'+cosPrice(c)+'</p>')});
}

/* ---------- detay açma ---------- */
function openDetail(t,k){
  if(!GD)return;let h='';
  if(t==='skin'){const s=GD.skins.find(x=>x.id===k);if(s)h=skinDetail(s);}
  else if(t==='weapon'){const w=GD.weapons.find(x=>x.key===k);if(w)h=weaponDetail(w);}
  else if(t==='book'){const b=GD.books.find(x=>x.key===k);if(b)h=bookDetail(b);}
  else if(t==='cos'){const c=GD.cosmetics.concat(GD.pets).find(x=>x.id===k);if(c)h=cosDetail(c);}
  if(h)info(h,true);
}
document.addEventListener('click',e=>{const c=e.target.closest('.card[data-t]');if(c)openDetail(c.dataset.t,c.dataset.k);});
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&document.activeElement&&document.activeElement.matches&&document.activeElement.matches('.card[data-t]')){const c=document.activeElement;openDetail(c.dataset.t,c.dataset.k);}});

/* ---------- sayfalar ---------- */
const pages={
  index(){
    const sc=$('#showcase');
    if(sc){NEW.forEach((id,i)=>{const s=GD.skins.find(x=>x.id===id);if(!s)return;const d=sc.querySelector('.s'+(i+1));if(d)d.innerHTML='<img alt="'+esc(s.name)+'" src="'+img(s.img)+'">';});}
    const ng=$('#newGrid');
    if(ng)ng.innerHTML=NEW.map(id=>{const s=GD.skins.find(x=>x.id===id);if(!s)return '';
      return '<a class="newcard" href="karakterler.html#'+esc(s.id)+'" style="--c:'+esc(s.color)+';--uc:'+esc(s.ult?s.ult.color:s.color)+'"><span class="tag new">Yeni</span>'+
        '<div class="stage"><img alt="'+esc(s.name)+'" src="'+img(s.img)+'"></div><h3>'+esc(s.name)+'</h3>'+
        (s.ult?'<div class="ult">⚡ '+esc(s.ult.name)+'</div><p>'+esc(s.ult.desc)+'</p>':'')+'</a>';}).join('');
    const pick=(arr,k,v)=>{const x=arr.find(a=>a[k]===v);return x?x.img:(arr[0]&&arr[0].img)};
    const ic={karakterler:pick(GD.skins,'id','cosmic'),silahlar:pick(GD.weapons,'key','axe'),evrimler:pick(GD.weapons,'key','meteor'),
      kitaplar:pick(GD.books,'key','r_luck'),kostumler:pick(GD.pets,'id','pet_dragon')};
    $$('.tile[data-ic]').forEach(t=>{const u=ic[t.dataset.ic];if(u)t.querySelector('.ic').innerHTML='<img alt="" src="'+img(u)+'">';});
    demo('oyun','dhp','dwv','dlv','dkl','dnot');
    initDownload();
  },
  karakterler(){
    renderSkins('all');tabs('#skinTabs',renderSkins);
    const h=location.hash.slice(1);if(h&&GD.skins.some(s=>s.id===h))setTimeout(()=>openDetail('skin',h),150);
  },
  silahlar(){
    $('#weaponGrid').innerHTML=GD.weapons.map(w=>card({t:'weapon',k:w.key,c:w.color,n:w.name,img:w.img,
      badges:w.timed?'<span class="tag soft">Döngü</span>':(w.passive?'<span class="tag soft">Sürekli</span>':''),
      meta:w.evo?'Evrim: '+esc(w.evo):'',foot:'<span class="muted" style="font-weight:600">Eş kitap: '+esc(w.book||'—')+'</span>'})).join('');
  },
  evrimler(){
    const R=GD.evo_rules;
    $('#rules').innerHTML=[0,1,2].map(i=>'<div class="rule"><div class="rn" style="color:'+['#7fd4ff','#c58cff','#f3c55e'][i]+'">'+['I','II','III'][i]+'. kademe</div>'+
      '<p>Silah <b>Lv '+R.lvl[i]+'</b> + eş kitap <b>Lv '+R.book[i]+'</b><br>Silah hasarı <b>×'+String(R.mult[i]).replace('.',',')+'</b></p></div>').join('');
    $('#evoList').innerHTML=GD.evos.map(e=>'<section class="evo" id="'+esc(e.key)+'">'+
      '<div class="pair"><figure><img alt="" src="'+img(e.wimg)+'"><figcaption>'+esc(e.weapon)+'</figcaption></figure><span class="plus">+</span>'+
      '<figure><img alt="" src="'+img(e.bimg)+'"><figcaption>'+esc(e.book)+(e.brare?' ★':'')+'</figcaption></figure></div>'+
      '<div class="tiers">'+e.tiers.map(t=>'<div class="tier" style="--tc:'+esc(t.color)+'"><span class="rn">'+t.roman+'</span><h4>'+esc(t.name)+'</h4><p>'+esc(t.perk)+'</p>'+
        '<div class="need">Silah Lv '+t.lvl+' + kitap Lv '+t.book_lvl+' · hasar ×'+String(t.mult).replace('.',',')+'</div></div>').join('')+'</div></section>').join('');
    const h=location.hash.slice(1);if(h){const el=document.getElementById(h);if(el)setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'center'}),150);}
  },
  kitaplar(){
    const r=f=>{$('#bookGrid').innerHTML=GD.books.filter(b=>f==='rare'?b.rare:!b.rare).map(b=>card({t:'book',k:b.key,c:b.color,n:b.name,img:b.img,
      badges:b.rare?'<span class="tag rare">Nadir</span>':'',meta:esc(b.desc),foot:b.pairs.length?'<span class="muted" style="font-weight:600">Eşi: '+esc(b.pairs.join(', '))+'</span>':''})).join('');};
    r('normal');tabs('#bookTabs',r);
  },
  kostumler(){
    const r=f=>{const L=f==='pet'?GD.pets:GD.cosmetics.filter(c=>c.slot===f);
      $('#cosGrid').innerHTML=L.map(c=>card({t:'cos',k:c.id,c:c.color,n:c.name,img:c.img,meta:c.slot!=='pet'&&c.perk?'★ '+esc(c.perk):'',foot:cosPrice(c)})).join('');};
    r('hat');tabs('#cosTabs',r);
  },
  rehber(){renderMaps('plaza');renderOaths();},
  magaza(){renderStore('gems');tabs('#storeTabs',renderStore);},
  kazi(){renderTiers();initScratch();},
  oyunlar(){initGames();}
};

/* ---------- mağaza ---------- */
const GEMS=[{g:100,old:null,p:'29,90'},{g:550,old:'74,90',p:'59,90'},{g:1200,old:'149,90',p:'119,90',best:true},{g:2600,old:null,p:'229,90'}];
function odeme(u){return 'odeme.php?urun='+encodeURIComponent(u);}
function renderStore(c){
  const b=$('#storeBody');if(!b)return;
  if(c==='gems'){b.innerHTML='<div class="packs">'+GEMS.map(p=>'<div class="pack'+(p.best?' best':'')+'">'+(p.best?'<span class="tag rare flag">En popüler</span>':'')+
    '<div class="gem">💎</div><h3>'+num(p.g)+' Elmas</h3><div class="old">'+(p.old?p.old+' ₺':'')+'</div><div class="pr">'+p.p+' ₺</div>'+
    '<a class="btn sm block" href="'+odeme(p.g+'_elmas')+'">Satın al</a></div>').join('')+'</div>';return;}
  const L=c==='skins'?GD.skins.filter(s=>s.premium):GD.pets;
  b.innerHTML='<div class="grid lg">'+L.map(s=>card({t:c==='skins'?'skin':'cos',k:s.id,c:s.color,n:s.name,img:s.img,meta:esc(s.desc),
    foot:'<span class="price p">'+esc(s.price)+'</span><a class="btn sm" href="'+odeme((c==='skins'?'skin_':'pet_')+s.name)+'" onclick="event.stopPropagation()">Satın al</a>'})).join('')+'</div>';
}

/* ---------- rehber: haritalar + yeminler ---------- */
const MAPS=[
 {id:'plaza',n:'Taş Meydan',ac:'#e8ba5a',bg:'linear-gradient(160deg,#4a4670,#1d1a36)',
  e:['Sürüngen','Yavru','Tüküren','Tank','Koşucu','Kaba Kuvvet','Elit','Bombacı','Kamikaze','Büyücü','Arı','Şifacı','Bölünen','Ölü Çağırıcı','Hayalet'],
  b:['Savaş Ağası','Cadı','Kolos','Orakçı','Kovan'],t:'Klasik arena. Skorun dünya sıralamasına girer; 10/15/20/25. dalgalarda patron, 25\'te Cehennem Kapısı.'},
 {id:'frost',n:'Buzul Vadisi',ac:'#9cd6ff',bg:'linear-gradient(160deg,#1d4a6e,#0e2238)',
  e:['Buz Böceği','Ayaz Yarasası','Kar Ruhu','Buz Golemi','Kar Kurdu','Yeti','Kartopu','Şifa Ruhu','Kristal Yarasa'],
  b:['Buz Şövalyesi','Ayaz Kraliçesi','Buzul Devi','Kar Orakçısı','Buz Kovanı'],t:'Yaratıklar %10 yavaş ama %10 dayanıklı. Başarımlar yeni silah açar.'},
 {id:'jungle',n:'Zümrüt Orman',ac:'#9be37a',bg:'linear-gradient(160deg,#1d5a3a,#0e2a18)',
  e:['Yılan','Ateşböceği','Zehir Kurbağası','Ağaç Adam','Panter','Goril','Gümüş Sırt','Patlak Mantar','Şaman Kurbağa','Eşek Arısı'],
  b:['Orman Reisi','Sarmaşık Cadısı','Kadim Ent','Gölge Panteri','Yılan Ana'],t:'+%12 tecrübe ama yaratıklar %12 daha sık doğar.'},
 {id:'desert',n:'Kızıl Çöl',ac:'#f2c46a',bg:'linear-gradient(160deg,#7a4a1e,#3a200c)',
  e:['Akrep','Sarı Akrep','Akbaba','Kum Okçusu','Mumya','Çakal','Çöl Haydudu','Firavun Muhafızı','Patlak Kaktüs','Kum Büyücüsü'],
  b:['Firavun','Serap Cadısı','Sfenks','Mumya Orakçısı','Akrep Ana'],t:'+%15 altın ama yaratıklar %8 hızlı. Cehennem yok: 25. dalgadan sonra ölüm duvarı gelir.'},
 {id:'hell',n:'Cehennem',ac:'#ff8a4a',bg:'linear-gradient(160deg,#6a1d1d,#2a0808)',
  e:['Lav yaratıkları','Zırh delen alevler'],b:['Lav Kolosu','+ Cehennem\'e özel 6 patron'],t:'25. dalga patronunu yen, mor portalda E\'ye bas. Cehennem Marketi açılır; zırhını delen yaratıklara dikkat!'}
];
function renderMaps(k){
  const mg=$('#mapGrid'),md=$('#mapDetail');if(!mg)return;
  mg.innerHTML=MAPS.map(m=>'<button class="map'+(m.id===k?' sel':'')+'" data-k="'+m.id+'"><div class="art" style="background:radial-gradient(120px 60px at 50% 40%,'+m.ac+'44,transparent),'+m.bg+'"></div><h4>'+esc(m.n)+'</h4><p>'+esc(m.t.split('.')[0])+'.</p></button>').join('');
  mg.querySelectorAll('.map').forEach(b=>b.onclick=()=>renderMaps(b.dataset.k));
  const m=MAPS.find(x=>x.id===k);
  md.innerHTML='<div><h3 style="color:'+m.ac+'">'+esc(m.n)+' · Yaratıklar</h3><ul>'+m.e.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>'+
    '<div><h3 style="color:'+m.ac+'">Patronlar</h3><ul>'+m.b.map(x=>'<li class="boss">👑 '+esc(x)+'</li>').join('')+'</ul></div><p class="note">📍 '+esc(m.t)+'</p>';
}
const OATHS=[
 ['Cam Top','+%25 hasar','-%25 maks can'],['Altın Humması','+%25 altın','Yaratıklar +%10 dayanıklı'],
 ['Kaplumbağa','+60 can, +4 zırh','-%7 hareket hızı'],['Alim','+%20 tecrübe','-%12 hasar'],
 ['Kumarbaz','+%30 şans','-%15 maks can'],['Kan Yemini','Can çalma +%4','Can yenilenmesi yok'],
 ['Rüzgâr','+%8 hız, dash +%10','Yaratıklar +%10 hızlı'],['Sur','+1 kalkan, 25 sn\'de dolar','-%10 saldırı hızı'],
 ['Avcı','+%20 patron/elit hasarı','-%10 altın'],['Şölen','+%10 tecrübe ve altın','+%15 yaratık sayısı'],
 ['Hazine','+150 altınla başla','-%10 tecrübe'],['Şahin Gözü','+%10 kritik, +%20 kritik hasar','-%10 saldırı hızı']
];
function renderOaths(){const el=$('#oathGrid');if(el)el.innerHTML=OATHS.map(o=>'<div class="oath"><h4>'+esc(o[0])+'</h4><div class="up">▲ '+esc(o[1])+'</div><div class="down">▼ '+esc(o[2])+'</div></div>').join('');}

/* ---------- indirme kilidi + sayaç ---------- */
function initDownload(){
  const sup=$('#destekle'),dl=$('#indirBtn'),note=$('#indirNot'),cnt=$('#indirmeSayaci');
  if(cnt)fetch('default.php?t='+Date.now()).then(r=>r.ok?r.text():'').then(t=>{const n=parseInt(t,10);if(n>=0)cnt.textContent=num(n);}).catch(()=>{});
  if(sup)sup.addEventListener('click',()=>setTimeout(()=>{sup.style.display='none';dl.style.display='inline-flex';note.textContent='Teşekkürler! Artık oyunu indirebilirsin.';},300));
  if(dl)dl.addEventListener('click',()=>{fetch('default.php?action=hit').then(r=>r.ok?r.text():'').then(t=>{const n=parseInt(t,10);if(n>=0&&cnt)cnt.textContent=num(n);}).catch(()=>{});});
}

/* ---------- mini demo ---------- */
function demo(cid,hpId,wvId,lvId,klId,notId){
  const cv=document.getElementById(cid);if(!cv)return;
  const x=cv.getContext('2d'),W=cv.width,H=cv.height;
  let P={x:W/2,y:H/2,hp:100,r:12,cd:0},E=[],Bu=[],kills=0,lvl=1,wave=1,mx=W/2,my=H/2,last=0;
  function pt(e){const r=cv.getBoundingClientRect(),p=e.touches?e.touches[0]:e;mx=(p.clientX-r.left)*W/r.width;my=(p.clientY-r.top)*H/r.height;}
  cv.addEventListener('mousemove',pt);cv.addEventListener('touchmove',e=>{pt(e);e.preventDefault();},{passive:false});cv.addEventListener('touchstart',pt,{passive:true});
  function spawn(){const a=Math.random()*6.283,d=Math.max(W,H)*.62;E.push({x:W/2+Math.cos(a)*d,y:H/2+Math.sin(a)*d,hp:1+Math.floor(wave/3),s:36+Math.random()*26+wave*3,r:9+Math.random()*5,hue:[0,205,45,280,15,320][Math.floor(Math.random()*6)]});}
  const set=(id,v)=>{const el=document.getElementById(id);if(el)el.textContent=v;};
  function loop(ts){
    const dt=Math.min((ts-last)/1000||0,.05);last=ts;
    const dx=mx-P.x,dy=my-P.y,dd=Math.hypot(dx,dy);if(dd>5){P.x+=dx/dd*155*dt;P.y+=dy/dd*155*dt;}
    if(Math.random()<dt*(1.1+wave*.3)&&E.length<42)spawn();
    P.cd-=dt;
    if(P.cd<=0&&E.length){let n=null,nd=1e9;E.forEach(e=>{const d=Math.hypot(e.x-P.x,e.y-P.y);if(d<nd){nd=d;n=e;}});
      if(nd<330){const a=Math.atan2(n.y-P.y,n.x-P.x);Bu.push({x:P.x,y:P.y,vx:Math.cos(a)*425,vy:Math.sin(a)*425,l:.9});P.cd=Math.max(.42-lvl*.02,.16);}}
    Bu.forEach(b=>{b.x+=b.vx*dt;b.y+=b.vy*dt;b.l-=dt;});Bu=Bu.filter(b=>b.l>0);
    E.forEach(e=>{const a=Math.atan2(P.y-e.y,P.x-e.x);e.x+=Math.cos(a)*e.s*dt;e.y+=Math.sin(a)*e.s*dt;
      if(Math.hypot(P.x-e.x,P.y-e.y)<P.r+e.r){P.hp-=28*dt;e.x-=Math.cos(a)*8;e.y-=Math.sin(a)*8;}
      Bu.forEach(b=>{if(b.l>0&&Math.hypot(b.x-e.x,b.y-e.y)<e.r+4){e.hp--;b.l=0;}});});
    E=E.filter(e=>{if(e.hp<=0){kills++;return false;}return true;});
    lvl=1+Math.floor(kills/8);wave=1+Math.floor(kills/22);
    if(P.hp<=0){E=[];Bu=[];kills=0;lvl=1;wave=1;P.hp=100;set(notId,'Öldün, arena seni geri çağırdı!');}
    P.hp=Math.min(100,P.hp+dt*2.5);
    x.clearRect(0,0,W,H);x.strokeStyle='#6ec8ff';x.globalAlpha=.07;
    for(let i=0;i<W;i+=38){x.beginPath();x.moveTo(i,0);x.lineTo(i,H);x.stroke();}
    for(let i=0;i<H;i+=38){x.beginPath();x.moveTo(0,i);x.lineTo(W,i);x.stroke();}
    x.globalAlpha=1;
    E.forEach(e=>{x.fillStyle='hsl('+e.hue+',72%,56%)';x.beginPath();x.arc(e.x,e.y,e.r,0,7);x.fill();x.fillStyle='#0e0c2c';x.beginPath();x.arc(e.x-3,e.y-2,2,0,7);x.arc(e.x+3,e.y-2,2,0,7);x.fill();});
    x.fillStyle='#fff';Bu.forEach(b=>{x.beginPath();x.arc(b.x,b.y,3.2,0,7);x.fill();});
    x.fillStyle='#6ec8ff';x.beginPath();x.arc(P.x,P.y,P.r,0,7);x.fill();x.strokeStyle='#e9e6ff';x.lineWidth=2;x.stroke();
    x.fillStyle='#fff';x.beginPath();x.arc(P.x+4,P.y-3,3,0,7);x.arc(P.x-2,P.y-3,3,0,7);x.fill();
    set(hpId,Math.round(P.hp));set(wvId,wave);set(lvId,lvl);set(klId,kills);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
}

/* =================== HESAP (site geçişi) =================== */
const ST={pass:null,state:null};
function sset(k,v){try{v==null?sessionStorage.removeItem(k):sessionStorage.setItem(k,v);}catch(e){}}
function sget(k){try{return sessionStorage.getItem(k);}catch(e){return null;}}
async function api(path,body){
  let r;
  try{r=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{}),credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',mode:'cors'});}
  catch(e){return {success:false,error:'sunucuya ulaşılamadı (sunucu uyanıyor olabilir, 30 sn sonra tekrar dene)'};}
  let j={};try{j=await r.json();}catch(e){}
  if(!j||typeof j!=='object')j={};
  if(r.status===401&&j.relogin)logout(true);
  if(!r.ok&&j.success===undefined)j.success=false;
  return j;
}
function setState(s){if(s&&typeof s==='object'){ST.state=s;renderAcct();renderWheelUi();if(PAGE==='kazi')renderTiers();if(PAGE==='oyunlar'){gameNeedLogin();if(!G.room&&G.tab!=='roul'&&G.tab!=='gw'&&!G.busy)renderGames();}}}
function setPass(p,s){ST.pass=p;sset('ea_pass',p);setState(s);}
function logout(expired){ST.pass=null;ST.state=null;sset('ea_pass',null);sset('ea_wt',null);renderAcct();renderWheelUi();if(PAGE==='kazi')renderTiers();
  if(expired)wNote('Oturumun süresi doldu: yeniden giriş yap ya da oyundan aç.',true);}
function renderAcct(){
  const a=$('#acct');if(!a)return;a.textContent='';
  if(ST.state){
    const w=document.createElement('span');w.className='who';w.textContent=ST.state.name;
    const g=document.createElement('span');g.className='gems';g.textContent='💎 '+num(ST.state.gems);
    const b=document.createElement('button');b.textContent='Çıkış';b.onclick=()=>logout(false);
    a.append(w,g,b);
  }else{const b=document.createElement('button');b.textContent='Giriş yap';b.onclick=()=>openModal('#mLogin');a.append(b);}
  const fc=$('#fabCnt');
  if(fc){const l=ST.state?ST.state.wheel.left:null;fc.hidden=!(l>0);fc.textContent=l||'';$('#fab').classList.toggle('hot',!!(ST.state&&ST.state.wheel.left>0));}
}
const lf=$('#loginForm');
if(lf)lf.addEventListener('submit',async e=>{
  e.preventDefault();const btn=$('#lgBtn');btn.disabled=true;$('#lgErr').textContent='';
  const j=await api('/site/login',{username:$('#lgUser').value.trim(),password:$('#lgPass').value});
  btn.disabled=false;$('#lgPass').value='';
  if(j.success){setPass(j.pass,j.state);closeAll();}else $('#lgErr').textContent=j.error||'giriş yapılamadı';
});

/* =================== ŞANS ÇARKI (panel) =================== */
const W={angle:0,spin:null,ticket:sget('ea_wt'),readyAt:0,timer:null,imgs:{},open:false,raf:0};
function openDrawer(){const d=$('#drawer');if(!d)return;d.classList.add('on');d.setAttribute('aria-hidden','false');W.open=true;if(!W.raf)W.raf=requestAnimationFrame(wheelLoop);}
function closeDrawer(){const d=$('#drawer');if(!d)return;d.classList.remove('on');d.setAttribute('aria-hidden','true');W.open=false;}
$('#fab')&&($('#fab').onclick=openDrawer);
document.addEventListener('click',e=>{if(e.target.closest('[data-open-wheel]')){e.preventDefault();openDrawer();}if(e.target.closest('[data-close-drawer]'))closeDrawer();});
function wNote(t,err){const n=$('#wNote');if(!n)return;n.textContent=t||'';n.classList.toggle('err',!!err);}
function wheelImgs(){
  if(!GD)return;const wd=GD.wheel;
  wd.order.forEach(pz=>{let src='';if(pz==='crown_god')src=wd.crown;else{const s=GD.skins.find(x=>x.id===pz);if(s)src=s.img;}
    if(src){const im=new Image();im.src=img(src);W.imgs[pz]=im;}});
}
function drawGem(x,r){x.beginPath();x.moveTo(0,-r);x.lineTo(r*.85,-r*.25);x.lineTo(0,r);x.lineTo(-r*.85,-r*.25);x.closePath();
  x.fillStyle='#7fe3ff';x.fill();x.lineWidth=2;x.strokeStyle='#103040';x.stroke();x.beginPath();x.moveTo(-r*.85,-r*.25);x.lineTo(r*.85,-r*.25);x.stroke();}
function drawWheel(){
  const cv=$('#wheelCv');if(!cv||!GD)return;const x=cv.getContext('2d'),S=cv.width,cx=S/2,cy=S/2+6,R=S/2-34;
  const wd=GD.wheel,n=wd.order.length,seg=Math.PI*2/n,rot=W.angle*Math.PI/180,tt=performance.now()/1000;
  x.clearRect(0,0,S,S);
  x.beginPath();x.arc(cx,cy,R+22,0,7);x.fillStyle='#2a1a0c';x.fill();
  const gr=x.createLinearGradient(0,cy-R,0,cy+R);gr.addColorStop(0,'#ffd86b');gr.addColorStop(1,'#a8701e');x.beginPath();x.arc(cx,cy,R+16,0,7);x.fillStyle=gr;x.fill();
  for(let i=0;i<24;i++){const a=i/24*Math.PI*2,on=(Math.floor(tt*4)+i)%2===0;x.beginPath();x.arc(cx+Math.cos(a)*(R+9),cy+Math.sin(a)*(R+9),4.2,0,7);x.fillStyle=on?'#fff6c8':'#8a5a1a';x.fill();}
  for(let i=0;i<n;i++){
    const pz=wd.order[i],a0=-Math.PI/2+rot+i*seg,a1=a0+seg;
    x.beginPath();x.moveTo(cx,cy);x.arc(cx,cy,R,a0,a1);x.closePath();x.fillStyle=wd.colors[pz]||'#555';x.fill();x.strokeStyle='#1a0f08';x.lineWidth=3;x.stroke();
    const g2=x.createRadialGradient(cx,cy,R*.2,cx,cy,R);g2.addColorStop(0,'rgba(255,255,255,0)');g2.addColorStop(1,'rgba(255,255,255,.13)');
    x.beginPath();x.moveTo(cx,cy);x.arc(cx,cy,R*.97,a0,a1);x.closePath();x.fillStyle=g2;x.fill();
    x.save();x.translate(cx,cy);x.rotate(a0+seg/2);
    const im=W.imgs[pz];x.save();x.translate(R*.7,0);x.rotate(Math.PI/2);
    if(im&&im.complete&&im.naturalWidth){const s=pz==='crown_god'?44:60;x.drawImage(im,-s/2,-s/2,s,s*im.naturalHeight/im.naturalWidth);}else drawGem(x,13);
    x.restore();x.rotate(Math.PI/2);x.fillStyle='#fff';x.strokeStyle='#1a0f08';x.lineWidth=4;x.font=(R*.085|0)+'px "Russo One",sans-serif';x.textAlign='center';
    x.strokeText(wd.short[pz],0,-R*.43);x.fillText(wd.short[pz],0,-R*.43);x.restore();
  }
  const g3=x.createRadialGradient(cx-8,cy-8,4,cx,cy,R*.16);g3.addColorStop(0,'#fff3b0');g3.addColorStop(1,'#c58a24');
  x.beginPath();x.arc(cx,cy,R*.16,0,7);x.fillStyle=g3;x.fill();x.lineWidth=4;x.strokeStyle='#2a1a0c';x.stroke();
  x.fillStyle='#2a1a0c';x.font=(R*.07|0)+'px "Russo One",sans-serif';x.textAlign='center';x.textBaseline='middle';x.fillText('ÇEVİR',cx,cy+1);x.textBaseline='alphabetic';
  x.beginPath();x.moveTo(cx-20,cy-R-30);x.lineTo(cx+20,cy-R-30);x.lineTo(cx,cy-R+18);x.closePath();x.fillStyle='#ff5a5a';x.fill();x.lineWidth=4;x.strokeStyle='#2a0c0c';x.stroke();
}
function wheelLoop(ts){
  if(W.spin){const k=Math.min(1,(ts-W.spin.t0)/W.spin.dur),e=1-Math.pow(1-k,3.6);W.angle=W.spin.a0+(W.spin.a1-W.spin.a0)*e;if(k>=1){const cb=W.spin.done;W.spin=null;cb&&cb();}}
  else W.angle+=0.06;
  drawWheel();
  W.raf=(W.open||W.spin)?requestAnimationFrame(wheelLoop):0;
}
function spinTo(pz,done){
  const wd=GD.wheel,seg=360/wd.order.length,i=wd.order.indexOf(pz);
  const center=(i+0.5+(Math.random()*0.6-0.3))*seg,cur=W.angle,delta=((-center-cur)%360+360)%360;
  W.spin={a0:cur,a1:cur+delta+360*7,t0:performance.now(),dur:5600,done};if(!W.raf)W.raf=requestAnimationFrame(wheelLoop);
}
function renderOdds(){
  const el=$('#wOdds');if(!el||!GD)return;const wd=GD.wheel;
  el.innerHTML=wd.order.slice().sort((a,b)=>wd.odds[b]-wd.odds[a]).map(pz=>{
    let ic='<span style="width:24px;text-align:center">💎</span>';
    if(pz==='crown_god')ic='<img alt="" src="'+img(wd.crown)+'">';else{const s=GD.skins.find(x=>x.id===pz);if(s)ic='<img alt="" src="'+img(s.img)+'">';}
    return '<div style="--c:'+esc(wd.colors[pz])+'">'+ic+esc(wd.names[pz])+'<em>'+pct(wd.odds[pz])+'</em></div>';}).join('');
}
function setBtn(text,mode){
  const b=$('#wBtn');if(!b)return;b.textContent=text;b.classList.toggle('off',mode==='off');b.classList.toggle('hot',mode==='hot');
  b.href='#';b.dataset.mode=mode;
}
/* ---------- AppLixir ödüllü video ----------
   API anahtarı assets/config.js içinde (window.EA_CFG.applixirKey). Reklam
   önceden yüklenir (preload); ÇEVİR'e basınca hemen açılır. Video bitince
   (status.type === "complete") çark açılır. Reklam yüklenemezse (reklam
   engelleyici vb.) aynı süre beklenir: çark yine çalışır. Asıl güvenlik
   sunucuda: çevirme ancak sunucunun başlattığı sürenin sonunda kabul edilir. */
const ADX={handle:null,last:0,busy:false,cb:null,to:0};
function axKey(){return (window.EA_CFG&&window.EA_CFG.applixirKey)||'';}
function axFire(ok){const f=ADX.cb;ADX.cb=null;if(ADX.to){clearTimeout(ADX.to);ADX.to=0;}if(f)f(ok);}
function axOptions(){
  // geri çağırmalar gösterim anındaki ADX.cb'ye gider (önceden yüklenen reklam da doğru yere haber verir)
  return {apiKey:axKey(),injectionElementId:'applixir-ad',
    adStatusCallbackFn:st=>{const t=st&&st.type;
      if(t==='complete'||t==='allAdsCompleted')axFire(true);
      else if(t==='skipped'||t==='manuallyEnded'||t==='thankYouModalClosed')axFire(false);},
    adErrorCallbackFn:()=>axFire(false)};
}
async function axPreload(){
  if(!axKey()||typeof preloadAd!=='function'||ADX.busy||ADX.handle)return;
  try{ADX.handle=await preloadAd(axOptions());ADX.last=Date.now();}catch(e){ADX.handle=null;}
}
function axShow(onDone){
  // onDone(true): video sonuna kadar izlendi; onDone(false): video yok / yarıda kaldı
  const box=$('#applixir-ad');if(box)box.classList.add('on');
  ADX.busy=true;
  ADX.cb=ok=>{if(box)box.classList.remove('on');ADX.busy=false;onDone(ok);setTimeout(axPreload,1500);};
  ADX.to=setTimeout(()=>axFire(false),120000);
  if(!axKey()||(typeof preloadAd!=='function'&&typeof initializeAndOpenPlayer!=='function')){axFire(false);return;}
  try{
    if(ADX.handle&&Date.now()-ADX.last<10*60*1000){const h=ADX.handle;ADX.handle=null;h.show();}
    else{ADX.handle=null;initializeAndOpenPlayer(axOptions());}
  }catch(e){axFire(false);}
}
function renderWheelUi(){
  if(!$('#wBtn'))return;const s=ST.state;
  ['#wS1','#wS2','#wS3','#wS4'].forEach(q=>$(q).classList.remove('done'));
  if(W.timer){clearInterval(W.timer);W.timer=null;}
  if(!s){$('#wWho').textContent='Giriş yapılmadı';$('#wDots').innerHTML='';setBtn('GİRİŞ YAP','login');return;}
  const w=s.wheel;$('#wS1').classList.add('done');
  $('#wWho').textContent=s.name+' · 💎 '+num(s.gems);
  $('#wDots').innerHTML=Array.from({length:w.daily},(_,i)=>'<i class="'+(i<w.left?'on':'')+'"></i>').join('');
  if(W.spin){setBtn('DÖNÜYOR...','off');return;}
  if(w.left<=0){setBtn('YARIN YENİLENİR','off');return;}
  if(w.pending&&W.ticket){
    $('#wS2').classList.add('done');W.readyAt=Date.now()+Math.max(0,(w.rest||0))*1000;
    const tick=()=>{const r=Math.ceil((W.readyAt-Date.now())/1000);
      if(r>0)setBtn('⏳ '+r+' sn bekle','off');else{$('#wS3').classList.add('done');setBtn('ÇEVİR!','hot');clearInterval(W.timer);W.timer=null;}};
    tick();W.timer=setInterval(tick,250);return;
  }
  setBtn('ÇEVİR','go');
}
const wb=$('#wBtn');
if(wb)wb.addEventListener('click',async e=>{
  const mode=e.currentTarget.dataset.mode;
  if(mode==='login'){e.preventDefault();openModal('#mLogin');return;}
  if(mode==='off'){e.preventDefault();return;}
  if(mode==='go'){
    e.preventDefault();
    // önce sunucu bekleme sayacını başlatır, sonra ödüllü video oynar
    const j=await api('/site/wheel/ad',{pass:ST.pass});
    if(!j.success){wNote(j.error||'başlatılamadı',true);return;}
    W.ticket=j.ticket;sset('ea_wt',j.ticket);ST.state.wheel.pending=true;ST.state.wheel.rest=j.wait;
    renderWheelUi();setBtn('🎬 VİDEO OYNUYOR…','off');wNote('Videoyu sonuna kadar izle, çark açılsın.');
    axShow(ok=>{wNote(ok?'Teşekkürler! Çark hazır, ÇEVİR!':'Video yüklenemedi: süre dolunca çark açılır.');renderWheelUi();});
    return;
  }
  if(mode==='hot'){
    e.preventDefault();setBtn('DÖNÜYOR...','off');
    const j=await api('/site/wheel/spin',{pass:ST.pass,ticket:W.ticket});
    if(!j.success){wNote(j.error||'çevrilemedi',true);if(j.rest)ST.state.wheel.rest=j.rest;renderWheelUi();return;}
    W.ticket=null;sset('ea_wt',null);wNote('');spinTo(j.prize,()=>{setState(j.state);showPrize(j);});
  }
});
function showPrize(j){
  const wd=GD.wheel,pz=j.prize;let im='',sub='';
  if(pz==='crown_god')im=wd.crown;else{const s=GD.skins.find(x=>x.id===pz);if(s)im=s.img;}
  if(j.dupe)sub='Zaten sendeydi: yerine +'+num(j.gems)+' elmas hesabına eklendi!';
  else if(j.gems)sub='+'+num(j.gems)+' elmas hesabına eklendi. Oyuna dönünce görürsün.';
  else if(pz==='crown_god')sub='GOD Tacı artık senin! Oyunda Kostümler › Şapka.';
  else sub='Yeni karakter! Oyunda karakter seçiminden kuşan.';
  info('<div class="prize"><span class="eyebrow" style="justify-content:center">Kazandın</span>'+(im?'<img alt="" src="'+img(im)+'">':'<div style="font-size:64px">💎</div>')+'<b>'+esc(wd.names[pz]||pz)+'</b><p>'+esc(sub)+'</p></div>');
  confetti();
}
function confetti(){
  const c=document.createElement('canvas');c.style.cssText='position:fixed;inset:0;pointer-events:none;z-index:200';c.width=innerWidth;c.height=innerHeight;document.body.appendChild(c);
  const x=c.getContext('2d'),P=[];for(let i=0;i<160;i++){const a=Math.random()*6.28,s=4+Math.random()*9;P.push({x:c.width/2,y:c.height/2,vx:Math.cos(a)*s,vy:Math.sin(a)*s-6,c:['#ffd86b','#6ec8ff','#ff78c8','#78d28c','#af78eb'][i%5],l:1});}
  let f=0;(function an(){x.clearRect(0,0,c.width,c.height);P.forEach(p=>{p.x+=p.vx;p.y+=p.vy;p.vy+=.25;p.l-=.008;x.globalAlpha=Math.max(0,p.l);x.fillStyle=p.c;x.fillRect(p.x,p.y,7,5);});if(++f<150)requestAnimationFrame(an);else c.remove();})();
}

/* =================== KAZI KAZAN =================== */
const TIER={'5k':['#3a2a7a','#1d1850','#b795ff'],'10k':['#164454','#14243f','#5cd6e4'],'50k':['#5a3a10','#2a1a08','#f3c55e'],'100k':['#5a1030','#2a0818','#ff6fa8']};
const FALLBACK={'5k':5000,'10k':10000,'50k':50000,'100k':100000};
const SC={tier:null,armed:null,armT:0,done:false,res:null};
function renderTiers(){
  const box=$('#tiers');if(!box)return;const st=ST.state&&ST.state.scratch,tiers=st?st.tiers:null;
  box.innerHTML=['5k','10k','50k','100k'].map(k=>{
    const t=tiers&&tiers[k],cost=t?t.cost:FALLBACK[k],c=TIER[k];
    const top=t?t.table.filter(r=>r[0]>0).map(r=>r[0]).sort((a,b)=>b-a).slice(0,3):[];
    const tbl=t?'<details><summary>Ödüller ve oranlar</summary><table>'+t.table.slice().sort((a,b)=>b[0]-a[0]).map(r=>'<tr><td>'+(r[0]?'💎 '+num(r[0]):'Boş')+'</td><td>'+pct(r[1])+'</td></tr>').join('')+'</table></details>':'';
    const armed=SC.armed===k&&Date.now()<SC.armT,can=ST.state&&ST.state.gems>=cost&&st&&st.left>0;
    const lab=!ST.state?'Giriş yap':(armed?'Onayla · 💎 '+num(cost):(can?'Satın al ve kazı':(st&&st.left<=0?'Bugünlük bitti':'Elmas yetmiyor')));
    return '<div class="stier" style="--t1:'+c[0]+';--t2:'+c[1]+';--tc:'+c[2]+'"><h3>'+num(cost)+'\'lik</h3><div class="cost">Kart: 💎 '+num(cost)+'</div>'+
      '<div class="top3">'+(top.length?'En büyük ödüller: '+top.map(num).join(' · '):(k==='100k'?'5.000.000 elmasa kadar!':'1.000.000 elmasa kadar!'))+'</div>'+
      '<button class="btn block'+(ST.state&&!can&&!armed?' off':'')+'" data-tier="'+k+'">'+lab+'</button>'+tbl+'</div>';
  }).join('');
}
function initScratch(){
  const box=$('#tiers');if(!box)return;
  box.addEventListener('click',e=>{
    const b=e.target.closest('button[data-tier]');if(!b)return;const k=b.dataset.tier;
    if(!ST.state){openModal('#mLogin');return;}
    const st=ST.state.scratch,t=st.tiers[k];if(!t||ST.state.gems<t.cost||st.left<=0)return;
    if(!(SC.armed===k&&Date.now()<SC.armT)){SC.armed=k;SC.armT=Date.now()+4000;renderTiers();setTimeout(renderTiers,4100);return;}
    SC.armed=null;buyCard(k);
  });
  const cv=$('#scv'),x=cv.getContext('2d');let down=false,last=null,n=0;
  const pos=e=>{const r=cv.getBoundingClientRect(),p=e.touches?e.touches[0]:e;return [(p.clientX-r.left)*cv.width/r.width,(p.clientY-r.top)*cv.height/r.height];};
  function scr(e){if(!down||SC.done||!SC.res)return;e.preventDefault();const p=pos(e);x.globalCompositeOperation='destination-out';x.lineCap='round';x.lineWidth=46;
    x.beginPath();x.moveTo(...(last||p));x.lineTo(...p);x.stroke();last=p;if(++n%12===0)check();}
  function check(){const d=x.getImageData(0,0,cv.width,cv.height).data;let c=0,t=0;for(let i=3;i<d.length;i+=64){t++;if(d[i]<40)c++;}if(c/t>.62)reveal();}
  cv.addEventListener('pointerdown',e=>{down=true;last=pos(e);cv.setPointerCapture&&cv.setPointerCapture(e.pointerId);scr(e);});
  cv.addEventListener('pointermove',scr);
  ['pointerup','pointercancel','pointerleave'].forEach(t=>cv.addEventListener(t,()=>{down=false;last=null;}));
  cv.addEventListener('contextmenu',e=>e.preventDefault());
  $('#sAll').onclick=reveal;
  $('#sAgain').onclick=()=>{if(!SC.tier)return;if(!SC.done)reveal();SC.armed=SC.tier;SC.armT=Date.now()+4000;renderTiers();box.scrollIntoView({behavior:'smooth',block:'center'});};
}
async function buyCard(k){
  $$('#tiers button').forEach(b=>b.disabled=true);
  const j=await api('/site/scratch/buy',{pass:ST.pass,tier:k});
  $$('#tiers button').forEach(b=>b.disabled=false);
  if(!j.success){renderTiers();info('<h3 style="margin-bottom:8px">Olmadı</h3><p>'+esc(j.error||'satın alınamadı')+'</p>');return;}
  SC.tier=k;SC.res=j;SC.done=false;
  // bedel hemen düşer; ödül kazınınca görünür (sonuç zaten hesabında)
  ST.state.gems=Math.max(0,ST.state.gems-j.cost);ST.state.scratch=j.state.scratch;renderAcct();renderTiers();
  const sc=$('#scratch');sc.classList.add('on');
  $('#sTitle').textContent=num(j.cost)+'\'lik kart · aynı miktardan 3 tane = kazandın';
  $('#g9').innerHTML=j.cells.map(v=>'<div class="cell" data-v="'+(+v)+'">'+num(v)+'<small>ELMAS</small></div>').join('');
  $('#sRes').textContent='Parmağınla ya da farenle kazı!';$('#sRes').className='sres';
  const cv=$('#scv'),x=cv.getContext('2d');x.globalCompositeOperation='source-over';
  const g=x.createLinearGradient(0,0,cv.width,cv.height);g.addColorStop(0,'#c9ccd6');g.addColorStop(.5,'#eef0f6');g.addColorStop(1,'#a9adba');
  x.fillStyle=g;x.fillRect(0,0,cv.width,cv.height);x.fillStyle='rgba(80,84,100,.35)';for(let i=0;i<260;i++)x.fillRect(Math.random()*cv.width,Math.random()*cv.height,2,2);
  x.fillStyle='#5a5f72';x.font='30px "Russo One",sans-serif';x.textAlign='center';x.fillText('KAZI KAZAN',cv.width/2,cv.height/2-6);
  x.font='700 15px Onest,sans-serif';x.fillText('EvolveArena',cv.width/2,cv.height/2+20);
  sc.scrollIntoView({behavior:'smooth',block:'center'});
}
function reveal(){
  if(!SC.res||SC.done)return;SC.done=true;const cv=$('#scv');cv.getContext('2d').clearRect(0,0,cv.width,cv.height);
  const p=SC.res.prize;
  if(p>0){$$('#g9 .cell').forEach(c=>{if(+c.dataset.v===p)c.classList.add('hit');});$('#sRes').textContent='Kazandın: 💎 '+num(p);$('#sRes').className='sres win';if(p>=SC.res.cost)confetti();}
  else{$('#sRes').textContent='Bu sefer olmadı. Bir sonraki senin!';$('#sRes').className='sres';}
  setState(SC.res.state);
}

/* =================== OYUN SALONU =================== */
// Bütün kartlar ve sonuçlar sunucuda. Burada yalnızca sunucunun bu oyuncuya
// gösterdiği görüntü çizilir; hamleler sunucuya gider ve orada doğrulanır.
const DEF_STAKES=[1000,5000,10000,25000,50000,100000,150000,200000,300000,500000,1000000];
const G={tab:'coin',stake:10000,side:'yazi',cap:4,room:null,seq:-1,poll:0,lpoll:0,busy:false,last:null};
const SUIT={S:'♠',H:'♥',D:'♦',C:'♣'};
const RANKN={J:'J',Q:'Q',K:'K',A:'A'};
function stakes(){return (ST.state&&ST.state.stakes)||DEF_STAKES;}
function kfmt(v){return v>=1000000?(v/1000000)+'M':(v>=1000?(v/1000)+'K':String(v));}
function pcard(c,cls,attr){
  if(!c||c==='??')return '<div class="pc back'+(cls?' '+cls:'')+'"'+(attr||'')+'><i></i></div>';
  const r=c.slice(0,-1),s=c.slice(-1),red=(s==='H'||s==='D'),face=RANKN[r]&&r!=='A';
  return '<div class="pc'+(red?' red':'')+(cls?' '+cls:'')+'"'+(attr||'')+'><span class="tl">'+esc(r)+'<em>'+SUIT[s]+'</em></span>'+
    '<span class="mid'+(face?' face':'')+'">'+(face?esc(r):SUIT[s])+'</span><span class="br">'+esc(r)+'<em>'+SUIT[s]+'</em></span></div>';
}
function gameNeedLogin(){const n=$('#gameNeedLogin');if(n)n.style.display=ST.state?'none':'block';}
function initGames(){
  tabs('#gameTabs',t=>{G.tab=t;G.room=null;renderGames();});
  renderGames();
  setInterval(()=>{if(document.hidden)return;if(G.room)pollRoom();else if(G.tab!=='roul'&&G.tab!=='gw')pollLobby();},1100);
}
function renderGames(){
  gameNeedLogin();
  const solo=G.tab==='roul'||G.tab==='gw';
  $('#roul').style.display=G.tab==='roul'?'block':'none';
  $('#gw').style.display=G.tab==='gw'?'block':'none';
  if(solo){$('#lobby').innerHTML='';$('#table').innerHTML='';if(G.tab==='roul')renderRoulette();else renderGemWheel();return;}
  if(ST.state&&ST.state.room&&!G.room){G.room={id:ST.state.room.id,kind:ST.state.room.kind};G.seq=-1;}
  if(G.room){$('#lobby').innerHTML='';if(G.room.kind!==G.tab){G.tab=G.room.kind;$$('#gameTabs button').forEach(b=>b.setAttribute('aria-selected',b.dataset.c===G.tab?'true':'false'));}pollRoom(true);return;}
  $('#table').innerHTML='';renderLobby(G.lastRooms||[]);pollLobby(true);
}
const RULES={coin:['Yazı mı tura mı?','Masayı açan tarafını seçer, oturan öbür tarafı alır. Para havaya atılır, kazanan potu alır.'],
  bj:['21\'e en yakın kazanır','İki oyuncu aynı anda oynar: kart çek ya da dur. 21\'i geçen batar. İkisi de batarsa ya da eşitse elmas geri döner.'],
  pisti:['Klasik pişti','Aynı kartla ya da vale ile masayı topla. Pişti 10, vale piştisi 20 puan; as ve vale 1, sinek 2\'li 2, karo 10\'lu 3, en çok kart 3 puan.']};
function renderLobby(rooms){
  const k=G.tab,box=$('#lobby'),st=stakes();
  if(!st.includes(G.stake))G.stake=st[2]||st[0];
  const stakeBtns=st.map(v=>'<button class="chipb'+(v>=150000?' hi':'')+'" data-stake="'+v+'" aria-pressed="'+(v===G.stake)+'"><b>'+kfmt(v)+'</b></button>').join('');
  const extra=k==='coin'?'<div class="lbl2">Senin tarafın</div><div class="opts seg"><button data-side="yazi" aria-pressed="'+(G.side==='yazi')+'">YAZI</button><button data-side="tura" aria-pressed="'+(G.side==='tura')+'">TURA</button></div>'
    :(k==='pisti'?'<div class="lbl2">Oyuncu sayısı</div><div class="opts seg"><button data-cap="2" aria-pressed="'+(G.cap===2)+'">2 kişi</button><button data-cap="4" aria-pressed="'+(G.cap===4)+'">4 kişi</button></div>':'');
  const players=k==='pisti'?G.cap:2,net=Math.round(G.stake*players*0.95);
  box.innerHTML='<div class="lob"><div class="box mk"><div class="mkh"><span class="gico g-'+k+'"></span><div><h3>'+esc(RULES[k][0])+'</h3><p>'+esc(RULES[k][1])+'</p></div></div>'+
    '<div class="lbl2">Bahis</div><div class="chips">'+stakeBtns+'</div>'+extra+
    '<div class="potline"><span>Kazanırsan</span><b>💎 '+num(net)+'</b></div>'+
    '<button class="btn block big" id="gCreate">'+(ST.state?'Masa aç · 💎 '+num(G.stake):'Giriş yap')+'</button>'+
    '<p class="secnote">Kazanan potun %95\'ini alır, berabere kalınırsa herkesin elması geri döner.</p></div>'+
    '<div><div class="lhead"><h3>Açık masalar</h3><span class="live"><i></i>canlı</span></div><div id="roomList">'+roomsHtml(rooms)+'</div></div></div>';
  box.querySelectorAll('[data-stake]').forEach(b=>b.onclick=()=>{G.stake=+b.dataset.stake;renderLobby(G.lastRooms||[]);});
  box.querySelectorAll('[data-side]').forEach(b=>b.onclick=()=>{G.side=b.dataset.side;renderLobby(G.lastRooms||[]);});
  box.querySelectorAll('[data-cap]').forEach(b=>b.onclick=()=>{G.cap=+b.dataset.cap;renderLobby(G.lastRooms||[]);});
  $('#gCreate').onclick=()=>createRoom();
  bindJoin();
}
function avatars(names,cap){let h='';for(let i=0;i<cap;i++){const n=names[i];h+='<span class="av'+(n?'':' emp')+'" title="'+esc(n||'boş koltuk')+'">'+(n?esc(n.slice(0,1).toUpperCase()):'+')+'</span>';}return h;}
function roomsHtml(rooms){
  const L=rooms.filter(r=>r.kind===G.tab);
  if(!L.length)return '<div class="empty">Şu an açık masa yok.<br><b>İlk masayı sen aç, rakibin gelsin!</b></div>';
  return '<div class="rooms">'+L.map(r=>'<div class="room"><div class="rtop"><span class="st">💎 '+num(r.stake)+'</span><span class="cnt">'+r.players.length+'/'+r.cap+'</span></div>'+
    '<div class="avs">'+avatars(r.players,r.cap)+'</div>'+
    '<div class="pl">'+esc(r.players.join(', '))+(r.side?' · masa '+(r.side==='yazi'?'YAZI':'TURA')+' seçti':'')+'</div>'+
    '<button class="btn sm" data-join="'+esc(r.id)+'">Otur · 💎 '+num(r.stake)+'</button></div>').join('')+'</div>';
}
function bindJoin(){const el=$('#roomList');if(el)el.querySelectorAll('[data-join]').forEach(b=>b.onclick=()=>joinRoom(b.dataset.join));}
async function pollLobby(force){
  if(!ST.pass){gameNeedLogin();return;}
  if(G.busy&&!force)return;
  const j=await api('/site/games/list',{pass:ST.pass,kind:G.tab});
  if(!j.success)return;
  if(j.mine&&!G.room){G.room={id:j.mine,kind:j.mine_kind};G.seq=-1;renderGames();return;}
  G.lastRooms=j.rooms||[];
  const el=$('#roomList');if(el){el.innerHTML=roomsHtml(G.lastRooms);bindJoin();}
}
async function createRoom(o){
  if(!ST.state){openModal('#mLogin');return;}
  o=o||{kind:G.tab,stake:G.stake,side:G.side,cap:G.cap};
  G.busy=true;const j=await api('/site/games/create',Object.assign({pass:ST.pass},o));G.busy=false;
  if(!j.success){info('<h3 style="margin-bottom:8px">Olmadı</h3><p>'+esc(j.error||'masa açılamadı')+'</p>');return;}
  G.last=o;setState(j.state);G.room={id:j.room.id,kind:j.room.kind};G.seq=-1;$('#lobby').innerHTML='';renderTable(j.room);
}
async function joinRoom(id){
  if(!ST.state){openModal('#mLogin');return;}
  G.busy=true;const j=await api('/site/games/join',{pass:ST.pass,room:id});G.busy=false;
  if(!j.success){info('<h3 style="margin-bottom:8px">Olmadı</h3><p>'+esc(j.error||'oturulamadı')+'</p>');pollLobby(true);return;}
  setState(j.state);G.room={id:j.room.id,kind:j.room.kind};G.seq=-1;$('#lobby').innerHTML='';renderTable(j.room);
}
async function pollRoom(force){
  if(!G.room||!ST.pass||(G.busy&&!force))return;
  const j=await api('/site/games/state',{pass:ST.pass,room:G.room.id,seq:G.seq});
  if(!j.success){if(j.gone){G.room=null;G.seq=-1;const me=await api('/site/me',{pass:ST.pass});if(me.success)setState(me.state);renderGames();}return;}
  if(j.same)return;
  renderTable(j.room);
}
async function act(action,extra){
  if(G.busy)return;G.busy=true;
  const j=await api('/site/games/act',Object.assign({pass:ST.pass,room:G.room.id,action},extra||{}));G.busy=false;
  if(!j.success){info('<h3 style="margin-bottom:8px">Olmadı</h3><p>'+esc(j.error||'hamle yapılamadı')+'</p>');return;}
  if(j.state)setState(j.state);
  if(action==='leave'&&(!j.room||j.room.state!=='play')){G.room=null;G.seq=-1;renderGames();return;}
  if(j.room)renderTable(j.room);
}
function resultHtml(r,room){
  if(!r)return '';
  const me=room.players[room.me];let head,cls;
  if(r.refund){head='Berabere';cls='draw';}
  else if(r.winners.includes(me)){head='KAZANDIN!';cls='win';}
  else{head='Kaybettin';cls='lose';}
  const sub=r.refund?'Elmasın geri döndü.':(r.winners.includes(me)?'+💎 '+num(r.payout)+' hesabına eklendi':'Kazanan: '+r.winners.join(', '));
  return '<div class="resbox '+cls+'"><b>'+esc(head)+'</b><div class="rsub">'+esc(sub)+'</div><span class="muted">'+esc(r.why||'')+(r.rake?' · site kesintisi 💎 '+num(r.rake):'')+'</span>'+
    '<div class="acts"><button class="btn big" id="gReplay">↻ Tekrar oyna · 💎 '+num(room.stake)+'</button><button class="btn ghost" id="gAgain">Lobiye dön</button></div></div>';
}
function seatHead(name,mine,extra){return '<div class="nm"><span class="who"><span class="av sm">'+esc((name||'?').slice(0,1).toUpperCase())+'</span>'+esc(name)+(mine?' <em>(sen)</em>':'')+'</span><span>'+extra+'</span></div>';}
function renderTable(room){
  G.seq=room.seq;const box=$('#table');if(!box)return;
  if(room.state==='done'&&G.doneFor!==room.id){G.doneFor=room.id;api('/site/me',{pass:ST.pass}).then(j=>{if(j.success){ST.state=j.state;renderAcct();renderWheelUi();}});}
  const pot=room.stake*(room.state==='wait'?room.cap:room.players.length);
  let h='<div class="felt k-'+room.kind+'"><div class="hdr"><b>'+({coin:'Yazı Tura',bj:'Blackjack',pisti:'Pişti'}[room.kind])+'</b><span class="pot">POT 💎 '+num(pot)+'</span></div>';
  if(room.state==='wait'){
    h+='<div class="waiting">'+(room.kind==='coin'?'<div class="coin3d spin"><span>?</span></div>':'<div class="dots3"><i></i><i></i><i></i></div>')+
      '<p class="big">Rakip bekleniyor</p><div class="avs lg">'+avatars(room.players,room.cap)+'</div><p class="muted">Masa açık: biri oturunca oyun kendiliğinden başlar.</p></div>'+
      '<div class="acts"><button class="btn sm ghost" id="gLeave">Masadan kalk (elmas iade)</button></div>';
  }else if(room.kind==='coin'){
    const f=room.flip,fresh=G.coinFor!==room.id;G.coinFor=room.id;
    h+='<div class="waiting"><div class="coin3d '+(fresh?'land ':'')+(f==='yazi'?'yazi':'tura')+'"><span>'+(f==='yazi'?'YAZI':'TURA')+'</span></div>'+
      '<div class="vs"><div><b>'+esc(room.players[0])+'</b><span>'+(room.side==='yazi'?'YAZI':'TURA')+'</span></div><i>VS</i><div><b>'+esc(room.players[1]||'')+'</b><span>'+(room.side==='yazi'?'TURA':'YAZI')+'</span></div></div></div>';
  }else if(room.kind==='bj'){
    const order=room.hands.map((_,i)=>i).sort((a,b)=>(a===room.me)-(b===room.me));
    order.forEach(i=>{
      const hd=room.hands[i],mine=i===room.me,bust=hd.value>21;
      const val=hd.value!=null?'<span class="hv'+(bust?' bust':(hd.value===21?' bj':''))+'">'+hd.value+(bust?' · BATTI':'')+'</span>':'<span class="muted">'+(hd.done?'durdu':'düşünüyor…')+'</span>';
      h+='<div class="seat'+(mine?' me':' opp')+'">'+seatHead(room.players[i],mine,val)+'<div class="cards fan">'+hd.cards.map((c,j)=>pcard(c,'lg','style="--i:'+j+'"')).join('')+'</div></div>';
    });
    if(room.state==='play'&&room.me!=null&&!room.hands[room.me].done)
      h+='<div class="acts"><button class="btn big" id="bjHit">KART ÇEK</button><button class="btn big violet" id="bjStand">DUR</button><span class="timer">⏱ '+(room.time_left||0)+' sn</span></div>';
    else if(room.state==='play')h+='<p class="waitmsg">Rakibin oynuyor…</p>';
  }else if(room.kind==='pisti'){
    const n=room.players.length,opp=[];for(let k=1;k<n;k++)opp.push(((room.me||0)+k)%n);
    h+='<div class="ptable"><div class="opps n'+opp.length+'">';
    opp.forEach(i=>{const turn=room.state==='play'&&room.turn===i;
      h+='<div class="oseat'+(turn?' turn':'')+'"><div class="ohead"><span class="av sm">'+esc((room.players[i]||'?').slice(0,1).toUpperCase())+'</span><b>'+esc(room.players[i])+'</b>'+(turn?'<span class="timer">⏱ '+(room.time_left||0)+'</span>':'')+'</div>'+
        '<div class="cards back-fan">'+Array.from({length:room.counts[i]},(_,j)=>pcard('??','sm','style="--i:'+j+'"')).join('')+'</div>'+
        '<div class="ost">'+room.taken_n[i]+' kart · pişti '+room.pisti[i]+(room.scores?' · <b>'+room.scores[i]+' puan</b>':'')+'</div></div>';});
    h+='</div><div class="pmid"><div class="deck">'+(room.deck_n?pcard('??','lg'):'')+'<span>'+room.deck_n+'</span></div>'+
      '<div class="pile">'+(room.table_n>2?pcard('??','lg','style="transform:rotate(-14deg) translate(-10px,4px)"'):'')+(room.table_n>1?pcard('??','lg','style="transform:rotate(9deg) translate(8px,2px)"'):'')+
      (room.table_top?pcard(room.table_top,'lg top'):'<div class="pc lg ghostc"></div>')+'</div><div class="pinfo">Masada <b>'+room.table_n+'</b> kart</div></div>';
    if(room.last)h+='<p class="lastmv">'+esc(room.last.by)+' <b>'+esc(room.last.card.replace(/(.+)([SHDC])$/,(m,r,s)=>r+SUIT[s]))+'</b> attı'+(room.last.pisti?' · <span class="pis">PİŞTİ! +'+room.last.pisti+'</span>':(room.last.took?' ve masayı topladı':''))+'</p>';
    const meI=room.me,turnMe=room.state==='play'&&room.turn===meI;
    if(meI!=null){
      h+='<div class="seat me'+(turnMe?' turn':'')+'">'+seatHead(room.players[meI],true,(turnMe?'<span class="timer">SIRA SENDE ⏱ '+(room.time_left||0)+'</span> · ':'')+room.taken_n[meI]+' kart · pişti '+room.pisti[meI]+(room.scores?' · <b class="gold">'+room.scores[meI]+' puan</b>':''))+
        '<div class="cards hand">'+room.hand.map((c,j)=>pcard(c,'xl'+(turnMe?' play':''),' data-card="'+esc(c)+'" style="--i:'+j+'"')).join('')+'</div></div>';
    }
    h+='</div>';
  }
  if(room.state==='done')h+=resultHtml(room.result,room);
  else if(room.state==='play')h+='<div class="acts"><button class="btn sm ghost" id="gLeave">Masadan kalk (kaybedersin)</button></div>';
  h+='</div>';
  box.innerHTML=h;
  const on=(id,f)=>{const el=document.getElementById(id);if(el)el.onclick=f;};
  on('gLeave',()=>{if(room.state==='play'&&!confirm('Oyun sürerken kalkarsan elin kendiliğinden oynanır ve büyük ihtimalle kaybedersin. Emin misin?'))return;act('leave');});
  on('bjHit',()=>act('hit'));on('bjStand',()=>act('stand'));
  on('gAgain',async()=>{G.room=null;G.seq=-1;const me=await api('/site/me',{pass:ST.pass});if(me.success)setState(me.state);renderGames();});
  on('gReplay',async()=>{const o={kind:room.kind,stake:room.stake,cap:room.cap,side:room.side||G.side};G.room=null;G.seq=-1;await createRoom(o);if(!G.room)renderGames();});
  box.querySelectorAll('.pc.play[data-card]').forEach(c=>c.onclick=()=>act('play',{card:c.dataset.card}));
  if(room.state==='done'&&room.result&&!room.result.refund&&room.result.winners.includes(room.players[room.me])&&G.cfFor!==room.id){G.cfFor=room.id;confetti();}
}

/* ---------- rulet ---------- */
const RW=[0,32,15,19,4,21,2,25,17,34,6,27,13,36,11,30,8,23,10,5,24,16,33,1,20,14,31,9,22,18,29,7,28,12,35,3,26];
const RRED=new Set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]);
const R={bets:{},chip:1000,angle:0,ball:0,spinning:false,hist:[]};
function rkey(t,v){return t+(v!=null?':'+v:'');}
function rTotal(){return Object.values(R.bets).reduce((a,b)=>a+b,0);}
function rMax(){return (ST.state&&ST.state.roul_max)||1000000;}
function renderRoulette(){
  const box=$('#roul');
  if(!box.dataset.built){
    box.dataset.built='1';
    let board='<div class="board"><button class="c g z" data-t="num" data-v="0">0</button>';
    for(let row=0;row<3;row++)for(let col=0;col<12;col++){const n=col*3+(3-row);board+='<button class="c '+(RRED.has(n)?'r':'k')+'" data-t="num" data-v="'+n+'">'+n+'</button>';}
    board+='</div><div class="outs d">'+[1,2,3].map(d=>'<button class="c o" data-t="dozen" data-v="'+d+'">'+(d*12-11)+' – '+d*12+'<small>2:1</small></button>').join('')+'</div>'+
      '<div class="outs">'+[['low','1 – 18'],['even','ÇİFT'],['red','KIRMIZI'],['black','SİYAH'],['odd','TEK'],['high','19 – 36']].map(x=>'<button class="c '+(x[0]==='red'?'r big':(x[0]==='black'?'k big':'o'))+'" data-t="'+x[0]+'">'+x[1]+'<small>1:1</small></button>').join('')+'</div>'+
      '<div class="outs d">'+[1,2,3].map(c=>'<button class="c o" data-t="col" data-v="'+c+'">'+c+'. SÜTUN<small>2:1</small></button>').join('')+'</div>';
    const chips=[100,500,1000,5000,10000,50000,100000];
    box.innerHTML='<div class="rlay"><div class="rleft"><div class="rwheel"><canvas id="rCv" width="460" height="460"></canvas></div><div class="rres" id="rRes">Bahsini koy, ÇEVİR\'e bas.</div><div class="hist" id="rHist"></div></div>'+
      '<div><div class="lbl2">Fiş seç</div><div class="pchips" id="rChips">'+chips.map(v=>'<button class="pchip v'+v+'" data-chip="'+v+'" aria-pressed="'+(v===R.chip)+'"><span>'+kfmt(v)+'</span></button>').join('')+'</div>'+
      '<div class="lbl2">Tahta <span class="muted" style="text-transform:none;letter-spacing:0">(sol tık: fiş koy · sağ tık: kaldır)</span></div>'+board+
      '<div class="rctl"><div class="tot">Toplam bahis<b id="rTot">0</b><small>en çok 💎 '+num(rMax())+'</small></div><button class="btn ghost" id="rClear">Temizle</button><button class="btn big" id="rSpin">ÇEVİR</button></div>'+
      '<p class="secnote">Sayı 35:1 · düzine ve sütun 2:1 · kırmızı/siyah, tek/çift, 1-18/19-36 1:1. Tek sıfırlı Avrupa ruleti; 0 gelirse dış bahisler kaybeder. Sonucu sunucu seçer.</p></div></div>';
    box.querySelectorAll('[data-chip]').forEach(b=>b.onclick=()=>{R.chip=+b.dataset.chip;box.querySelectorAll('[data-chip]').forEach(x=>x.setAttribute('aria-pressed',x===b));});
    box.querySelectorAll('.board .c,.outs .c').forEach(c=>{
      c.onclick=()=>{if(R.spinning)return;const k=rkey(c.dataset.t,c.dataset.v);if(rTotal()+R.chip>rMax()){$('#rRes').textContent='Tek çevirmede en çok 💎 '+num(rMax());return;}R.bets[k]=(R.bets[k]||0)+R.chip;drawBets();};
      c.oncontextmenu=e=>{e.preventDefault();const k=rkey(c.dataset.t,c.dataset.v);delete R.bets[k];drawBets();};
    });
    $('#rClear').onclick=()=>{if(!R.spinning){R.bets={};drawBets();}};
    $('#rSpin').onclick=spinRoulette;
    drawRWheel();
  }
  drawBets();
}
function drawBets(){
  $$('#roul .c').forEach(c=>{const k=rkey(c.dataset.t,c.dataset.v),v=R.bets[k];let ch=c.querySelector('.chip');
    if(v){if(!ch){ch=document.createElement('span');ch.className='chip';c.appendChild(ch);}ch.textContent=kfmt(v);}else if(ch)ch.remove();});
  const t=$('#rTot');if(t)t.textContent='💎 '+num(rTotal());
}
function drawRWheel(){
  const cv=$('#rCv');if(!cv)return;const x=cv.getContext('2d'),S=cv.width,c=S/2,R2=S/2-12,n=RW.length,seg=Math.PI*2/n,rot=R.angle;
  x.clearRect(0,0,S,S);
  const wood=x.createRadialGradient(c,c,R2*.7,c,c,R2+8);wood.addColorStop(0,'#7a4a20');wood.addColorStop(1,'#3a200c');
  x.beginPath();x.arc(c,c,R2+8,0,7);x.fillStyle=wood;x.fill();
  x.beginPath();x.arc(c,c,R2-2,0,7);x.fillStyle='#d9b45a';x.fill();
  for(let i=0;i<n;i++){const v=RW[i],a0=-Math.PI/2+rot+i*seg-seg/2;
    x.beginPath();x.moveTo(c,c);x.arc(c,c,R2-6,a0,a0+seg);x.closePath();x.fillStyle=v===0?'#1f8a4e':(RRED.has(v)?'#c0202f':'#16161f');x.fill();
    x.strokeStyle='#d9b45a';x.lineWidth=1.2;x.stroke();
    x.save();x.translate(c,c);x.rotate(a0+seg/2);x.translate(R2-24,0);x.rotate(Math.PI/2);x.fillStyle='#fff';x.font='15px "Russo One",sans-serif';x.textAlign='center';x.fillText(v,0,5);x.restore();}
  x.beginPath();x.arc(c,c,R2-44,0,7);x.strokeStyle='rgba(217,180,90,.8)';x.lineWidth=2;x.stroke();
  const inner=x.createRadialGradient(c-20,c-20,10,c,c,R2*.55);inner.addColorStop(0,'#6a4220');inner.addColorStop(1,'#2a160a');
  x.beginPath();x.arc(c,c,R2*.55,0,7);x.fillStyle=inner;x.fill();x.strokeStyle='#d9b45a';x.lineWidth=4;x.stroke();
  for(let k=0;k<4;k++){const a=rot+k*Math.PI/2;x.beginPath();x.moveTo(c,c);x.lineTo(c+Math.cos(a)*R2*.42,c+Math.sin(a)*R2*.42);x.strokeStyle='#e8c46a';x.lineWidth=6;x.lineCap='round';x.stroke();}
  x.beginPath();x.arc(c,c,R2*.1,0,7);x.fillStyle='#f3d27a';x.fill();
  // ibre
  x.beginPath();x.moveTo(c-12,2);x.lineTo(c+12,2);x.lineTo(c,26);x.closePath();x.fillStyle='#fff';x.fill();x.strokeStyle='#222';x.lineWidth=2;x.stroke();
  // top: dönerken dış halkada, sonunda kazanan cebin içinde
  const br=R.spinning?R2-14+Math.max(0,R.ballR||0):R2-36,ba=-Math.PI/2+R.ball;
  x.beginPath();x.arc(c+Math.cos(ba)*br,c+Math.sin(ba)*br,8,0,7);const bg=x.createRadialGradient(c+Math.cos(ba)*br-3,c+Math.sin(ba)*br-3,1,c+Math.cos(ba)*br,c+Math.sin(ba)*br,8);
  bg.addColorStop(0,'#fff');bg.addColorStop(1,'#b8b8c4');x.fillStyle=bg;x.fill();
}
async function spinRoulette(){
  if(R.spinning)return;
  if(!ST.state){openModal('#mLogin');return;}
  const bets=Object.entries(R.bets).map(([k,a])=>{const [t,v]=k.split(':');return {type:t,value:v!=null?+v:undefined,amount:a};});
  if(!bets.length){$('#rRes').textContent='Önce bahis koy: tahtaya tıkla.';return;}
  R.spinning=true;$('#rRes').textContent='Dönüyor…';$('#rSpin').classList.add('off');
  const j=await api('/site/roulette/spin',{pass:ST.pass,bets});
  if(!j.success){R.spinning=false;$('#rSpin').classList.remove('off');$('#rRes').textContent=j.error||'çevrilemedi';return;}
  const i=RW.indexOf(j.number),seg=Math.PI*2/RW.length,a0=R.angle,target=-i*seg;
  let delta=((target-a0)%(Math.PI*2)+Math.PI*2)%(Math.PI*2);const a1=a0+delta+Math.PI*2*5,t0=performance.now(),dur=5200,b0=R.ball;
  (function an(ts){const k=Math.min(1,(ts-t0)/dur),e=1-Math.pow(1-k,3.4);R.angle=a0+(a1-a0)*e;
    R.ball=b0-(1-e)*Math.PI*2*3;R.ballR=-22*Math.max(0,(k-.7)/.3);if(k>=1)R.ball=0;drawRWheel();
    if(k<1)requestAnimationFrame(an);else{
      R.spinning=false;R.ball=0;drawRWheel();$('#rSpin').classList.remove('off');setState(j.state);
      const col={red:'KIRMIZI',black:'SİYAH',green:'YEŞİL'}[j.color];
      $('#rRes').innerHTML='<span class="rn '+j.color+'">'+j.number+'</span> '+col+' · '+(j.win?'<span class="gold">+💎 '+num(j.win)+'</span>':'<span class="muted">kazanç yok</span>');
      R.hist.unshift(j);R.hist=R.hist.slice(0,12);$('#rHist').innerHTML=R.hist.map(h=>'<span class="rn '+h.color+'">'+h.number+'</span>').join('');
      if(j.win>=j.bet*3&&j.win>0)confetti();
    }})(t0);
}

/* ---------- elmas çarkı (kasaya karşı) ---------- */
const GW={bet:10000,angle:0,spinning:false,hist:[]};
const GW_COL={0:'#2a2638',0.5:'#3c4a6a',1.2:'#1f7a86',1.5:'#2f8a4a',2:'#6a3fb0',3:'#c46a1c',5:'#c23a7a',10:'#e2a922'};
function gwCfg(){return (ST.state&&ST.state.gw)||{bets:[1000,5000,10000,50000,100000,250000],segs:[0,0.5,1.2,0,2,0.5,1.5,0,3,0.5,1.2,0,5,0.5,1.5,10],odds:[]};}
function renderGemWheel(){
  const box=$('#gw'),cfg=gwCfg();
  if(!cfg.bets.includes(GW.bet))GW.bet=cfg.bets[2]||cfg.bets[0];
  box.innerHTML='<div class="gwlay"><div class="gwwheel"><canvas id="gwCv" width="520" height="520"></canvas></div><div class="gwside">'+
    '<h3>Elmas Çarkı</h3><p>Bahsini seç, çarkı çevir. Dilimdeki çarpan kadar elmas kazanırsın: <b>x10</b>\'a kadar! Sonucu sunucu seçer, kazanç anında hesabına yazılır.</p>'+
    '<div class="lbl2">Bahis</div><div class="chips">'+cfg.bets.map(v=>'<button class="chipb'+(v>=100000?' hi':'')+'" data-gb="'+v+'" aria-pressed="'+(v===GW.bet)+'"><b>'+kfmt(v)+'</b></button>').join('')+'</div>'+
    '<button class="btn block big" id="gwSpin">'+(ST.state?'ÇEVİR · 💎 '+num(GW.bet):'Giriş yap')+'</button>'+
    '<div class="rres" id="gwRes"></div><div class="hist" id="gwHist">'+GW.hist.map(gwHistChip).join('')+'</div>'+
    (cfg.odds.length?'<details class="odds2"><summary>Oranlar</summary><table>'+cfg.odds.slice().reverse().map(o=>'<tr><td><span class="sw" style="background:'+(GW_COL[o[0]]||'#555')+'"></span>x'+String(o[0]).replace('.',',')+'</td><td>'+pct(o[1])+'</td></tr>').join('')+'</table></details>':'')+
    '</div></div>';
  box.querySelectorAll('[data-gb]').forEach(b=>b.onclick=()=>{if(GW.spinning)return;GW.bet=+b.dataset.gb;renderGemWheel();});
  $('#gwSpin').onclick=spinGemWheel;
  drawGemWheel();
  if(!GW.raf)GW.raf=requestAnimationFrame(gwLoop);
}
function gwHistChip(h){return '<span class="gwh" style="background:'+(GW_COL[h.mult]||'#555')+'">x'+String(h.mult).replace('.',',')+'</span>';}
function drawGemWheel(){
  const cv=$('#gwCv');if(!cv)return;const x=cv.getContext('2d'),S=cv.width,c=S/2,R2=S/2-30,segs=gwCfg().segs,n=segs.length,seg=Math.PI*2/n,rot=GW.angle,tt=performance.now()/1000;
  x.clearRect(0,0,S,S);
  const rim=x.createLinearGradient(0,c-R2,0,c+R2);rim.addColorStop(0,'#9fe8ff');rim.addColorStop(1,'#2a6c9a');
  x.beginPath();x.arc(c,c,R2+18,0,7);x.fillStyle='#0d1830';x.fill();x.beginPath();x.arc(c,c,R2+12,0,7);x.fillStyle=rim;x.fill();
  for(let i=0;i<28;i++){const a=i/28*Math.PI*2,on=(Math.floor(tt*5)+i)%2===0;x.beginPath();x.arc(c+Math.cos(a)*(R2+6),c+Math.sin(a)*(R2+6),3.6,0,7);x.fillStyle=on?'#eaffff':'#21506e';x.fill();}
  for(let i=0;i<n;i++){const m=segs[i],a0=-Math.PI/2+rot+i*seg-seg/2;
    x.beginPath();x.moveTo(c,c);x.arc(c,c,R2,a0,a0+seg);x.closePath();x.fillStyle=GW_COL[m]||'#444';x.fill();x.strokeStyle='#0d1830';x.lineWidth=3;x.stroke();
    x.save();x.translate(c,c);x.rotate(a0+seg/2);x.translate(R2*.68,0);x.rotate(Math.PI/2);x.textAlign='center';
    x.font=(m>=5?'26px':'21px')+' "Russo One",sans-serif';x.lineWidth=5;x.strokeStyle='rgba(0,0,0,.55)';const t='x'+String(m).replace('.',',');x.strokeText(t,0,8);x.fillStyle=m>=5?'#fff6c8':'#fff';x.fillText(t,0,8);x.restore();}
  const hub=x.createRadialGradient(c-10,c-10,4,c,c,R2*.2);hub.addColorStop(0,'#eaffff');hub.addColorStop(1,'#2a8ac0');
  x.beginPath();x.arc(c,c,R2*.2,0,7);x.fillStyle=hub;x.fill();x.lineWidth=5;x.strokeStyle='#0d1830';x.stroke();
  x.fillStyle='#0d1830';x.font='22px "Russo One",sans-serif';x.textAlign='center';x.textBaseline='middle';x.fillText('💎',c,c+1);x.textBaseline='alphabetic';
  x.beginPath();x.moveTo(c-18,c-R2-26);x.lineTo(c+18,c-R2-26);x.lineTo(c,c-R2+16);x.closePath();x.fillStyle='#ffd86b';x.fill();x.lineWidth=4;x.strokeStyle='#3a2a08';x.stroke();
}
function gwLoop(){
  const box=$('#gw');
  if(!document.getElementById('gwCv')||!box||box.style.display==='none'){GW.raf=0;return;}
  if(!GW.spinning)drawGemWheel();
  GW.raf=requestAnimationFrame(gwLoop);
}
async function spinGemWheel(){
  if(GW.spinning)return;
  if(!ST.state){openModal('#mLogin');return;}
  if(ST.state.gems<GW.bet){$('#gwRes').textContent='Yeterli elmasın yok.';return;}
  GW.spinning=true;$('#gwSpin').classList.add('off');$('#gwRes').textContent='Dönüyor…';
  const j=await api('/site/gemwheel/spin',{pass:ST.pass,bet:GW.bet});
  if(!j.success){GW.spinning=false;$('#gwSpin').classList.remove('off');$('#gwRes').textContent=j.error||'çevrilemedi';return;}
  const n=gwCfg().segs.length,seg=Math.PI*2/n,a0=GW.angle,target=-j.seg*seg+(Math.random()*.6-.3)*seg;
  const delta=((target-a0)%(Math.PI*2)+Math.PI*2)%(Math.PI*2),a1=a0+delta+Math.PI*2*6,t0=performance.now(),dur=5000;
  (function an(ts){const k=Math.min(1,(ts-t0)/dur),e=1-Math.pow(1-k,3.6);GW.angle=a0+(a1-a0)*e;drawGemWheel();
    if(k<1)requestAnimationFrame(an);else{
      GW.spinning=false;$('#gwSpin').classList.remove('off');setState(j.state);
      const m=String(j.mult).replace('.',',');
      $('#gwRes').innerHTML=j.win>0?'<span class="gold">x'+m+' · +💎 '+num(j.win)+'</span>':'<span class="muted">x0 · bu sefer olmadı</span>';
      GW.hist.unshift(j);GW.hist=GW.hist.slice(0,10);const hh=$('#gwHist');if(hh)hh.innerHTML=GW.hist.map(gwHistChip).join('');
      if(j.mult>=3)confetti();
    }})(t0);
}

/* =================== AÇILIŞ =================== */
// İnceleme araçlarına küçük bir caydırıcı. Asıl koruma sunucuda: sonuçlar orada belirlenir, sayfada gizli sonuç / kod yoktur.
document.addEventListener('contextmenu',e=>{if(e.target.closest('#drawer,#scratch,#tiers,#table,#roul,#gw'))e.preventDefault();});
document.addEventListener('keydown',e=>{const k=(e.key||'').toUpperCase();if(k==='F12'||(e.ctrlKey&&e.shiftKey&&['I','J','C'].includes(k))||(e.ctrlKey&&k==='U'))e.preventDefault();});

(async function boot(){
  if(GD&&pages[PAGE])pages[PAGE]();
  // sunucuyu erkenden uyandır (ilk istek beklemesin) + ödüllü videoyu önceden yükle
  try{fetch(API+'/health',{mode:'no-cors',cache:'no-store',credentials:'omit'}).catch(()=>{});}catch(e){}
  setTimeout(axPreload,2500);
  renderAcct();renderOdds();wheelImgs();renderWheelUi();
  const h=location.hash||'',m=h.match(/[#&]k=([A-Za-z0-9_-]{8,64})/);
  if(m){
    history.replaceState(null,'',location.pathname+location.search);   // kod adres çubuğunda kalmasın
    openDrawer();
    const j=await api('/site/exchange',{code:m[1]});
    if(j.success){setPass(j.pass,j.state);wNote('Hoş geldin '+j.state.name+'! Çark hazır.');}else wNote(j.error||'bağlantı geçersiz',true);
    return;
  }
  if(/^#cark/.test(h))openDrawer();
  const p=sget('ea_pass');
  if(p){ST.pass=p;const j=await api('/site/me',{pass:p});if(j.success)setState(j.state);}
})();
})();
