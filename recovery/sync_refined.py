import html,json,re,shutil
from pathlib import Path
from package_archive import ROOT,OUT
MAIN=ROOT/'outputs/github-site';OTHER=ROOT/'outputs/github-media'
docs=MAIN/'docs'
manifest=json.loads((MAIN/'split-manifest.json').read_text())
locations=manifest['locations']
media=json.loads((OUT/'media-inventory.json').read_text())
for m in media:
    f=OUT/m['file']
    if not f.exists() or m['file'] in locations:continue
    shutil.copy2(f,docs/m['file']);locations[m['file']]=m['file']
for name in ['inventory.json','media-inventory.json','pdf-inventory.json','sayfa-listesi.csv','gorsel-listesi.csv','tum-metinler.txt','OKU.txt','pdfler.html']:shutil.copy2(OUT/name,docs/name)
shutil.copytree(OUT/'texts',docs/'texts',dirs_exist_ok=True)
shutil.copytree(OUT/'raw',MAIN/'source/raw',dirs_exist_ok=True)
if (OUT/'other-snapshots').exists():shutil.copytree(OUT/'other-snapshots',MAIN/'source/other-snapshots',dirs_exist_ok=True)
external={f:u for f,u in locations.items() if u.startswith('https:')}
for f in (OUT/'pages').glob('*.html'):
    s=f.read_text().replace('href="../index.html"','href="../arsiv.html"')
    s=re.sub(r'(?<=["\'])\.\./(media/[^"\']+)',lambda m:external.get(m.group(1),m.group(0)),s)
    (docs/'pages'/f.name).write_text(s)
archive=(OUT/'index.html').read_text()
archive=archive.replace('render();</script>','const params=new URLSearchParams(location.search);if(params.get("section"))$("section").value=params.get("section");if(params.get("q"))$("q").value=params.get("q");render();</script>')
archive=archive.replace('<h1>PİLEVNELİ · Kurtarılan site arşivi</h1>','<nav><a href="index.html">← Ana sayfa</a></nav><h1>PİLEVNELİ · Kurtarılan site arşivi</h1>')
(docs/'arsiv.html').write_text(archive)
homepage=(docs/'index.html').read_text().replace('<b>4,386</b>','<b>4,507</b>')
(docs/'index.html').write_text(homepage)
gallery=(OTHER/'docs/index.html').read_text()
start=gallery.index('const data=')+len('const data=')
old,end=json.JSONDecoder().raw_decode(gallery[start:])
items=[]
for m in media:
    if m['file'] not in locations:continue
    u=locations[m['file']]
    if not u.startswith('https:'):u='https://ardakie.github.io/dorukpilevneliyibatirdimi/'+u
    else:u=u.replace('https://ardakie.github.io/dorukpilevneliyibatirdimi-medya/','')
    items.append(dict(url=u,name=m['url'].rsplit('/',1)[-1],source=m['url']))
gallery=gallery[:start]+json.dumps(items,ensure_ascii=False).replace('</','<\\/')+gallery[start+end:]
(OTHER/'docs/index.html').write_text(gallery)
manifest['locations']=locations
manifest['sizes']=[sum(f.stat().st_size for f in (repo/'docs').rglob('*') if f.is_file()) for repo in [MAIN,OTHER]]
(MAIN/'split-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
for repo in [MAIN,OTHER]:
    p=repo/'README.md';p.write_text(p.read_text().replace('iki özel depoda','iki depoda'))
for f in ['refine_archive.py','sync_refined.py','remove_notes.py']:shutil.copy2(ROOT/'work'/f,MAIN/'recovery'/f)
print('REFINED_SYNC',manifest['sizes'],len(items),flush=True)
