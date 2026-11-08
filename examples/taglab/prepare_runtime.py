"""Prepare a private local runtime only after Docker is available. Never print keys."""
import json,secrets,shutil,subprocess
from pathlib import Path

def main():
 docker=shutil.which('docker')
 if not docker:raise SystemExit('Docker is unavailable. Install/start Docker Desktop with a Linux engine, then rerun. No server was started.')
 result=subprocess.run([docker,'info','--format','{{.OSType}}'],capture_output=True,text=True,timeout=20)
 if result.returncode or result.stdout.strip()!='linux':raise SystemExit('Docker Linux engine is not ready; no runtime was created.')
 path=Path(__file__).parent/'private/runtime.env';path.parent.mkdir(exist_ok=True)
 if path.exists():raise SystemExit('Runtime credentials already exist; refusing to overwrite.')
 values={'ARGILLA_USERNAME':'taglab-owner','ARGILLA_PASSWORD':secrets.token_urlsafe(24),
  'ARGILLA_API_KEY':secrets.token_urlsafe(32),'POSTGRES_PASSWORD':secrets.token_urlsafe(24)}
 with path.open('x',encoding='utf-8') as f:f.write('\n'.join(k+'='+v for k,v in values.items())+'\n')
 print(json.dumps({'docker':'ready','credentials_file':str(path),'server_started':False}))
if __name__=='__main__':main()
