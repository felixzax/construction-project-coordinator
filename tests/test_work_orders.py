import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from decimal import Decimal
from contextlib import closing
import sqlite3
import csv
import zipfile
import pytest
from cpc.store import Store

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()
@pytest.fixture
def project(store):return store.save('projects',{'name':'Work order project','address':'100 Example Street'})
@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])

def order(store,p,**values):return store.save('work_orders',{'project_id':p,'title':'Tenant improvement work',**values})


def test_separate_valuation_fee_rounding_unknown_and_zero(store,project):
 rid=order(store,project,job_valuation='25000.125',permit_fee='650.125');row=store.work_order_rows()[0]
 assert row['job_valuation']=='25000.13' and row['permit_fee']=='650.13' and row['site_address']=='100 Example Street' and row['fee_status']=='Estimated'
 store.save('work_orders',{'job_valuation':'','permit_fee':'','fee_status':'Unknown'},rid);assert store.work_order_rows()[0]['job_valuation']==''
 store.save('work_orders',{'job_valuation':'0','permit_fee':'0','fee_status':'Paid'},rid);assert store.work_order_rows()[0]['job_valuation']=='0.00' and store.work_order_rows()[0]['permit_fee']=='0.00'


@pytest.mark.parametrize('values',[{'job_valuation':'-1'},{'permit_fee':'NaN'},{'permit_fee':'abc'},{'currency':'XYZ'},{'fee_status':'Paid'},{'permit_fee':'20','fee_status':'Waived'},{'issued_date':'11/20/2026'},{'start_date':'2026-12-02','deadline':'2026-12-01'}])
def test_invalid_amounts_and_dates_do_not_save(store,project,values):
 with pytest.raises(ValueError):order(store,project,**values)
 assert store.all('work_orders')==[]


def test_waiver_and_changed_paid_fee_require_new_confirmation(store,project):
 rid=order(store,project,fee_status='Waived');assert store.work_order_rows()[0]['permit_fee']=='0.00'
 store.save('work_orders',{'permit_fee':'100','fee_status':'Paid'},rid);assert store.work_order_rows()[0]['fee_status']=='Paid'
 store.save('work_orders',{'permit_fee':'120','fee_status':'Paid'},rid);row=store.work_order_rows()[0];assert row['fee_status']=='Assessed' and 'Fee changed' in row['notes']
 store.save('work_orders',{'fee_status':'Paid'},rid);assert store.work_order_rows()[0]['fee_status']=='Paid'
 activity=store.rows('SELECT description FROM activity WHERE project_id=?',(project,));assert any('permit fee 100.00' in r['description'] for r in activity)


def test_permit_and_contract_context_validate_and_survive_unlink_deletion(store,project):
 permit=store.save('registers',dict(project_id=project,title='County permit',record_type='Permit',jurisdiction_type='County',jurisdiction_name='Example County'))
 contract=store.save('contracts',dict(project_id=project,title='Work contract',contractor_name='Example company',currency='USD'))
 rid=order(store,project,permit_id=permit,contract_id=contract,job_valuation='10000',permit_fee='250');row=store.work_order_rows()[0]
 assert row['jurisdiction_type']=='County' and row['jurisdiction_name']=='Example County'
 other=store.save('projects',{'name':'Other project'})
 with pytest.raises(ValueError):order(store,other,permit_id=permit)
 with pytest.raises(ValueError):order(store,project,contract_id=contract,currency='EUR')
 with pytest.raises(ValueError,match='work orders'):store.save('registers',{'record_type':'RFI'},permit)
 with pytest.raises(ValueError,match='work orders'):store.save('registers',{'project_id':other},permit)
 with pytest.raises(ValueError,match='work orders'):store.save('contracts',{'currency':'EUR'},contract)
 store.delete_records([('registers',permit),('contracts',contract)]);row=store.work_order_rows()[0]
 assert row['permit_id'] is None and row['contract_id'] is None and row['jurisdiction_name']=='Example County' and row['permit_fee']=='250.00'


def test_valuation_and_fee_are_not_automatic_budget_expenses(store,project):
 budget=store.save('budgets',dict(project_id=project,title='Budget',base_amount='50000'));contract=store.save('contracts',dict(project_id=project,title='Contract',contractor_name='Example',budget_id=budget,original_amount='10000',status='Active'))
 before=store.budget_totals(budget);order(store,project,contract_id=contract,job_valuation='25000',permit_fee='500',fee_status='Paid');assert store.budget_totals(budget)==before
 store.save('receipts',dict(project_id=project,title='Actual permit fee',supplier_name='Example City',cost_category='Other',actual_amount='500',budget_id=budget))
 assert store.budget_totals(budget)['projected_total']==Decimal('10500.00')


def test_money_fields_are_side_by_side_in_form_and_list(store,project,app,monkeypatch):
 from cpc.ui import Window,Form
 from PySide6.QtWidgets import QMessageBox
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail);w=Window(store)
 def submit(form):
  form.show();app.processEvents();a=form.inputs['job_valuation'];b=form.inputs['permit_fee'];assert a.parentWidget() is b.parentWidget() and a.geometry().x()<b.geometry().x()
  form.inputs['title'].setText('Office work order');a.setText('12500');b.setText('325');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);w.edit('Work Orders');assert store.work_order_rows()[0]['job_valuation']=='12500.00'
 headers=[w.tables['Work Orders'].horizontalHeaderItem(i).text() for i in range(w.tables['Work Orders'].columnCount())];assert headers.index('Permit Fee')==headers.index('Job Valuation')+1;w.close()


def test_permit_selection_updates_city_county_fields_and_address(store,project,app,monkeypatch):
 from cpc.ui import Window,Form
 permit=store.save('registers',dict(project_id=project,title='County permit',record_type='Permit',jurisdiction_type='County',jurisdiction_name='Example County'))
 w=Window(store)
 def submit(form):
  form.inputs['title'].setText('Permit-linked order');form.inputs['permit_id'].setCurrentIndex(form.inputs['permit_id'].findData(permit));assert form.inputs['jurisdiction_name'].text()=='Example County' and form.inputs['site_address'].text()=='100 Example Street'
  form.inputs['job_valuation'].setText('10000');form.inputs['permit_fee'].setText('200');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);w.edit('Work Orders');assert store.work_order_rows()[0]['jurisdiction_type']=='County';w.close()


def test_deadline_search_hidden_section_exports_and_original_files(store,project,app,tmp_path):
 from cpc.ui import Window
 from cpc.exports import department_rows,write_docx
 rid=order(store,project,job_valuation='8000',permit_fee='150',discipline='Electrical',deadline='2020-01-01');source=tmp_path/'work-order.pdf';source.write_bytes(b'%PDF original work order');fid=store.import_finance_files('work_orders',rid,[source])[0]
 out=tmp_path/'saved.pdf';store.save_finance_copy(fid,out);assert out.read_bytes()==source.read_bytes()
 w=Window(store);w.hide_sidebar_section('Work Orders');w.refresh();assert any(r.get('_source_table')=='work_orders' for r in w.data['Dashboard']) and any(r['type']=='work_orders' for r in store.search('Tenant improvement work'))
 rows=department_rows(store,['Electrical'],project);row=next(r for r in rows if r['record_type']=='Work order');assert row['job_valuation']=='8000.00' and row['permit_fee']=='150.00' and row['total']==''
 store.export(tmp_path/'work-orders.csv',store.work_order_rows());write_docx(tmp_path/'work-orders.docx','Work orders',store.work_order_rows());assert '8000.00' in store.report(project)
 with zipfile.ZipFile(tmp_path/'work-orders.docx') as archive:assert b'150.00' in archive.read('word/document.xml')
 store.save('work_orders',{'status':'Completed'},rid);w.refresh();assert not any(r.get('_source_table')=='work_orders' for r in w.data['Dashboard']);w.close()


def test_work_order_delete_backup_restore_retains_files_and_values(store,project,tmp_path):
 rid=order(store,project,job_valuation='5000',permit_fee='100');source=tmp_path/'scope.txt';source.write_text('Original scope');store.import_finance_files('work_orders',rid,[source]);backup=store.delete_records([('projects',project)])
 assert store.all('work_orders')==[] and store.all('finance_files')==[]
 store.restore(backup);assert store.work_order_rows()[0]['job_valuation']=='5000.00' and len(store.finance_files('work_orders',rid))==1


def test_work_order_recovery_draft_keeps_pair_and_none_permit(store,project,app,monkeypatch):
 from cpc.ui import Window,Form
 w=Window(store);values=dict(project_id=project,title='Recover work',currency='USD',job_valuation='7000',permit_fee='220',status='Draft',fee_status='Estimated',valuation_basis='Estimated',permit_id=None)
 store.save_draft('work-order-draft','work_orders',None,values);w.reload_recovery_lists();w.draft_table.selectRow(0)
 def submit(form):
  assert form.inputs['permit_id'].currentData() is None and form.inputs['job_valuation'].parentWidget() is form.inputs['permit_fee'].parentWidget()
  form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);w.resume_draft();assert store.work_order_rows()[0]['permit_fee']=='220.00' and store.drafts()==[];w.close()


def test_schema10_upgrade_preserves_approvals_parts_and_order(store,tmp_path):
 old=tmp_path/'v10.sqlite3'
 with closing(sqlite3.connect(old)) as db:db.executescript((Path(__file__).parent/'fixtures/v10_database.sql').read_text())
 upgraded=Store(old)
 try:
  assert upgraded.db.execute('PRAGMA user_version').fetchone()[0]==11 and upgraded.all('work_orders')==[] and len(upgraded.all('approvals'))==1
  pid=upgraded.all('projects')[0]['id'];assert upgraded.section_order(pid,'sidebar')[0]=='Contracts' and 'Work Orders' in upgraded.section_order(pid,'sidebar')
  assert upgraded.all('receipts')[0]['actual_amount']=='1295.50'
 finally:upgraded.db.close()
 safety=str(old)+'.before-v1.11.0.sqlite3'
 with closing(sqlite3.connect(safety)) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==10
 store.restore(safety);assert len(store.all('approvals'))==1 and store.all('work_orders')==[]
