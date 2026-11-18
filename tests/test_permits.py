import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3
import pytest
from cpc.store import Store
from cpc.permits import validate_url

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3'); yield s; s.db.close()

@pytest.fixture
def permit(store):
 p=store.save('projects',{'name':'Permit project'})
 return store.save('registers',dict(project_id=p,title='Building application',record_type='Permit',jurisdiction_type='County',jurisdiction_name='Example County',department='Planning and Building',application_url='https://example.com/apply',requirements_url='https://example.com/checklist',requirements_reviewed=0,status='Open'))

def test_jurisdiction_fields_and_requirement_checkmarks(store,permit):
 permit_row=store.all('registers')[0]
 assert permit_row['jurisdiction_name']=='Example County'
 assert permit_row['requirements_url']=='https://example.com/checklist'
 item=store.save('permit_requirements',dict(register_id=permit,title='Signed application',source_url='https://example.com/forms',completed=0,notes='Obtain owner signature'))
 assert store.permit_progress(permit)=='0/1 checked'
 store.set_requirement_completed(item,True)
 assert store.permit_requirements(permit)[0]['completed_on']==date.today().isoformat()
 assert store.permit_progress(permit)=='1/1 checked'
 assert store.all('registers')[0]['status']=='Open'
 store.set_requirement_completed(item,False)
 assert store.permit_requirements(permit)[0]['completed_on']==''
 store.save('registers',{'requirements_reviewed':1},permit)
 assert store.all('registers')[0]['requirements_reviewed']==1
 assert store.rows('SELECT * FROM activity')[-1]['description'].startswith('Registers')

@pytest.mark.parametrize('url',['javascript:alert(1)','file:///C:/secret','ftp://example.com/file','https://user:password@example.com','https:///missing-host','https://example.com/a b','https://example.com\nnext','https://example.com:bad','https://example.com\\folder'])
def test_invalid_links_rejected(store,permit,url):
 with pytest.raises(ValueError): store.save('registers',{'requirements_url':url},permit)
 with pytest.raises(ValueError): store.save('permit_requirements',dict(register_id=permit,title='Requirement',source_url=url))
 assert store.permit_requirements(permit)==[]

@pytest.mark.parametrize('url',['https://example.gov/permit?type=commercial&revision=2#requirements','http://example.com/checklist',''])
def test_valid_optional_web_links(url): assert validate_url(url)==url


def test_only_permits_accept_checklist_items(store,permit):
 p=store.all('registers')[0]['project_id']; rfi=store.save('registers',dict(project_id=p,title='RFI',record_type='RFI'))
 with pytest.raises(ValueError): store.save('permit_requirements',dict(register_id=rfi,title='Not a permit'))
 with pytest.raises(ValueError): store.save('permit_requirements',dict(register_id=permit,title=' '))
 item=store.save('permit_requirements',dict(register_id=permit,title='Plan set'))
 with pytest.raises(ValueError): store.save('registers',{'record_type':'RFI'},permit)
 with pytest.raises(ValueError): store.save('permit_requirements',{'register_id':rfi},item)


def test_requirement_search_report_and_backup_restore(store,permit,tmp_path):
 item=store.save('permit_requirements',dict(register_id=permit,title='Energy compliance certificate',completed=1,source_url='https://example.com/energy'))
 project=store.all('registers')[0]['project_id']
 assert any(r['type']=='permit_requirements' and r['project_id']==project for r in store.search('Energy compliance'))
 assert any(r['type']=='registers' for r in store.search('Example County'))
 report=store.report(project)
 for text in ['Permit application checklists','Example County','[x] Energy compliance','https://example.com/checklist']: assert text in report
 backup=tmp_path/'backup.sqlite3'; store.backup(backup); store.set_requirement_completed(item,False); store.restore(backup)
 assert store.permit_progress(permit)=='1/1 checked'


def v2_database(path):
 with closing(sqlite3.connect(path)) as db:
  db.executescript((Path(__file__).parent/'fixtures/v2_database.sql').read_text())
  db.execute("INSERT INTO registers(project_id,title,record_type,status) VALUES(1,'Existing permit','Permit','Submitted')"); db.commit()


def test_v2_upgrade_preserves_permits_and_bids_and_snapshot(tmp_path):
 path=tmp_path/'v2.sqlite3'; v2_database(path); s=Store(path)
 try:
  assert s.db.execute('PRAGMA user_version').fetchone()[0]==8
  old=next(r for r in s.all('registers') if r['record_type']=='Permit')
  assert old['title']=='Existing permit' and old['status']=='Submitted'
  assert old['jurisdiction_name']=='' and old['requirements_reviewed']==0
  assert len(s.all('bids'))==2 and s.bid_totals(s.all('bids')[0]['id'])['total']>0
  with closing(sqlite3.connect(str(path)+'.before-v1.7.0.sqlite3')) as backup:
   assert backup.execute('PRAGMA user_version').fetchone()[0]==2
 finally: s.db.close()


def test_v2_backup_restore_into_current_schema(store,tmp_path):
 store.seed(); old=tmp_path/'old.sqlite3'; v2_database(old); store.restore(old)
 assert store.db.execute('PRAGMA user_version').fetchone()[0]==8
 assert len(store.all('bids'))==2
 assert any(r['title']=='Existing permit' for r in store.all('registers'))
 assert store.all('permit_requirements')==[]

@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])

@pytest.fixture
def window(store,permit,app,monkeypatch):
 from PySide6.QtWidgets import QMessageBox
 from cpc.ui import Window
 def fail(*args): raise AssertionError('Unexpected error dialog: '+str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 w=Window(store); w.tables['Permits'].selectRow(0)
 yield w
 w.close()


def test_permit_form_city_county_link_and_reviewed_checkbox(window,store,monkeypatch):
 from cpc.ui import Form
 def submit(form):
  form.inputs['jurisdiction_type'].setCurrentText('City')
  form.inputs['jurisdiction_name'].setText('Example City')
  form.inputs['requirements_url'].setText('https://example.com/new-checklist')
  form.inputs['requirements_reviewed'].setChecked(True)
  form.accept(); return form.result()
 monkeypatch.setattr(Form,'exec',submit)
 window.edit('Permits',True)
 row=store.all('registers')[0]
 assert row['jurisdiction_type']=='City' and row['jurisdiction_name']=='Example City'
 assert row['requirements_reviewed']==1 and row['requirements_url'].endswith('new-checklist')


def test_checklist_ui_add_and_toggle_persists(window,store,permit,monkeypatch):
 from PySide6.QtCore import Qt
 from PySide6.QtWidgets import QDialog,QPushButton,QTableWidget,QCheckBox
 from cpc.ui import Form
 def submit(form):
  form.inputs['title'].setText('Site plan and drainage checklist')
  form.inputs['source_url'].setText('https://example.com/site-plan')
  form.accept(); return form.result()
 def run(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='+ Requirement').click()
  table=dialog.findChild(QTableWidget)
  assert table.rowCount()==1
  table.item(0,0).setCheckState(Qt.Checked)
  dialog.findChild(QCheckBox).setChecked(True)
  assert store.permit_progress(permit)=='1/1 checked'
  dialog.accept(); return dialog.result()
 monkeypatch.setattr(Form,'exec',submit); monkeypatch.setattr(QDialog,'exec',run)
 window.permit_checklist()
 assert store.permit_requirements(permit)[0]['completed']==1
 assert store.all('registers')[0]['requirements_reviewed']==1
 assert window.data['Permits'][0]['checklist_progress']=='1/1 checked'


def test_open_saved_web_link_uses_only_explicit_action(window,monkeypatch):
 from PySide6.QtGui import QDesktopServices
 opened=[]; monkeypatch.setattr(QDesktopServices,'openUrl',lambda url:opened.append(url.toString()) or True)
 assert opened==[]
 window.open_permit_link('requirements_url')
 assert opened==['https://example.com/checklist']


def test_checklist_csv_has_jurisdiction_and_completion(window,store,permit,tmp_path,monkeypatch):
 from PySide6.QtWidgets import QDialog,QPushButton,QFileDialog
 store.save('permit_requirements',dict(register_id=permit,title='Signed plan set',completed=1))
 path=tmp_path/'checklist.csv'
 monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(path),'CSV'))
 def run(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Export checklist CSV').click()
  dialog.accept(); return dialog.result()
 monkeypatch.setattr(QDialog,'exec',run)
 window.permit_checklist()
 content=path.read_text('utf-8-sig')
 assert 'Example County' in content and 'Signed plan set' in content and 'Yes' in content
