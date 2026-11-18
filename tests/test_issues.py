import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import closing
from datetime import date,timedelta
from pathlib import Path
import sqlite3
import pytest
from cpc.store import Store
from cpc.exports import department_rows

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()

@pytest.fixture
def project(store):return store.save('projects',dict(name='Fixes project',address='125 Example Street'))

@pytest.fixture
def issue(store,project):
 return store.save('issues',dict(project_id=project,title='Panel clearance',issue_type='Violation',location='Electrical room, rear wall',required_fix='Clear the panel working space',discipline='Electrical',priority='High',deadline=(date.today()-timedelta(days=1)).isoformat(),status='Open',authority='Example City inspector'))


def test_issue_address_location_required_fix_and_project_log(store,project,issue):
 row=store.issue_rows('Violation',project)[0]
 assert row['site_address']=='125 Example Street' and row['project_address']=='125 Example Street'
 assert row['location']=='Electrical room, rear wall' and row['required_fix']=='Clear the panel working space'
 assert row['issue_type']=='Violation' and row['status']=='Open'
 assert store.rows('SELECT * FROM activity WHERE project_id=?',(project,))[-2]['description'].startswith('Violation')


def test_custom_address_preserved_and_corrections_separate(store,project,issue):
 store.save('issues',dict(project_id=project,title='Plan correction',issue_type='Correction',site_address='127 Example Street, Annex',required_fix='Revise the ramp detail',sheet_reference='A-102'))
 assert len(store.issue_rows('Violation'))==1 and len(store.issue_rows('Correction'))==1
 assert store.issue_rows('Correction')[0]['site_address']=='127 Example Street, Annex'


def test_resolution_and_reopening_dates(store,issue):
 store.save('issues',{'status':'Resolved','resolution_notes':'Clearance inspected'},issue)
 assert store.issue_rows()[0]['resolved_date']==date.today().isoformat()
 store.save('issues',{'status':'Closed'},issue)
 assert store.issue_rows()[0]['status']=='Closed'
 store.save('issues',{'status':'In Progress'},issue)
 assert store.issue_rows()[0]['resolved_date']==''

@pytest.mark.parametrize('data',[{'required_fix':' '},{'status':'Approved'},{'issue_type':'Other'},{'priority':'bad'},{'reported_date':'20261117'},{'deadline':'tomorrow'},{'reported_date':'2026-12-02','resolved_date':'2026-12-01','status':'Closed'}])
def test_invalid_issue_input_does_not_overwrite(store,issue,data):
 with pytest.raises(ValueError):store.save('issues',data,issue)
 assert store.issue_rows()[0]['required_fix']=='Clear the panel working space'


def test_permit_links_validate_project_and_unlink_on_permit_delete(store,project,issue):
 permit=store.save('registers',dict(project_id=project,title='Building permit',record_type='Permit'))
 store.save('issues',{'permit_id':permit},issue)
 other=store.save('projects',{'name':'Other project'})
 other_permit=store.save('registers',dict(project_id=other,title='Other permit',record_type='Permit'))
 with pytest.raises(ValueError,match='same project'):store.save('issues',{'permit_id':other_permit},issue)
 with pytest.raises(ValueError,match='remain a permit'):store.save('registers',{'record_type':'RFI'},permit)
 with pytest.raises(ValueError,match='moving the permit'):store.save('registers',{'project_id':other},permit)
 store.delete_records([('registers',permit)])
 row=store.issue_rows()[0];assert row['permit_id'] is None and row['required_fix']=='Clear the panel working space'
 assert store.db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_evidence_copies_and_preserves_original_files(store,issue,tmp_path):
 path=tmp_path/'notice.txt';path.write_text('City notice');first=store.attach_issue(issue,path)
 path.write_text('Revised notice');second=store.attach_issue(issue,path)
 assert first.read_text()=='City notice' and second.read_text()=='Revised notice' and first!=second
 store.delete_records([('issues',issue)]);assert first.exists() and second.exists()


def test_issue_search_exports_report_backup_and_project_delete(store,project,issue,tmp_path):
 assert any(row['type']=='issues' for row in store.search('Electrical room'))
 rows=department_rows(store,['Electrical'],project)
 assert any(row['record_type']=='Violation' and row['site_address']=='125 Example Street' and row['required_fix']=='Clear the panel working space' for row in rows)
 report=store.report(project);assert 'Panel clearance' in report and '125 Example Street' in report and 'Clear the panel working space' in report
 backup=tmp_path/'backup.sqlite3';store.backup(backup);store.save('issues',{'status':'Closed'},issue);store.restore(backup)
 assert store.issue_rows()[0]['status']=='Open'
 safety=store.delete_records([('projects',project)]);assert store.all('issues')==[]
 store.restore(safety);assert len(store.all('issues'))==1


def v5_database(path):
 with closing(sqlite3.connect(path)) as db:db.executescript((Path(__file__).parent/'fixtures/v5_database.sql').read_text())


def test_v5_upgrade_preserves_receipts_and_permits(tmp_path):
 path=tmp_path/'v5.sqlite3';v5_database(path);s=Store(path)
 try:
  assert s.db.execute('PRAGMA user_version').fetchone()[0]==9
  assert len(s.all('receipts'))==1 and len(s.all('permit_requirements'))==2 and len(s.all('bids'))==2
  assert s.all('issues')==[]
  with closing(sqlite3.connect(str(path)+'.before-v1.9.0.sqlite3')) as old:assert old.execute('PRAGMA user_version').fetchone()[0]==5
 finally:s.db.close()


def test_v5_restore_into_current_schema(store,issue,tmp_path):
 path=tmp_path/'v5.sqlite3';v5_database(path);store.restore(path)
 assert store.all('issues')==[] and len(store.all('receipts'))==1
 assert store.db.execute('PRAGMA user_version').fetchone()[0]==9

@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])

@pytest.fixture
def window(store,issue,app,monkeypatch):
 from PySide6.QtWidgets import QMessageBox
 from cpc.ui import Window
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail);w=Window(store);yield w;w.close()


def test_issue_dashboard_timeline_overdue_and_resolution(window,store,issue,app):
 assert any(row.get('_source_table')=='issues' for row in window.data['Dashboard'])
 assert any(row.get('_source_table')=='issues' for row in window.data['Timeline'])
 from cpc.theme import tokens
 table=window.tables['Violations'];assert table.item(0,0).background().color().name()==tokens()['error_bg']
 store.save('issues',{'status':'Resolved'},issue);window.refresh()
 assert not any(row.get('_source_table')=='issues' for row in window.data['Dashboard'])
 assert table.item(0,0).background().color().name()!=tokens()['error_bg']


def test_new_correction_form_autofills_address_and_required_fix(window,store,project,monkeypatch):
 from cpc.ui import Form
 def submit(form):
  assert form.inputs['site_address'].text()=='125 Example Street'
  form.inputs['title'].setText('Plan correction');form.inputs['location'].setText('First floor, ramp');form.inputs['required_fix'].setPlainText('Revise ramp detail');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);window.edit('Corrections')
 row=store.issue_rows('Correction')[0];assert row['site_address']=='125 Example Street' and row['location']=='First floor, ramp'


def test_edit_keeps_custom_address_and_project_switch_autofills(window,store,project,issue,monkeypatch):
 from cpc.ui import Form
 store.save('issues',{'site_address':'Custom site address'},issue);window.refresh();window.tables['Violations'].selectRow(0)
 def edit(form):
  assert form.inputs['site_address'].text()=='Custom site address'
  form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',edit);window.edit('Violations',True)
 other=store.save('projects',dict(name='Second',address='900 Example Road'));window.refresh()
 def create(form):
  form.inputs['project_id'].setCurrentIndex(form.inputs['project_id'].findData(project))
  assert form.inputs['site_address'].text()=='125 Example Street'
  form.inputs['project_id'].setCurrentIndex(form.inputs['project_id'].findData(other))
  assert form.inputs['site_address'].text()=='900 Example Road'
  form.inputs['title'].setText('Second correction');form.inputs['required_fix'].setPlainText('Repair the floor');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',create);window.edit('Corrections')
 assert store.issue_rows('Correction')[0]['site_address']=='900 Example Road'


def test_project_shortcut_filter_and_issue_draft_recovery(window,store,project,issue,monkeypatch):
 from cpc.ui import Form
 window.tables['Projects'].selectRow(0);window.show_project_issues('Violations')
 assert window.project_filter.currentData()==project and window.nav.currentItem().text()=='Violations'
 other=store.save('projects',{'name':'Empty'});window.refresh();window.project_filter.setCurrentIndex(window.project_filter.findData(other))
 assert window.tables['Violations'].rowCount()==0
 store.save_draft('issue:new','issues',None,dict(project_id=project,title='Recovered correction',issue_type='Correction',required_fix='Fix the stairs',status='Open'))
 window.reload_recovery_lists();window.draft_table.selectRow(0)
 def submit(form):form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);window.resume_draft()
 assert any(row['title']=='Recovered correction' for row in store.issue_rows()) and not store.drafts()


def test_issue_csv_docx_and_attachment_actions(window,store,issue,tmp_path,monkeypatch):
 from PySide6.QtWidgets import QFileDialog
 window.tables['Violations'].selectRow(0)
 photo=tmp_path/'notice.txt';photo.write_text('Example violation notice')
 monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:(str(photo),'File'));window.attach_issue_file('Violations')
 assert Path(store.issue_rows()[0]['attachment_path']).read_text()=='Example violation notice'
 path=tmp_path/'violations.csv';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(path),'CSV'));window.export_section('Violations','csv')
 assert '125 Example Street' in path.read_text('utf-8-sig') and 'Clear the panel' in path.read_text('utf-8-sig')
 word=tmp_path/'violations.docx';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(word),'DOCX'));window.export_section('Violations','docx')
 from docx import Document
 doc=Document(word);assert any('125 Example Street' in c.text for t in doc.tables for r in t.rows for c in r.cells)
