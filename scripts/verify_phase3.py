"""Offline Phase 3 source, privacy and no-schema-change review evidence.
Requires the approved Phase 2 git commit locally; uses fictional temporary data.
Does not fetch agency pages, submit anything, build, publish or touch live data.
"""
from pathlib import Path
import csv,hashlib,json,os,sqlite3,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cpc.store import Store
from cpc.city_permits import catalog
BASE='fcafec424ae7d0c255b5103825e6567d8b3109af'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def schema(db):return [list(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
def rows(db):return {r[0]:[list(v) for v in db.execute(f'SELECT * FROM {r[0]} ORDER BY rowid')] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
def main():
 from PySide6.QtWidgets import QApplication
 from PySide6.QtGui import QPdfWriter,QPainter
 from docx import Document
 app=QApplication.instance() or QApplication([]);out=ROOT/'review/phase3';out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='cpc-phase3-evidence-') as folder:
  temp=Path(folder);old=temp/'phase2-code';old.mkdir()
  for name in subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'cpc'],cwd=ROOT,text=True).splitlines():
   if name.endswith('.py'):
    path=old/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(subprocess.check_output(['git','show',f'{BASE}:{name}'],cwd=ROOT))
  original=temp/'phase2-original.sqlite3';env=dict(os.environ);env.pop('PYTHONPATH',None)
  program="""from cpc.store import Store
import sys
s=Store(sys.argv[1]);s.seed();p=s.all('projects')[0]['id'];s.set_hidden_sections(p,{'Meetings','Budgets'});s.set_section_order(p,'sidebar',['Projects','Dashboard']);s.set_section_order(p,'hidden',['Budgets','Meetings']);s.set_regulatory_settings(p,cgp_subject='No',jurisdiction='Other');s.db.close()
"""
  subprocess.run([sys.executable,'-c',program,str(original)],cwd=old,env=env,check=True)
  source_sha=sha(original);copy=temp/'phase3-copy.sqlite3'
  with sqlite3.connect(original) as source,sqlite3.connect(copy) as dest:
   before=schema(source);before_rows=rows(source);source.backup(dest)
  s=Store(copy);assert schema(s.db)==before and rows(s.db)==before_rows and sha(original)==source_sha
  no_schema=dict(phase2_commit=BASE,schema_version=12,all_schema_sql_equal=True,all_original_rows_equal=True,tables_added=[],columns_added=[],original_database_sha256=source_sha,original_hash_unchanged=sha(original)==source_sha,hidden_settings_preserved=True,section_order_preserved=True,foreign_key_check=[list(r) for r in s.db.execute('PRAGMA foreign_key_check')])
  p=s.all('projects')[0]['id'];record=s.all('registers')[0]['id']
  # Ordinary signed/stamped PDF (fictional ink representation, no certificate).
  pdf=temp/'signed-permit.pdf';writer=QPdfWriter(str(pdf));painter=QPainter(writer);painter.drawText(200,400,'FICTIONAL PERMIT - APPROVED TEST STAMP');painter.drawText(200,700,'Signed: Fictional Engineer');painter.drawLine(200,750,650,675);painter.end();del writer
  word=temp/'ordinary-permit-form.docx';doc=Document();doc.add_paragraph('Fictional permit form. Do not include passwords.');doc.save(word)
  mention=temp/'password-mention.txt';mention.write_text('Use a password manager. Never share your password or portal login details.',encoding='utf-8')
  instruction=temp/'instruction-false-positive.txt';instruction.write_text('Password: do not put one in this form.',encoding='utf-8')
  cases=[]
  for path,expected in [(pdf,True),(word,True),(mention,True),(instruction,False)]:
   try:
    fid=s.import_finance_files('registers',record,[path])[0];dest=temp/('copy-'+path.name);s.save_finance_copy(fid,dest)
   except ValueError as error:
    assert not expected;cases.append(dict(file=path.name,accepted=False,legitimate_content=True,known_false_positive=True,reason=str(error)))
   else:
    assert expected and sha(path)==sha(dest);cases.append(dict(file=path.name,accepted=True,original_sha256=sha(path),download_sha256=sha(dest),bytes_identical=True))
  s.db.close()
  (out/'schema-and-privacy.json').write_text(json.dumps(dict(no_schema_change=no_schema,privacy_file_cases=cases,limits='Synthetic ordinary files only. No certificate validation or PDF content inspection. Assignment-like harmless text can be blocked. No DLP guarantee.'),indent=2)+'\n')
 with (out/'source-revision-register.csv').open('w',newline='',encoding='utf-8-sig') as f:
  data=Store.__new__(Store).city_source_register();writer=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');writer.writeheader();writer.writerows(data)
 data=catalog();(out/'sources-and-conflicts.json').write_text(json.dumps({k:data[k] for k in ('verified_date','sources','conflicts')},indent=2)+'\n')
 print(json.dumps(dict(schema=12,tables_added=0,columns_added=0,existing_rows_and_preferences_preserved=True,source_items=len(data['items']),sources=len(data['sources']),source_conflicts_or_qualifications=len(data['conflicts']),privacy_file_cases=cases),indent=2))
if __name__=='__main__':main()
