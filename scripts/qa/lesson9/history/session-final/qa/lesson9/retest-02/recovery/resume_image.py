import pathlib,json,urllib.request,hashlib,tarfile,gzip,io,subprocess
B=pathlib.Path(__file__).resolve().parent;proof=json.loads((B/'official-manifest.json').read_text());m=proof['manifest'];archive=B/'official-golang-image.tar'
with tarfile.open(archive) as t:
 names=[x.name for x in t];cname=m['config']['digest'].split(':')[1]+'.json';config=json.loads(t.extractfile(cname).read())
 for n,l in enumerate(m['layers']):
  name=l['digest'].split(':')[1]+'/layer.tar'
  if name in names:
   assert 'sha256:'+hashlib.sha256(t.extractfile(name).read()).hexdigest()==config['rootfs']['diff_ids'][n]
repaired=B/'official-golang-restored.tar'
with tarfile.open(archive,'r') as src,tarfile.open(repaired,'w') as dst:
 for item in src:dst.addfile(item,src.extractfile(item))
archive=repaired
op=urllib.request.build_opener(urllib.request.ProxyHandler({'https':'http://127.0.0.1:7897'}));token=json.loads(op.open('https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/golang:pull',timeout=20).read())['token']
def add(t,name,data):
 i=tarfile.TarInfo(name);i.size=len(data);t.addfile(i,io.BytesIO(data))
with tarfile.open(archive,'a') as t:
 for n,l in enumerate(m['layers']):
  name=l['digest'].split(':')[1]+'/layer.tar'
  if name in names:continue
  data=op.open(urllib.request.Request('https://registry-1.docker.io/v2/library/golang/blobs/'+l['digest'],headers={'Authorization':'Bearer '+token}),timeout=30).read();assert 'sha256:'+hashlib.sha256(data).hexdigest()==l['digest'];plain=gzip.decompress(data);assert 'sha256:'+hashlib.sha256(plain).hexdigest()==config['rootfs']['diff_ids'][n];add(t,name,plain)
 add(t,'manifest.json',json.dumps([{'Config':cname,'RepoTags':['golang:1.26.11-alpine'],'Layers':[l['digest'].split(':')[1]+'/layer.tar' for l in m['layers']]}]).encode())
p=subprocess.run(['docker','load','-i',str(archive)],capture_output=True);(B/'logs/image-load.txt').write_bytes(p.stdout+p.stderr);p.check_returncode();print('official image restored; all diff_ids verified')
