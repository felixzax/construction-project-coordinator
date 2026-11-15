import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from datetime import date
import sqlite3
import pytest
from cpc.store import Store, TASK_STATUSES

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3'); yield s; s.db.close()

def project(s,name='Test Project'):
 return s.save('projects',dict(name=name,address='123 Example St',owner='Example Owner',description='Test',phase='Planning',status='Active',archived=0))

def task(s,p,status='Not Started'):
 return s.save('tasks',dict(project_id=p,title='Review plans',deadline='2020-01-01',priority='High',contact_id=None,status=status,notes='Check code'))

def test_project_create_update_archive(store):
 p=project(store); row=store.all('projects')[0]; assert row['name']=='Test Project'
 row.update(name='Updated',archived=1); store.save('projects',row,p)
 assert store.all('projects')[0]['archived']==1
 assert len(store.rows('SELECT * FROM activity WHERE project_id=?',(p,)))==2

def test_required_fields_and_foreign_keys(store):
 with pytest.raises(ValueError): project(store,' ')
 with pytest.raises(sqlite3.IntegrityError): task(store,999)
 assert not store.all('tasks')

def test_task_statuses_and_outstanding(store):
 p=project(store); tid=task(store,p)
 for status in TASK_STATUSES:
  row=store.all('tasks')[0]; row['status']=status; store.save('tasks',row,tid)
  assert store.all('tasks')[0]['status']==status
 assert not store.outstanding()
 row['status']='bad'
 with pytest.raises(ValueError): store.save('tasks',row,tid)

def test_document_revision_history(store):
 p=project(store); d=store.save('documents',dict(project_id=p,title='Plans',category='Architectural Plans'))
 store.add_version(d,'A',status='Approved',requirements='Original')
 store.add_version(d,'B',requirements='Accessibility correction')
 versions=store.versions(d)
 assert versions[0]['status']=='Draft' and versions[0]['resubmission']==1
 assert versions[1]['status']=='Approved'
 with pytest.raises(sqlite3.IntegrityError): store.add_version(d,'A')
 assert len(store.versions(d))==2

def test_search_across_records(store):
 store.seed()
 for word,kind in [('Cedar','projects'),('Alex','contacts'),('accessibility','tasks'),('Architectural','documents'),('resubmission','versions')]:
  assert any(r['type']==kind for r in store.search(word))
 assert store.search("' OR 1=1 --")==[]

def test_backup_restore_and_safety_copy(store,tmp_path):
 p=project(store); task(store,p); backup=tmp_path/'backup.sqlite3'; store.backup(backup)
 project(store,'New Project'); assert len(store.all('projects'))==2
 store.restore(backup); assert len(store.all('projects'))==1
 assert len(store.all('tasks'))==1
 safety=sqlite3.connect(str(store.path)+'.before-restore.sqlite3')
 assert safety.execute('SELECT count(*) FROM projects').fetchone()[0]==2; safety.close()

def test_invalid_restore_does_not_replace(store,tmp_path):
 project(store); bad=tmp_path/'bad.sqlite3'; bad.write_text('bad')
 with pytest.raises(sqlite3.DatabaseError): store.restore(bad)
 assert len(store.all('projects'))==1
 with pytest.raises(ValueError): store.backup(store.path)

def test_contacts_drafts_reports_exports(store,tmp_path):
 store.seed(); comm=store.all('communications')[0]
 draft=store.draft(comm); assert 'alex@example.com' in draft and comm['follow_up'] in draft
 assert 'Cedar Grove' in store.report(comm['project_id'])
 store.export(tmp_path/'out.csv',store.outstanding()); assert 'Request revised' in (tmp_path/'out.csv').read_text('utf-8-sig')
 store.export(tmp_path/'safe.csv',[{'name':'=1+1'}]); assert "'=1+1" in (tmp_path/'safe.csv').read_text('utf-8-sig')

def test_bad_date(store):
 p=project(store)
 with pytest.raises(ValueError): store.save('milestones',dict(project_id=p,title='Bad',deadline='tomorrow'))

def test_desktop_navigation_and_edit(store,monkeypatch):
 from PySide6.QtWidgets import QApplication, QDialog
 from cpc.ui import Window, Form
 app=QApplication.instance() or QApplication([])
 store.seed(); w=Window(store); w.show(); app.processEvents()
 for i in range(w.nav.count()):
  w.nav.setCurrentRow(i); app.processEvents(); assert w.stack.currentIndex()==i
 assert w.tables['Tasks'].rowCount()==2
 w.tables['Tasks'].selectRow(0)
 monkeypatch.setattr(Form,'exec',lambda self: QDialog.Accepted)
 original=Form.values
 def values(self):
  data=original(self)
  if 'status' in data: data['status']='Completed'
  return data
 monkeypatch.setattr(Form,'values',values)
 w.edit('Tasks',True)
 assert store.all('tasks')[0]['status']=='Completed'
 w.search_input.setText('Cedar'); app.processEvents(); assert w.tables['Search'].rowCount()>0
 assert w.tables['Documents'].item(0,8) is not None
 w.close()

def test_document_files_preserve_previous_content(store,tmp_path):
 p=project(store); d=store.save('documents',dict(project_id=p,title='Drawing',category='Engineering Drawings'))
 source=tmp_path/'plans.txt'; source.write_text('Version A')
 store.add_version(d,'A',file_path=str(source),status='Approved')
 source.write_text('Version B'); store.add_version(d,'B',file_path=str(source))
 from pathlib import Path
 b,a=store.versions(d)
 assert Path(a['file_path']).read_text()=='Version A'
 assert Path(b['file_path']).read_text()=='Version B'
 assert a['file_path']!=b['file_path']

def test_timeline_task_edit_preserves_title(store,monkeypatch):
 from PySide6.QtWidgets import QApplication,QDialog
 from cpc.ui import Window,Form
 app=QApplication.instance() or QApplication([])
 store.seed(); w=Window(store)
 row=next(i for i,r in enumerate(w.data['Timeline']) if r['kind']=='Task')
 w.tables['Timeline'].selectRow(row)
 original=w.data['Timeline'][row]['id']
 monkeypatch.setattr(Form,'exec',lambda self:QDialog.Accepted)
 w.edit('Timeline',True)
 result=store.rows('SELECT title FROM tasks WHERE id=?',(original,))[0]
 assert not result['title'].startswith('Task:')
 w.close()
