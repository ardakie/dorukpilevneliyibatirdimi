import html,json,re,shutil,time
from pathlib import Path
from bs4 import BeautifulSoup
from package_archive import ROOT,OUT,media_url

MAIN=ROOT/'outputs/github-site'
MEDIA_REPO=ROOT/'outputs/github-media'
MAIN_URL='https://ardakie.github.io/dorukpilevneliyibatirdimi/'
MEDIA_URL='https://ardakie.github.io/dorukpilevneliyibatirdimi-medya/'
while not (OUT/'index.html').exists() or not (OUT/'media-inventory.json').exists():time.sleep(5)
docs=MAIN/'docs';other=MEDIA_REPO/'docs'
docs.mkdir(parents=True,exist_ok=True);other.mkdir(parents=True,exist_ok=True)
for d in ['pages','texts','pdf']:shutil.copytree(OUT/d,docs/d,dirs_exist_ok=True)
for f in OUT.glob('*'):
    if f.is_file():shutil.copy2(f,docs/f.name)
shutil.copytree(OUT/'raw',MAIN/'source/raw',dirs_exist_ok=True)
inventory=json.loads((OUT/'inventory.json').read_text())
media=json.loads((OUT/'media-inventory.json').read_text())
pdfs=json.loads((OUT/'pdf-inventory.json').read_text())
lookup={r['path']:r for r in inventory}
base=sum(f.stat().st_size for f in docs.rglob('*') if f.is_file())
assets=sorted((OUT/'media').glob('*'),key=lambda f:f.stat().st_size,reverse=True)
total=sum(f.stat().st_size for f in assets)
sizes=[base,0];locations={}
for f in assets:
    slot=0 if sizes[0]<=sizes[1] else 1
    if sizes[slot]+f.stat().st_size>900*1024**2:slot=1-slot
    target=(docs if slot==0 else other)/'media'/f.name
    target.parent.mkdir(exist_ok=True);shutil.copy2(f,target)
    sizes[slot]+=f.stat().st_size
    locations['media/'+f.name]=('media/'+f.name) if slot==0 else MEDIA_URL+'media/'+f.name
if max(sizes)>950*1024**2:raise RuntimeError('Two Pages sites exceed size budget; all content preserved locally.')
external={file:url for file,url in locations.items() if url.startswith('https:')}
for f in (docs/'pages').glob('*.html'):
    s=f.read_text().replace('href="../index.html"','href="../arsiv.html"')
    s=re.sub(r'(?<=["\'])\.\./(media/[^"\']+)',lambda m:external.get(m.group(1),m.group(0)),s)
    f.write_text(s)
archive=(docs/'index.html').read_text()
archive=archive.replace('render();</script>','const params=new URLSearchParams(location.search);if(params.get("section"))$("section").value=params.get("section");if(params.get("q"))$("q").value=params.get("q");render();</script>')
archive=archive.replace('<h1>PİLEVNELİ · Kurtarılan site arşivi</h1>','<nav><a href="index.html">← Ana sayfa</a></nav><h1>PİLEVNELİ · Kurtarılan site arşivi</h1>')
(docs/'arsiv.html').write_text(archive)
def target(r):return r.get('local_file') or 'pages/'+r['key']+'.html'
def image(r):
    raw=OUT/'raw'/(r['key']+'.html')
    if not raw.exists():return ''
    s=BeautifulSoup(raw.read_text(errors='replace'),'html.parser')
    root=s.select_one('#content') or s
    candidates=[im.get('data-src') or im.get('src') for im in root.find_all('img')]
    og=s.find('meta',property='og:image')
    if og:candidates.append(og.get('content'))
    for candidate in candidates:
        u=media_url(candidate,r['url'])
        m=next((m for m in media if m['url']==u and m['status']=='saved'),None)
        if m:return locations.get(m['file'],m['url'])
    return ''
cards=[]
for ident in ['131-','130-','129-']:
    matches=[r for r in inventory if re.search(r'/exhibitions/'+ident,r['path']) and r['path'].endswith('/overview/') and r['status']=='saved']
    if not matches:continue
    r=next((x for x in matches if x['path'].startswith('/tr/')),matches[0])
    title=r.get('title',r['path']).split('|')[0].split(' - Overview')[0]
    cards.append('<a class="card" href="'+target(r)+'"><div class="card-image"><img src="'+html.escape(image(r),quote=True)+'" alt="" loading="lazy"></div><div class="card-label"><span>'+html.escape(title)+'</span><span>↗</span></div></a>')
hero=image(lookup['/']) if '/' in lookup else ''
if not hero and cards:hero=re.search(r'src="([^"]+)"',cards[0]).group(1)
artists=[]
artist_page=lookup.get('/tr/artists/') or lookup.get('/artists/')
if artist_page:
    s=BeautifulSoup((OUT/'raw'/(artist_page['key']+'.html')).read_text(errors='replace'),'html.parser')
    seen=set()
    for a in s.select('#content a[href]'):
        p=a['href'];r=lookup.get(p) or lookup.get(p.rstrip('/')+'/overview/')
        name=a.get_text(' ',strip=True)
        if not r or not name or name in seen:continue
        seen.add(name);artists.append('<a href="'+target(r)+'">'+html.escape(name)+' <span>↗</span></a>')
if not artists:
    for r in inventory:
        if r['path'].startswith('/tr/artists/') and r['path'].endswith('/overview/'):
            artists.append('<a href="'+target(r)+'">'+html.escape(r.get('title',r['path']).split('|')[0])+' <span>↗</span></a>')
nav=''.join('<a href="arsiv.html?section='+section+'">'+label+'</a>' for section,label in [('Sanatçılar','SANATÇILAR'),('Sergiler','SERGİLER'),('Fuarlar','FUARLAR'),('Yayınlar','YAYINLAR'),('Haberler','HABERLER')])
css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f4ef;color:#151515;font-family:Arial,Helvetica,sans-serif}a{color:inherit;text-decoration:none}header{padding:28px 4vw;display:flex;justify-content:space-between;align-items:center;gap:30px;border-bottom:1px solid #d6d5cf}.brand{font-size:36px;font-weight:700;letter-spacing:-2px}.brand small{font-size:10px;font-weight:400;letter-spacing:2px;display:block;margin-top:5px}nav{display:flex;gap:25px;font-size:11px;letter-spacing:1px;flex-wrap:wrap}nav a:hover{text-decoration:underline}.hero{display:grid;grid-template-columns:1fr 1fr;min-height:650px}.hero-copy{padding:7vw 4vw 5vw;display:flex;flex-direction:column;align-items:flex-start;justify-content:center}.eyebrow{font-size:11px;letter-spacing:2px;text-transform:uppercase}.hero h1{font-size:clamp(50px,5.5vw,92px);font-weight:400;line-height:1.02;letter-spacing:-4px;margin:35px 0}.hero p{font-size:17px;line-height:1.65;max-width:430px;color:#555}.hero-image{min-height:500px;background:#dad8d1}.hero-image img{width:100%;height:100%;object-fit:cover;max-height:760px}.button{display:inline-flex;gap:50px;border-bottom:1px solid #222;padding:16px 0;font-size:13px;letter-spacing:1px;margin-top:15px}.section{padding:70px 4vw;border-top:1px solid #d6d5cf}.section-title{display:flex;justify-content:space-between;align-items:baseline;gap:20px;margin-bottom:35px}.section h2{font-weight:400;font-size:38px;letter-spacing:-1px;margin:0}.section-title a{font-size:12px;border-bottom:1px solid #222;padding-bottom:6px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}.card-image{height:350px;background:#e8e6de;overflow:hidden}.card-image img{width:100%;height:100%;object-fit:contain}.card-label{display:flex;justify-content:space-between;gap:20px;padding-top:18px;font-size:14px;line-height:1.5}.artists{display:grid;grid-template-columns:repeat(3,1fr);column-gap:40px}.artists a{display:flex;justify-content:space-between;border-bottom:1px solid #d6d5cf;padding:18px 0;font-size:14px}.artists a:hover{color:#72725c}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:30px}.stats b{font-size:45px;font-weight:400;display:block;margin-bottom:10px}.stats p{font-size:13px;color:#555}.search{display:flex;max-width:800px;border-bottom:1px solid #222;margin-top:30px}.search input{flex:1;min-width:0;font:inherit;border:0;background:transparent;padding:16px 0;outline-offset:6px}.search button{border:0;background:transparent;font-size:24px;padding:8px 15px;cursor:pointer}footer{padding:35px 4vw;border-top:1px solid #d6d5cf;display:flex;justify-content:space-between;gap:30px;font-size:12px;color:#666;line-height:1.6}footer p{max-width:650px;margin:0}footer a{text-decoration:underline}@media(max-width:800px){header{align-items:flex-start;flex-direction:column}.brand{font-size:30px}nav{gap:16px}.hero{grid-template-columns:1fr;min-height:0}.hero-copy{padding:60px 6vw}.hero h1{letter-spacing:-2px}.hero-image{min-height:350px;height:450px}.cards{grid-template-columns:1fr}.card-image{height:400px}.artists{grid-template-columns:repeat(2,1fr)}.section{padding:45px 6vw}.section h2{font-size:30px}.stats b{font-size:32px}footer{flex-direction:column}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}'''
body=f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PİLEVNELİ · Site Arşivi</title><meta name="description" content="PİLEVNELİ sanatçıları, sergileri, eserleri ve yayınlarından kurtarılan site arşivi."><style>{css}</style></head><body><header><a class="brand" href="index.html">PİLEVNELİ<small>SİTE ARŞİVİ</small></a><nav>{nav}<a href="arsiv.html">TÜM ARŞİV ↗</a></nav></header><main><section class="hero"><div class="hero-copy"><span class="eyebrow">Sanat · Sergiler · Hafıza</span><h1>Sanatın<br>izi burada.</h1><p>PİLEVNELİ’nin sanatçıları, sergileri ve yayınları. Erişilemeyen web sitesinden kurtarılan içerikleri keşfedin.</p><a class="button" href="arsiv.html">ARŞİVİ KEŞFET <span>↗</span></a></div><div class="hero-image"><img src="{html.escape(hero,quote=True)}" alt="PİLEVNELİ sergi arşivinden görsel"></div></section><section class="section"><div class="section-title"><h2>Sergi arşivi</h2><a href="arsiv.html?section=Sergiler">Tüm sergiler ↗</a></div><div class="cards">{''.join(cards)}</div></section><section class="section"><div class="section-title"><h2>Sanatçılar</h2><a href="arsiv.html?section=Sanatçılar">Sanatçı arşivi ↗</a></div><div class="artists">{''.join(artists)}</div></section><section class="section"><span class="eyebrow">Arşivde ara</span><h2 style="margin-top:20px">Aradığınız içerik.</h2><form class="search" action="arsiv.html"><input name="q" aria-label="Arşivde ara" placeholder="Sanatçı, sergi veya eser adı"><button aria-label="Ara">↗</button></form></section><section class="section stats"><div><b>{sum(r['status']=='saved' for r in inventory):,}</b><p>Kurtarılan sayfa</p></div><div><b>{sum(m['status']=='saved' for m in media):,}</b><p>Kaydedilen görsel</p></div><div><b>{sum(m['status']=='saved' for m in pdfs)}</b><p>PDF belge</p></div></section></main><footer><p>Bu bağımsız arşiv, PİLEVNELİ’nin resmî web sitesi değildir. İçerikler Internet Archive ve erişilebilir dosya sunucularından kurtarılmıştır. Kayıt tarihleri farklıdır; eksikler olabilir. İçerik ve görsel hakları ilgili sahiplerindedir.</p><div><a href="arsiv.html">TR / EN arşivi</a><br><a href="pdfler.html">PDF belgeler</a><br><a href="{MEDIA_URL}">Görsel arşivi</a></div></footer></body></html>'''
(docs/'index.html').write_text(body)
# Secondary site provides a browseable media directory; all images remain accounted for.
items=[]
for m in media:
    if m['file'] not in locations:continue
    url=locations[m['file']]
    if not url.startswith('https:'):url=MAIN_URL+url
    elif url.startswith(MEDIA_URL):url=url[len(MEDIA_URL):]
    items.append(dict(url=url,name=m['url'].rsplit('/',1)[-1],source=m['url']))
data=json.dumps(items,ensure_ascii=False).replace('</','<\\/')
gallery='''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PİLEVNELİ · Görsel Arşivi</title><style>body{font:16px/1.5 Arial;margin:35px;background:#f5f4ef}a{color:#333}input,button{font:inherit;padding:10px}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:25px;margin-top:30px}figure{margin:0}img{width:100%;height:270px;object-fit:contain;background:#e8e6de}figcaption{word-break:break-word;font-size:12px}button{margin-top:30px}</style><a href="MAINURL">← Ana site</a><h1>Görsel arşivi</h1><p>İki depoda korunan görsellerin tamamı.</p><input id="q" aria-label="Görsel ara" placeholder="Dosya veya sanatçı adı"><p id="count"></p><div id="grid"></div><button id="more">Daha fazla</button><script>const data=DATA;let limit=60;const q=document.getElementById('q'),grid=document.getElementById('grid');function render(){let a=data.filter(r=>(r.name+' '+r.source).toLocaleLowerCase('tr').includes(q.value.toLocaleLowerCase('tr')));document.getElementById('count').textContent=a.length+' görsel';grid.replaceChildren();a.slice(0,limit).forEach(r=>{let f=document.createElement('figure'),link=document.createElement('a'),im=document.createElement('img'),c=document.createElement('figcaption');link.href=r.url;im.src=r.url;im.loading='lazy';im.alt=r.name;c.textContent=r.name;link.append(im);f.append(link,c);grid.append(f)});document.getElementById('more').hidden=limit>=a.length}q.oninput=()=>{limit=60;render()};document.getElementById('more').onclick=()=>{limit+=60;render()};render();</script></html>'''.replace('MAINURL',MAIN_URL).replace('DATA',data)
(other/'index.html').write_text(gallery)
for repo in [MAIN,MEDIA_REPO]:
    (repo/'docs/.nojekyll').write_text('')
    (repo/'.gitignore').write_text('.DS_Store\n__pycache__/\n*.log\n*.zip\n')
    (repo/'README.md').write_text('# PİLEVNELİ site arşivi\n\nInternet Archive ve erişilebilir dosya sunucularından kurtarılan bağımsız arşiv.\nGalerinin resmî sitesi değildir. Kayıtlar farklı tarihlerdendir. Haklar ilgili sahiplerindedir.\n\nAna site: '+MAIN_URL+'\nGörsel arşivi: '+MEDIA_URL+'\n\nKurtarılan bütün medya iki özel depoda korunur. Sayfalar gerektiğinde ikinci sitenin görsellerini kullanır. Tam çevrimdışı ZIP ana deponun Releases bölümündedir.\n')
(MAIN/'recovery').mkdir(exist_ok=True)
for f in ['recover.py','package_archive.py','prefetch_media.py','prepare_github.py']:shutil.copy2(ROOT/'work'/f,MAIN/'recovery'/f)
(MAIN/'split-manifest.json').write_text(json.dumps(dict(sizes=sizes,locations=locations),ensure_ascii=False,indent=2))
print('SITES_READY',sizes,'files',len(assets),'cross_repo_media',len(external),'artists',len(artists),flush=True)
