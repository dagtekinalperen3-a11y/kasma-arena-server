/* EvolveArena sitesi — ortak kod. Veri: window.GD (assets/data.js, tools/build_site.py üretir). */
(function(){
'use strict';
const GD=window.GD||null;
const API=(/onrender\.com$/.test(location.hostname)||location.hostname==='localhost'||location.hostname==='127.0.0.1')?'':'https://kasma-arena-server-wir3.onrender.com';
const AD_URL='https://ardance.org/4/8eb87fad3ff308b09ec866979c2bcfe7';
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const PAGE=document.body.dataset.page||'';
function esc(t){return String(t==null?'':t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function num(n){return Number(n||0).toLocaleString('tr-TR');}
function img(u){return /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(u||'')?u:'';}
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
function setState(s){if(s&&typeof s==='object'){ST.state=s;renderAcct();renderWheelUi();if(PAGE==='kazi')renderTiers();if(PAGE==='oyunlar'){gameNeedLogin();if(!G.room&&G.tab!=='roul'&&!G.busy)renderGames();}}}
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
function setBtn(text,mode,href){
  const b=$('#wBtn');if(!b)return;b.textContent=text;b.classList.toggle('off',mode==='off');b.classList.toggle('hot',mode==='hot');
  if(href){b.href=href;b.target='_blank';b.rel='noopener noreferrer sponsored';}else{b.href='#';b.removeAttribute('target');b.removeAttribute('rel');}
  b.dataset.mode=mode;
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
  setBtn('ÇEVİR','go',s.ad_url||AD_URL);
}
const wb=$('#wBtn');
if(wb)wb.addEventListener('click',async e=>{
  const mode=e.currentTarget.dataset.mode;
  if(mode==='login'){e.preventDefault();openModal('#mLogin');return;}
  if(mode==='off'){e.preventDefault();return;}
  if(mode==='go'){
    // sponsor bağlantısı yeni sekmede açılır (tarayıcı engellemez); bekleme sayacı sunucuda başlar
    const j=await api('/site/wheel/ad',{pass:ST.pass});
    if(!j.success){wNote(j.error||'başlatılamadı',true);return;}
    W.ticket=j.ticket;sset('ea_wt',j.ticket);ST.state.wheel.pending=true;ST.state.wheel.rest=j.wait;
    wNote('Sponsor sayfası açıldı. '+Math.round(j.wait)+' saniye sonra ÇEVİR aktif olur.');renderWheelUi();return;
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
const TIER={'5k':['#3a2a7a','#1d1850','#b795ff'],'10k':['#164454','#14243f','#5cd6e4'],'50k':['#5a3a10','#2a1a08','#f3c55e']};
const FALLBACK={'5k':5000,'10k':10000,'50k':50000};
const SC={tier:null,armed:null,armT:0,done:false,res:null};
function renderTiers(){
  const box=$('#tiers');if(!box)return;const st=ST.state&&ST.state.scratch,tiers=st?st.tiers:null;
  box.innerHTML=['5k','10k','50k'].map(k=>{
    const t=tiers&&tiers[k],cost=t?t.cost:FALLBACK[k],c=TIER[k];
    const top=t?t.table.filter(r=>r[0]>0).map(r=>r[0]).sort((a,b)=>b-a).slice(0,3):[];
    const tbl=t?'<details><summary>Ödüller ve oranlar</summary><table>'+t.table.slice().sort((a,b)=>b[0]-a[0]).map(r=>'<tr><td>'+(r[0]?'💎 '+num(r[0]):'Boş')+'</td><td>'+pct(r[1])+'</td></tr>').join('')+'</table></details>':'';
    const armed=SC.armed===k&&Date.now()<SC.armT,can=ST.state&&ST.state.gems>=cost&&st&&st.left>0;
    const lab=!ST.state?'Giriş yap':(armed?'Onayla · 💎 '+num(cost):(can?'Satın al ve kazı':(st&&st.left<=0?'Bugünlük bitti':'Elmas yetmiyor')));
    return '<div class="stier" style="--t1:'+c[0]+';--t2:'+c[1]+';--tc:'+c[2]+'"><h3>'+num(cost)+'\'lik</h3><div class="cost">Kart: 💎 '+num(cost)+'</div>'+
      '<div class="top3">'+(top.length?'En büyük ödüller: '+top.map(num).join(' · '):'1.000.000 elmasa kadar!')+'</div>'+
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
const G={tab:'coin',stake:10000,side:'yazi',cap:4,room:null,seq:-1,poll:0,lpoll:0,busy:false,stakes:[1000,5000,10000,25000,50000,100000]};
const SUIT={S:'♠',H:'♥',D:'♦',C:'♣'};
function pcard(c,cls,attr){
  if(!c||c==='??')return '<div class="pc back'+(cls?' '+cls:'')+'"><span></span></div>';
  const r=c.slice(0,-1),s=c.slice(-1),red=(s==='H'||s==='D');
  return '<div class="pc'+(red?' red':'')+(cls?' '+cls:'')+'"'+(attr||'')+'><span>'+esc(r)+'</span><span class="s">'+SUIT[s]+'</span><span class="b">'+esc(r)+'</span></div>';
}
function gameNeedLogin(){const n=$('#gameNeedLogin');if(n)n.style.display=ST.state?'none':'block';}
function initGames(){
  tabs('#gameTabs',t=>{G.tab=t;G.room=null;renderGames();});
  renderGames();
  setInterval(()=>{if(document.hidden)return;if(G.room)pollRoom();else if(G.tab!=='roul')pollLobby();},1100);
}
function renderGames(){
  gameNeedLogin();
  const roulOn=G.tab==='roul';
  $('#roul').style.display=roulOn?'block':'none';
  if(roulOn){$('#lobby').innerHTML='';$('#table').innerHTML='';renderRoulette();return;}
  if(ST.state&&ST.state.room&&!G.room){G.room={id:ST.state.room.id,kind:ST.state.room.kind};G.seq=-1;}
  if(G.room){$('#lobby').innerHTML='';if(G.room.kind!==G.tab){G.tab=G.room.kind;$$('#gameTabs button').forEach(b=>b.setAttribute('aria-selected',b.dataset.c===G.tab?'true':'false'));}pollRoom(true);return;}
  $('#table').innerHTML='';renderLobby([]);pollLobby(true);
}
function renderLobby(rooms){
  const k=G.tab,box=$('#lobby');
  const stakeBtns=G.stakes.map(v=>'<button data-stake="'+v+'" aria-pressed="'+(v===G.stake)+'">💎 '+num(v)+'</button>').join('');
  const extra=k==='coin'?'<div class="lbl2">Senin tarafın</div><div class="opts"><button data-side="yazi" aria-pressed="'+(G.side==='yazi')+'">Yazı</button><button data-side="tura" aria-pressed="'+(G.side==='tura')+'">Tura</button></div>'
    :(k==='pisti'?'<div class="lbl2">Oyuncu sayısı</div><div class="opts"><button data-cap="2" aria-pressed="'+(G.cap===2)+'">2 kişi</button><button data-cap="4" aria-pressed="'+(G.cap===4)+'">4 kişi</button></div>':'');
  const rules={coin:'Masayı açan tarafını seçer, oturan öbür tarafı alır. Para atılır, kazanan potu alır.',
    bj:'İki oyuncu da aynı anda oynar: kart çek ya da dur. 21\'i geçmeden en yüksek el kazanır; ikisi de batarsa ya da eşitse elmas geri döner.',
    pisti:'Klasik pişti: aynı kartla ya da vale ile masayı topla. Pişti 10, vale piştisi 20 puan; as, vale 1, sinek 2\'li 2, karo 10\'lu 3, en çok kart 3 puan.'}[k];
  box.innerHTML='<div class="lob"><div class="box"><h3>Masa aç</h3><p style="font-size:.88rem;margin-bottom:12px">'+esc(rules)+'</p>'+
    '<div class="lbl2">Bahis</div><div class="opts">'+stakeBtns+'</div>'+extra+
    '<button class="btn block" id="gCreate">'+(ST.state?'Masa aç · 💎 '+num(G.stake):'Giriş yap')+'</button>'+
    '<p class="secnote">Kazanan pot − %5 alır. Örnek: 10.000\'lik masada kazanan 19.000 alır.</p></div>'+
    '<div><h3 style="margin-bottom:12px">Açık masalar</h3><div id="roomList">'+roomsHtml(rooms)+'</div></div></div>';
  box.querySelectorAll('[data-stake]').forEach(b=>b.onclick=()=>{G.stake=+b.dataset.stake;renderLobby(G.lastRooms||[]);});
  box.querySelectorAll('[data-side]').forEach(b=>b.onclick=()=>{G.side=b.dataset.side;renderLobby(G.lastRooms||[]);});
  box.querySelectorAll('[data-cap]').forEach(b=>b.onclick=()=>{G.cap=+b.dataset.cap;renderLobby(G.lastRooms||[]);});
  $('#gCreate').onclick=createRoom;
}
function roomsHtml(rooms){
  const L=rooms.filter(r=>r.kind===G.tab);
  if(!L.length)return '<div class="empty">Şu an açık masa yok. İlk masayı sen aç!</div>';
  return '<div class="rooms">'+L.map(r=>'<div class="room"><div class="st">💎 '+num(r.stake)+'</div>'+
    '<div class="pl">'+esc(r.players.join(', '))+' · '+r.players.length+'/'+r.cap+(r.side?' · masa: '+(r.side==='yazi'?'Yazı':'Tura'):'')+'</div>'+
    '<button class="btn sm" data-join="'+esc(r.id)+'">Otur · 💎 '+num(r.stake)+'</button></div>').join('')+'</div>';
}
async function pollLobby(force){
  if(!ST.pass){gameNeedLogin();return;}
  if(G.busy&&!force)return;
  const j=await api('/site/games/list',{pass:ST.pass,kind:G.tab});
  if(!j.success)return;
  if(j.mine&&!G.room){G.room={id:j.mine,kind:j.mine_kind};G.seq=-1;renderGames();return;}
  G.lastRooms=j.rooms||[];
  const el=$('#roomList');if(el){el.innerHTML=roomsHtml(G.lastRooms);el.querySelectorAll('[data-join]').forEach(b=>b.onclick=()=>joinRoom(b.dataset.join));}
}
async function createRoom(){
  if(!ST.state){openModal('#mLogin');return;}
  G.busy=true;const j=await api('/site/games/create',{pass:ST.pass,kind:G.tab,stake:G.stake,side:G.side,cap:G.cap});G.busy=false;
  if(!j.success){info('<h3 style="margin-bottom:8px">Olmadı</h3><p>'+esc(j.error||'masa açılamadı')+'</p>');return;}
  setState(j.state);G.room={id:j.room.id,kind:j.room.kind};G.seq=-1;renderTable(j.room);
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
  const me=room.players[room.me];
  let head;
  if(r.refund)head='Berabere · elmasın geri döndü';
  else if(r.winners.includes(me))head='Kazandın! +💎 '+num(r.payout);
  else head='Kaybettin · kazanan: '+r.winners.join(', ');
  return '<div class="resbox"><b>'+esc(head)+'</b><span class="muted">'+esc(r.why||'')+(r.rake?' · site kesintisi 💎 '+num(r.rake):'')+'</span>'+
    '<div class="acts"><button class="btn sm" id="gAgain">Yeni masa</button></div></div>';
}
function renderTable(room){
  G.seq=room.seq;const box=$('#table');if(!box)return;
  // oyun rakibin hamlesiyle bittiyse bakiye sunucudan tazelenir
  if(room.state==='done'&&G.doneFor!==room.id){G.doneFor=room.id;api('/site/me',{pass:ST.pass}).then(j=>{if(j.success){ST.state=j.state;renderAcct();renderWheelUi();}});}
  const pot=room.stake*room.players.length;
  let h='<div class="felt"><div class="hdr"><b>'+({coin:'Yazı Tura',bj:'Blackjack',pisti:'Pişti'}[room.kind])+' · 💎 '+num(room.stake)+'\'lik masa</b><span class="pot">Pot: 💎 '+num(room.state==='wait'?room.stake*room.cap:pot)+'</span></div>';
  if(room.state==='wait'){
    h+='<div class="center" style="flex-direction:column">'+(room.kind==='coin'?'<div class="coin3d spin">?</div>':'')+
      '<p style="color:#e8f5ee">Rakip bekleniyor… ('+room.players.length+'/'+room.cap+')</p><p class="muted">'+esc(room.players.join(', '))+'</p></div>'+
      '<div class="acts"><button class="btn sm ghost" id="gLeave">Masadan kalk (elmas iade)</button></div>';
  }else if(room.kind==='coin'){
    const f=room.flip;
    h+='<div class="center" style="flex-direction:column"><div class="coin3d">'+(f==='yazi'?'YAZI':'TURA')+'</div>'+
      '<p style="color:#e8f5ee">'+esc(room.players[0])+': '+(room.side==='yazi'?'Yazı':'Tura')+' · '+esc(room.players[1]||'')+': '+(room.side==='yazi'?'Tura':'Yazı')+'</p></div>';
  }else if(room.kind==='bj'){
    room.hands.forEach((hd,i)=>{
      const mine=i===room.me;
      h+='<div class="seat'+(mine?' me':'')+'"><div class="nm"><span>'+esc(room.players[i])+(mine?' (sen)':'')+'</span><span>'+
        (hd.value!=null?'Toplam: '+hd.value+(hd.value>21?' · BATTI':''):(hd.done?'bitti':'oynuyor…'))+'</span></div><div class="cards">'+hd.cards.map(c=>pcard(c)).join('')+'</div></div>';
    });
    if(room.state==='play'&&room.me!=null&&!room.hands[room.me].done)
      h+='<div class="acts"><button class="btn" id="bjHit">Kart çek</button><button class="btn violet" id="bjStand">Dur</button><span class="timer">⏱ '+(room.time_left||0)+' sn</span></div>';
    else if(room.state==='play')h+='<p style="text-align:center;color:#e8f5ee">Rakibin oynuyor…</p>';
  }else if(room.kind==='pisti'){
    const n=room.players.length;
    h+='<div class="center"><div class="stack">'+(room.table_n>1?pcard('??','',' style="left:-6px;top:-4px"'):'')+(room.table_top?pcard(room.table_top):'<div class="pc back" style="opacity:.2"></div>')+'</div>'+
      '<div style="color:#e8f5ee;font-weight:700">Masada '+room.table_n+' kart · destede '+room.deck_n+'</div></div>';
    if(room.last)h+='<p style="text-align:center;color:#e8f5ee;margin-bottom:12px">'+esc(room.last.by)+' '+esc(room.last.card.replace(/(.+)([SHDC])$/,(m,r,s)=>r+SUIT[s]))+' attı'+(room.last.pisti?' · <b style="color:var(--gold)">PİŞTİ! +'+room.last.pisti+'</b>':(room.last.took?' ve masayı topladı':''))+'</p>';
    for(let i=0;i<n;i++){
      const mine=i===room.me,turn=room.state==='play'&&room.turn===i;
      h+='<div class="seat'+(mine?' me':'')+(turn&&!mine?' turn':'')+'"><div class="nm"><span>'+esc(room.players[i])+(mine?' (sen)':'')+(turn?' · <span class="timer">sırada ⏱ '+(room.time_left||0)+'</span>':'')+'</span>'+
        '<span>'+(room.taken_n[i])+' kart · pişti '+room.pisti[i]+(room.scores?' · <b style="color:var(--gold)">'+room.scores[i]+' puan</b>':'')+'</span></div>';
      if(mine)h+='<div class="cards">'+room.hand.map(c=>pcard(c,turn?'play':'',' data-card="'+esc(c)+'"')).join('')+'</div>';
      else h+='<div class="cards">'+Array.from({length:room.counts[i]},()=>pcard('??','sm')).join('')+'</div>';
      h+='</div>';
    }
  }
  if(room.state==='done')h+=resultHtml(room.result,room);
  else if(room.state==='play')h+='<div class="acts"><button class="btn sm ghost" id="gLeave">Masadan kalk (kaybedersin)</button></div>';
  h+='</div>';
  box.innerHTML=h;
  const on=(id,f)=>{const el=document.getElementById(id);if(el)el.onclick=f;};
  on('gLeave',()=>{if(room.state==='play'&&!confirm('Oyun sürerken kalkarsan elin kendiliğinden oynanır ve büyük ihtimalle kaybedersin. Emin misin?'))return;act('leave');});
  on('bjHit',()=>act('hit'));on('bjStand',()=>act('stand'));
  on('gAgain',async()=>{G.room=null;G.seq=-1;const me=await api('/site/me',{pass:ST.pass});if(me.success)setState(me.state);renderGames();});
  box.querySelectorAll('.pc.play[data-card]').forEach(c=>c.onclick=()=>act('play',{card:c.dataset.card}));
}

/* ---------- rulet ---------- */
const RW=[0,32,15,19,4,21,2,25,17,34,6,27,13,36,11,30,8,23,10,5,24,16,33,1,20,14,31,9,22,18,29,7,28,12,35,3,26];
const RRED=new Set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]);
const R={bets:{},chip:1000,angle:0,spinning:false,last:null};
function rkey(t,v){return t+(v!=null?':'+v:'');}
function rTotal(){return Object.values(R.bets).reduce((a,b)=>a+b,0);}
function renderRoulette(){
  const box=$('#roul');
  if(!box.dataset.built){
    box.dataset.built='1';
    let board='<div class="board"><div class="c g z" data-t="num" data-v="0">0</div>';
    for(let row=0;row<3;row++)for(let col=0;col<12;col++){const n=col*3+(3-row);board+='<div class="c '+(RRED.has(n)?'r':'k')+'" data-t="num" data-v="'+n+'">'+n+'</div>';}
    board+='</div><div class="outs d">'+[1,2,3].map(d=>'<div class="c o" data-t="dozen" data-v="'+d+'">'+(d*12-11)+'-'+d*12+'</div>').join('')+'</div>'+
      '<div class="outs">'+[['low','1-18'],['even','ÇİFT'],['red','KIRMIZI'],['black','SİYAH'],['odd','TEK'],['high','19-36']].map(x=>'<div class="c '+(x[0]==='red'?'r':(x[0]==='black'?'k':'o'))+'" data-t="'+x[0]+'">'+x[1]+'</div>').join('')+'</div>'+
      '<div class="outs d">'+[1,2,3].map(c=>'<div class="c o" data-t="col" data-v="'+c+'">'+c+'. sütun (2:1)</div>').join('')+'</div>';
    box.innerHTML='<div class="rlay"><div><div class="rwheel"><canvas id="rCv" width="420" height="420"></canvas></div><div class="rres" id="rRes"></div></div>'+
      '<div><div class="lbl2">Fiş</div><div class="opts" id="rChips">'+[100,500,1000,5000,10000].map(v=>'<button data-chip="'+v+'" aria-pressed="'+(v===R.chip)+'">💎 '+num(v)+'</button>').join('')+'</div>'+
      board+'<div class="rctl"><span>Toplam bahis: <b id="rTot">0</b> 💎 (en çok 100.000)</span><button class="btn sm ghost" id="rClear">Temizle</button><button class="btn" id="rSpin">Çevir</button></div>'+
      '<p class="secnote">Sayı 35:1 · düzine ve sütun 2:1 · kırmızı/siyah, tek/çift, 1-18/19-36 1:1. Tek sıfırlı Avrupa ruleti; 0 gelirse dış bahisler kaybeder. Sonucu sunucu seçer.</p></div></div>';
    box.querySelectorAll('[data-chip]').forEach(b=>b.onclick=()=>{R.chip=+b.dataset.chip;box.querySelectorAll('[data-chip]').forEach(x=>x.setAttribute('aria-pressed',x===b));});
    box.querySelectorAll('.board .c,.outs .c').forEach(c=>{
      c.onclick=()=>{if(R.spinning)return;const k=rkey(c.dataset.t,c.dataset.v);if(rTotal()+R.chip>100000)return;R.bets[k]=(R.bets[k]||0)+R.chip;drawBets();};
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
    if(v){if(!ch){ch=document.createElement('span');ch.className='chip';c.appendChild(ch);}ch.textContent=v>=1000?(v/1000)+'K':v;}else if(ch)ch.remove();});
  const t=$('#rTot');if(t)t.textContent=num(rTotal());
}
function drawRWheel(ball){
  const cv=$('#rCv');if(!cv)return;const x=cv.getContext('2d'),S=cv.width,c=S/2,R2=S/2-10,n=RW.length,seg=Math.PI*2/n,rot=R.angle;
  x.clearRect(0,0,S,S);
  x.beginPath();x.arc(c,c,R2,0,7);x.fillStyle='#5a3a1c';x.fill();
  for(let i=0;i<n;i++){const v=RW[i],a0=-Math.PI/2+rot+i*seg-seg/2;
    x.beginPath();x.moveTo(c,c);x.arc(c,c,R2-12,a0,a0+seg);x.closePath();x.fillStyle=v===0?'#1f7a46':(RRED.has(v)?'#b3202f':'#1b1b26');x.fill();
    x.strokeStyle='#c9a24a';x.lineWidth=1;x.stroke();
    x.save();x.translate(c,c);x.rotate(a0+seg/2);x.translate(R2-28,0);x.rotate(Math.PI/2);x.fillStyle='#fff';x.font='13px "Russo One",sans-serif';x.textAlign='center';x.fillText(v,0,4);x.restore();}
  x.beginPath();x.arc(c,c,R2*0.55,0,7);x.fillStyle='#3a2410';x.fill();x.strokeStyle='#c9a24a';x.lineWidth=3;x.stroke();
  x.beginPath();x.arc(c,c,R2*0.12,0,7);x.fillStyle='#e8c46a';x.fill();
  // ibre
  x.beginPath();x.moveTo(c-10,4);x.lineTo(c+10,4);x.lineTo(c,26);x.closePath();x.fillStyle='#fff';x.fill();
  if(ball!=null){x.beginPath();x.arc(c,c-(R2-46),8,0,7);x.fillStyle='#fff';x.fill();x.strokeStyle='#999';x.stroke();}
}
async function spinRoulette(){
  if(R.spinning)return;
  if(!ST.state){openModal('#mLogin');return;}
  const bets=Object.entries(R.bets).map(([k,a])=>{const [t,v]=k.split(':');return {type:t,value:v!=null?+v:undefined,amount:a};});
  if(!bets.length){$('#rRes').textContent='Önce bahis koy: tahtaya tıkla.';return;}
  R.spinning=true;$('#rRes').textContent='';$('#rSpin').classList.add('off');
  const j=await api('/site/roulette/spin',{pass:ST.pass,bets});
  if(!j.success){R.spinning=false;$('#rSpin').classList.remove('off');$('#rRes').textContent=j.error||'çevrilemedi';return;}
  const i=RW.indexOf(j.number),seg=Math.PI*2/RW.length,a0=R.angle,target=-i*seg;
  let delta=((target-a0)%(Math.PI*2)+Math.PI*2)%(Math.PI*2);const a1=a0+delta+Math.PI*2*6,t0=performance.now(),dur=4800;
  (function an(ts){const k=Math.min(1,(ts-t0)/dur),e=1-Math.pow(1-k,3.4);R.angle=a0+(a1-a0)*e;drawRWheel(1);
    if(k<1)requestAnimationFrame(an);else{
      R.spinning=false;$('#rSpin').classList.remove('off');setState(j.state);
      const col={red:'kırmızı',black:'siyah',green:'yeşil'}[j.color];
      const net=j.win-j.bet;
      $('#rRes').innerHTML='<span style="color:'+(j.color==='red'?'#ff6b7a':(j.color==='green'?'#6ddc8e':'#ecebff'))+'">'+j.number+' '+col+'</span> · '+(j.win?'<span style="color:var(--gold)">+💎 '+num(j.win)+'</span>':'<span class="muted">kazanç yok</span>');
      if(net>0&&j.win>=j.bet*5)confetti();
    }})(t0);
}

/* =================== AÇILIŞ =================== */
// İnceleme araçlarına küçük bir caydırıcı. Asıl koruma sunucuda: sonuçlar orada belirlenir, sayfada gizli sonuç / kod yoktur.
document.addEventListener('contextmenu',e=>{if(e.target.closest('#drawer,#scratch,#tiers,#table,#roul'))e.preventDefault();});
document.addEventListener('keydown',e=>{const k=(e.key||'').toUpperCase();if(k==='F12'||(e.ctrlKey&&e.shiftKey&&['I','J','C'].includes(k))||(e.ctrlKey&&k==='U'))e.preventDefault();});

(async function boot(){
  if(GD&&pages[PAGE])pages[PAGE]();
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
