import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from contextlib import closing
import sqlite3
import zipfile
import pytest
from cpc.store import Store
from cpc.scope import STARTERS,PROTECTED_SECTIONS

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()
@pytest.fixture
def project(store):return store.save('projects',{'name':'Fictional mixed-use project','address':'100 Example Lane'})
@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])

def system(store,p,**values):
 return store.save('scope_items',dict(project_id=p,title='Hybrid water heater',category='Energy & Utilities',discipline='Plumbing',energy_source='Hybrid (electric / gas)',**values))


def test_profile_preserves_unknown_decisions_and_editable_use(store,project):
 rid=store.save('project_profiles',dict(project_id=project,title='Project profile',use_type='Mixed Use',kitchen='Undecided',bathroom='Yes',stories='2',residential_units='4',floor_area='2400'))
 assert store.profile(project)['kitchen']=='Undecided'
 store.save('project_profiles',{'kitchen':'No'},rid);assert store.profile(project)['kitchen']=='No'
 with pytest.raises(ValueError,match='already has'):store.save('project_profiles',dict(project_id=project,title='Duplicate'))
 with pytest.raises(ValueError,match='whole'):store.save('project_profiles',{'stories':'2.5'},rid)


def test_checkbox_answers_save_no_yes_and_recover_draft(store,project,app):
 from cpc.ui import Window,Form
 from cpc.scope_ui import AnswerChecks
 w=Window(store);form=Form(w,'Project profile',['project_id','title','kitchen'],{'project_id':project,'title':'Profile'},w.choices('project_profiles'))
 assert isinstance(form.inputs['kitchen'],AnswerChecks)
 assert form.values()['kitchen']=='Undecided'
 form.enable_draft('project_profiles');form.inputs['kitchen'].boxes['No'].click();form.save_recovery_draft()
 assert form.values()['kitchen']=='No' and store.drafts()[0]['values']['kitchen']=='No'
 form.inputs['kitchen'].boxes['Yes'].click();form.persist=lambda v:store.save('project_profiles',v);form.accept()
 assert store.profile(project)['kitchen']=='Yes' and store.drafts()==[];w.close()


def test_standard_prompts_are_opt_in_idempotent_and_project_specific(store,project):
 other=store.save('projects',{'name':'Other'})
 assert store.all('scope_items')==[]
 count=store.add_scope_starters(project);assert count==len(STARTERS) and store.add_scope_starters(project)==0
 assert not store.rows('SELECT id FROM scope_items WHERE project_id=?',(other,))
 assert all(row['applicability']=='Undecided' for row in store.all('scope_items'))
 for text in ('Stairs','trusses','Elevator','Commissioning','Warranties'):assert any(text.casefold() in row['title'].casefold() for row in store.all('scope_items'))


@pytest.mark.parametrize('kind,value',[('Number','NaN'),('Number','abc'),('Yes / No','Maybe'),('Date','11/18/2026'),('URL','file:///C:/private')])
def test_invalid_custom_typed_values_rejected(store,project,kind,value):
 with pytest.raises(ValueError):store.save('custom_fields',dict(project_id=project,title='Custom spec',field_type=kind,value=value))


def test_custom_field_requirements_keep_blank_information_visible(store,project):
 sid=system(store,project);rid=store.save('custom_fields',dict(project_id=project,scope_item_id=sid,title='Required efficiency rating',field_type='Number',unit='UEF',is_required=1))
 assert store.scope_rows('custom_fields')[0]['completion']=='Missing required value'
 store.save('custom_fields',{'value':'3.5'},rid);assert store.scope_rows('custom_fields')[0]['completion']=='Recorded'
 other=store.save('projects',{'name':'Other'})
 with pytest.raises(ValueError,match='belong'):store.save('custom_fields',dict(project_id=other,scope_item_id=sid,title='Wrong'))


def test_rebates_preserve_amounts_and_never_reduce_budget(store,project):
 sid=system(store,project);b=store.save('budgets',dict(project_id=project,title='Equipment',base_amount='10000'))
 r=store.save('rebates',dict(project_id=project,title='Fictional utility incentive',provider='Example utility',scope_item_id=sid,requirements_url='https://example.com/requirements',application_url='https://example.com/apply',deadline='2026-12-01',estimated_amount='500',status='Researching'))
 store.save('rebates',{'status':'Received','approved_amount':'450','received_amount':'450'},r)
 assert str(store.budget_totals(b)['remaining_funds'])=='10000.00'
 assert store.scope_rows('rebates')[0]['received_amount']=='450.00'
 with pytest.raises(ValueError):store.save('rebates',{'estimated_amount':'-1'},r)
 with pytest.raises(ValueError):store.save('rebates',{'requirements_url':'javascript:alert(1)'},r)


def test_section_visibility_persists_per_project_without_deleting_data(store,project,app):
 from cpc.ui import Window
 other=store.save('projects',{'name':'Other'});sid=system(store,project,deadline='2020-01-01',hidden=1)
 store.set_hidden_sections(project,['Scope & Systems','Rebates & Incentives','Electrical'])
 w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(project));w.refresh()
 assert w.nav.item(w.navigation.index('Electrical')).isHidden()
 assert w.tables['Scope & Systems'].rowCount()==0
 assert any(r.get('_source_table')=='scope_items' and r['_source_id']==sid for r in w.data['Dashboard'])
 assert any(r['type']=='scope_items' for r in store.search('Hybrid'))
 w.show_hidden_scope.setChecked(True);assert w.tables['Scope & Systems'].rowCount()==1
 w.project_filter.setCurrentIndex(w.project_filter.findData(other));assert not w.nav.item(w.navigation.index('Electrical')).isHidden()
 from PySide6.QtCore import Qt
 w.project_filter.setCurrentIndex(0);assert all(w.nav.item(i).isHidden()==(w.nav.item(i).data(Qt.UserRole)=='Regulatory & Permits') for i in range(w.nav.count()))
 w.close();reopened=Store(store.path)
 try:assert reopened.hidden_sections(project)=={'Scope & Systems','Rebates & Incentives','Electrical'} and len(reopened.all('scope_items'))==1
 finally:reopened.db.close()
 for section in PROTECTED_SECTIONS:
  with pytest.raises(ValueError):store.set_hidden_sections(project,[section])


def test_hidden_navigation_returns_to_safe_page_and_restores(store,project,app):
 from cpc.ui import Window
 w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(project));w.nav.setCurrentRow(w.navigation.index('Electrical'))
 store.set_hidden_sections(project,['Electrical']);w.refresh();assert w.current=='Dashboard' and w.stack.currentIndex()==0
 store.set_hidden_sections(project,[]);w.refresh();assert not w.nav.item(w.navigation.index('Electrical')).isHidden();w.close()


def test_scope_rebate_and_change_order_reports_include_full_project_data(store,project,tmp_path):
 from cpc.exports import department_rows,write_docx
 sid=system(store,project,hidden=1,specifications='Equipment capacity: custom')
 store.save('custom_fields',dict(project_id=project,scope_item_id=sid,title='Installation type',value='Replacement'))
 store.save('rebates',dict(project_id=project,scope_item_id=sid,title='Utility grant'))
 report=store.report(project);assert 'Hybrid water heater' in report and 'Installation type' in report and 'Utility grant' in report
 rows=department_rows(store,['Plumbing'],project);assert any(r['title']=='Hybrid water heater' for r in rows)
 out=tmp_path/'scope.docx';write_docx(out,'Scope',store.scope_rows('scope_items'))
 with zipfile.ZipFile(out) as z:assert b'Hybrid water heater' in z.read('word/document.xml')
 store.export(tmp_path/'scope.csv',store.scope_rows('scope_items'));assert 'Hybrid water heater' in (tmp_path/'scope.csv').read_text(encoding='utf-8-sig')


def test_generic_files_can_round_trip_edit_and_delete_with_record(store,project,tmp_path,app):
 from cpc.file_editor import FileEditor
 from cpc.ui import Window
 sid=system(store,project);source=tmp_path/'specification.txt';source.write_text('Original specification');fid=store.import_finance_files('scope_items',sid,[source])[0]
 out=tmp_path/'download.txt';store.save_finance_copy(fid,out);assert out.read_bytes()==source.read_bytes()
 assert store.project_for('finance_files',store.all('finance_files')[0])==project
 w=Window(store);editor=FileEditor(w,store,fid);editor.editor.setPlainText('Revised specification');assert editor.save_version(automatic=True)
 assert len(store.finance_files('scope_items',sid))==2 and store.checked_finance_file(fid)[1].read_text()=='Original specification'
 editor.close();w.close();zipout=tmp_path/'specs.zip';store.export_finance_zip('scope_items',sid,zipout)
 with zipfile.ZipFile(zipout) as archive:assert len(archive.namelist())==3
 backup=store.delete_records([('scope_items',sid)]);assert store.all('finance_files')==[]
 store.restore(backup);assert len(store.finance_files('scope_items',sid))==2 and store.checked_finance_file(fid)[1].read_text()=='Original specification'


@pytest.mark.parametrize('table',['projects','project_profiles','rebates','custom_fields','tasks','documents','meetings','registers','contract_changes','work_packages','bids','bid_items'])
def test_attachment_support_across_project_areas(store,project,tmp_path,table):
 if table=='projects':rid=project
 elif table in ('project_profiles','rebates','custom_fields','tasks','documents','work_packages'):rid=store.save(table,dict(project_id=project,title='Supporting record',**({'status':'Not Started'} if table=='tasks' else {})))
 elif table=='meetings':rid=store.save(table,dict(project_id=project,title='Meeting',meeting_date='2026-11-18'))
 elif table=='registers':rid=store.save(table,dict(project_id=project,title='Permit',record_type='Permit'))
 elif table=='contract_changes':
  contract=store.save('contracts',dict(project_id=project,title='Contract',contractor_name='Example'));rid=store.save(table,dict(contract_id=contract,title='Change'))
 else:
  pack=store.save('bid_packages',dict(project_id=project,title='Package'));bid=store.save('bids',dict(package_id=pack,title='Estimate'))
  rid=bid if table=='bids' else store.save('bid_items',dict(bid_id=bid,title='Cost item'))
 source=tmp_path/'evidence.pdf';source.write_bytes(b'%PDF original bytes');fid=store.import_finance_files(table,rid,[source])[0]
 assert store.attachment_owner(store.checked_finance_file(fid)[0])==(table,rid)
 assert store.finance_files(table,rid)[0]['original_name']=='evidence.pdf'
 assert store.project_for('finance_files',store.checked_finance_file(fid)[0])==project
 store.delete_records([(table,rid)]);assert not store.rows('SELECT id FROM finance_files WHERE id=?',(fid,))


def test_deleting_scope_unlinks_rebate_and_deletes_custom_fields(store,project):
 sid=system(store,project);r=store.save('rebates',dict(project_id=project,scope_item_id=sid,title='Rebate'));store.save('custom_fields',dict(project_id=project,scope_item_id=sid,title='Specification'))
 store.delete_records([('scope_items',sid)]);assert store.all('custom_fields')==[] and store.all('rebates')[0]['scope_item_id'] is None


def test_project_delete_removes_visibility_scope_and_files(store,project,tmp_path):
 sid=system(store,project);store.set_hidden_sections(project,['Electrical']);source=tmp_path/'original.csv';source.write_text('item,cost\nA,10');store.import_finance_files('scope_items',sid,[source])
 store.save('project_profiles',dict(project_id=project,title='Profile'));store.save('rebates',dict(project_id=project,title='Rebate'))
 backup=store.delete_records([('projects',project)]);assert not store.rows('SELECT * FROM project_sections')
 for table in ('projects','scope_items','project_profiles','rebates','finance_files'):assert store.all(table)==[]
 store.restore(backup);assert store.hidden_sections(project)=={'Electrical'} and len(store.all('finance_files'))==1


def test_v7_upgrade_retains_attachment_ids_bytes_and_finance(store,tmp_path):
 old=tmp_path/'v7.sqlite3';legacy=tmp_path/'legacy.txt';legacy.write_bytes(b'legacy agreement')
 with closing(sqlite3.connect(old)) as db:
  db.executescript((Path(__file__).parent/'fixtures/v7_database.sql').read_text());db.execute('UPDATE finance_files SET file_path=?',(str(legacy),));db.commit()
 upgraded=Store(old)
 try:
  assert upgraded.db.execute('PRAGMA user_version').fetchone()[0]==12
  fid=upgraded.all('finance_files')[0]['id'];copy=tmp_path/'saved.txt';upgraded.save_finance_copy(fid,copy);assert copy.read_bytes()==legacy.read_bytes()
  assert len(upgraded.all('contracts'))==1 and upgraded.all('scope_items')==[]
  assert upgraded.all('finance_files')[0]['owner_table']==''
 finally:upgraded.db.close()
 with closing(sqlite3.connect(str(old)+'.before-v1.11.0.sqlite3')) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==7
 store.restore(str(old)+'.before-v1.11.0.sqlite3');assert len(store.all('finance_files'))==1 and store.all('project_profiles')==[]


def test_generic_file_manager_ui_adds_and_saves_scope_original(store,project,app,tmp_path,monkeypatch):
 from cpc.ui import Window
 from PySide6.QtWidgets import QFileDialog,QDialog,QPushButton,QMessageBox
 sid=system(store,project);source=tmp_path/'truss.dwg';source.write_bytes(b'original drawing');out=tmp_path/'download.dwg'
 monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *args:([str(source)],''));monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(out),''))
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 def run(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Add files…').click();dialog.findChild(DataTable).selectRow(0)
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Save a copy…').click();dialog.accept();return dialog.result()
 from cpc.table import DataTable
 monkeypatch.setattr(QDialog,'exec',run);w=Window(store);w.tables['Scope & Systems'].selectRow(0);w.record_files('Scope & Systems');assert out.read_bytes()==source.read_bytes();w.close()


def test_custom_category_is_filterable_and_custom_choices_save(store,project,app,monkeypatch):
 from cpc.ui import Window,Form
 from PySide6.QtWidgets import QMessageBox
 w=Window(store)
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 def submit(form):
  form.inputs['project_id'].setCurrentIndex(form.inputs['project_id'].findData(project));form.inputs['title'].setText('Special installation');form.inputs['category'].setEditText('Custom acoustics');form.inputs['system_type'].setEditText('Acoustic panels');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);w.edit('Scope & Systems')
 assert store.all('scope_items')[0]['category']=='Custom acoustics' and store.all('scope_items')[0]['system_type']=='Acoustic panels'
 assert w.scope_category.findText('Custom acoustics')>=0
 w.scope_category.setCurrentText('Custom acoustics');assert w.tables['Scope & Systems'].rowCount()==1;w.close()


def test_minimal_view_preset_can_be_saved_and_restored(store,project,app,monkeypatch):
 from cpc.ui import Window
 from PySide6.QtWidgets import QDialog,QPushButton
 w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(project))
 def run(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Minimal view').click();dialog.accept();return dialog.result()
 monkeypatch.setattr(QDialog,'exec',run);w.customize_sections()
 assert 'Electrical' in store.hidden_sections(project) and not store.hidden_sections(project)&PROTECTED_SECTIONS
 w.show_all_sections();assert not store.hidden_sections(project);w.close()


def test_legacy_document_revision_original_can_be_saved(store,project,tmp_path):
 doc=store.save('documents',dict(project_id=project,title='Approved plan'));source=tmp_path/'plan.dwg';source.write_bytes(b'original CAD bytes');store.add_version(doc,'A',status='Approved',file_path=str(source))
 version=store.versions(doc)[0];out=tmp_path/'copy.dwg';store.save_revision_copy(version['id'],out);assert out.read_bytes()==source.read_bytes()
 with pytest.raises(ValueError):store.save_revision_copy(version['id'],version['file_path'])
 assert store.versions(doc)[0]['status']=='Approved'


def test_restore_rejects_orphan_polymorphic_file_link_before_replacing_live_data(store,project,tmp_path):
 sid=system(store,project);source=tmp_path/'file.txt';source.write_text('original');store.import_finance_files('scope_items',sid,[source]);bad=tmp_path/'bad.sqlite3';store.backup(bad)
 with closing(sqlite3.connect(bad)) as db:db.execute('UPDATE finance_files SET owner_id=99999');db.commit()
 with pytest.raises(ValueError):store.restore(bad)
 assert len(store.finance_files('scope_items',sid))==1
