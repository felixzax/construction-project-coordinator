"""Build, stage and verify the standalone Windows distribution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

NAME='ConstructionProjectCoordinator.exe'
PROJECT_ROOT=Path(__file__).resolve().parents[1]

def isolated_environment(platform='offscreen'):
 env=dict(os.environ)
 for name in list(env):
  if name.upper().startswith(('PYTHON','QT_','QML','CONDA','VIRTUAL_ENV')):
   env.pop(name,None)
 system_root=env.get('SystemRoot',r'C:\Windows')
 env['PATH']=os.pathsep.join([str(Path(system_root)/'System32'),system_root])
 env['QT_QPA_PLATFORM']=platform
 return env

def check_manifest(folder):
 folder=Path(folder)
 manifest=json.loads((folder/'SHA256SUMS.json').read_text(encoding='utf-8'))
 required={NAME,'README.md','CHANGELOG.md'}
 if set(manifest)!=required:raise ValueError('Unexpected release manifest contents')
 for name,expected in manifest.items():
  path=folder/name
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
   raise ValueError('Missing or changed release file: '+name)
 if any(p.is_dir() for p in folder.iterdir()):
  raise ValueError('Standalone release must not depend on companion directories')
 return folder/NAME

def stage_release(dist,output):
 dist=Path(dist);output=Path(output)
 output.mkdir(parents=True,exist_ok=True)
 for old in output.iterdir():
  if old.is_file():old.unlink()
  else:shutil.rmtree(old)
 for source in [dist/NAME,PROJECT_ROOT/'README.md',PROJECT_ROOT/'CHANGELOG.md']:
  shutil.copy2(source,output/source.name)
 manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
 (output/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 check_manifest(output)

def run_isolated(folder,platform='offscreen'):
 exe=check_manifest(folder).resolve()
 # Move to a separate working/data directory so neither source nor venv paths help.
 with tempfile.TemporaryDirectory(prefix='CPC clean working directory ') as working:
  env=isolated_environment(platform);env['CPC_DATA_DIR']=str(Path(working)/'disposable-data')
  subprocess.run([str(exe),'--smoke-test'],cwd=working,env=env,check=True,timeout=180)

def verify_zip_roundtrip(folder):
 folder=Path(folder)
 with tempfile.TemporaryDirectory(prefix='CPC ZIP roundtrip ') as working:
  zip_path=Path(working)/'portable.zip'
  with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
   for file in folder.iterdir():archive.write(file,file.name)
  with zipfile.ZipFile(zip_path) as archive:
   if archive.testzip():raise ValueError('Release ZIP integrity failed')
   extracted=Path(working)/'Desktop'/'Construction Project Coordinator – clean extract'
   archive.extractall(extracted)
  run_isolated(extracted,'offscreen')

def verify_downloaded(folder):
 # Verify the actual Actions artifact after the download-artifact step.
 folder=Path(folder)
 check_manifest(folder)
 run_isolated(folder,'offscreen')
 run_isolated(folder,'windows')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['stage','zip-check','verify']);parser.add_argument('folder');args=parser.parse_args()
 if args.action=='stage':stage_release(PROJECT_ROOT/'dist',args.folder)
 elif args.action=='zip-check':verify_zip_roundtrip(args.folder)
 else:verify_downloaded(args.folder)

if __name__=='__main__':main()
