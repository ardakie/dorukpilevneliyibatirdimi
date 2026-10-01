import concurrent.futures as cf
import csv, hashlib, html, json, re, time, threading
from pathlib import Path
from urllib.parse import urlsplit, urljoin, unquote
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/pilevneli-arsivi'
CSS='''body{margin:0;background:#f6f5f1;color:#1d2327;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:36px 28px}a{color:#244e8b}h1{font-size:32px;line-height:1.25}img{max-width:100%;height:auto}nav,.notice{padding:14px 20px;background:white;border:1px solid #ddd;border-radius:8px;margin:0 0 24px}nav{display:flex;gap:24px;flex-wrap:wrap}.records_list ul{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}.records_list li{background:white;padding:16px}.image img{max-height:600px;object-fit:contain}.clear{clear:both}button,input,select{font:inherit;padding:9px 14px;border:1px solid #bbb;border-radius:6px}button{cursor:pointer;background:white}small{color:#667}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #ddd}.tag{font-size:12px;border-radius:5px;padding:3px 8px;background:#e5ebe5}pre{white-space:pre-wrap}'''
def wrap(title,body):
    return '<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+CSS+'</style><main>'+body+'</main></html>'
def media_url(u,base):
    if not u or u.startswith(('data:','javascript:','#')): return None
    u=urljoin(base,u)
    for marker in ['/ws-pilevneli/','/artlogicstorage/']:
        if marker in u and urlsplit(u).netloc in ['artlogic-res.cloudinary.com','static-assets.artlogic.net']:
            tail=u.split(marker,1)[1].split('?',1)[0]
            return 'https://static-assets.artlogic.net/w_1600,h_1600,c_limit,f_auto,fl_lossy,q_auto'+marker+tail
    if urlsplit(u).netloc in ['www.pilevneli.com','pilevneli.com'] and '/usr/images/' in u:
        return 'https://static-assets.artlogic.net/w_1600,h_1600,c_limit,f_auto,fl_lossy,q_auto/ws-pilevneli'+urlsplit(u).path
    return None
def identity(u): return hashlib.sha256(u.encode()).hexdigest()[:24]
local=threading.local()
def fetch_asset(item):
    url,dst=item
    if dst.exists() and dst.stat().st_size>200: return url,True,dst.stat().st_size
    try:
        if not hasattr(local,'session'):
            local.session=requests.Session()
            local.session.headers['User-Agent']='Mozilla/5.0'
        r=local.session.get(url,timeout=(15,45))
        r.raise_for_status()
        if len(r.content)<200 or 'text/html' in r.headers.get('Content-Type',''):raise ValueError('No media')
        dst.write_bytes(r.content);return url,True,len(r.content)
    except Exception as e:return url,False,str(e)[:180]
def download_pdfs():
    entries=[]
    for ts,u in json.loads((ROOT/'work/pdf.bin').read_text())[1:]:
        key=identity(u);name=key+'-'+unquote(urlsplit(u).path.split('/')[-1])
        dst=OUT/'pdf'/name
        entries.append(dict(url=u,timestamp=ts,file='pdf/'+name,archive_url='https://web.archive.org/web/'+ts+'id_/'+u))
    results={}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        for u,ok,val in ex.map(fetch_asset,[(r['archive_url'],OUT/r['file']) for r in entries]):results[u]=(ok,val)
    for r in entries:
        ok,val=results[r['archive_url']];r['status']='saved' if ok else 'failed'
        if not ok:r['error']=val
    missing=[r for r in entries if r['status']=='failed']
    cdn={r['url']:'https://artlogic-res.cloudinary.com/ws-pilevneli'+urlsplit(r['url']).path for r in missing}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        attempts=list(ex.map(fetch_asset,[(cdn[r['url']],OUT/r['file']) for r in missing]))
    for r,(u,ok,val) in zip(missing,attempts):
        if ok:r.update(status='saved',download_url=u);r.pop('error',None)
    (OUT/'pdf-inventory.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2))
    print('PDF',sum(r['status']=='saved' for r in entries),'/',len(entries),flush=True)

def build():
    records=json.loads((OUT/'inventory.json').read_text())
    lookup={r['path']:r for r in records}
    media={};documents={};contents={}
    for r in records:
        raw=OUT/'raw'/(r['key']+'.html')
        if not raw.exists():continue
        r['status']='saved';r.pop('error',None)
        s=BeautifulSoup(raw.read_text(errors='replace'),'html.parser')
        r['title']=s.title.get_text(' ',strip=True) if s.title else r['path']
        content=s.select_one('#content') or s.select_one('#main_content') or s.body or s
        for frame in content.find_all('iframe'):
            src=frame.get('src') or frame.get('data-src')
            if src:
                p=s.new_tag('p');a=s.new_tag('a',href=urljoin(r['url'],src));a.string='Video / gömülü içerik bağlantısı';p.append(a);frame.replace_with(p)
            else:frame.decompose()
        for x in content.select('script,style,form,.cookie_popup,.mailinglist_signup_popup,.image_popup,#cookie_notification,#cookie_preferences,.cookie-preferences,#artlogic_mailinglist_signup_form_wrapper'):
            x.decompose()
        for tag in content.find_all(True):
            for attr in list(tag.attrs):
                if attr.startswith('on'):del tag[attr]
            if tag.name=='img':
                src=tag.get('data-src') or tag.get('data-image-src') or tag.get('src')
                u=media_url(src,r['url'])
                if u:
                    ext=urlsplit(u).path.split('.')[-1].lower()
                    if ext not in ['jpg','jpeg','png','gif','webp','svg','avif']:ext='jpg'
                    file='media/'+identity(u)+'.'+ext
                    media[u]=file;tag['src']='../'+file
                    tag['loading']='lazy';tag['alt']=tag.get('alt','')
                tag.attrs={k:v for k,v in tag.attrs.items() if k in ['src','alt','loading','class']}
            if tag.get('style'):
                found=re.findall(r'url\([\'\"]?([^\)\'\"]+)',tag['style'])
                tag.attrs.pop('style',None)
                for src in found:
                    u=media_url(src,r['url'])
                    if u:
                        ext=urlsplit(u).path.rsplit('.',1)[-1].lower()
                        if ext not in ['jpg','jpeg','png','gif','webp','svg','avif']:ext='jpg'
                        file='media/'+identity(u)+'.'+ext;media[u]=file
                        img=s.new_tag('img',src='../'+file,loading='lazy',alt='')
                        tag.append(img)
            if tag.name=='a' and tag.get('href'):
                href=tag['href']
                if href.startswith('javascript:'):tag.attrs.pop('href');continue
                if href.startswith('#'):continue
                u=urljoin(r['url'],href);parts=urlsplit(u)
                if parts.netloc in ['pilevneli.com','www.pilevneli.com']:
                    if parts.path in lookup:
                        other=lookup[parts.path];tag['href']=other['key']+'.html' if (OUT/'raw'/(other['key']+'.html')).exists() else 'https://web.archive.org/web/'+other['timestamp']+'/'+other['url']
                    elif parts.path.lower().endswith('.pdf'):
                        tag['href']='https://web.archive.org/web/'+r['timestamp']+'/'+u
                        documents[u]=r['timestamp']
                    else:tag['href']='https://web.archive.org/web/'+r['timestamp']+'/'+u
                else:tag['href']=u
        text=content.get_text('\n',strip=True)
        (OUT/'texts'/(r['key']+'.txt')).write_text('URL: '+r['url']+'\nSnapshot: '+r['timestamp']+'\n\n'+text)
        contents[r['key']]=str(content)
    print('PARSED',len(contents),'MEDIA',len(media),'DOC_LINKS',len(documents),flush=True)
    # Include images referenced outside the main content (home slides and background images).
    for raw in (OUT/'raw').glob('*.html'):
        for src in re.findall(r'https://[^\s\'\"<>]+/(?:ws-pilevneli|artlogicstorage)/[^\s\'\"<>]+',raw.read_text(errors='replace')):
            u=media_url(src.rstrip(');,\\'),'https://www.pilevneli.com/')
            if not u:continue
            ext=urlsplit(u).path.rsplit('.',1)[-1].lower()
            if ext in ['jpg','jpeg','png','gif','webp','svg','avif']:media[u]='media/'+identity(u)+'.'+ext
    print('ALL_REFERENCED_MEDIA',len(media),flush=True)
    results={}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for n,(u,ok,val) in enumerate(ex.map(fetch_asset,[(u,OUT/f) for u,f in media.items()]),1):
            results[u]=(ok,val)
            if n%100==0:print('MEDIA',n,'/',len(media),'saved',sum(v[0] for v in results.values()),flush=True)
    media_entries=[]
    for u,file in media.items():
        ok,val=results[u];media_entries.append(dict(url=u,file=file,status='saved' if ok else 'failed',detail=val))
        if not ok:
            for key in contents:contents[key]=contents[key].replace('../'+file,u)
    (OUT/'media-inventory.json').write_text(json.dumps(media_entries,ensure_ascii=False,indent=2))
    with (OUT/'gorsel-listesi.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['url','file','status','detail']);w.writeheader();w.writerows(media_entries)
    for r in records:
        if r['key'] not in contents:continue
        ts=r['timestamp'];date=ts[:4]+'-'+ts[4:6]+'-'+ts[6:8]
        r['local_file']='pages/'+r['key']+'.html'
        body='<nav><a href="../index.html">← Arşiv dizini</a><a href="https://web.archive.org/web/'+ts+'/'+html.escape(r['url'],quote=True)+'">Wayback kopyası</a><a href="../texts/'+r['key']+'.txt">Düz metin</a></nav><h1>'+html.escape(r.get('title',r['path']))+'</h1><div class="notice">'+html.escape(r['path'])+' · Kayıt tarihi: '+date+'<br><small>Arşivden kurtarılan içerik. Sayfaların kayıt tarihleri farklıdır. İşlevler ve özgün tasarım birebir korunmamış olabilir.</small></div>'+contents[r['key']]
        (OUT/r['local_file']).write_text(wrap(r.get('title',r['path']),body))
    # Remap saved PDFs into readable pages.
    pdf_entries=json.loads((OUT/'pdf-inventory.json').read_text()) if (OUT/'pdf-inventory.json').exists() else []
    for page in (OUT/'pages').glob('*.html'):
        text=page.read_text()
        for pdf in pdf_entries:
            if pdf['status']=='saved':
                pattern=r'https://web\.archive\.org/web/\d+(?:id_)?/'+re.escape(pdf['url'])
                text=re.sub(pattern,'../'+pdf['file'],text)
        page.write_text(text)
    (OUT/'inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    with (OUT/'sayfa-listesi.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['path','title','timestamp','status','url','local_file','error'],extrasaction='ignore');w.writeheader();w.writerows(records)
    with (OUT/'tum-metinler.txt').open('w') as f:
        for r in records:
            textfile=OUT/'texts'/(r['key']+'.txt')
            if textfile.exists():f.write('\n\n'+'='*80+'\n'+r.get('title',r['path'])+'\n'+textfile.read_text())
    for r in records:
        p=r['path'].strip('/').split('/');r['language']='TR' if p[0]=='tr' else 'EN'
        if p[0]=='tr':p=p[1:]
        sec=p[0] if p else ''
        r['section']={'artists':'Sanatçılar','artworks':'Eserler','exhibitions':'Sergiler','events':'Fuarlar','publications':'Yayınlar','news':'Haberler','contact':'İletişim'}.get(sec,'Diğer')
    data=json.dumps([dict(title=r.get('title') or unquote(r['path']).replace('-',' '),path=r['path'],section=r['section'],lang=r['language'],date=r['timestamp'][:8],saved=r['key'] in contents,local=r.get('local_file'),archive='https://web.archive.org/web/'+r['timestamp']+'/'+r['url']) for r in records],ensure_ascii=False).replace('</','<\\/')
    npdf=sum(x['status']=='saved' for x in pdf_entries);nmedia=sum(v[0] for v in results.values())
    body=f'''<h1>PİLEVNELİ · Kurtarılan site arşivi</h1><p>Türkçe ve İngilizce sayfalar, sanatçılar, sergiler, eserler, fuarlar, haberler ve yayınlar. Kaynak: Internet Archive Wayback Machine ve sitenin erişilebilir görsel sunucusu.</p><div class="notice"><b>{len(contents):,} sayfa indirildi · {nmedia:,} görsel indirildi · {npdf} PDF indirildi</b><br>{len(records):,} farklı sayfa adresi bulundu. Arşiv kayıtları farklı tarihlerdendir; tüm içeriğin eksiksiz veya kapanmadan önceki son sürüm olduğu doğrulanamaz. İndirilemeyen içeriklerin arşiv bağlantıları aşağıdadır. Görseller 1600 piksel sınırıyla indirildi; ham HTML dosyalarında özgün görsel adresleri korunuyor.</div><nav><a href="sayfa-listesi.csv">CSV sayfa listesi</a><a href="inventory.json">JSON envanteri</a><a href="pdfler.html">PDF belgeler</a><a href="OKU.txt">Kullanım ve kapsam</a></nav><label>Arama <input id="q" placeholder="Sanatçı, sergi veya sayfa adresi" size="38"></label> <select id="section"><option value="">Tüm bölümler</option>Sanatçılar</option>Sergiler</option>Eserler</option>Fuarlar</option>Haberler</option>Yayınlar</option>İletişim</option>Diğer</option></select> <select id="lang"><option value="">TR + EN</option><option>TR</option><option>EN</option></select> <select id="state"><option value="">Tüm kayıtlar</option><option value="saved">İndirilenler</option><option value="missing">Yalnızca arşiv bağlantısı</option></select><p id="count"></p><table><thead><tr><th>Sayfa / içerik</th><th>Bölüm</th><th>Dil</th><th>Kayıt tarihi</th><th>Erişim</th></tr></thead><tbody id="rows"></tbody></table><p><button id="more">Daha fazla göster</button></p>'''
    js='''<script>const data=DATA;let limit=100;const $=id=>document.getElementById(id);const norm=s=>s.toLocaleLowerCase('tr').normalize('NFD').replace(/[\u0300-\u036f]/g,'');function render(){let q=norm($('q').value);let filtered=data.filter(r=>(!q||norm(r.title+' '+r.path).includes(q))&&(!$('section').value||r.section==$('section').value)&&(!$('lang').value||r.lang==$('lang').value)&&(!$('state').value||r.saved==($('state').value=='saved')));$('count').textContent=filtered.length+' kayıt · '+Math.min(limit,filtered.length)+' gösteriliyor';let frag=document.createDocumentFragment();filtered.slice(0,limit).forEach(r=>{let tr=document.createElement('tr'),td=document.createElement('td'),a=document.createElement('a');a.href=r.saved?r.local:r.archive;a.textContent=r.title;td.append(a,document.createElement('br'));let small=document.createElement('small');small.textContent=r.path;td.append(small);tr.append(td);[r.section,r.lang,r.date.slice(0,4)+'-'+r.date.slice(4,6)+'-'+r.date.slice(6,8),r.saved?'Çevrimdışı':'Wayback'].forEach(x=>{let td=document.createElement('td');td.textContent=x;tr.append(td)});frag.append(tr)});$('rows').replaceChildren(frag);$('more').hidden=limit>=filtered.length}['q','section','lang','state'].forEach(id=>$(id).addEventListener('input',()=>{limit=100;render()}));$('more').onclick=()=>{limit+=100;render()};render();</script>'''.replace('DATA',data)
    (OUT/'index.html').write_text(wrap('PİLEVNELİ kurtarılan site arşivi',body+js))
    pdf_body='<h1>PDF belgeler</h1><p><a href="index.html">← Arşiv dizini</a></p><ul>'+''.join('<li><a href="'+html.escape(r['file'] if r['status']=='saved' else r['archive_url'],quote=True)+'">'+html.escape(unquote(urlsplit(r['url']).path.split('/')[-1]))+'</a> · '+r['status']+'</li>' for r in pdf_entries)+'</ul>'
    (OUT/'pdfler.html').write_text(wrap('PİLEVNELİ PDF belgeler',pdf_body))
    (OUT/'OKU.txt').write_text(f'''PİLEVNELİ SITE ARŞİVİ\nHazırlanma: 1 Ekim 2026\n\nindex.html dosyasını tarayıcıda açın. ZIP indirirseniz önce tamamını bir klasöre çıkartın.\n\n{len(records)} farklı HTML sayfa adresi bulundu. {len(contents)} sayfa, {nmedia} görsel, {npdf} PDF indirildi.\n\nKAPSAM\nKaynak: web.archive.org CDX kayıtları ve erişilebilir Artlogic görsel sunucusu. Türkçe ve İngilizce bölümler dahil. Her URL için bulunan en yeni kayıt seçildi. Bazı adresler aynı içeriğin farklı URL veya galeri görünümüdür. Sayfa sayısı, benzersiz sanatçı/eser/sergi sayısı değildir.\nSayfaların kayıt tarihleri farklıdır. Arşivde bulunmayan içerikler, eksik kayıtlar, videolar ve dinamik işlevler tümüyle kurtarılamayabilir. Bu paket sitenin eksiksiz son sürümü olduğu iddiasını taşımaz.\n\nDOSYALAR\nraw/: Internet Archive'dan indirilen ham HTML.\npages/: okunabilir, bağlantıları düzenlenmiş yerel HTML sayfaları.\ntexts/: sayfa içeriklerinin düz metinleri.\nmedia/: en fazla 1600 piksel sınırında indirilen erişilebilir görseller.\npdf/: indirilen PDF belgeler.\nsayfa-listesi.csv ve inventory.json: sayfa adresleri, kayıt tarihleri, indirme durumları, hatalar.\nmedia-inventory.json ve pdf-inventory.json: medya ve PDF kaynakları, indirme durumları.\n\nÖzgün içerik ve görsellerin hakları ilgili sahiplerindedir.\n''')
    print('BUILD_DONE',len(contents),nmedia,npdf,flush=True)

if __name__=='__main__':
    import sys
    if 'pdf' in sys.argv:download_pdfs()
    else:build()
