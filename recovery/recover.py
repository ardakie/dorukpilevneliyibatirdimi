import concurrent.futures as cf
import csv, hashlib, json, re, threading, time
from pathlib import Path
from urllib.parse import urlsplit, urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs' / 'pilevneli-arsivi'
for d in ['raw', 'pages', 'texts', 'media', 'pdf']:
    (OUT / d).mkdir(parents=True, exist_ok=True)
rows = json.loads((ROOT/'work/probe-6.txt').read_text())[1:] + json.loads((ROOT/'work/latest.bin').read_text())[1:]
records = {}
for ts, url in rows:
    path = urlsplit(url).path
    if path not in records or ts > records[path]['timestamp']:
        key = hashlib.sha256(path.encode()).hexdigest()[:16]
        records[path] = dict(path=path, url=url, timestamp=ts, key=key, status='pending')
pdf_rows = json.loads((ROOT/'work/pdf.bin').read_text())[1:]
statefile = OUT/'inventory.json'
if statefile.exists():
    old = {r['path']:r for r in json.loads(statefile.read_text())}
    for p,r in records.items():
        if p in old: r.update(old[p])
lock=threading.Lock()
local=threading.local()
stop=threading.Event()
stats={'ok':0,'failed':0,'bytes':0}
def session():
    if not hasattr(local,'s'):
        local.s=requests.Session()
        local.s.headers['User-Agent']='Mozilla/5.0 (Public website archival recovery)'
    return local.s
def save_state():
    statefile.write_text(json.dumps(list(records.values()),ensure_ascii=False,indent=2))
def is_slide(p):
    return any('/'+x+'/' in p and p.split('/'+x+'/')[1].strip('/') for x in ['works','installation_shots'])
def fetch(r):
    if stop.is_set():return r
    dst=OUT/'raw'/(r['key']+'.html')
    if dst.exists() and dst.stat().st_size>500:
        r['status']='saved'; return r
    u='https://web.archive.org/web/'+r['timestamp']+'id_/'+r['url']
    try:
        resp=session().get(u,timeout=(12,35))
        resp.raise_for_status()
        data=resp.content
        if b'Wayback Machine has not archived' in data or b'Rate limit' in data or len(data)<500:
            raise ValueError('Snapshot content unavailable')
        dst.write_bytes(data)
        r.update(status='saved',bytes=len(data),archive_url=resp.url)
    except Exception as e:
        r.update(status='failed',error=str(e)[:200])
    return r
def run(items,workers,label):
    print(label,len(items),flush=True)
    done=0
    streak=0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(fetch,items):
            done+=1
            stats['ok' if r['status']=='saved' else 'failed']+=1
            streak=streak+1 if r['status']=='failed' else 0
            if streak>=30:
                stop.set()
            if done%20==0 or done==len(items):
                save_state()
                print(label,done,'/',len(items),'saved',stats['ok'],'failed',stats['failed'],flush=True)
    save_state()
    if stop.is_set():raise SystemExit('Stopped after repeated archive connection failures; saved work preserved.')
if __name__=='__main__':
    ordered=sorted(records.values(),key=lambda r:(is_slide(r['path']), not r['path'].startswith('/tr/'),len(r['path'].split('/')),r['path']))
    run([r for r in ordered if not is_slide(r['path']) and r['status']!='saved'],3,'main')
    run([r for r in ordered if is_slide(r['path']) and r['status']!='saved'],3,'detail')
    failed=[r for r in ordered if r['status']=='failed']
    if failed: run(failed,2,'retry')
    print('HTML_DONE',flush=True)
