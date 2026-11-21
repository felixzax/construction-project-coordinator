"""Phase 2 acceptance tests; no agency requirement content is expected."""
from datetime import date
from pathlib import Path
import hashlib
import json
import sqlite3
import zipfile
import pytest
from cpc.store import Store,FIELDS
from cpc.regulatory import REG_SECTION,PRIVACY_NOTE
from cpc.regulatory_schema import REG_FIELDS

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()
@pytest.fixture
def pid(store):return store.save('projects',{'name':'Fictional coordination project'})
def snapshot(db):
 names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT GLOB 'reg_*' ORDER BY name")]
 return {n:[tuple(r) for r in db.execute(f'SELECT * FROM {n} ORDER BY rowid')] for n in names}
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@pytest.mark.parametrize('kind',['empty','populated'])
def test_migration_on_copy_and_rollback(tmp_path,kind):
 source=tmp_path/'original.sqlite3'
 with sqlite3.connect(source) as db:db.executescript((Path(__file__).parent/'fixtures'/f'schema11_{kind}.sql').read_text());before=snapshot(db)
 source_hash=digest(source);copy=tmp_path/'upgrade-copy.sqlite3'
 with sqlite3.connect(source) as src,sqlite3.connect(copy) as dest:src.backup(dest)
 s=Store(copy)
 assert s.db.execute('PRAGMA user_version').fetchone()[0]==12
 assert snapshot(s.db)==before
 assert set(REG_FIELDS).issubset({r[0] for r in s.db.execute("SELECT name FROM sqlite_master WHERE type='table'")})
 assert all(s.all(t)==[] for t in REG_FIELDS) # no requirements, rules, sources or settings seeded
 safety=Path(str(copy)+'.before-v1.12.0.sqlite3');assert safety.is_file()
 with sqlite3.connect(safety) as db:
  assert db.execute('PRAGMA user_version').fetchone()[0]==11
  assert snapshot(db)==before
  rollback=tmp_path/'rollback.sqlite3'
  with sqlite3.connect(rollback) as target:db.backup(target)
 # A real rollback restores schema 11, not a re-upgrade by the current app.
 # The separate verification script also opens this with pinned v11 code.
 with sqlite3.connect(rollback) as db:
  assert db.execute('PRAGMA user_version').fetchone()[0]==11
  assert not db.execute("SELECT name FROM sqlite_master WHERE name GLOB 'reg_*'").fetchall()
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and snapshot(db)==before
 # New app can also restore a v11 safety copy without dropping preferences.
 s.restore(safety);assert snapshot(s.db)==before
 s.db.close();saved_hash=digest(safety);reopened=Store(copy);reopened.db.close()
 assert digest(source)==source_hash and digest(safety)==saved_hash


def test_schema_inventory_has_no_original_column_changes(store):
 with sqlite3.connect(':memory:') as db:
  db.executescript((Path(__file__).parent/'fixtures/schema11_empty.sql').read_text())
  for name in snapshot(db):assert [tuple(r) for r in db.execute(f'PRAGMA table_info({name})')]==[tuple(r) for r in store.db.execute(f'PRAGMA table_info({name})')]
 assert store.db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_profile_settings_atomic_and_no_legacy_export_columns(store,pid):
 r=store.save('project_profiles',dict(project_id=pid,title='Profile',reg_cgp_subject='Yes',reg_jurisdiction='City of Sacramento'))
 assert store.regulatory_settings(pid)['cgp_subject']=='Yes'
 assert 'reg_cgp_subject' not in store.profile(pid) and 'reg_cgp_subject' not in FIELDS['project_profiles']
 with pytest.raises(ValueError):store.save('project_profiles',dict(title='',reg_cgp_subject='No'),r)
 assert store.regulatory_settings(pid)['cgp_subject']=='Yes'


def test_roles_many_per_contact_and_delete_unassigns(store,pid):
 c=store.save('contacts',dict(name='Fictional Consultant'))
 roles=[store.save('reg_project_roles',dict(project_id=pid,contact_id=c,role=role,eauthorization_status='Yes',eauthorization_date='2026-11-20')) for role in ('LRP','QSD')]
 request=store.save('reg_document_requests',dict(project_id=pid,title='Request plans',requested_from_contact_id=c))
 store.delete_records([('contacts',c)])
 assert len(store.all('reg_project_roles'))==2
 assert all(r['contact_id'] is None and r['eauthorization_status']=='Unknown' and r['eauthorization_date']=='' for r in store.all('reg_project_roles'))
 assert store.all('reg_document_requests')[0]['requested_from_contact_id'] is None
 assert not store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_document_request_statuses_links_deadlines_files_search_recovery(store,pid,tmp_path):
 permit=store.save('registers',dict(project_id=pid,title='Fictional permit',record_type='Permit'))
 r=store.save('reg_document_requests',dict(project_id=pid,title='Requested engineer calculation',register_id=permit,needed_by='2020-01-01'))
 for status in ('Received','In Review','Needs Changes','Approved','N/A','Requested'):store.save('reg_document_requests',dict(status=status),r)
 assert store.regulatory_deadlines(pid)[0]['overdue']
 assert any(x['type']=='reg_document_requests' for x in store.search('engineer calculation'))
 original=tmp_path/'signed stamped approval.pdf';original.write_bytes(b'%PDF-1.4 signed approval example')
 f=store.import_finance_files('reg_document_requests',r,[original])[0];out=tmp_path/'redownload.pdf';store.save_finance_copy(f,out);assert original.read_bytes()==out.read_bytes()
 store.save_draft('request:new','reg_document_requests',None,dict(project_id=pid,title='Unfinished'))
 assert store.drafts()[0]['values']['title']=='Unfinished';store.clear_display_cache();assert store.drafts()
 p2=store.save('projects',dict(name='Other project'));p2permit=store.save('registers',dict(project_id=p2,title='Other permit',record_type='Permit'))
 with pytest.raises(ValueError,match='this project'):store.save('reg_document_requests',dict(register_id=p2permit),r)
 with pytest.raises((ValueError,sqlite3.IntegrityError)):store.save('reg_document_requests',dict(status='Submitted'),r)
 backup=store.backup(tmp_path/'backup.sqlite3');store.delete_records([('reg_document_requests',r)])
 assert not store.all('finance_files');store.restore(tmp_path/'backup.sqlite3');assert store.all('finance_files')


def test_inspections_reuse_canonical_records_progress_and_corrections(store,pid):
 contact=store.save('contacts',dict(name='Fictional Inspector'))
 correction=store.save('issues',dict(project_id=pid,title='Fix detail',issue_type='Correction',required_fix='Review detail'))
 ids=[store.save('registers',dict(project_id=pid,title=title,record_type='Inspection',contact_id=contact)) for title in ('Weekly failed','Building passed','Cancelled','Pending','Future')]
 store.save_regulatory_inspection(ids[0],dict(inspection_kind='Stormwater Weekly',inspection_date='2026-11-18',result='Fail',correction_id=correction))
 store.save_regulatory_inspection(ids[1],dict(inspection_date='2026-11-19',result='Pass'))
 store.save_regulatory_inspection(ids[2],dict(inspection_kind='Stormwater Weekly',inspection_date='2026-11-20',result='Cancelled'))
 store.save_regulatory_inspection(ids[4],dict(inspection_kind='Stormwater Weekly',inspection_date='2026-12-20',result='Pass'))
 result=store.regulatory_overview(pid,date(2026,11,20))
 assert result['passed_inspections']==1 and result['open_inspections']==3 and result['days_since_weekly']==2
 assert len(store.all('registers'))==5 and len(store.all('issues'))==1
 with pytest.raises(ValueError):store.save_regulatory_inspection(ids[3],dict(result='Pass'))
 store.delete_records([('issues',correction)]);assert store.all('reg_inspection_details')[-1]['correction_id'] is None
 store.delete_records([('registers',ids[0])]);assert len(store.all('reg_inspection_details'))==3


def test_waiting_on_agency_is_never_overdue_and_closed_items_drop_out(store,pid):
 for status in ('Waiting on Agency','In Progress','Submitted','Approved','Terminated','Done'):
  store.save('reg_tracker_steps',dict(project_id=pid,title=status,step_key=status,status=status,deadline='2020-01-01'))
 r=store.regulatory_deadlines(pid,date(2026,11,20));assert len(r)==2
 assert {x['title']:x['overdue'] for x in r}=={'Waiting on Agency':False,'In Progress':True}
 assert len(store.regulatory_overview(pid)['waiting_on_agency'])==1


def test_delete_project_preserves_global_sources_rules_templates(store,pid,tmp_path):
 source=store.save('reg_sources',dict(title='User supplied reference'))
 template=store.save('reg_templates',dict(template_key='custom',jurisdiction_key='Other',title='User template',source_id=source))
 rule=store.save('reg_rules',dict(rule_key='custom',title='User note',source_id=source))
 store.save('reg_project_roles',dict(project_id=pid,role='Owner'))
 store.save('reg_document_requests',dict(project_id=pid,title='User request',source_id=source))
 store.delete_records([('projects',pid)])
 assert store.all('reg_sources') and store.all('reg_rules') and store.all('reg_templates')
 assert not store.all('reg_document_requests') and not store.all('reg_project_roles')
 assert not store.db.execute('PRAGMA foreign_key_check').fetchall()

@pytest.mark.parametrize('text',['password=example-secret','portal login: example-user','security answer: example-answer','https://example.com/?access_token=example-secret','-----BEGIN PRIVATE KEY-----'])
def test_prohibited_text_never_enters_record_draft_or_log(store,pid,text):
 before=store.rows('SELECT * FROM activity')
 for operation in (lambda:store.save('tasks',dict(project_id=pid,title='Safe title',notes=text)),lambda:store.save_draft('bad','tasks',None,dict(notes=text))):
  with pytest.raises(ValueError):operation()
 assert store.rows('SELECT * FROM activity')==before and not store.drafts() and not store.all('tasks')

@pytest.mark.parametrize('filename',['signature.pfx','private.key','eAuthorization form.pdf'])
def test_prohibited_files_rejected_but_signed_documents_allowed(store,pid,tmp_path,filename):
 r=store.save('reg_document_requests',dict(project_id=pid,title='Plans'))
 f=tmp_path/filename;f.write_bytes(b'example')
 with pytest.raises(ValueError):store.import_finance_files('reg_document_requests',r,[f])
 assert not store.all('finance_files')


def test_archive_sensitive_entry_rejected(store,pid,tmp_path):
 r=store.save('reg_document_requests',dict(project_id=pid,title='Plans'));archive=tmp_path/'plans.zip'
 with zipfile.ZipFile(archive,'w') as z:z.writestr('private.pfx',b'example')
 with pytest.raises(ValueError):store.import_finance_files('reg_document_requests',r,[archive])


def test_water_board_gated_and_filing_workflow_deferred(store,pid):
 with pytest.raises(ValueError):store.save('reg_wb_sites',dict(project_id=pid))
 store.set_regulatory_settings(pid,cgp_subject='Yes');site=store.save('reg_wb_sites',dict(project_id=pid))
 with pytest.raises(ValueError,match='Phase 4'):store.save('reg_filings',dict(project_id=pid,wb_site_id=site,filing_type='COI (Site)',status='Submitted'))
 assert not store.all('reg_filings')


def test_ui_optional_visibility_order_theme_filter_and_warning(store,pid):
 from PySide6.QtWidgets import QApplication,QLabel
 from cpc.ui import Window
 app=QApplication.instance() or QApplication([]);w=Window(store)
 assert REG_SECTION in w.navigation_hidden();assert w.current=='Dashboard'
 w.project_filter.setCurrentIndex(w.project_filter.findData(pid));w.restore_sidebar_section(REG_SECTION)
 assert REG_SECTION not in w.navigation_hidden()
 w.hide_sidebar_section(REG_SECTION);assert REG_SECTION in w.navigation_hidden()
 w.hide_sidebar_section('Meetings');assert w.reorder_sections('hidden',[REG_SECTION,'Meetings']);assert [x for x in store.section_order(pid,'hidden') if x in w.navigation_hidden()]==[REG_SECTION,'Meetings']
 assert any(x.text()==PRIVACY_NOTE for x in w.findChildren(QLabel))
 request=store.save('reg_document_requests',dict(project_id=pid,title='Engineer request'))
 w.refresh();assert len(w.reg_rows['Document Requests'])==1
 w.reg_filters['Document Requests'].setText('missing');assert not w.reg_rows['Document Requests']
 w.choose_theme('light');w.choose_theme('dark');assert REG_SECTION in w.navigation_hidden()
 w.close();w2=Window(store);w2.project_filter.setCurrentIndex(w2.project_filter.findData(pid));assert REG_SECTION in w2.navigation_hidden();w2.close()


def test_canonical_parent_changes_cannot_break_regulatory_links(store,pid):
 inspection=store.save('registers',dict(project_id=pid,title='Inspection',record_type='Inspection'))
 correction=store.save('issues',dict(project_id=pid,title='Fix',required_fix='Revise detail',issue_type='Correction'))
 store.save_regulatory_inspection(inspection,dict(correction_id=correction))
 with pytest.raises(ValueError,match='Unlink'):store.save('registers',dict(record_type='RFI'),inspection)
 with pytest.raises(ValueError,match='Unlink'):store.save('issues',dict(issue_type='Violation'),correction)
 other=store.save('projects',dict(name='Other'))
 with pytest.raises(ValueError,match='Unlink'):store.save('registers',dict(project_id=other),inspection)


def test_authorization_reset_on_contact_reassignment_and_flag_only(store,pid):
 c1=store.save('contacts',dict(name='Person A'));c2=store.save('contacts',dict(name='Person B'))
 r=store.save('reg_project_roles',dict(project_id=pid,role='DAR',contact_id=c1,eauthorization_status='Yes',eauthorization_date='2026-11-20'))
 store.save('reg_project_roles',dict(contact_id=c2),r)
 assert store.all('reg_project_roles')[0]['eauthorization_status']=='Unknown'
 assert store.all('reg_project_roles')[0]['eauthorization_date']==''
 assert not any('secret' in k or 'form' in k or 'file' in k for k in REG_FIELDS['reg_project_roles'])


def test_secret_json_and_export_preflight(store,pid,tmp_path):
 with pytest.raises(ValueError):store.save('reg_rules',dict(title='Private',rule_key='private',details_json=json.dumps({'password':'example-secret'})))
 with pytest.raises(ValueError):store.export(tmp_path/'blocked.csv',[dict(notes='password=example-secret')])
 from cpc.exports import write_docx
 with pytest.raises(ValueError):write_docx(tmp_path/'blocked.docx','Report',[dict(notes='password=example-secret')])
 assert not (tmp_path/'blocked.csv').exists() and not (tmp_path/'blocked.docx').exists()


def test_reference_browser_requires_confirmation(store,pid,monkeypatch):
 from PySide6.QtWidgets import QApplication,QMessageBox
 from cpc.regulatory_ui import QDesktopServices
 from cpc.ui import Window
 app=QApplication.instance() or QApplication([]);source=store.save('reg_sources',dict(title='Fictional source',url='https://example.com/reference'))
 w=Window(store);w.reg_tables['References'].selectRow(0);opened=[]
 monkeypatch.setattr(QDesktopServices,'openUrl',lambda url:opened.append(url.toString()))
 monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.No);w.open_regulatory_source();assert not opened
 monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.Yes);w.open_regulatory_source();assert opened==['https://example.com/reference'];w.close()


def test_shared_draft_resume_including_profile_flags(store,pid,monkeypatch):
 from PySide6.QtWidgets import QApplication
 from cpc.ui import Window,Form
 app=QApplication.instance() or QApplication([]);w=Window(store)
 store.save_draft('profile','project_profiles',None,dict(project_id=pid,title='Profile',reg_cgp_subject='No',reg_jurisdiction='Sacramento County unincorporated'))
 captured=[]
 def accept(form):
  captured.append(form.values());form.persist(form.values());form.clear_recovery_draft();return 1
 monkeypatch.setattr(Form,'exec',accept)
 w.reload_recovery_lists();w.draft_table.selectRow(0);w.resume_draft()
 assert captured[0]['reg_cgp_subject']=='No' and store.regulatory_settings(pid)['cgp_subject']=='No'
 store.save_draft('request','reg_document_requests',None,dict(project_id=pid,title='Recovered request',status='Needs Changes'))
 w.reload_recovery_lists();w.draft_table.selectRow(0);w.resume_draft()
 assert store.all('reg_document_requests')[0]['status']=='Needs Changes' and not store.drafts();w.close()
