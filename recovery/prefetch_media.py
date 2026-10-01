import concurrent.futures as cf
import re
import sys
from urllib.parse import urlsplit
from package_archive import OUT,media_url,identity,fetch_asset
assets={}
for f in (OUT/'raw').glob('*.html'):
    s=f.read_text(errors='replace')
    for src in re.findall(r'https://[^\s\'\"<>]+/(?:ws-pilevneli|artlogicstorage)/[^\s\'\"<>]+',s):
        src=src.rstrip(');,\\')
        u=media_url(src,'https://www.pilevneli.com/')
        if not u:continue
        if len(sys.argv)>1 and sys.argv[1] not in u:continue
        ext=urlsplit(u).path.rsplit('.',1)[-1].lower()
        if ext not in ['jpg','jpeg','png','gif','webp','svg','avif']:continue
        assets[u]=OUT/'media'/(identity(u)+'.'+ext)
print('PREFETCH',len(assets),flush=True)
success=0
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for n,(u,ok,val) in enumerate(ex.map(fetch_asset,assets.items()),1):
        success+=ok
        if n%100==0:print(n,'/',len(assets),'saved',success,flush=True)
print('PREFETCH_DONE',success,flush=True)
