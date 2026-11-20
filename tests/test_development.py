import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sqlite3
import pytest
from cpc.store import Store
from cpc.development import DISCIPLINES,line_totals

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3')
 yield s
 s.db.close()

@pytest.fixture
def estimate(store):
 p=store.save('projects',{'name':'Development project'})
 package=store.save('bid_packages',dict(project_id=p,title='Electrical package',discipline='Electrical',scope='Lighting and distribution',deadline='2026-12-10'))
 bid=store.save('bids',dict(package_id=package,title='Contractor A',currency='USD',status='Received',tax_percent='8',markup_percent='10',contingency_percent='5'))
 return p,package,bid

def item(store,bid,**overrides):
 values=dict(bid_id=bid,title='Lighting',quantity='10',unit='each',material='LED',material_unit_cost='20',waste_percent='10',labor_hours_per_unit='0.5',labor_rate='60',equipment_unit_cost='2',subcontract_unit_cost='3',other_cost='5',included=1)
 values.update(overrides)
 return store.save('bid_items',values)

def test_bid_totals_exact_material_labor_tax_and_markup(store,estimate):
 p,package,bid=estimate; item(store,bid)
 t=store.bid_totals(bid)
 assert t['materials']==Decimal('220.00')
 assert t['labor_hours']==Decimal('5') and t['labor']==Decimal('300.00')
 assert t['equipment']==Decimal('20') and t['subcontract']==Decimal('30') and t['other']==Decimal('5')
 assert t['subtotal']==Decimal('575.00')
 assert t['tax']==Decimal('17.60') and t['markup']==Decimal('57.50') and t['contingency']==Decimal('28.75')
 assert t['total']==Decimal('678.85')
 store.save('bids',{'discount':'18.85'},bid)
 assert store.bid_totals(bid)['total']==Decimal('660.00')
 assert store.rows('SELECT * FROM activity WHERE project_id=?',(p,))[-1]['description'].startswith('Bids')

def test_area_quantity_and_alternate_exclusion(store,estimate):
 bid=estimate[2]
 item(store,bid,quantity_basis='Area (length × width)',length='12.5',width='8',unit='sq ft',quantity='999',waste_percent='0')
 baseline=store.bid_totals(bid)
 assert baseline['materials']==Decimal('2000')
 alternate=item(store,bid,title='Optional fixture upgrade',item_type='Alternate',included=0)
 assert store.bid_totals(bid)==baseline
 store.save('bid_items',{'included':1},alternate)
 assert store.bid_totals(bid)['included_items']==2

def test_money_round_half_up():
 t=line_totals(dict(quantity='3',material_unit_cost='0.335'))
 assert t['materials']==Decimal('1.01')

@pytest.mark.parametrize('field,value',[('material_unit_cost','-1'),('quantity','NaN'),('labor_rate','Infinity'),('quantity','abc'),('waste_percent','101'),('quantity','1.0000001'),('equipment_unit_cost','1e100')])
def test_bad_cost_input_rejected_atomically(store,estimate,field,value):
 with pytest.raises(ValueError): item(store,estimate[2],**{field:value})
 assert store.all('bid_items')==[]

def test_oversized_derived_cost_is_rejected():
 with pytest.raises(ValueError,match='too large'):
  line_totals(dict(quantity_basis='Area (length × width)',length='1000000000',width='1000000000',material_unit_cost='1000000000'))

def test_discount_limits_and_invalid_date(store,estimate):
 bid=estimate[2]; item(store,bid)
 with pytest.raises(ValueError): store.save('bids',{'discount':'999999'},bid)
 with pytest.raises(ValueError): store.save('bids',{'received':'2026-12-10','valid_until':'2026-12-01'},bid)
 with pytest.raises(ValueError): store.save('bid_packages',{'deadline':'20261210'},estimate[1])
 assert store.bid_totals(bid)['total']==Decimal('678.85')

def test_awards_and_currency_comparison(store,estimate):
 package,bid=estimate[1:]; item(store,bid)
 second=store.save('bids',dict(package_id=package,title='Contractor B',currency='CAD'))
 item(store,second,material_unit_cost='10')
 store.save('bids',{'status':'Awarded'},bid)
 with pytest.raises(ValueError,match='already'): store.save('bids',{'status':'Awarded'},second)
 comparison=store.bid_comparison(package)
 assert {r['currency'] for r in comparison}=={'USD','CAD'}
 assert any(r['status']=='Awarded' for r in comparison)

def test_cannot_move_estimate_parent(store,estimate):
 bid=estimate[2]; iid=item(store,bid)
 second=store.save('bids',dict(package_id=estimate[1],title='Second'))
 with pytest.raises(ValueError,match='fixed'): store.save('bid_items',{'bid_id':second},iid)
 with pytest.raises(ValueError,match='fixed'): store.save('bid_packages',{'project_id':999},estimate[1])

def test_meetings_action_links_and_validation(store):
 p=store.save('projects',{'name':'Project A'}); other=store.save('projects',{'name':'Project B'})
 m=store.save('meetings',dict(project_id=p,title='Coordination',meeting_date='2026-12-01',start_time='14:30',minutes='Review MEP clashes',decisions='Request revised drawings'))
 t=store.save('tasks',dict(project_id=p,title='Update MEP plan',meeting_id=m,status='Not Started'))
 assert store.all('tasks')[0]['meeting_id']==m
 with pytest.raises(ValueError): store.save('tasks',{'project_id':other},t)
 with pytest.raises(ValueError): store.save('meetings',dict(project_id=p,title='Bad date',meeting_date='not a date'))
 with pytest.raises(ValueError): store.save('meetings',dict(project_id=p,title='No date',meeting_date=''))
 with pytest.raises(ValueError): store.save('meetings',{'start_time':'25:00'},m)

def test_discipline_registers_documents_search_and_report(store):
 store.seed(); p=store.all('projects')[0]['id']
 assert {r['discipline'] for r in store.all('work_packages')}>={'Architecture','Electrical','Plumbing'}
 for kind in ('RFI','Submittal','Permit','Inspection','Punch Item','Change Request'):
  store.save('registers',dict(project_id=p,title=kind+' record',record_type=kind,discipline='Electrical',status='Open'))
 store.save('documents',dict(project_id=p,title='Panel layout DWG',category='CAD File',discipline='Electrical',drawing_type='CAD / DWG',sheet_number='E-101',building_area='Ground floor',scale='1:100',issue_purpose='For Coordination'))
 for word,kind in [('E-101','documents'),('Weekly','meetings'),('LED','bid_items'),('Retail electrical','bid_packages'),('Electrical A','bids')]:
  assert any(r['type']==kind and r['project_id']==p for r in store.search(word))
 report=store.report(p)
 for text in ('Discipline coordination','Meetings','Bid comparisons','Electrical'): assert text in report
 bid_report=store.bid_report(store.all('bids')[0]['id'])
 assert 'LED' in bid_report and 'Totals' in bid_report

def create_v1(path):
 with closing(sqlite3.connect(path)) as db:
  db.executescript((Path(__file__).parent/'fixtures/v1_schema.sql').read_text())
  db.execute("INSERT INTO projects(id,name,updated) VALUES(1,'Existing v1 Project','2026-11-01')")
  db.execute("INSERT INTO documents(id,project_id,title,category) VALUES(1,1,'Legacy drawings','Architectural Plans')")
  db.execute("INSERT INTO versions(document_id,revision,status,created) VALUES(1,'A','Approved','2026-11-01')")
  db.execute("INSERT INTO tasks(project_id,title,status) VALUES(1,'Existing task','Waiting on Someone')")
  db.commit()

def test_v1_upgrade_preserves_records_and_takes_snapshot(tmp_path):
 path=tmp_path/'v1.sqlite3'; create_v1(path); upgraded=Store(path)
 try:
  assert upgraded.db.execute('PRAGMA user_version').fetchone()[0]==11
  assert upgraded.all('projects')[0]['name']=='Existing v1 Project'
  assert upgraded.all('tasks')[0]['discipline']=='General'
  assert upgraded.versions(1)[0]['status']=='Approved'
  assert upgraded.all('documents')[0]['discipline']=='Architecture'
  with closing(sqlite3.connect(str(path)+'.before-v1.11.0.sqlite3')) as db: assert db.execute('PRAGMA user_version').fetchone()[0]==1
 finally: upgraded.db.close()
 reopened=Store(path); assert len(reopened.all('projects'))==1; reopened.db.close()

def test_v1_backup_restores_and_upgrades_without_losing_current_safety_copy(store,tmp_path):
 store.seed(); old=tmp_path/'old.sqlite3'; create_v1(old); store.restore(old)
 assert store.all('projects')[0]['name']=='Existing v1 Project'
 assert store.all('bids')==[]
 assert store.versions(1)[0]['status']=='Approved'
 assert store.db.execute('PRAGMA user_version').fetchone()[0]==11
 with closing(sqlite3.connect(str(store.path)+'.before-restore.sqlite3')) as db:
  assert db.execute('SELECT count(*) FROM bids').fetchone()[0]==2

def test_v2_backup_restores_bidding_and_meetings(store,tmp_path):
 store.seed(); before=store.bid_totals(store.all('bids')[0]['id']); backup=tmp_path/'v2.sqlite3'; store.backup(backup)
 store.save('projects',{'name':'After backup'}); store.restore(backup)
 assert len(store.all('projects'))==1
 assert store.bid_totals(store.all('bids')[0]['id'])==before
 assert len(store.all('meetings'))==1

def test_bad_backup_schema_preserves_live_data(store,tmp_path):
 store.seed(); bad=tmp_path/'bad.sqlite3'
 with closing(sqlite3.connect(bad)) as db: db.executescript('CREATE TABLE projects(id INTEGER PRIMARY KEY); PRAGMA user_version=1;')
 with pytest.raises(ValueError,match='schema'): store.restore(bad)
 assert len(store.all('bids'))==2

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

def test_new_workspaces_project_filter_and_bid_selection(window,store,app):
 w=window
 for title in ('Architecture','Engineering','Electrical','Plumbing','Mechanical / HVAC','Site & Civil','Meetings'):
  assert w.tables[title].rowCount()>=1
 w.tables['Bidding'].selectRow(0); app.processEvents()
 assert w.tables['Bids'].rowCount()==2
 second=store.save('projects',{'name':'Empty project'})
 w.refresh(); w.project_filter.setCurrentIndex(w.project_filter.findData(second)); app.processEvents()
 assert w.tables['Architecture'].rowCount()==0 and w.tables['Bids'].rowCount()==0
 assert w.tables['Tasks'].rowCount()==0 and w.tables['Dashboard'].rowCount()==0
 w.project_filter.setCurrentIndex(0); app.processEvents(); assert w.tables['Tasks'].rowCount()==2

def test_meeting_create_task_from_real_form(window,store,monkeypatch):
 from cpc.ui import Form
 def submit(form):
  form.inputs['title'].setText('Meeting action from UI')
  form.accept(); return form.result()
 monkeypatch.setattr(Form,'exec',submit)
 window.tables['Meetings'].selectRow(0); window.meeting_task()
 task=store.all('tasks')[0]
 assert task['meeting_id']==store.all('meetings')[0]['id']
 assert task['title']=='Meeting action from UI'

def test_new_discipline_form_persists(window,store,monkeypatch):
 from cpc.ui import Form
 def submit(form):
  form.inputs['title'].setText('Plumbing riser coordination')
  form.accept(); return form.result()
 monkeypatch.setattr(Form,'exec',submit)
 window.edit('Plumbing')
 saved=store.all('work_packages')[0]
 assert saved['discipline']=='Plumbing' and saved['title']=='Plumbing riser coordination'

def test_bid_item_dialog_add_edit_and_live_preview(window,store,app,monkeypatch):
 from PySide6.QtWidgets import QDialog,QPushButton,QLineEdit
 from cpc.ui import Form
 window.tables['Bidding'].selectRow(0); window.tables['Bids'].selectRow(0)
 bid_id=window.selected('Bids')['id']
 def submit(form):
  form.inputs['title'].setText('UI conduit')
  form.inputs['quantity'].setText('10')
  form.inputs['material_unit_cost'].setText('3')
  app.processEvents(); assert '30.00' in form.preview.text()
  form.accept(); return form.result()
 def run_dialog(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='+ Cost item').click()
  dialog.accept(); return dialog.result()
 monkeypatch.setattr(Form,'exec',submit); monkeypatch.setattr(QDialog,'exec',run_dialog)
 window.cost_items()
 assert any(r['title']=='UI conduit' for r in store.rows('SELECT * FROM bid_items WHERE bid_id=?',(bid_id,)))


def test_validation_keeps_cost_form_open(app,store,estimate,monkeypatch):
 from PySide6.QtWidgets import QMessageBox
 from cpc.ui import Form
 from cpc.store import FIELDS
 from cpc.development_ui import DEFAULTS
 errors=[]; monkeypatch.setattr(QMessageBox,'warning',lambda *args:errors.append(args[-1]))
 form=Form(None,'Cost item',FIELDS['bid_items'],{**DEFAULTS['bid_items'],'bid_id':estimate[2]},choices={'bid_id':[('Bid',estimate[2])]})
 form.persist=lambda values:store.save('bid_items',values)
 form.inputs['title'].setText('Invalid quantity'); form.inputs['quantity'].setText('-1'); form.accept()
 assert errors and form.result()==0 and not store.all('bid_items')
 form.close()

def test_later_cad_revisions_keep_resubmission_review_flag(store,tmp_path):
 p=store.save('projects',{'name':'CAD project'})
 d=store.save('documents',dict(project_id=p,title='DWG set',drawing_type='CAD / DWG'))
 store.add_version(d,'A',status='Approved')
 store.add_version(d,'B',status='Draft')
 store.add_version(d,'C',status='Draft')
 assert store.versions(d)[0]['resubmission']==1
 assert store.versions(d)[-1]['status']=='Approved'


def test_unpriced_bid_is_identified_separately(store,estimate):
 item(store,estimate[2]); empty=store.save('bids',dict(package_id=estimate[1],title='Invited contractor',status='Invited'))
 comparison=store.bid_comparison(estimate[1])
 assert comparison[-1]['id']==empty
 assert comparison[-1]['pricing_status']=='No included cost items'

def test_project_filter_keeps_linked_contact_search_and_dashboard_counts(window,store,app):
 project=store.all('projects')[0]['id']
 window.project_filter.setCurrentIndex(window.project_filter.findData(project))
 window.search_input.setText('Alex'); app.processEvents()
 assert any(r['type']=='contacts' for r in window.data['Search'])
 empty=store.save('projects',{'name':'Empty dashboard'})
 window.refresh(); window.project_filter.setCurrentIndex(window.project_filter.findData(empty)); app.processEvents()
 assert '0 outstanding tasks' in window.dashboard_summary.text()


def test_bid_and_expanded_project_reports_render_to_pdf(store,app,tmp_path):
 from PySide6.QtGui import QTextDocument
 from PySide6.QtPrintSupport import QPrinter
 store.seed()
 for title,html in [('bid',store.bid_report(store.all('bids')[0]['id'])),('project',store.report(store.all('projects')[0]['id']))]:
  doc=QTextDocument(); doc.setHtml(html); printer=QPrinter(); printer.setOutputFormat(QPrinter.PdfFormat)
  path=tmp_path/(title+'.pdf'); printer.setOutputFileName(str(path)); doc.print_(printer)
  assert path.read_bytes().startswith(b'%PDF') and path.stat().st_size>1000
