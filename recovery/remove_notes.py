import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def clean(p):
    s=p.read_text()
    s=re.sub(r'<div class="notice">.*?</div>','',s,flags=re.S)
    s=re.sub(r'<p>Türkçe ve İngilizce sayfalar, sanatçılar, sergiler, eserler, fuarlar, haberler ve yayınlar\. Kaynak:.*?</p>','<p>Sanatçılar, sergiler, eserler, fuarlar, haberler ve yayınlar.</p>',s,flags=re.S)
    s=re.sub(r'<footer><p>Bu bağımsız arşiv,.*?</p>','<footer><p>PİLEVNELİ · Site arşivi</p>',s,flags=re.S)
    s=s.replace('Erişilemeyen web sitesinden kurtarılan içerikleri keşfedin.','İçerikleri keşfedin.')
    s=s.replace("r.saved?'Çevrimdışı':'Wayback'","r.saved?'Kaydedildi':'Wayback'")
    p.write_text(s)
for directory in ['outputs/pilevneli-arsivi/pages','outputs/github-site/docs/pages']:
    for f in (ROOT/directory).glob('*.html'):clean(f)
for filename in ['outputs/pilevneli-arsivi/index.html','outputs/github-site/docs/index.html','outputs/github-site/docs/arsiv.html']:
    p=ROOT/filename
    if p.exists():clean(p)
print('VISIBLE_NOTES_REMOVED',flush=True)
