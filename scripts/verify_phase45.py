"""Offline review evidence for schema preservation, manual arithmetic and sources.
Requires the approved Phase 3 commit locally. Uses temporary fictional data only.
"""
from pathlib import Path
from datetime import date
import csv,hashlib,json,os,sqlite3,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cpc.store import Store
from cpc.water_board import water_catalog
from cpc.city_permits import catalog,metadata,CITY
BASE='89fe3e5d25a2ac6081f4a87ae2cc61d9206768eb'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def schema(db):return [list(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
def snapshot(db):return {r[0]:[list(v) for v in db.execute(f'SELECT * FROM {r[0]} ORDER BY rowid')] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
def main():
 out=ROOT/'review/phase45';out.mkdir(parents=True,exist_ok=True);results={}
 with tempfile.TemporaryDirectory(prefix='cpc-phase45-') as folder:
  temp=Path(folder);old=temp/'old';old.mkdir()
  for name in subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'cpc'],cwd=ROOT,text=True).splitlines():
   if name.endswith(('.py','.json')):
    p=old/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',f'{BASE}:{name}'],cwd=ROOT))
  for kind in ('empty','populated'):
   path=temp/(kind+'-original.sqlite3');env=dict(os.environ);env.pop('PYTHONPATH',None)
   program="""from cpc.store import Store
from cpc.city_permits import CITY
import sys
s=Store(sys.argv[1])
if sys.argv[2]=='populated':
 s.seed();p=s.all('projects')[0]['id'];s.set_hidden_sections(p,{'Meetings','Budgets'});s.set_section_order(p,'sidebar',['Projects','Dashboard']);s.set_section_order(p,'hidden',['Budgets','Meetings']);s.set_regulatory_settings(p,cgp_subject='Yes',jurisdiction=CITY)
 r=s.configure_city_permit(dict(project_id=p,title='Prior City permit',jurisdiction_key=CITY,occupancy_type='Commercial',work_type='New Construction',permit_family='Building'));s.add_city_standard(r)
 s.save('reg_wb_sites',dict(project_id=p,wdid='Fictional WDID'))
s.db.close()
"""
   subprocess.run([sys.executable,'-c',program,str(path),kind],cwd=old,env=env,check=True);original_hash=sha(path)
   copy=temp/(kind+'-copy.sqlite3')
   with sqlite3.connect(path) as src,sqlite3.connect(copy) as dst:before_schema=schema(src);before=snapshot(src);src.backup(dst)
   s=Store(copy);assert schema(s.db)==before_schema and snapshot(s.db)==before and sha(path)==original_hash
   backup=temp/(kind+'-backup.sqlite3');s.backup(backup);s.save('projects',dict(name='Temporary added project'));s.restore(backup);assert snapshot(s.db)==before
   results[kind]=dict(schema=12,added_tables=[],added_columns=[],all_schema_sql_equal=True,all_original_rows_equal=True,hidden_settings_preserved=True,section_order_preserved=True,original_file_sha256_before=original_hash,original_file_sha256_after=sha(path),backup_restore_passed=True,foreign_key_check=[list(r) for r in s.db.execute('PRAGMA foreign_key_check')])
   if kind=='populated':
    pid=s.all('projects')[0]['id'];sid=s.water_site(pid)['id'];s.save('reg_wb_sites',dict(construction_start='2020-11-01',final_stabilization='2022-12-28'),sid);s.generate_water_periods(sid)
    for r,v in zip(s.water_periods(sid),['45.49','45.49','14.16']):s.save_r_period(dict(r_value_text=v),r['id'])
    results['requested_r_fixture']=s.water_r_summary(sid);assert results['requested_r_fixture']['total']=='105.14'
    person=s.save('contacts',dict(name='Fictional Seal Engineer'));rid=s.configure_city_permit(dict(project_id=pid,title='Seal coordination permit',jurisdiction_key=CITY,occupancy_type='Commercial',work_type='New Construction',permit_family='Building',seal_contact_id=person,seal_discipline='Structural'))
    results['seal']=dict(name=metadata(s.city_details(rid))['seal_person_name'],appears_in_report='Fictional Seal Engineer' in s.report(pid),signature_or_certificate_stored=False)
   s.db.close()
 (out/'schema-backup-and-golden.json').write_text(json.dumps(results,indent=2)+'\n')
 water=water_catalog();city=catalog();register=[]
 for module,data in [('City/County',city),('Water Board',water)]:
  for item in data['items']:
   src=data['sources'][item['source']]
   register.append(dict(module=module,item_key=item['key'],kind=item.get('kind',item.get('check_kind','')),title=item['title'],source_document=src['title'],source_revision=src.get('document_revision_date') or src['title']+' — exact day not stated / verify',source_link=src['url'],last_verified_date=item.get('last_verified_date',data['verified_date']),if_applicable=item.get('if_applicable',1),verify_label=item['verify_label'],source_conflicts=src.get('conflict_notes',''),source_sha256=src.get('sha256','')))
 with (out/'source-revision-register.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(register[0]),lineterminator='\n');w.writeheader();w.writerows(register)
 (out/'water-sources-and-conflicts.json').write_text(json.dumps({k:water[k] for k in ('verified_date','sources','conflicts')},indent=2)+'\n')
 print(json.dumps(dict(schema=12,empty_and_populated_preserved=True,backup_restore=True,source_items=len(register),water_sources=len(water['sources']),water_conflicts=len(water['conflicts']),r_total='105.14',seal_name='Fictional Seal Engineer'),indent=2))
if __name__=='__main__':main()
