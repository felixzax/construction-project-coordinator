import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import hashlib
import sqlite3
import zipfile
import pytest
from cpc.store import Store,FIELDS
from cpc.finance import SUPPORTED_EXTENSIONS

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()

@pytest.fixture
def setup(store):
 p=store.save('projects',{'name':'Budget project'})
 b=store.save('budgets',dict(project_id=p,title='Electrical',currency='USD',base_amount='1000',contingency_amount='100'))
 c=store.save('contracts',dict(project_id=p,title='Installation',contractor_name='Example Contractor',budget_id=b,currency='USD',original_amount='1000',status='Active'))
 return p,b,c

def receipt(store,p,**kw):
 values=dict(project_id=p,title='Materials',supplier_name='Example Supply',currency='USD',actual_amount='200',status='Pending Review');values.update(kw);return store.save('receipts',values)


def test_budget_does_not_double_count_contract_receipts(store,setup):
 p,b,c=setup;receipt(store,p,contract_id=c);receipt(store,p,budget_id=b,actual_amount='50')
 t=store.budget_totals(b)
 assert t['total_budget']==Decimal('1100') and t['committed_amount']==Decimal('1000')
 assert t['actual_amount']==Decimal('250') and t['remaining_commitments']==Decimal('800')
 assert t['projected_total']==Decimal('1050') and t['remaining_funds']==Decimal('50')
 assert t['budget_alert']=='Within budget'


def test_approved_changes_and_budget_overrun(store,setup):
 p,b,c=setup
 change=store.save('contract_changes',dict(contract_id=c,title='Extra outlets',amount='200',status='Proposed'))
 assert store.contract_totals(c)['adjusted_amount']==Decimal('1000')
 store.save('contract_changes',{'status':'Approved'},change)
 assert store.contract_totals(c)['adjusted_amount']==Decimal('1200')
 assert store.budget_totals(b)['budget_alert']=='OVER BUDGET'
 store.save('contract_changes',dict(contract_id=c,title='Scope reduction',amount='-150',status='Approved'))
 assert store.contract_totals(c)['adjusted_amount']==Decimal('1050')
 with pytest.raises(ValueError):store.save('contract_changes',dict(contract_id=c,title='Invalid reduction',amount='-2000',status='Approved'))


def test_actual_over_contract_not_hidden_and_inclusion_explicit(store,setup):
 p,b,c=setup;r=receipt(store,p,contract_id=c,actual_amount='1300')
 assert store.budget_totals(b)['projected_total']==Decimal('1300')
 store.save('receipts',{'include_in_budget':0},r)
 assert store.budget_totals(b)['actual_amount']==0
 assert store.budget_totals(b)['projected_total']==Decimal('1000')


def test_project_currency_and_parent_changes_validated(store,setup):
 p,b,c=setup;other=store.save('projects',{'name':'Other'});other_b=store.save('budgets',dict(project_id=other,title='Other',currency='CAD'))
 with pytest.raises(ValueError):receipt(store,p,budget_id=other_b)
 with pytest.raises(ValueError):receipt(store,p,contract_id=c,currency='CAD')
 receipt(store,p,contract_id=c)
 with pytest.raises(ValueError):store.save('contracts',{'budget_id':None},c)
 with pytest.raises(ValueError):store.save('budgets',{'currency':'CAD'},b)


def test_awarded_bid_creates_single_snapshot_contract(store):
 store.seed();bid=store.all('bids')[0];store.save('bids',{'status':'Awarded'},bid['id'])
 cid=store.contract_from_bid(bid['id']);contract=next(r for r in store.all('contracts') if r['id']==cid)
 assert contract['original_amount']==str(store.bid_totals(bid['id'])['total']) and contract['status']=='Draft'
 with pytest.raises(ValueError):store.contract_from_bid(bid['id'])
 store.delete_records([('bids',bid['id'])]);assert store.rows('SELECT bid_id FROM contracts WHERE id=?',(cid,))[0]['bid_id'] is None


@pytest.mark.parametrize('extension',['.pdf','.doc','.docx','.xls','.xlsx','.csv','.txt','.png','.jpg','.dwg','.dxf','.zip'])
def test_standard_file_upload_download_original_bytes(store,setup,tmp_path,extension):
 p,b,c=setup;source=tmp_path/('original'+extension);payload=b'\x00Original bytes\xff'+extension.encode();source.write_bytes(payload)
 fid=store.import_finance_files('contracts',c,[source])[0]
 source.write_bytes(b'Changed external file')
 output=tmp_path/('download'+extension);store.save_finance_copy(fid,output)
 assert output.read_bytes()==payload
 row=store.finance_files('contracts',c)[0];assert row['original_name']=='original'+extension and row['sha256']==hashlib.sha256(payload).hexdigest()


def test_budget_files_zip_duplicates_integrity_and_recovery(store,setup,tmp_path):
 p,b,c=setup;one=tmp_path/'one';two=tmp_path/'two';one.mkdir();two.mkdir();(one/'plan.pdf').write_bytes(b'one');(two/'plan.pdf').write_bytes(b'two')
 ids=store.import_finance_files('budgets',b,[one/'plan.pdf',two/'plan.pdf'])
 archive=tmp_path/'download.zip';store.export_finance_zip('budgets',b,archive)
 with zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==3 and 'manifest.csv' in z.namelist()
  assert {z.read(n) for n in z.namelist() if n!='manifest.csv'}=={b'one',b'two'}
 retained=Path(store.finance_files('budgets',b)[0]['file_path']);snapshot=store.delete_records([('budgets',b)])
 assert retained.exists() and store.rows('SELECT budget_id FROM contracts WHERE id=?',(c,))[0]['budget_id'] is None
 store.restore(snapshot);assert len(store.finance_files('budgets',b))==2
 retained.write_bytes(b'tampered')
 with pytest.raises(ValueError,match='changed outside'):store.save_finance_copy(ids[-1],tmp_path/'bad.pdf')


def test_contract_delete_keeps_receipt_actual_budget_allocation(store,setup):
 p,b,c=setup;r=receipt(store,p,contract_id=c)
 store.save('contract_changes',dict(contract_id=c,title='Extra',amount='100',status='Approved'))
 store.delete_records([('contracts',c)])
 row=store.all('receipts')[0];assert row['contract_id'] is None and row['budget_id']==b
 assert store.budget_totals(b)['projected_total']==Decimal('200') and store.all('contract_changes')==[]


def test_project_delete_cascades_finance_and_all_data_reset(store,setup,tmp_path):
 p,b,c=setup;f=tmp_path/'budget.csv';f.write_text('item,cost\nA,10');store.import_finance_files('budgets',b,[f]);receipt(store,p,contract_id=c)
 store.delete_records([('projects',p)])
 for table in ('budgets','contracts','contract_changes','finance_files','receipts'):assert store.all(table)==[]
 assert not store.db.execute('PRAGMA foreign_key_check').fetchall()


def test_backup_restores_original_finance_files_and_links(store,setup,tmp_path):
 p,b,c=setup;r=receipt(store,p,contract_id=c);f=tmp_path/'agreement.docx';f.write_bytes(b'original');store.import_finance_files('contracts',c,[f]);backup=tmp_path/'backup.sqlite3';store.backup(backup)
 store.delete_all_data();store.restore(backup)
 assert store.budget_totals(b)['projected_total']==Decimal('1000') and len(store.finance_files('contracts',c))==1
 assert any(r['type']=='finance_files' and r['project_id']==p for r in store.search('agreement.docx'))


def test_v6_upgrade_and_restore_preserve_existing_data(store,tmp_path):
 old=tmp_path/'v6.sqlite3'
 with closing(sqlite3.connect(old)) as db:db.executescript((Path(__file__).parent/'fixtures/v6_database.sql').read_text())
 upgraded=Store(old)
 try:
  assert upgraded.db.execute('PRAGMA user_version').fetchone()[0]==7 and len(upgraded.all('issues'))==2
  assert upgraded.all('budgets')==[] and upgraded.all('receipts')[0]['include_in_budget']==1
 finally:upgraded.db.close()
 with closing(sqlite3.connect(str(old)+'.before-v1.6.0.sqlite3')) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==6
 store.restore(str(old)+'.before-v1.6.0.sqlite3');assert len(store.all('receipts'))==1 and store.all('contracts')==[]

@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])


def test_finance_ui_forms_and_original_file_download(store,setup,app,tmp_path,monkeypatch):
 from cpc.ui import Window,Form
 from PySide6.QtWidgets import QFileDialog,QDialog,QPushButton,QMessageBox
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 w=Window(store);w.tables['Contracts'].selectRow(0)
 source=tmp_path/'contract.pdf';source.write_bytes(b'%PDF-original');out=tmp_path/'copy.pdf'
 monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *args:([str(source)],'Files'));monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(out),'PDF'))
 def run(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Add files…').click()
  from cpc.table import DataTable
  dialog.findChild(DataTable).selectRow(0)
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='Save a copy…').click()
  dialog.accept();return dialog.result()
 monkeypatch.setattr(QDialog,'exec',run);w.finance_file_manager('Contracts');assert out.read_bytes()==source.read_bytes();w.close()


def test_external_working_copy_does_not_overwrite_original(store,setup,tmp_path):
 p,b,c=setup;source=tmp_path/'contract.pdf';source.write_bytes(b'original agreement');fid=store.import_finance_files('contracts',c,[source])[0]
 work=store.finance_working_copy(fid);work.write_bytes(b'revised agreement')
 assert store.checked_finance_file(fid)[1].read_bytes()==b'original agreement'
 store.import_finance_files('contracts',c,[work],notes='External revision')
 assert len(store.finance_files('contracts',c))==2


def test_contract_budget_forms_and_change_orders_save(store,setup,app,monkeypatch):
 from cpc.ui import Window,Form
 from PySide6.QtWidgets import QDialog,QMessageBox,QPushButton
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail);w=Window(store);w.tables['Contracts'].selectRow(0)
 def submit(form):
  form.inputs['title'].setText('Approved addition');form.inputs['amount'].setText('50');form.inputs['status'].setCurrentText('Approved');form.accept();return form.result()
 def run(dialog):
  next(b for b in dialog.findChildren(QPushButton) if b.text()=='+ Change order').click();dialog.accept();return dialog.result()
 monkeypatch.setattr(Form,'exec',submit);monkeypatch.setattr(QDialog,'exec',run);w.change_orders()
 assert store.contract_totals(setup[2])['adjusted_amount']==Decimal('1050');w.close()
