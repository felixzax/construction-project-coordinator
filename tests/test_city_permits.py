"""Phase 3 tests: isolation, editable templates, warnings and ordinary Files."""
from pathlib import Path
import hashlib
import json
import sqlite3
import pytest
from cpc.store import Store
from cpc.city_permits import CITY,COUNTY,OTHER,catalog,metadata

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()
@pytest.fixture
def pid(store):return store.save('projects',dict(name='Fictional permit project'))
def config(pid,jurisdiction=CITY,use='Commercial',work='New Construction',family='Building'):
 return dict(project_id=pid,title='Fictional permit',jurisdiction_key=jurisdiction,occupancy_type=use,work_type=work,permit_family=family,currency='USD')
def permit(store,pid,**kw):
 rid=store.configure_city_permit(config(pid,**kw));store.add_city_standard(rid);return rid


def test_schema12_only_and_catalog_not_seeded_at_startup(store):
 assert store.db.execute('PRAGMA user_version').fetchone()[0]==12
 assert not store.all('reg_sources') and not store.all('reg_templates') and not store.all('reg_template_items')
 expected=Path(__file__).parents[1]/'review/phase2/schema-inventory.csv'
 import csv
 with expected.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
 actual={(r[0],c[1]) for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name GLOB 'reg_*'") for c in store.db.execute(f'PRAGMA table_info({r[0]})')}
 assert actual=={(r['table'],r['column']) for r in rows}

@pytest.mark.parametrize('jurisdiction',[CITY,COUNTY,OTHER])
@pytest.mark.parametrize('use',['Residential','Commercial'])
def test_jurisdiction_isolation_and_other_has_no_imports(store,pid,jurisdiction,use):
 rid=permit(store,pid,jurisdiction=jurisdiction,use=use)
 rows=store.city_checklist(rid);steps=store.city_steps(rid)
 expected='city.' if jurisdiction==CITY else 'county.'
 assert all(r['template_key'].startswith(expected) for r in rows)
 assert all(r['step_key'].startswith(expected) for r in steps)
 if jurisdiction==OTHER:assert rows==steps==[]
 if jurisdiction==COUNTY:
  assert not any('CDD-' in r['title'] for r in rows)
  if use=='Commercial':
   allowed={'AP-36','AP-17','AP-34','ST-13','ST-14','ST-16','ST-17','EC-07.1','CO-50','AP-24','OA-24'}
   forms=[r['template_key'].removeprefix('county.form.') for r in rows if r['template_key'].startswith('county.form.')]
   assert set(forms)<=allowed


def test_add_is_idempotent_keeps_edits_checked_hidden_deleted_and_files(store,pid,tmp_path):
 rid=permit(store,pid);rows=store.city_checklist(rid);item=rows[0];step=store.city_steps(rid)[0]
 store.save_city_checklist(rid,dict(title='User edited title',completed=1,notes='User note'),item['id'])
 store.save('reg_tracker_steps',dict(title='Edited step',status='Waiting on Agency'),step['id'])
 store.set_city_item_hidden('checklist',rows[1]['id'],True)
 file=tmp_path/'plan.txt';file.write_text('ordinary plan note');fid=store.import_finance_files('permit_requirements',item['id'],[file])[0]
 deleted=rows[2];backup=store.delete_city_item('checklist',deleted['id']);assert backup.is_file()
 before=(len(store.all('permit_requirements')),len(store.all('reg_tracker_steps')),len(store.all('reg_manual_charges')))
 assert store.add_city_standard(rid)==0
 assert before==(len(store.all('permit_requirements')),len(store.all('reg_tracker_steps')),len(store.all('reg_manual_charges')))
 edited=next(r for r in store.city_checklist(rid) if r['id']==item['id']);assert edited['title']=='User edited title' and edited['completed']==1
 assert any(r['id']==rows[1]['id'] for r in store.city_checklist(rid,True)) and not any(r['id']==rows[1]['id'] for r in store.city_checklist(rid))
 assert store.city_steps(rid)[0]['title']=='Edited step'
 assert store.checked_finance_file(fid)[1].read_bytes()==file.read_bytes()
 assert store.all('reg_template_tombstones')
 # Charge titles and notes are editable without breaking stable identity.
 charge=store.city_charges(rid)[0];store.save('reg_manual_charges',dict(title='Edited charge',notes='Edited manual note'),charge['id']);assert store.add_city_standard(rid)==0


def test_context_swap_confirmation_keeps_user_items_and_prior_checks(store,pid,tmp_path):
 rid=permit(store,pid);city=store.city_checklist(rid)[0];store.set_requirement_completed(city['id'],True)
 manual=store.save_city_checklist(rid,dict(title='User supplied requirement',completed=1))
 step=store.city_steps(rid)[0];store.set_city_item_hidden('tracker',step['id'],True)
 snapshot=store.city_details(rid);rows_before=store.all('permit_requirements')
 with pytest.raises(ValueError,match='Confirm'):store.configure_city_permit(config(pid,COUNTY),rid)
 assert store.city_details(rid)==snapshot and store.all('permit_requirements')==rows_before
 store.configure_city_permit(config(pid,COUNTY),rid,confirmed=True)
 active=store.city_checklist(rid);assert any(r['id']==manual and r['completed']==1 for r in active)
 assert all(r['origin']!='Template' or r['template_key'].startswith('county.') for r in active)
 assert not any('CDD-' in r['title'] for r in store.permit_requirements(rid))
 assert not store.city_charges(rid)
 store.configure_city_permit(config(pid,CITY),rid,confirmed=True)
 assert next(r for r in store.city_checklist(rid) if r['id']==city['id'])['completed']==1
 assert not any(r['id']==step['id'] for r in store.city_steps(rid))
 assert any(r['id']==step['id'] for r in store.city_steps(rid,True))
 assert not store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_same_jurisdiction_work_swap_keeps_matching_checked_items(store,pid):
 rid=permit(store,pid,use='Residential');r=next(x for x in store.city_checklist(rid) if x['template_key']=='city.check.application');store.set_requirement_completed(r['id'],True)
 store.configure_city_permit(config(pid,CITY,'Residential','Remodel / TI'),rid,True)
 rows=store.city_checklist(rid);assert next(x for x in rows if x['id']==r['id'])['completed']==1
 assert any(x['template_key']=='city.form.0253' for x in rows) and not any(x['template_key']=='city.form.0312' for x in rows)


def test_deleted_tracker_is_not_resurrected_after_swap(store,pid):
 rid=permit(store,pid);r=store.city_steps(rid)[0];store.delete_records([('reg_tracker_steps',r['id'])])
 store.configure_city_permit(config(pid,COUNTY),rid,True);store.configure_city_permit(config(pid,CITY),rid,True)
 assert r['step_key'] not in [s['step_key'] for s in store.city_steps(rid,True)]

@pytest.mark.parametrize('family',['Engineering','Planning','Operational Permit Inspections','Fire Code Enforcement','Fire (verify district)'])
def test_optional_types_have_no_imported_checklist(store,pid,family):
 rid=permit(store,pid,family=family);assert store.city_checklist(rid)==[] and store.city_steps(rid)==[]


def test_city_fire_is_separate_from_building_and_county(store,pid):
 rid=permit(store,pid,family='Fire Development Services')
 assert len(store.city_steps(rid))==7 and all('city.fire.' in r['step_key'] for r in store.city_steps(rid))
 assert not any('CDD-' in r['title'] for r in store.city_checklist(rid))
 other=permit(store,pid,jurisdiction=COUNTY,family='Fire Development Services');assert store.city_steps(other)==[]


def test_city_record_one_to_one_and_cross_permit_rejected(store,pid):
 rid=permit(store,pid);sub=store.save('reg_city_records',dict(project_id=pid,permit_register_id=rid,record_kind='SUB',reference='SUB-fictional'))
 record=store.save('reg_city_records',dict(project_id=pid,permit_register_id=rid,record_kind='COM',reference='COM-1234567',parent_sub_id=sub))
 with pytest.raises(sqlite3.IntegrityError):store.save('reg_city_records',dict(project_id=pid,permit_register_id=rid,record_kind='RES',parent_sub_id=sub))
 with pytest.raises(ValueError):store.save('reg_city_records',dict(record_kind='PLN'),sub)
 other=permit(store,pid)
 with pytest.raises(ValueError):store.save('reg_city_records',dict(project_id=pid,permit_register_id=other,record_kind='MP',parent_sub_id=sub))
 county=permit(store,pid,jurisdiction=COUNTY)
 with pytest.raises(ValueError):store.save('reg_city_records',dict(project_id=pid,permit_register_id=county,record_kind='SUB'))


def test_cycles_disciplines_and_city_warning_logic(store,pid):
 rid=permit(store,pid);cycle=store.save('reg_review_cycles',dict(project_id=pid,register_id=rid,cycle_no=2,stage='Review'))
 assert store.add_city_disciplines(cycle)==12 and store.add_city_disciplines(cycle)==0
 row=store.all('reg_cycle_reviews')[0];store.save('reg_cycle_reviews',dict(notes='Keep engineer response'),row['id']);store.add_city_disciplines(cycle);assert store.all('reg_cycle_reviews')[0]['notes']=='Keep engineer response'
 warnings=store.city_cycle_warnings(rid,4,'Review');assert any('CDD-0270' in x for x in warnings) and any('hourly' in x for x in warnings) and any('Plan Check Wait' in x for x in warnings)
 assert not any('Wait for Plan Check Wait' in x for x in store.city_cycle_warnings(rid,2,'Plan Check Wait'))
 county=permit(store,pid,jurisdiction=COUNTY);cycle2=store.save('reg_review_cycles',dict(project_id=pid,register_id=county,cycle_no=1))
 with pytest.raises(ValueError):store.add_city_disciplines(cycle2)

@pytest.mark.parametrize('filename,cycle,basis,prefix,valid',[('120 Main-CYC1-APP.pdf',1,'Address','',True),('000-0000-000-0000-CYC1-PLANS.pdf',1,'APN','',True),('000-000-000-CYC1-PLANS.pdf',1,'APN','',False),('Model-Bldg1-CYC1-SUPP.pdf',1,'Master Plan','Model-Bldg1',True),('COM-1234567-CYC2-REPLY.pdf',2,'Address','',True),('RES-123456-CYC2-PLANS.pdf',2,'Address','',False),('COM-1234567-CYC1-REPLY.pdf',1,'Address','',False),('COM-1234567-CYC3-APP.pdf',2,'Address','',False),('plans.docx',1,'Address','',False)])
def test_city_file_name_patterns(store,pid,tmp_path,filename,cycle,basis,prefix,valid):
 rid=permit(store,pid);path=tmp_path/filename;path.write_bytes(b'ordinary sample')
 warnings=store.city_file_warnings(rid,path,cycle,basis,prefix)
 assert (not any('Verify City file naming' in x for x in warnings))==valid


def test_editable_file_limits_are_decimal_warning_only(store,pid,tmp_path):
 rid=permit(store,pid);f=tmp_path/'120 Main-CYC1-APP.pdf';f.write_bytes(b'x'*1001)
 store.set_city_file_limits(rid,dict(APP='0.001',PLANS='300',SUPP='150',REPLY=''))
 warnings=store.city_file_warnings(rid,f);assert any('exceeds editable' in x for x in warnings)
 assert f.stat().st_size==1001 # no rewrite, upload or deletion
 for invalid in ('-1','NaN','Infinity','words'):
  with pytest.raises(ValueError):store.set_city_file_limits(rid,dict(APP=invalid))
 assert any('SUB' in x for x in store.city_file_warnings(rid,f,upload_record_kind='COM'))
 county=permit(store,pid,jurisdiction=COUNTY);assert not any('APP' in x for x in store.city_file_warnings(county,f))


def test_revision_helper_never_decides_or_submits(store,pid):
 rid=permit(store,pid)
 assert 'REPLY' in store.city_revision_guidance(rid,'No','No')
 assert 'new separate permit' in store.city_revision_guidance(rid,'Yes','Yes')
 assert 'unknown' in store.city_revision_guidance(rid,'Yes','Unknown')
 for deferred in (True,False):
  text=store.city_revision_guidance(rid,'Yes','No',deferred);assert all(x in text for x in ('CDD-0269','delta','same licensed','nothing'))
 assert not store.all('reg_filings')


def test_sources_register_every_item_and_known_conflicts(store):
 rows=store.city_source_register();assert len(rows)==109
 for r in rows:
  assert r['source_document'] and r['source_revision_date'] and r['last_verified_date'] and r['source_sha256']
  assert r['source_link'].startswith(('https://www.cityofsacramento.gov/','https://development.saccounty.gov/'))
  assert r['jurisdiction'] in (CITY,COUNTY) and 'Elk Grove' not in r['item']
 assert len(catalog()['conflicts'])==5 and any('400 MB' in c['description'] and '50 MB' in c['description'] for c in catalog()['conflicts'])
 county=[r for r in rows if r['jurisdiction']==COUNTY and r['kind']=='Checklist'];assert any(r['verification']=='Verify' for r in county)


def test_ordinary_signed_pdf_word_and_password_mention_pass_files(store,pid,tmp_path):
 from PySide6.QtWidgets import QApplication
 from PySide6.QtGui import QPdfWriter,QPainter
 from docx import Document
 app=QApplication.instance() or QApplication([])
 pdf=tmp_path/'signed-stamped-permit.pdf';writer=QPdfWriter(str(pdf));painter=QPainter(writer);painter.drawText(200,400,'FICTIONAL PERMIT - APPROVED TEST STAMP');painter.drawText(200,700,'Signed: Fictional Engineer');painter.drawLine(200,750,650,675);painter.end();del writer
 word=tmp_path/'permit-form.docx';doc=Document();doc.add_paragraph('Fictional permit form. Do not include passwords.');doc.save(word)
 text=tmp_path/'office-instructions.txt';text.write_text('Use a password manager. Never share your password or portal login details.',encoding='utf-8')
 rid=permit(store,pid)
 for path in (pdf,word,text):
  fid=store.import_finance_files('registers',rid,[path])[0];out=tmp_path/('copy-'+path.name);store.save_finance_copy(fid,out);assert hashlib.sha256(out.read_bytes()).digest()==hashlib.sha256(path.read_bytes()).digest()
 # Report conservative known false positive rather than imply semantic DLP.
 instruction=tmp_path/'password-instruction.txt';instruction.write_text('Password: do not put one in this form.',encoding='utf-8')
 with pytest.raises(ValueError):store.import_finance_files('registers',rid,[instruction])


def test_ui_city_screens_and_swap_cancel_are_reviewable(store,pid,monkeypatch):
 from PySide6.QtWidgets import QApplication,QMessageBox
 from cpc.ui import Window,Form
 app=QApplication.instance() or QApplication([]);rid=permit(store,pid);w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(pid));w.city_permit_select.setCurrentIndex(w.city_permit_select.findData(rid))
 assert [w.city_inner_tabs.tabText(i) for i in range(w.city_inner_tabs.count())]==['Tracker','Checklist','Review Cycles','City Records','Manual Charges','File checks','Revision guidance']
 assert w.city_tables['Checklist'].rowCount()>0 and w.city_tables['Tracker'].rowCount()==12
 w.city_filters['Checklist'].setText('no-such-item');assert not w.city_rows['Checklist'];w.city_filters['Checklist'].clear()
 def fake_exec(form):
  form.inputs['jurisdiction_key'].setCurrentText(COUNTY)
  with pytest.raises(ValueError,match='cancelled'):form.persist(form.values())
  return 0
 monkeypatch.setattr(Form,'exec',fake_exec);monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.No)
 w.edit_city_config(True);assert store.city_details(rid)['jurisdiction_key']==CITY;w.close()


def test_opt_in_existing_legacy_permit_is_explicit_and_synchronizes_jurisdiction(store,pid):
 rid=store.save('registers',dict(project_id=pid,title='Legacy',record_type='Permit',jurisdiction_type='City & County',jurisdiction_name='Legacy mixed jurisdiction'))
 item=store.save('permit_requirements',dict(register_id=rid,title='User original requirement',completed=1))
 store.configure_city_permit(config(pid,COUNTY),rid)
 parent=next(r for r in store.all('registers') if r['id']==rid)
 assert parent['jurisdiction_type']=='County' and parent['jurisdiction_name']==COUNTY
 assert store.permit_requirements(rid)[0]['id']==item and store.permit_requirements(rid)[0]['completed']==1
 with pytest.raises(ValueError):store.save('registers',dict(jurisdiction_name='Another city'),rid)


def test_context_swap_failure_rolls_back_all_original_and_generated_rows(store,pid,monkeypatch):
 rid=permit(store,pid);before={t:store.rows(f'SELECT * FROM {t} ORDER BY id') for t in ('registers','reg_permit_details','permit_requirements','reg_requirement_details','reg_tracker_steps','activity')}
 original=store._city_put
 def fail(table,values,row_id=None):
  if table=='reg_templates' and values.get('jurisdiction_key')==COUNTY:raise RuntimeError('Simulated failure')
  return original(table,values,row_id)
 monkeypatch.setattr(store,'_city_put',fail)
 with pytest.raises(RuntimeError):store.configure_city_permit(config(pid,COUNTY),rid,True)
 assert all(store.rows(f'SELECT * FROM {t} ORDER BY id')==rows for t,rows in before.items())


def test_existing_manual_checklist_hiding_and_sources_are_editable(store,pid):
 rid=permit(store,pid);manual=store.save_city_checklist(rid,dict(title='Verify local detail',verify_label='Verify'))
 store.set_city_item_hidden('checklist',manual,True);assert manual not in [r['id'] for r in store.city_checklist(rid)]
 store.set_city_item_hidden('checklist',manual,False)
 item=next(r for r in store.city_checklist(rid) if r['id']==manual);assert item['verify_label']=='Verify'
 source=store.save('reg_sources',dict(title='User verified official reference',url='https://www.cityofsacramento.gov/'))
 store.save_city_checklist(rid,dict(title='Verified with team',source_id=source,last_verified_date='2026-11-20',verify_label='Verify applicability'),manual)
 assert next(r for r in store.city_checklist(rid) if r['id']==manual)['source_document']=='User verified official reference'


def test_ci_test_job_cannot_build_or_publish_release():
 workflow=(Path(__file__).parents[1]/'.github/workflows/windows.yml').read_text()
 tests=workflow.split('  windows-tests:',1)[1].split('\n  windows:',1)[0]
 assert 'python -m pytest' in tests and 'windows-latest' in tests
 assert 'PyInstaller' not in tests and 'portable_build.py' not in tests
 release=workflow.split('\n  windows:',1)[1]
 assert "if: github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main' && inputs.build_release == true" in release
 assert 'default: false' in workflow


def test_city_record_files_warn_about_sub_before_opening_local_manager(store,pid,monkeypatch):
 from PySide6.QtWidgets import QApplication,QMessageBox
 from cpc.ui import Window
 app=QApplication.instance() or QApplication([]);rid=permit(store,pid)
 store.save('reg_city_records',dict(project_id=pid,permit_register_id=rid,record_kind='COM',reference='COM-1234567'))
 w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(pid));w.city_permit_select.setCurrentIndex(w.city_permit_select.findData(rid));w.city_tables['City Records'].selectRow(0);opened=[];warnings=[]
 monkeypatch.setattr(w,'finance_file_manager',lambda *args:opened.append(args))
 def cancel(*args):warnings.append(args[2]);return QMessageBox.Cancel
 monkeypatch.setattr(QMessageBox,'warning',cancel);w.city_row_files('City Records');assert not opened and 'SUB' in warnings[0]
 monkeypatch.setattr(QMessageBox,'warning',lambda *a:QMessageBox.Ok);w.city_row_files('City Records');assert opened;w.close()


def test_deleted_generated_charge_stays_deleted(store,pid):
 rid=permit(store,pid);charge=store.city_charges(rid)[0];store.delete_records([('reg_manual_charges',charge['id'])]);store.add_city_standard(rid)
 assert charge['title'] not in [r['title'] for r in store.city_charges(rid)]


def test_deleted_charge_id_reuse_does_not_hide_new_user_charge_on_county(store,pid):
 rid=permit(store,pid);last=store.city_charges(rid)[-1];store.delete_records([('reg_manual_charges',last['id'])])
 new=store.save('reg_manual_charges',dict(project_id=pid,register_id=rid,title='User manual charge'))
 store.configure_city_permit(config(pid,COUNTY),rid,True)
 assert new in [r['id'] for r in store.city_charges(rid)]
