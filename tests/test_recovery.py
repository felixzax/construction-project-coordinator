import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest
from cpc.store import Store,FIELDS

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3'); yield s; s.db.close()

@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])

@pytest.fixture
def window(store,app,monkeypatch):
 from PySide6.QtWidgets import QMessageBox
 from cpc.ui import Window
 def fail(*args): raise AssertionError('Unexpected error dialog: '+str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 store.seed(); w=Window(store); yield w; w.close()

@pytest.mark.parametrize('table,child',[('documents','versions'),('registers','permit_requirements'),('bid_packages','bids'),('bids','bid_items')])
def test_delete_cascades_only_related_records_and_can_restore(store,table,child):
 store.seed()
 row=next(r for r in store.all(table) if table!='registers' or r['record_type']=='Permit')
 count=store.db.execute(f'SELECT count(*) FROM {child}').fetchone()[0]
 backup=store.delete_records([(table,row['id'])])
 assert backup.is_file() and len(store.all('projects'))==1
 assert store.db.execute(f'SELECT count(*) FROM {child}').fetchone()[0]<count
 assert not store.db.execute('PRAGMA foreign_key_check').fetchall()
 store.restore(backup)
 assert store.db.execute(f'SELECT count(*) FROM {child}').fetchone()[0]==count


def test_project_delete_removes_its_children_but_keeps_contacts_and_other_projects(store):
 store.seed(); original=store.all('projects')[0]['id']; second=store.save('projects',{'name':'Keep me'})
 summary=store.deletion_summary([('projects',original)])
 assert summary['projects']==1 and summary['tasks']==2 and summary['permit_requirements']==2
 store.delete_records([('projects',original)])
 assert [r['id'] for r in store.all('projects')]==[second]
 assert len(store.all('contacts'))==3
 for table in ('tasks','documents','meetings','registers','bid_packages','bids','bid_items','permit_requirements'): assert store.all(table)==[]
 assert store.db.execute('SELECT count(*) FROM activity WHERE project_id=?',(original,)).fetchone()[0]==0
 assert store.db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_contact_delete_unassigns_without_deleting_work(store):
 store.seed(); person=next(c for c in store.all('contacts') if c['name']=='Alex Morgan')
 store.delete_records([('contacts',person['id'])])
 assert len(store.all('tasks'))==2 and all(r['contact_id'] is None for r in store.all('tasks'))
 assert store.all('meetings')[0]['contact_id'] is None
 assert store.all('communications')[0]['contact_id'] is None
 bidder=next(c for c in store.all('contacts') if c['name']=='Casey Rivera')
 bid=next(b for b in store.all('bids') if b['contact_id']==bidder['id']); before=store.bid_totals(bid['id'])
 store.delete_records([('contacts',bidder['id'])])
 assert store.bid_totals(bid['id'])==before
 assert next(b for b in store.all('bids') if b['id']==bid['id'])['contact_id'] is None
 assert not store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_meeting_delete_unlinks_action_tasks(store):
 store.seed(); meeting=store.all('meetings')[0]
 tid=store.save('tasks',dict(project_id=meeting['project_id'],title='Keep action',meeting_id=meeting['id'],status='Not Started'))
 store.delete_records([('meetings',meeting['id'])])
 assert next(t for t in store.all('tasks') if t['id']==tid)['meeting_id'] is None


def test_deleting_cost_items_rolls_back_when_discount_would_be_invalid(store):
 store.seed(); bid=store.all('bids')[0]; total=store.bid_totals(bid['id'])['total']; store.save('bids',{'discount':str(total/2)},bid['id'])
 items=store.rows('SELECT * FROM bid_items WHERE bid_id=?',(bid['id'],)); before=store.bid_totals(bid['id'])
 with pytest.raises(ValueError,match='Discount'): store.delete_records([('bid_items',items[0]['id'])])
 assert store.bid_totals(bid['id'])==before
 assert store.rows('SELECT * FROM bid_items WHERE id=?',(items[0]['id'],))


def test_delete_all_data_has_recoverable_snapshot_and_keeps_document_files(store,tmp_path):
 store.seed(); original=tmp_path/'file.txt'; original.write_text('Retained document')
 doc=store.all('documents')[0]; store.add_version(doc['id'],'File',file_path=str(original)); retained=Path(store.versions(doc['id'])[0]['file_path'])
 store.save_draft('unfinished','tasks',None,{'title':'Unfinished task'})
 backup=store.delete_all_data()
 assert all(store.all(table)==[] for table in FIELDS)
 assert not store.drafts() and retained.read_text()=='Retained document'
 store.restore(backup)
 assert len(store.all('projects'))==1 and store.drafts()[0]['values']['title']=='Unfinished task'


def test_delete_snapshot_failure_prevents_deletion(store,monkeypatch):
 p=store.save('projects',{'name':'Must stay'})
 def fail(*args): raise OSError('Disk full')
 monkeypatch.setattr(store,'recovery_snapshot',fail)
 with pytest.raises(OSError): store.delete_records([('projects',p)])
 assert store.all('projects')[0]['name']=='Must stay'


def test_recovery_snapshot_rotation_and_integrity(store):
 store.save('projects',{'name':'Snapshot record'})
 for _ in range(7): store.recovery_snapshot('automatic')
 snapshots=store.recovery_snapshots(); assert len(snapshots)==5
 for snapshot in snapshots:
  with closing(sqlite3.connect(snapshot['path'])) as backup:
   assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   assert backup.execute('SELECT name FROM projects').fetchone()[0]=='Snapshot record'


def test_drafts_survive_backup_and_restore(store,tmp_path):
 store.save_draft('tasks:new:test','tasks',None,{'title':'Recover text','notes':'Details','status':'Not Started'})
 backup=tmp_path/'backup.sqlite3'; store.backup(backup); store.discard_draft('tasks:new:test'); store.restore(backup)
 assert store.drafts()[0]['values']['notes']=='Details'


def test_abrupt_process_exit_preserves_saved_records_and_form_autosave(tmp_path):
 path=tmp_path/'crashed.sqlite3'
 code=r'''
import os,sys
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from cpc.store import Store,FIELDS
from cpc.ui import Window,Form
app=QApplication([])
s=Store(sys.argv[1]);s.start_session()
p=s.save('projects',{'name':'Committed before crash'})
w=Window(s)
f=Form(w,'New task',FIELDS['tasks'],{'project_id':p,'status':'Not Started'},w.choices('tasks'))
f.enable_draft('tasks')
f.inputs['title'].setText('Unfinished before crash')
f.inputs['notes'].setPlainText('Recover this exact note')
QTest.qWait(1100)
assert s.drafts()
os._exit(17)
'''
 result=subprocess.run([sys.executable,'-c',code,str(path)],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=30)
 assert result.returncode==17,result.stdout+result.stderr
 s=Store(path)
 try:
  assert s.all('projects')[0]['name']=='Committed before crash'
  assert s.drafts()[0]['values']['notes']=='Recover this exact note'
  assert s.start_session() is True
  s.end_session()
 finally: s.db.close()
 clean=Store(path)
 try: assert clean.start_session() is False; clean.end_session()
 finally: clean.db.close()


def test_v3_upgrade_preserves_permits_and_creates_pre_upgrade_backup(tmp_path):
 path=tmp_path/'v3.sqlite3'
 with closing(sqlite3.connect(path)) as db: db.executescript((Path(__file__).parent/'fixtures/v3_database.sql').read_text())
 s=Store(path)
 try:
  assert s.db.execute('PRAGMA user_version').fetchone()[0]==6
  assert len(s.all('bids'))==2 and len(s.all('permit_requirements'))==2
  with closing(sqlite3.connect(str(path)+'.before-v1.5.0.sqlite3')) as backup: assert backup.execute('PRAGMA user_version').fetchone()[0]==3
 finally: s.db.close()


def test_v3_backup_can_be_restored_with_current_recovery_schema(store,tmp_path):
 path=tmp_path/'v3.sqlite3'
 with closing(sqlite3.connect(path)) as db: db.executescript((Path(__file__).parent/'fixtures/v3_database.sql').read_text())
 store.restore(path)
 assert store.db.execute('PRAGMA user_version').fetchone()[0]==6
 assert store.drafts()==[] and len(store.all('permit_requirements'))==2


def test_keyboard_cell_copy_select_all_and_checkbox_text(app):
 from PySide6.QtCore import Qt
 from PySide6.QtWidgets import QTableWidgetItem,QTableWidgetSelectionRange
 from PySide6.QtTest import QTest
 from cpc.table import DataTable
 table=DataTable(2,2)
 for i,row in enumerate([['Name','Status'],['Plan set','Ready']]):
  for j,value in enumerate(row): table.setItem(i,j,QTableWidgetItem(value))
 table.show(); table.setFocus(); table.setCurrentCell(0,0)
 QTest.keyClick(table,Qt.Key_Right,Qt.ShiftModifier); QTest.keyClick(table,Qt.Key_C,Qt.ControlModifier)
 assert app.clipboard().text()=='Name\tStatus'
 QTest.keyClick(table,Qt.Key_A,Qt.ControlModifier); QTest.keyClick(table,Qt.Key_C,Qt.ControlModifier)
 assert app.clipboard().text()=='Name\tStatus\nPlan set\tReady'
 check=QTableWidgetItem(); check.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable); check.setCheckState(Qt.Checked); table.setItem(0,0,check); table.clearSelection(); table.setRangeSelected(QTableWidgetSelectionRange(0,0,0,0),True)
 assert table.copy_selection()=='Yes'; table.close()


def test_delete_confirmation_cancel_and_cell_selection_deduplicates_records(window,store,monkeypatch):
 from PySide6.QtWidgets import QMessageBox,QTableWidgetSelectionRange
 table=window.tables['Tasks']; table.setRangeSelected(QTableWidgetSelectionRange(0,0,0,1),True)
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.No)
 window.delete_page('Tasks'); assert len(store.all('tasks'))==2 and not store.recovery_snapshots()
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
 window.delete_page('Tasks'); assert len(store.all('tasks'))==1 and len(store.recovery_snapshots())==1


def test_delete_all_listed_respects_project_and_text_filters(window,store,monkeypatch):
 from PySide6.QtWidgets import QMessageBox
 original=store.all('projects')[0]['id']; other=store.save('projects',{'name':'Other project'})
 store.save('tasks',dict(project_id=other,title='Other task',status='Not Started'))
 window.refresh(); window.project_filter.setCurrentIndex(window.project_filter.findData(original)); window.filter_Tasks.setText('Coordinate permit review')
 assert window.tables['Tasks'].rowCount()==1
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
 window.delete_page('Tasks',True)
 assert len(store.all('tasks'))==2 and any(t['title']=='Other task' for t in store.all('tasks'))


def test_delete_all_application_requires_typed_phrase(window,store,monkeypatch):
 from PySide6.QtWidgets import QInputDialog
 monkeypatch.setattr(QInputDialog,'getText',lambda *args:('NO',True)); window.delete_application_data(); assert store.all('projects')
 monkeypatch.setattr(QInputDialog,'getText',lambda *args:('DELETE ALL',True)); window.delete_application_data(); assert all(not store.all(t) for t in FIELDS)


def test_refresh_preserves_records_drafts_snapshots_and_filter(window,store):
 pid=store.all('projects')[0]['id']; window.project_filter.setCurrentIndex(window.project_filter.findData(pid))
 store.save_draft('recover','tasks',None,{'title':'Do not lose'})
 store.recovery_snapshot(); before={t:store.all(t) for t in FIELDS}; snapshots=store.recovery_snapshots()
 window.refresh_from_disk()
 assert {t:store.all(t) for t in FIELDS}==before
 assert store.drafts()[0]['values']['title']=='Do not lose'
 assert store.recovery_snapshots()==snapshots and window.project_filter.currentData()==pid


def test_resume_draft_saves_record_and_removes_draft(window,store,monkeypatch):
 from cpc.ui import Form
 pid=store.all('projects')[0]['id']; store.save_draft('tasks:new:recover','tasks',None,dict(project_id=pid,title='Recovered task',status='Not Started'))
 window.reload_recovery_lists(); window.draft_table.selectRow(0)
 def submit(form): form.accept(); return form.result()
 monkeypatch.setattr(Form,'exec',submit); window.resume_draft()
 assert not store.drafts() and any(t['title']=='Recovered task' for t in store.all('tasks'))


def test_cancel_removes_draft_but_invalid_save_keeps_it(window,store,app,monkeypatch):
 from PySide6.QtWidgets import QMessageBox
 from cpc.ui import Form
 pid=store.all('projects')[0]['id']
 form=Form(window,'Task',FIELDS['tasks'],dict(project_id=pid,title='Task draft',status='Not Started'),window.choices('tasks')); form.persist=lambda data:store.save('tasks',data); form.enable_draft('tasks'); form.save_recovery_draft()
 assert len(store.drafts())==1
 form.inputs['deadline'].setText('bad date'); monkeypatch.setattr(QMessageBox,'warning',lambda *args:None); form.accept()
 assert form.result()==0 and len(store.drafts())==1
 form.reject(); assert not store.drafts()


def test_main_window_copy_shortcut_preserves_text_field_behavior(window,app):
 from PySide6.QtCore import Qt
 from PySide6.QtTest import QTest
 window.show(); field=window.filter_Tasks; field.setText('Select this text'); field.setFocus(); field.selectAll(); app.processEvents()
 QTest.keyClick(field,Qt.Key_C,Qt.ControlModifier)
 assert app.clipboard().text()=='Select this text'


def test_delete_key_and_derived_dashboard_source(window,store,monkeypatch,app):
 from PySide6.QtCore import Qt
 from PySide6.QtTest import QTest
 from PySide6.QtWidgets import QMessageBox
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
 window.show(); table=window.tables['Dashboard']; target=window.data['Dashboard'][0]; source=window.source_target('Dashboard',target)
 table.setCurrentCell(0,0); table.setFocus(); QTest.keyClick(table,Qt.Key_Delete)
 assert not store.rows(f'SELECT id FROM {source[0]} WHERE id=?',(source[1],))


def test_checklist_and_version_history_delete_controls(window,store,monkeypatch):
 from PySide6.QtWidgets import QDialog,QPushButton,QMessageBox
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
 permit=next(r for r in store.all('registers') if r['record_type']=='Permit')
 window.tables['Permits'].selectRow(0)
 def remove_requirements(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Delete all requirements').click()
  dialog.accept(); return dialog.result()
 monkeypatch.setattr(QDialog,'exec',remove_requirements); window.permit_checklist()
 assert store.permit_requirements(permit['id'])==[]
 window.tables['Documents'].selectRow(0)
 def remove_versions(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Delete all revisions').click()
  dialog.accept(); return dialog.result()
 monkeypatch.setattr(QDialog,'exec',remove_versions); window.history()
 assert store.versions(store.all('documents')[0]['id'])==[]


def test_recovery_snapshot_ui_restore(window,store,monkeypatch):
 from PySide6.QtWidgets import QMessageBox
 store.recovery_snapshot(); store.save('projects',{'name':'After snapshot'}); window.refresh(); window.snapshot_table.selectRow(0)
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
 window.restore_snapshot()
 assert len(store.all('projects'))==1


def test_continuous_typing_has_maximum_autosave_interval(window,store,app):
 from cpc.ui import Form
 from PySide6.QtTest import QTest
 pid=store.all('projects')[0]['id']
 form=Form(window,'Task',FIELDS['tasks'],{'project_id':pid,'status':'Not Started'},window.choices('tasks')); form.enable_draft('tasks')
 # Accelerate the ten-second maximum timer while keeping the 750 ms idle debounce unchanged.
 form._draft_max_timer.setInterval(100)
 QTest.keyClicks(form.inputs['title'],'Continuous typing',delay=20)
 assert store.drafts() and store.drafts()[0]['values']['title'].startswith('Cont')
 form.reject()
