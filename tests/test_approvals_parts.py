import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sqlite3
import csv
import zipfile
import pytest
from cpc.store import Store

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()
@pytest.fixture
def project(store):return store.save('projects',{'name':'Example project'})
@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])

def approval(store,p,**values):return store.save('approvals',dict(project_id=p,title='Approve replacement parts',**values))
def receipt(store,p,**values):return store.save('receipts',{'project_id':p,'title':'Parts cost','supplier_name':'Example supplier',**values})


def test_approval_price_and_decisions_preserve_prior_snapshot(store,project):
 rid=approval(store,project,price='123.456',status='Approved',reviewed_by='Example reviewer');assert store.approval_rows()[0]['price']=='123.46' and store.approval_rows()[0]['review_date']
 store.save('approvals',{'price':'150','status':'Approved'},rid);row=store.approval_rows()[0]
 assert row['status']=='Pending Review' and row['reviewed_by']=='' and row['review_date']==''
 events=store.approval_events(rid);assert events[0]['price']=='150.00' and events[-1]['price']=='123.46' and events[-1]['status']=='Approved'
 store.save('approvals',{'status':'Approved','reviewed_by':'Reviewer 2'},rid);store.save('approvals',{'notes':'Office filing note'},rid);assert store.approval_rows()[0]['status']=='Approved'
 store.save('approvals',{'description':'Changed scope'},rid);assert store.approval_rows()[0]['status']=='Pending Review'


@pytest.mark.parametrize('values',[{'price':'-1'},{'price':'NaN'},{'price':'abc'},{'price':'','status':'Approved'},{'price':'10','currency':'XYZ'},{'price':'10','review_date':'11/19/2026'}])
def test_invalid_approval_prices_and_dates_rejected(store,project,values):
 with pytest.raises(ValueError):approval(store,project,**values)
 assert store.all('approvals')==[] and store.rows('SELECT * FROM approval_history')==[]


def test_explicit_zero_can_be_approved_and_draft_price_can_be_unknown(store,project):
 rid=approval(store,project,status='Draft');assert store.approval_rows()[0]['price']==''
 store.save('approvals',{'price':'0','status':'Approved'},rid);assert store.approval_rows()[0]['price']=='0.00'


def test_approval_contract_matching_and_nonfinancial_tracking(store,project):
 b=store.save('budgets',dict(project_id=project,title='Parts',base_amount='1000'));c=store.save('contracts',dict(project_id=project,title='Work',contractor_name='Example',budget_id=b,original_amount='500',status='Active'))
 rid=approval(store,project,contract_id=c,price='150',status='Approved');assert store.budget_totals(b)['projected_total']==Decimal('500.00')
 with pytest.raises(ValueError,match='Unlink'):store.save('contracts',{'currency':'EUR','budget_id':None},c)
 other=store.save('projects',{'name':'Other'})
 with pytest.raises(ValueError):approval(store,other,contract_id=c,price='50')
 store.delete_records([('contracts',c)]);assert store.all('approvals')[0]['contract_id'] is None and store.all('approvals')[0]['price']=='150.00'


def test_approval_files_download_and_changes_reset_review(store,project,tmp_path):
 rid=approval(store,project,price='100',status='Approved');source=tmp_path/'quote.pdf';source.write_bytes(b'%PDF-original quote');fid=store.import_finance_files('approvals',rid,[source])[0]
 assert store.approval_rows()[0]['status']=='Pending Review'
 out=tmp_path/'download.pdf';store.save_finance_copy(fid,out);assert out.read_bytes()==source.read_bytes()
 store.save('approvals',{'status':'Approved'},rid);safety=store.delete_records([('finance_files',fid)]);assert store.approval_rows()[0]['status']=='Pending Review'
 store.restore(safety);assert store.approval_rows()[0]['status']=='Approved' and store.checked_finance_file(fid)[1].read_bytes()==source.read_bytes()
 assert any(e['supporting_files']=='quote.pdf' for e in store.approval_events(rid))


def test_approval_search_reports_exports_and_project_delete_restore(store,project,tmp_path):
 from cpc.exports import department_rows,write_docx
 rid=approval(store,project,price='80',discipline='Electrical',status='Pending Review');assert any(r['type']=='approvals' for r in store.search('replacement parts'))
 assert '80.00' in store.report(project) and any(r['record_type']=='Approval' for r in department_rows(store,['Electrical'],project))
 out=tmp_path/'approvals.docx';write_docx(out,'Approvals',store.approval_rows())
 with zipfile.ZipFile(out) as z:assert b'80.00' in z.read('word/document.xml')
 safety=store.delete_records([('projects',project)]);assert store.all('approvals')==[] and store.rows('SELECT * FROM approval_history')==[]
 store.restore(safety);assert len(store.approval_events(rid))==1


def test_approval_ui_price_form_drafts_and_deadline_dashboard(store,project,app,monkeypatch):
 from cpc.ui import Window,Form
 from PySide6.QtWidgets import QMessageBox
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 w=Window(store)
 def submit(form):
  form.inputs['title'].setText('Price review');form.inputs['price'].setText('200');form.inputs['deadline'].setText('2020-01-01');form.inputs['status'].setCurrentText('Pending Review');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);w.edit('Approvals');assert store.approval_rows()[0]['price']=='200.00' and w.tables['Approvals'].rowCount()==1
 assert any(r.get('_source_table')=='approvals' for r in w.data['Dashboard'])
 w.hide_sidebar_section('Approvals');w.refresh();assert any(r.get('_source_table')=='approvals' for r in w.data['Dashboard'])
 store.save('approvals',{'status':'Approved'},store.all('approvals')[0]['id']);w.refresh();assert not any(r.get('_source_table')=='approvals' for r in w.data['Dashboard']);w.close()


def test_reimbursement_is_not_counted_twice_and_contract_material_cost_is_not_extra_commitment(store,project):
 b=store.save('budgets',dict(project_id=project,title='Project budget',base_amount='2000'));c=store.save('contracts',dict(project_id=project,title='Labor and parts contract',contractor_name='Example',budget_id=b,original_amount='1000',status='Active'))
 rid=receipt(store,project,contract_id=c,actual_amount='200',source_type='Contractor Purchase',purchaser_name='Example contractor',payment_responsibility='Reimburse Purchaser',reimbursement_amount='150')
 assert store.all('receipts')[0]['reimbursement_status']=='Pending Review'
 t=store.budget_totals(b);assert t['actual_amount']==Decimal('200.00') and t['projected_total']==Decimal('1000.00')
 store.save('receipts',{'reimbursement_status':'Paid'},rid);assert store.all('receipts')[0]['reimbursed_date'] and store.budget_totals(b)==t
 receipt(store,project,budget_id=b,actual_amount='50',source_type='Company Stock',supplier_name='')
 assert store.all('receipts')[0]['supplier_name']=='Company stock' and store.budget_totals(b)['projected_total']==Decimal('1050.00')


@pytest.mark.parametrize('source',['Company Purchase','Company Stock','Employee Purchase','Contractor Purchase','Owner Supplied','Other'])
def test_parts_budget_inclusion_is_independent_of_source_and_payer(store,project,source):
 b=store.save('budgets',dict(project_id=project,title='Parts',base_amount='1000'))
 rid=receipt(store,project,budget_id=b,actual_amount='120',source_type=source,payment_responsibility='No Company Payment')
 assert store.budget_totals(b)['actual_amount']==Decimal('120.00')
 store.save('receipts',{'include_in_budget':0},rid);assert store.budget_totals(b)['actual_amount']==Decimal('0.00')


@pytest.mark.parametrize('values',[{'actual_amount':'100','reimbursement_amount':'101','payment_responsibility':'Reimburse Purchaser'},{'reimbursement_status':'Paid','payment_responsibility':'Reimburse Purchaser'},{'reimbursement_amount':'50','payment_responsibility':'Company / Direct Cost'},{'source_type':'Unknown'},{'reimbursement_amount':'-1','payment_responsibility':'Reimburse Purchaser'}])
def test_invalid_reimbursement_values_do_not_create_receipts(store,project,values):
 with pytest.raises(ValueError):receipt(store,project,**values)
 assert store.all('receipts')==[]


def test_source_and_reimbursement_amount_changes_reset_existing_receipt_approval(store,project):
 rid=receipt(store,project,actual_amount='100',status='Approved');store.save('receipts',{'source_type':'Contractor Purchase','payment_responsibility':'Reimburse Purchaser','reimbursement_amount':'50'},rid);assert store.all('receipts')[0]['status']=='Pending Review'
 store.save('receipts',{'status':'Approved'},rid);store.save('receipts',{'reimbursement_status':'Paid'},rid);assert store.all('receipts')[0]['status']=='Approved'
 store.save('receipts',{'reimbursement_amount':'60'},rid);assert store.all('receipts')[0]['status']=='Pending Review'


def test_parts_form_export_includes_source_and_reimbursement_without_extra_budget_cost(store,project,app,tmp_path,monkeypatch):
 from cpc.ui import Window,Form
 from cpc.exports import department_rows
 from PySide6.QtWidgets import QMessageBox
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail);w=Window(store)
 def submit(form):
  form.inputs['title'].setText('Stock connectors');form.inputs['source_type'].setCurrentText('Company Stock');form.inputs['actual_amount'].setText('75');form.inputs['discipline'].setCurrentText('Electrical');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);w.edit('Receipts');row=store.receipt_rows()[0];assert row['actual_amount']=='75.00' and row['source_type']=='Company Stock'
 out=tmp_path/'parts.csv';store.export(out,store.receipt_rows())
 with out.open(encoding='utf-8-sig',newline='') as stream:export=list(csv.DictReader(stream))
 assert export[0]['source_type']=='Company Stock' and export[0]['reimbursement_status']=='Not Applicable'
 assert 'source type: Company Stock' in department_rows(store,['Electrical'],project)[0]['details'];w.close()


def test_schema9_upgrade_and_restore_preserve_existing_costs_and_orders(store,tmp_path):
 path=tmp_path/'legacy.sqlite3'
 with closing(sqlite3.connect(path)) as db:db.executescript((Path(__file__).parent/'fixtures/v9_database.sql').read_text())
 upgraded=Store(path)
 try:
  assert upgraded.db.execute('PRAGMA user_version').fetchone()[0]==12 and upgraded.all('approvals')==[]
  p=upgraded.all('projects')[0]['id'];assert upgraded.section_order(p,'sidebar')[0]=='Contracts' and 'Approvals' in upgraded.section_order(p,'sidebar')
  row=upgraded.all('receipts')[0];assert row['actual_amount']=='1295.50' and row['reimbursement_status']=='Not Applicable'
 finally:upgraded.db.close()
 backup=str(path)+'.before-v1.11.0.sqlite3'
 with closing(sqlite3.connect(backup)) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==9
 store.restore(backup);assert store.all('approvals')==[] and len(store.all('receipts'))==1


def test_parts_outside_labor_only_contract_add_to_budget_as_separate_cost(store,project):
 b=store.save('budgets',dict(project_id=project,title='Labor and materials',base_amount='2000'));store.save('contracts',dict(project_id=project,title='Labor only',contractor_name='Example',budget_id=b,original_amount='1000',status='Active'))
 receipt(store,project,budget_id=b,actual_amount='200',source_type='Company Stock',supplier_name='')
 assert store.budget_totals(b)['projected_total']==Decimal('1200.00')
 receipt(store,project,budget_id=b,actual_amount='75',source_type='Employee Purchase',payment_responsibility='Reimburse Purchaser',reimbursement_amount='75',reimbursement_status='Paid')
 assert store.budget_totals(b)['projected_total']==Decimal('1275.00')


def test_approval_file_button_uploads_and_downloads_original(store,project,app,tmp_path,monkeypatch):
 from cpc.ui import Window
 from cpc.table import DataTable
 from PySide6.QtWidgets import QDialog,QPushButton,QFileDialog,QMessageBox
 rid=approval(store,project,price='100',status='Approved');source=tmp_path/'estimate.docx';source.write_bytes(b'original supporting bytes');out=tmp_path/'saved.docx'
 monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *args:([str(source)],''));monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(out),''))
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 def run(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Add files…').click();dialog.findChild(DataTable).selectRow(0);next(b for b in dialog.findChildren(QPushButton) if b.text()=='Save a copy…').click();dialog.accept();return dialog.result()
 monkeypatch.setattr(QDialog,'exec',run);w=Window(store);w.tables['Approvals'].selectRow(0);next(b for b in w.primary_commands['Approvals'] if b.text()=='Files').click()
 assert out.read_bytes()==source.read_bytes() and store.approval_rows()[0]['status']=='Pending Review';w.close()
