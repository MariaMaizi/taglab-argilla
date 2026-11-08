from pathlib import Path
import yaml

def test_only_upstream_runs_release_and_cloud_jobs():
 root=Path(__file__).resolve().parents[3]/'.github/workflows'
 count=0
 for p in root.glob('*.yml'):
  if p.name=='taglab-tests.yml':continue
  doc=yaml.load(p.read_text(encoding='utf-8-sig'),Loader=yaml.BaseLoader)
  for name,job in doc.get('jobs',{}).items():
   assert "github.repository == 'argilla-io/argilla'" in job.get('if',''),(p.name,name)
   count+=1
 assert count>=10
