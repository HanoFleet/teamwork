"""Fetch a Docker Official Image through the existing local proxy; verify every digest.
No daemon/global proxy changes, credentials, alternate registry, or tag substitution.
"""
import urllib.request,json,hashlib,pathlib,tarfile,gzip,io,subprocess,datetime
B=pathlib.Path(__file__).resolve().parent
repo='library/golang';tag='1.26.11-alpine'
op=urllib.request.build_opener(urllib.request.ProxyHandler({'https':'http://127.0.0.1:7897'}))
token=json.loads(op.open('https://auth.docker.io/token?service=registry.docker.io&scope=repository:'+repo+':pull',timeout=30).read())['token']
def fetch(path,accept=None):
 headers={'Authorization':'Bearer '+token}
 if accept:headers['Accept']=accept
 for n in range(2):
  try:return op.open(urllib.request.Request('https://registry-1.docker.io/v2/'+repo+'/'+path,headers=headers),timeout=90).read()
  except Exception:
   if n:raise
def verify(data,digest):assert 'sha256:'+hashlib.sha256(data).hexdigest()==digest
accept='application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'
raw=fetch('manifests/'+tag,accept);index=json.loads(raw)
index_digest='sha256:'+hashlib.sha256(raw).hexdigest()
desc=next(x for x in index['manifests'] if x.get('platform',{}).get('os')=='linux' and x['platform'].get('architecture')=='amd64')
raw=fetch('manifests/'+desc['digest'],accept);verify(raw,desc['digest']);manifest=json.loads(raw)
config=fetch('blobs/'+manifest['config']['digest']);verify(config,manifest['config']['digest']);c=json.loads(config)
archive=B/'official-golang-image.tar'
def add(t,name,data):
 info=tarfile.TarInfo(name);info.size=len(data);t.addfile(info,io.BytesIO(data))
names=[]
with tarfile.open(archive,'w') as t:
 cname=manifest['config']['digest'].split(':')[1]+'.json';add(t,cname,config)
 for n,layer in enumerate(manifest['layers']):
  data=fetch('blobs/'+layer['digest']);verify(data,layer['digest']);plain=gzip.decompress(data);verify(plain,c['rootfs']['diff_ids'][n]);name=layer['digest'].split(':')[1]+'/layer.tar';names.append(name);add(t,name,plain);print('verified layer',n+1,len(data),flush=True)
 add(t,'manifest.json',json.dumps([{'Config':cname,'RepoTags':['golang:'+tag],'Layers':names}]).encode())
proof=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),source='docker.io/'+repo+':'+tag,proxy='127.0.0.1:7897',index_digest=index_digest,platform_digest=desc['digest'],config_digest=manifest['config']['digest'],layers=[x['digest'] for x in manifest['layers']],verification='registry blob sha256 and uncompressed config diff_ids verified')
(B/'official-image-provenance.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
p=subprocess.run(['docker','load','-i',str(archive)],capture_output=True);(B/'logs/image-load.txt').write_bytes(p.stdout+p.stderr);print('docker load exit',p.returncode);p.check_returncode()
