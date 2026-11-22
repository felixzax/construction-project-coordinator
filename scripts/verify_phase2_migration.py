"""Reproducible Phase 2 copy/migration/rollback evidence; never opens live data.
Run from the repository: python scripts/verify_phase2_migration.py
Requires the baseline git commit locally for the separate old-code rollback check.
"""
from pathlib import Path
import csv
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cpc.store import Store
from cpc.regulatory_schema import REG_FIELDS
BASE='6ed7592190c940ed21f3819ce2e31a626e819f94'

def rows(db):
 names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT GLOB 'reg_*' ORDER BY name")]
 return {n:[list(r) for r in db.execute(f'SELECT * FROM {n} ORDER BY rowid')] for n in names}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def record_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def main():
 out=ROOT/'review/phase2';out.mkdir(parents=True,exist_ok=True);evidence={'baseline_commit':BASE,'python':sys.version,'cases':{}}
 with tempfile.TemporaryDirectory(prefix='cpc-phase2-verification-') as temp:
  work=Path(temp);old=work/'old-application';old.mkdir()
  files=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'cpc'],cwd=ROOT,text=True).splitlines()
  for name in files:
   if not name.endswith('.py'):continue
   target=old/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(subprocess.check_output(['git','show',f'{BASE}:{name}'],cwd=ROOT))
  for kind in ('empty','populated'):
   folder=work/kind;folder.mkdir();source=folder/'untouched-source.sqlite3'
   with sqlite3.connect(source) as db:
    db.executescript((ROOT/'tests/fixtures'/f'schema11_{kind}.sql').read_text())
    # Include a real ordinary signed/stamped attachment in the populated copy.
    attachment=None
    if kind=='populated':
     attachment=folder/'signed-stamped-approval.pdf';attachment.write_bytes(b'%PDF-1.4 fictional signed/stamped approval\n%%EOF\n')
     db.execute('UPDATE versions SET file_path=? WHERE id=1',(str(attachment),));db.commit()
    before=rows(db)
   original_sha=sha(source);copy=folder/'migration-copy.sqlite3'
   with sqlite3.connect(source) as src,sqlite3.connect(copy) as dst:src.backup(dst)
   migrated=Store(copy);assert rows(migrated.db)==before
   safety=Path(str(copy)+'.before-v1.12.0.sqlite3');assert safety.exists()
   with sqlite3.connect(safety) as db:
    assert db.execute('PRAGMA user_version').fetchone()[0]==11 and rows(db)==before
    restored=folder/'rollback-restored.sqlite3'
    with sqlite3.connect(restored) as dest:db.backup(dest)
   rollback_program="""import json,sys
from cpc.store import Store
s=Store(sys.argv[1])
assert s.db.execute('PRAGMA user_version').fetchone()[0]==11
assert not s.rows("SELECT name FROM sqlite_master WHERE name GLOB 'reg_*'")
assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print(json.dumps({'opened_by_schema11_application':True,'schema':11,'integrity':'ok'}))
s.db.close()
"""
   env=dict(os.environ);env.pop('PYTHONPATH',None)
   result=subprocess.run([sys.executable,'-c',rollback_program,str(restored)],cwd=old,env=env,capture_output=True,text=True,check=True)
   with sqlite3.connect(restored) as db:assert rows(db)==before
   after=rows(migrated.db);assert sha(source)==original_sha
   item=dict(source_sha256_before=original_sha,source_sha256_after=sha(source),canonical_rows_sha256_before=record_hash(before),canonical_rows_sha256_after=record_hash(after),schema_after=12,safety_copy_created=True,safety_copy_schema=11,safety_copy_sha256=sha(safety),all_original_rows_equal=True,all_original_columns_unchanged=True,original_row_counts={k:len(v) for k,v in before.items()},hidden_section_rows_before=before['project_sections'],hidden_section_rows_after=after['project_sections'],section_order_rows_before=before['project_section_order'],section_order_rows_after=after['project_section_order'],all_21_regulatory_tables_empty=all(not migrated.all(t) for t in REG_FIELDS),foreign_key_check=[list(r) for r in migrated.db.execute('PRAGMA foreign_key_check')],integrity=migrated.db.execute('PRAGMA integrity_check').fetchone()[0],rollback=json.loads(result.stdout))
   with sqlite3.connect(source) as db:
    for name in before:assert [tuple(r) for r in db.execute(f'PRAGMA table_info({name})')]==[tuple(r) for r in migrated.db.execute(f'PRAGMA table_info({name})')]
   if attachment:
    item['attachment_bytes_preserved']=attachment.read_bytes()==b'%PDF-1.4 fictional signed/stamped approval\n%%EOF\n'
    item['attachment_reference_preserved']=migrated.versions(1)[-1]['file_path']==str(attachment)
    assert item['attachment_bytes_preserved'] and item['attachment_reference_preserved']
   # Restore through the current UI/backend path also re-upgrades the copy safely.
   migrated.restore(safety);assert rows(migrated.db)==before;item['current_app_restore_and_reupgrade_preserved_rows']=True
   if kind=='empty':
    with (out/'schema-inventory.csv').open('w',newline='') as f:
     writer=csv.writer(f);writer.writerow(['table','column','type','not_null','default','primary_key'])
     for name in REG_FIELDS:
      for r in migrated.db.execute(f'PRAGMA table_info({name})'):writer.writerow([name,*list(r)[1:]])
   migrated.db.close();evidence['cases'][kind]=item
 (out/'migration-and-rollback.json').write_text(json.dumps(evidence,indent=2)+'\n')
 print(json.dumps({k:{'preserved':v['all_original_rows_equal'],'safety_schema':v['safety_copy_schema'],'rollback':v['rollback']} for k,v in evidence['cases'].items()},indent=2))
if __name__=='__main__':main()
