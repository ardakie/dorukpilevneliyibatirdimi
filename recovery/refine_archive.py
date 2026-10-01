import concurrent.futures as cf
import json,re,shutil,threading
from pathlib import Path
from urllib.parse import urlsplit
import requests
from package_archive import OUT,ROOT,fetch_asset
records=json.loads((OUT/'inventory.json').read_text())
rows=json.loads((ROOT/'work/probe-6.txt').read_text())[1:]+json.loads((ROOT/'work/latest.bin').read_text())[1:]
candidates={}
for ts,u in rows:candidates.setdefault(urlsplit(u).path,set()).add((ts,u))
local=threading.local()
def recover(r):
    old=OUT/'raw'/(r['key']+'.html')
    attempts=sorted(candidates.get(r['path'],[]),reverse=True)
    for ts,u in attempts:
        if ts==r['timestamp']:continue
        try:
            if not hasattr(local,'s'):local.s=requests.Session()
            q=local.s.get('https://web.archive.org/web/'+ts+'id_/'+u,timeout=(10,25))
            q.raise_for_status()
            data=q.content
            title=re.search(rb'<title[^>]*>(.*?)</title>',data,re.S|re.I)
            if len(data)<3000 or not title or b'Coming soon' in title.group(1) or b'Natro' in title.group(1):continue
            snap=OUT/'other-snapshots';snap.mkdir(exist_ok=True)
            shutil.copy2(old,snap/(r['key']+'.'+r['timestamp']+'.html'))
            old.write_bytes(data)
            r.update(timestamp=ts,url=u,archive_url=q.url,bytes=len(data),title=title.group(1).decode(errors='replace').strip())
            return True
        except Exception:pass
    return False
placeholder=[r for r in records if r.get('title')=='Coming soon' and any(ts!=r['timestamp'] for ts,u in candidates.get(r['path'],[]))]
with cf.ThreadPoolExecutor(max_workers=3) as ex:
    restored=sum(ex.map(recover,placeholder))
root=next(r for r in records if r['path']=='/')
raw=OUT/'raw'/(root['key']+'.html')
if b'Natro' in raw.read_bytes():
    snap=OUT/'other-snapshots';snap.mkdir(exist_ok=True)
    shutil.copy2(raw,snap/(root['key']+'.'+root['timestamp']+'.html'))
    shutil.copy2(ROOT/'work/home.bin',raw)
    root.update(timestamp='20260512122528',url='https://www.pilevneli.com/',archive_url='https://web.archive.org/web/20260512122528id_/https://www.pilevneli.com/',title='PİLEVNELİ',bytes=raw.stat().st_size)
(OUT/'inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
media=json.loads((OUT/'media-inventory.json').read_text())
missing=[m for m in media if m['status']=='failed']
with cf.ThreadPoolExecutor(max_workers=4) as ex:
    attempts=list(ex.map(fetch_asset,[(m['url'].replace('static-assets.artlogic.net','artlogic-res.cloudinary.com'),OUT/m['file']) for m in missing]))
fixed=0
for m,(u,ok,val) in zip(missing,attempts):
    if ok:m.update(status='saved',download_url=u,detail=val);fixed+=1
(OUT/'media-inventory.json').write_text(json.dumps(media,ensure_ascii=False,indent=2))
print('REFINED',restored,'placeholder pages;',fixed,'additional images',flush=True)
