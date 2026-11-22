"""Contract commitments, budget exposure and original-file attachments."""
from contextlib import closing
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
from pathlib import Path,PureWindowsPath
import csv
import hashlib
import html
import io
import os
import shutil
import tempfile
import uuid
import zipfile
from .development import number,money,validate_date

CURRENCIES=['USD','CAD','EUR','GBP','AUD']
CONTRACT_STATUSES=['Draft','Pending Signature','Active','On Hold','Completed','Cancelled']
COMMITTED_STATUSES=('Active','On Hold','Completed')
FINANCE_FIELDS={
 'budgets':['project_id','title','discipline','currency','base_amount','contingency_amount','status','notes'],
 'contracts':['project_id','title','contract_number','contractor_name','contact_id','budget_id','bid_id','discipline','currency','original_amount','scope','signed_date','start_date','end_date','status','notes'],
 'contract_changes':['contract_id','title','reference','amount','status','approved_date','notes'],
 'finance_files':['contract_id','budget_id','original_name','file_path','sha256','byte_size','added_date','notes'],
}
RECEIPT_FINANCE_COLUMNS={'budget_id':'INTEGER REFERENCES budgets(id)','contract_id':'INTEGER REFERENCES contracts(id)','include_in_budget':'INTEGER DEFAULT 1'}
SUPPORTED_EXTENSIONS={'.pdf','.doc','.docx','.xls','.xlsx','.xlsm','.csv','.txt','.rtf','.odt','.ods','.jpg','.jpeg','.png','.tif','.tiff','.bmp','.gif','.webp','.dwg','.dxf','.dgn','.ifc','.rvt','.rfa','.zip','.7z','.rar','.ppt','.pptx','.msg','.eml'}
FILE_FILTER='Supported files ('+' '.join('*'+x for x in sorted(SUPPORTED_EXTENSIONS))+');;PDF (*.pdf);;Word (*.doc *.docx);;Excel / CSV (*.xls *.xlsx *.xlsm *.csv);;Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.gif *.webp);;CAD / BIM (*.dwg *.dxf *.dgn *.ifc *.rvt *.rfa);;Text (*.txt *.rtf);;Archives (*.zip *.7z *.rar)'
FINANCE_SCHEMA='''
CREATE TABLE IF NOT EXISTS budgets(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,discipline TEXT DEFAULT 'General',currency TEXT DEFAULT 'USD',base_amount TEXT DEFAULT '0.00',contingency_amount TEXT DEFAULT '0.00',status TEXT DEFAULT 'Active',notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS contracts(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,contract_number TEXT DEFAULT '',contractor_name TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),budget_id INTEGER REFERENCES budgets(id),bid_id INTEGER REFERENCES bids(id),discipline TEXT DEFAULT 'General',currency TEXT DEFAULT 'USD',original_amount TEXT DEFAULT '0.00',scope TEXT DEFAULT '',signed_date TEXT DEFAULT '',start_date TEXT DEFAULT '',end_date TEXT DEFAULT '',status TEXT DEFAULT 'Draft',notes TEXT DEFAULT '');
CREATE UNIQUE INDEX IF NOT EXISTS one_contract_per_bid ON contracts(bid_id) WHERE bid_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS contract_changes(id INTEGER PRIMARY KEY,contract_id INTEGER NOT NULL REFERENCES contracts(id),title TEXT NOT NULL,reference TEXT DEFAULT '',amount TEXT DEFAULT '0.00',status TEXT DEFAULT 'Proposed',approved_date TEXT DEFAULT '',notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS finance_files(id INTEGER PRIMARY KEY,contract_id INTEGER REFERENCES contracts(id),budget_id INTEGER REFERENCES budgets(id),original_name TEXT NOT NULL,file_path TEXT NOT NULL,sha256 TEXT NOT NULL,byte_size INTEGER NOT NULL,added_date TEXT NOT NULL,notes TEXT DEFAULT '',CHECK((contract_id IS NOT NULL)+(budget_id IS NOT NULL)=1));
CREATE INDEX IF NOT EXISTS contract_project ON contracts(project_id);
CREATE INDEX IF NOT EXISTS budget_project ON budgets(project_id);
'''

def signed_money(value):
 try:value=Decimal(str(value or '0'))
 except InvalidOperation:raise ValueError('Enter a valid amount') from None
 if not value.is_finite() or abs(value)>Decimal('1000000000'):raise ValueError('Amount is out of range')
 return str(money(value))

def digest(path):
 result=hashlib.sha256()
 with open(path,'rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
 return result.hexdigest()

def safe_name(name):return Path(PureWindowsPath(name).name).name or 'attachment'

class FinanceStore:
 def migrate_finance(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=7:return
  self.db.executescript('BEGIN IMMEDIATE;'+FINANCE_SCHEMA)
  with self.db:
   present={r[1] for r in self.db.execute('PRAGMA table_info(receipts)')}
   for name,kind in RECEIPT_FINANCE_COLUMNS.items():
    if name not in present:self.db.execute(f'ALTER TABLE receipts ADD COLUMN {name} {kind}')
   self.db.execute('PRAGMA user_version=7')
 def finance_project(self,table,data):
  if table=='finance_files' and data.get('owner_table'):
   owner=self.attachment_parent(data['owner_table'],data.get('owner_id'));return self.project_for(data['owner_table'],owner)
  if table=='contract_changes' or (table=='finance_files' and data.get('contract_id')):
   rows=self.rows('SELECT project_id FROM contracts WHERE id=?',(data.get('contract_id'),))
  elif table=='finance_files':rows=self.rows('SELECT project_id FROM budgets WHERE id=?',(data.get('budget_id'),))
  else:return data.get('project_id')
  return rows[0]['project_id'] if rows else None
 def validate_finance(self,table,data,row_id):
  if table in ('budgets','contracts'):
   if data.get('currency','USD') not in CURRENCIES:raise ValueError('Choose a supported currency')
   if table=='budgets':
    for key in ('base_amount','contingency_amount'):data[key]=str(money(number(data.get(key,0),key)))
    if data.get('status','Active') not in ('Active','Closed'):raise ValueError('Unknown budget status')
    if row_id:
     old=self.rows('SELECT project_id,currency FROM budgets WHERE id=?',(row_id,))[0]
     if any(data.get(k,old[k])!=old[k] for k in ('project_id','currency')) and (self.rows('SELECT id FROM contracts WHERE budget_id=?',(row_id,)) or self.rows('SELECT id FROM receipts WHERE budget_id=?',(row_id,))):raise ValueError('Unlink contracts and receipts before changing the budget project or currency')
   else:
    data['original_amount']=str(money(number(data.get('original_amount',0),'Contract amount')))
    if data.get('status','Draft') not in CONTRACT_STATUSES:raise ValueError('Unknown contract status')
    for key in ('signed_date','start_date','end_date'):
     if data.get(key):validate_date(data[key])
    if data.get('start_date') and data.get('end_date') and data['end_date']<data['start_date']:raise ValueError('Contract end date cannot precede start date')
    if not str(data.get('contractor_name','') or '').strip() and data.get('contact_id'):
     contacts=self.rows('SELECT company,name FROM contacts WHERE id=?',(data['contact_id'],))
     if contacts:data['contractor_name']=contacts[0]['company'] or contacts[0]['name']
    if not str(data.get('contractor_name','') or '').strip():raise ValueError('Enter the contractor/company or choose a contact')
    if data.get('budget_id'):self._matching_budget(data['budget_id'],data['project_id'],data.get('currency','USD'))
    old=self.rows('SELECT * FROM contracts WHERE id=?',(row_id,))[0] if row_id else None
    if old and any(data.get(k,old[k])!=old[k] for k in ('project_id','currency')) and self.rows('SELECT id FROM approvals WHERE contract_id=?',(row_id,)):raise ValueError('Unlink related approvals before moving the contract or changing currency')
    if old and any(data.get(k,old[k])!=old[k] for k in ('project_id','currency')) and self.rows('SELECT id FROM work_orders WHERE contract_id=?',(row_id,)):raise ValueError('Unlink related work orders before moving the contract or changing currency')
    if old and any(data.get(k,old[k])!=old[k] for k in ('project_id','currency','budget_id')) and self.rows('SELECT id FROM receipts WHERE contract_id=?',(row_id,)):raise ValueError('Unlink receipt allocations before moving the contract or changing its currency/budget')
    if data.get('bid_id') and (not old or old['bid_id']!=data['bid_id']):
     bids=self.rows('SELECT b.*,p.project_id FROM bids b JOIN bid_packages p ON p.id=b.package_id WHERE b.id=?',(data['bid_id'],))
     if not bids or bids[0]['status']!='Awarded' or bids[0]['project_id']!=data['project_id'] or bids[0]['currency']!=data.get('currency','USD'):raise ValueError('Source bid must be Awarded and match project and currency')
     if self.rows('SELECT id FROM contracts WHERE bid_id=? AND id!=?',(data['bid_id'],row_id or -1)):raise ValueError('This bid already has a contract')
    if row_id:
     changes=sum((Decimal(r['amount']) for r in self.rows("SELECT amount FROM contract_changes WHERE contract_id=? AND status='Approved'",(row_id,))),Decimal(0))
     if Decimal(data['original_amount'])+changes<0:raise ValueError('Adjusted contract amount cannot be negative')
  if table=='contract_changes':
   parent=self.rows('SELECT * FROM contracts WHERE id=?',(data.get('contract_id'),))
   if not parent:raise ValueError('Choose an existing contract')
   if row_id and self.rows('SELECT contract_id FROM contract_changes WHERE id=?',(row_id,))[0]['contract_id']!=data['contract_id']:raise ValueError('Create a new change order to move it to another contract')
   data['amount']=signed_money(data.get('amount',0))
   if data.get('status','Proposed') not in ('Proposed','Approved','Rejected'):raise ValueError('Unknown change-order status')
   if data.get('approved_date'):validate_date(data['approved_date'])
   data['approved_date']=(data.get('approved_date') or date.today().isoformat()) if data.get('status')=='Approved' else ''
   other=sum((Decimal(r['amount']) for r in self.rows("SELECT amount FROM contract_changes WHERE contract_id=? AND status='Approved' AND id!=?",(data['contract_id'],row_id or -1))),Decimal(0))
   if Decimal(parent[0]['original_amount'])+other+(Decimal(data['amount']) if data.get('status')=='Approved' else 0)<0:raise ValueError('Approved changes cannot make the contract total negative')
  if table=='receipts':
   if data.get('include_in_budget',1) not in (0,1):raise ValueError('Budget inclusion must be checked or unchecked')
   if data.get('contract_id'):
    parents=self.rows('SELECT project_id,currency,budget_id FROM contracts WHERE id=?',(data['contract_id'],))
    if not parents or parents[0]['project_id']!=data['project_id'] or parents[0]['currency']!=data.get('currency','USD'):raise ValueError('Receipt contract must match its project and currency')
    if data.get('budget_id') not in (None,parents[0]['budget_id']):raise ValueError('A contract receipt uses its contract budget')
    data['budget_id']=parents[0]['budget_id']
   if data.get('budget_id'):self._matching_budget(data['budget_id'],data['project_id'],data.get('currency','USD'))
 def _matching_budget(self,budget_id,pid,currency):
  rows=self.rows('SELECT project_id,currency FROM budgets WHERE id=?',(budget_id,))
  if not rows or rows[0]['project_id']!=pid or rows[0]['currency']!=currency:raise ValueError('Budget must match project and currency')
 def contract_totals(self,cid):
  rows=self.rows('SELECT * FROM contracts WHERE id=?',(cid,))
  if not rows:raise ValueError('Contract not found')
  contract=rows[0];changes=sum((Decimal(r['amount']) for r in self.rows("SELECT amount FROM contract_changes WHERE contract_id=? AND status='Approved'",(cid,))),Decimal(0))
  actual=sum((Decimal(r['actual_amount']) for r in self.rows("SELECT actual_amount FROM receipts WHERE contract_id=? AND include_in_budget=1 AND actual_amount!=''",(cid,))),Decimal(0))
  adjusted=Decimal(contract['original_amount'])+changes
  if adjusted<0:raise ValueError('Adjusted contract total cannot be negative')
  return dict(approved_changes=money(changes),adjusted_amount=money(adjusted),actual_amount=money(actual),remaining_commitment=money(max(adjusted-actual,Decimal(0))) if contract['status'] in COMMITTED_STATUSES else Decimal('0.00'))
 def budget_totals(self,bid):
  rows=self.rows('SELECT * FROM budgets WHERE id=?',(bid,))
  if not rows:raise ValueError('Budget not found')
  budget=rows[0];allocated=Decimal(budget['base_amount'])+Decimal(budget['contingency_amount']);committed=Decimal(0);remaining=Decimal(0)
  for contract in self.rows('SELECT * FROM contracts WHERE budget_id=?',(bid,)):
   totals=self.contract_totals(contract['id'])
   if contract['status'] in COMMITTED_STATUSES:committed+=totals['adjusted_amount'];remaining+=totals['remaining_commitment']
  actual=sum((Decimal(r['actual_amount']) for r in self.rows("SELECT actual_amount FROM receipts WHERE budget_id=? AND include_in_budget=1 AND actual_amount!=''",(bid,))),Decimal(0))
  exposure=actual+remaining
  return dict(total_budget=money(allocated),committed_amount=money(committed),actual_amount=money(actual),remaining_commitments=money(remaining),projected_total=money(exposure),unspent_funds=money(allocated-actual),remaining_funds=money(allocated-exposure),budget_alert='OVER BUDGET' if exposure>allocated else 'Within budget')
 def finance_rows(self,table):
  rows=self.all(table);projects={p['id']:p['name'] for p in self.all('projects')};budgets={b['id']:b['title'] for b in self.all('budgets')}
  for row in rows:
   row['project']=projects.get(row.get('project_id'),'')
   if table=='contracts':row['budget']=budgets.get(row['budget_id'],'Unallocated');row.update({k:str(v) for k,v in self.contract_totals(row['id']).items()})
   elif table=='budgets':row.update({k:str(v) for k,v in self.budget_totals(row['id']).items()})
  return rows
 def contract_from_bid(self,bid_id,budget_id=None):
  rows=self.rows('SELECT b.*,p.project_id,p.discipline,p.scope FROM bids b JOIN bid_packages p ON p.id=b.package_id WHERE b.id=?',(bid_id,))
  if not rows:raise ValueError('Choose an awarded bid')
  row=rows[0]
  return self.save('contracts',dict(project_id=row['project_id'],title=row['title'],contractor_name=row['title'],contact_id=row['contact_id'],budget_id=budget_id,bid_id=bid_id,discipline=row['discipline'],currency=row['currency'],original_amount=str(self.bid_totals(bid_id)['total']),scope=row['scope'],status='Draft'))
 def attachment_parent(self,table,parent_id):
  from .store import FIELDS
  if table not in FIELDS or table in ('finance_files','contacts'):raise ValueError('Unsupported attachment area')
  rows=self.rows(f'SELECT * FROM {table} WHERE id=?',(parent_id,))
  if not rows:raise ValueError('Save the record before attaching files')
  return rows[0]
 def attachment_owner(self,row):
  if row.get('contract_id'):return 'contracts',row['contract_id']
  if row.get('budget_id'):return 'budgets',row['budget_id']
  return row['owner_table'],row['owner_id']
 def finance_files(self,table,parent_id):
  self.attachment_parent(table,parent_id)
  if table in ('contracts','budgets'):
   key='contract_id' if table=='contracts' else 'budget_id'
   return self.rows(f'SELECT * FROM finance_files WHERE {key}=? ORDER BY id DESC',(parent_id,))
  return self.rows('SELECT * FROM finance_files WHERE owner_table=? AND owner_id=? ORDER BY id DESC',(table,parent_id))
 def import_finance_files(self,table,parent_id,paths,notes=''):
  from .privacy import check_values,check_attachment
  check_values(notes)
  paths=list(paths)
  for path in paths:check_attachment(path)
  parent=self.attachment_parent(table,parent_id);pid=self.project_for(table,parent)
  if not pid:raise ValueError('Files must belong to a project record')
  sources=[Path(p) for p in paths]
  if not sources:raise ValueError('Choose at least one file')
  for source in sources:
   if not source.is_file() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:raise ValueError('Choose a supported document, spreadsheet, image, CAD or archive file')
  folder=self.path.parent/'documents'/'finance';folder.mkdir(parents=True,exist_ok=True);created=[];ids=[]
  try:
   with self.db:
    for source in sources:
     target=folder/(uuid.uuid4().hex+source.suffix.lower());created.append(target);shutil.copy2(source,target)
     contract=parent_id if table=='contracts' else None;budget=parent_id if table=='budgets' else None
     owner='' if contract or budget else table;oid=None if contract or budget else parent_id
     fid=self.db.execute('INSERT INTO finance_files(contract_id,budget_id,owner_table,owner_id,original_name,file_path,sha256,byte_size,added_date,notes) VALUES(?,?,?,?,?,?,?,?,?,?)',(contract,budget,owner,oid,source.name,str(target.resolve()),digest(target),target.stat().st_size,datetime.now().isoformat(timespec='seconds'),notes)).lastrowid;ids.append(fid)
    if table=='approvals':self.approval_evidence_changed(parent_id)
    self.log(pid,f'Imported {len(ids)} original file(s) for {table} #{parent_id}')
  except Exception:
   for target in created:target.unlink(missing_ok=True)
   raise
  return ids
 def checked_finance_file(self,file_id):
  rows=self.rows('SELECT * FROM finance_files WHERE id=?',(file_id,))
  if not rows:raise ValueError('Attachment not found')
  row=rows[0];path=Path(row['file_path'])
  if not path.is_file():raise ValueError('Restore this attachment from your documents-folder backup')
  if digest(path)!=row['sha256']:raise ValueError('The retained file changed outside the app; restore the original or import it as a new version')
  return row,path
 def finance_working_copy(self,file_id):
  row,source=self.checked_finance_file(file_id)
  folder=self.path.parent/'workfiles'/'finance'/uuid.uuid4().hex;folder.mkdir(parents=True)
  target=folder/safe_name(row['original_name']);shutil.copy2(source,target);return target
 def save_finance_copy(self,file_id,destination):
  row,source=self.checked_finance_file(file_id);destination=Path(destination)
  if destination.resolve()==source.resolve():raise ValueError('Save outside the retained original file')
  if (self.path.parent/'documents').resolve() in destination.resolve().parents:raise ValueError('Choose a destination outside the retained documents folder')
  with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False,suffix='.partial') as tmp:temporary=Path(tmp.name)
  try:shutil.copy2(source,temporary);os.replace(temporary,destination)
  finally:temporary.unlink(missing_ok=True)
 def export_finance_zip(self,table,parent_id,destination):
  rows=self.finance_files(table,parent_id);destination=Path(destination)
  if not rows:raise ValueError('No attachments to export')
  if (self.path.parent/'documents').resolve() in destination.resolve().parents:raise ValueError('Save the archive outside retained documents')
  with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False,suffix='.partial') as tmp:temporary=Path(tmp.name)
  try:
   with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
    used={'manifest.csv'};manifest=[]
    for row in rows:
     checked,path=self.checked_finance_file(row['id']);name=safe_name(row['original_name'])
     if name.lower() in used:name=f'{row["id"]}-{name}'
     used.add(name.lower());archive.write(path,name);manifest.append([name,row['original_name'],row['sha256'],row['added_date'],row['notes']])
    text=io.StringIO();writer=csv.writer(text);writer.writerow(['archive_name','original_name','sha256','added_date','notes']);writer.writerows([["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for v in row] for row in manifest]);archive.writestr('manifest.csv',text.getvalue())
   os.replace(temporary,destination)
  finally:temporary.unlink(missing_ok=True)
 def save_revision_copy(self,version_id,destination):
  rows=self.rows('SELECT file_path FROM versions WHERE id=?',(version_id,))
  if not rows or not rows[0]['file_path'] or not Path(rows[0]['file_path']).is_file():raise ValueError('Restore the revision file from your documents-folder backup first')
  source=Path(rows[0]['file_path']);destination=Path(destination)
  if source.resolve()==destination.resolve() or (self.path.parent/'documents').resolve() in destination.resolve().parents:raise ValueError('Save outside the retained originals')
  with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False,suffix='.partial') as file:temporary=Path(file.name)
  try:shutil.copy2(source,temporary);os.replace(temporary,destination)
  finally:temporary.unlink(missing_ok=True)
 def finance_report(self,pid):
  e=lambda v:html.escape(str(v if v is not None else ''));out='<h2>Contracts and budgets</h2>'
  for table in ('budgets','contracts'):
   out+='<h3>'+table.title()+'</h3>'
   for row in self.finance_rows(table):
    if row['project_id']==pid:out+='<p>'+' | '.join(e(k)+': '+e(v) for k,v in row.items() if not k.endswith('_id') and k!='id')+'</p>'
  return out
