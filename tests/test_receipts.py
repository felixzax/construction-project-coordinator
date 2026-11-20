import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3
import pytest
from cpc.store import Store
from cpc.receipts import receipt_variance,receipt_comparison
from cpc.exports import department_rows

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()

@pytest.fixture
def receipt(store):
 p=store.save('projects',{'name':'Supply project'})
 return store.save('receipts',dict(project_id=p,title='Lighting materials',supplier_name='Example Supply',discipline='Electrical',currency='USD',estimated_amount='100.00',actual_amount='112.35',status='Pending Review'))

def test_estimated_actual_supplier_and_variance(store,receipt):
 row=store.receipt_rows()[0]
 assert row['supplier_name']=='Example Supply' and row['estimated_amount']=='100.00'
 assert row['actual_amount']=='112.35' and row['variance_amount']=='12.35'
 assert row['comparison']=='Over estimate' and row['status']=='Pending Review'
 store.save('receipts',{'actual_amount':'90'},receipt)
 assert store.receipt_rows()[0]['variance_amount']=='-10.00' and store.receipt_rows()[0]['comparison']=='Under estimate'
 store.save('receipts',{'actual_amount':'100'},receipt)
 assert store.receipt_rows()[0]['comparison']=='On estimate'


def test_blank_prices_are_unknown_and_zero_is_real(store,receipt):
 store.save('receipts',{'actual_amount':''},receipt)
 assert store.receipt_rows()[0]['variance_amount']=='' and store.receipt_rows()[0]['comparison']=='Awaiting actual price'
 store.save('receipts',{'estimated_amount':'0','actual_amount':'0'},receipt)
 row=store.receipt_rows()[0];assert row['variance_amount']=='0.00' and row['comparison']=='On estimate'
 store.save('receipts',{'estimated_amount':''},receipt)
 assert store.receipt_rows()[0]['comparison']=='Awaiting estimate'

@pytest.mark.parametrize('status',['Approved','Rejected','Needs Changes'])
def test_approval_review_status_and_date(store,receipt,status):
 store.save('receipts',{'status':status,'reviewed_by':'Example manager'},receipt)
 row=store.receipt_rows()[0];assert row['status']==status and row['review_date']==date.today().isoformat()
 assert row['reviewed_by']=='Example manager'

@pytest.mark.parametrize('change',[{'actual_amount':'115'},{'estimated_amount':'99'},{'supplier_name':'Another Supplier'},{'currency':'CAD'}])
def test_changed_approved_price_supplier_or_currency_requires_review(store,receipt,change):
 store.save('receipts',{'status':'Approved','reviewed_by':'Manager'},receipt)
 store.save('receipts',change,receipt)
 row=store.receipt_rows()[0]
 assert row['status']=='Pending Review' and row['review_date']=='' and row['reviewed_by']==''
 assert 'Approval reset' in row['approval_notes']
 store.save('receipts',{'status':'Approved'},receipt)
 assert store.receipt_rows()[0]['status']=='Approved'


def test_notes_edit_does_not_invalidate_approval(store,receipt):
 store.save('receipts',{'status':'Approved'},receipt);store.save('receipts',{'notes':'Filed in project folder'},receipt)
 assert store.receipt_rows()[0]['status']=='Approved'

@pytest.mark.parametrize('field,value',[('actual_amount','-1'),('estimated_amount','NaN'),('actual_amount','Infinity'),('estimated_amount','not a price'),('status','Invalid'),('currency','ZZZ'),('receipt_date','20261201')])
def test_invalid_receipt_data_rejected(store,receipt,field,value):
 with pytest.raises(ValueError):store.save('receipts',{field:value},receipt)
 assert store.receipt_rows()[0]['actual_amount']=='112.35'


def test_supplier_contact_autofill_and_contact_delete_preserve_receipt(store):
 p=store.save('projects',{'name':'Supplier project'});c=store.save('contacts',dict(name='Example Person',company='Fictional Supply',role='Supplier'))
 r=store.save('receipts',dict(project_id=p,title='Quote',contact_id=c,estimated_amount='25.005'))
 assert store.receipt_rows()[0]['supplier_name']=='Fictional Supply' and store.receipt_rows()[0]['estimated_amount']=='25.01'
 store.delete_records([('contacts',c)])
 row=store.receipt_rows()[0];assert row['supplier_name']=='Fictional Supply' and row['contact_id'] is None


def test_supplier_is_required(store):
 p=store.save('projects',{'name':'Project'})
 with pytest.raises(ValueError,match='supplier'):store.save('receipts',dict(project_id=p,title='Missing supplier'))


def test_attachments_copy_content_reset_approval_and_remain_after_delete(store,receipt,tmp_path):
 source=tmp_path/'receipt.txt';source.write_text('Original supplier receipt');first=store.attach_receipt(receipt,source)
 source.write_text('Revised supplier receipt');store.save('receipts',{'status':'Approved'},receipt);second=store.attach_receipt(receipt,source)
 assert first.read_text()=='Original supplier receipt' and second.read_text()=='Revised supplier receipt'
 assert first!=second and store.receipt_rows()[0]['status']=='Pending Review'
 store.delete_records([('receipts',receipt)]);assert first.exists() and second.exists()


def test_receipts_search_department_exports_report_and_backup_restore(store,receipt,tmp_path):
 p=store.receipt_rows()[0]['project_id']
 assert any(row['type']=='receipts' for row in store.search('Example Supply'))
 rows=department_rows(store,['Electrical'],p)
 assert any(row['record_type']=='Supplier receipt' and row['variance_amount']=='12.35' for row in rows)
 report=store.report(p);assert 'Example Supply' in report and '112.35' in report and 'Pending Review' in report
 path=tmp_path/'backup.sqlite3';store.backup(path);store.save('receipts',{'status':'Rejected'},receipt);store.restore(path)
 assert store.receipt_rows()[0]['status']=='Pending Review'


def test_project_delete_cascades_receipts_and_recovery_restores(store,receipt):
 p=store.receipt_rows()[0]['project_id'];snapshot=store.delete_records([('projects',p)]);assert not store.all('receipts')
 store.restore(snapshot);assert len(store.all('receipts'))==1


def v4_database(path):
 with closing(sqlite3.connect(path)) as db:db.executescript((Path(__file__).parent/'fixtures/v4_database.sql').read_text())


def test_v4_upgrade_preserves_existing_data_and_recovery_schema(tmp_path):
 path=tmp_path/'v4.sqlite3';v4_database(path);s=Store(path)
 try:
  assert s.db.execute('PRAGMA user_version').fetchone()[0]==11
  assert len(s.all('bids'))==2 and len(s.all('permit_requirements'))==2
  assert s.all('receipts')==[] and s.drafts()==[]
  with closing(sqlite3.connect(str(path)+'.before-v1.11.0.sqlite3')) as backup:assert backup.execute('PRAGMA user_version').fetchone()[0]==4
 finally:s.db.close()


def test_v4_backup_restore_into_v5(store,receipt,tmp_path):
 path=tmp_path/'v4.sqlite3';v4_database(path);store.restore(path)
 assert store.all('receipts')==[] and len(store.all('bids'))==2
 assert store.db.execute('PRAGMA user_version').fetchone()[0]==11

@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])

@pytest.fixture
def window(store,receipt,app,monkeypatch):
 from cpc.ui import Window
 from PySide6.QtWidgets import QMessageBox
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail);w=Window(store);w.tables['Receipts'].selectRow(0);yield w;w.close()


def test_receipt_form_actual_price_and_approval(window,store,monkeypatch):
 from cpc.ui import Form
 def submit(form):
  form.inputs['actual_amount'].setText('105.75');form.inputs['status'].setCurrentText('Approved');form.inputs['reviewed_by'].setText('Manager');form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);window.edit('Receipts',True)
 row=store.receipt_rows()[0];assert row['actual_amount']=='105.75' and row['status']=='Approved' and row['variance_amount']=='5.75'


def test_receipt_attachment_ui_and_filtered_export(window,store,receipt,tmp_path,monkeypatch):
 from PySide6.QtWidgets import QFileDialog
 source=tmp_path/'supplier-receipt.txt';source.write_text('Receipt document')
 monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *args:(str(source),'All files'));window.attach_receipt_file()
 assert Path(store.receipt_rows()[0]['attachment_path']).read_text()=='Receipt document'
 csv=tmp_path/'receipts.csv';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(csv),'CSV'));window.export_section('Receipts','csv')
 assert 'Example Supply' in csv.read_text('utf-8-sig') and '12.35' in csv.read_text('utf-8-sig')
 word=tmp_path/'receipts.docx';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(word),'DOCX'));window.export_section('Receipts','docx')
 from docx import Document
 doc=Document(word);assert any('Example Supply' in cell.text for table in doc.tables for row in table.rows for cell in row.cells)


def test_receipt_project_filter_and_draft_recovery(window,store,receipt,monkeypatch):
 from cpc.ui import Form
 p=store.receipt_rows()[0]['project_id'];other=store.save('projects',{'name':'Other'});window.refresh();window.project_filter.setCurrentIndex(window.project_filter.findData(other))
 assert window.tables['Receipts'].rowCount()==0
 window.project_filter.setCurrentIndex(0)
 store.save_draft('receipt:new','receipts',None,dict(project_id=p,title='Recovered supplier quote',supplier_name='Saved Supplier',estimated_amount='50',actual_amount='',currency='USD',status='Pending Review'))
 window.reload_recovery_lists();window.draft_table.selectRow(0)
 def submit(form):form.accept();return form.result()
 monkeypatch.setattr(Form,'exec',submit);window.resume_draft()
 assert any(row['title']=='Recovered supplier quote' for row in store.all('receipts')) and not store.drafts()
