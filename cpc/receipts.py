"""Local supplier receipt estimates, actual costs and review status."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import html
import shutil
import uuid
from .development import number,money,validate_date

RECEIPT_STATUSES=['Pending Review','Approved','Rejected','Needs Changes']
RECEIPT_FIELDS=['project_id','title','supplier_name','contact_id','reference','receipt_date','discipline','building_area','currency','estimated_amount','actual_amount','status','reviewed_by','review_date','approval_notes','notes','attachment_path','attachment_name']
RECEIPT_FORM_FIELDS=[f for f in RECEIPT_FIELDS if f not in ('attachment_path','attachment_name')]
RECEIPT_SCHEMA='''
CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,supplier_name TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),reference TEXT DEFAULT '',receipt_date TEXT DEFAULT '',discipline TEXT DEFAULT 'General',building_area TEXT DEFAULT '',currency TEXT DEFAULT 'USD',estimated_amount TEXT DEFAULT '',actual_amount TEXT DEFAULT '',status TEXT DEFAULT 'Pending Review',reviewed_by TEXT DEFAULT '',review_date TEXT DEFAULT '',approval_notes TEXT DEFAULT '',notes TEXT DEFAULT '',attachment_path TEXT DEFAULT '',attachment_name TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS receipts_project ON receipts(project_id);
'''

def amount(value):
 if value in ('',None): return ''
 return str(money(number(value,'Price')))

def receipt_variance(row):
 estimate=row.get('estimated_amount'); actual=row.get('actual_amount')
 if estimate in ('',None) or actual in ('',None): return ''
 return str(money(Decimal(actual)-Decimal(estimate)))

def receipt_comparison(row):
 variance=receipt_variance(row)
 if variance=='': return 'Awaiting estimate' if row.get('estimated_amount') in ('',None) else 'Awaiting actual price'
 value=Decimal(variance)
 return 'Over estimate' if value>0 else 'Under estimate' if value<0 else 'On estimate'

class ReceiptStore:
 def migrate_receipts(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=5: return
  self.db.executescript('BEGIN IMMEDIATE;'+RECEIPT_SCHEMA+'PRAGMA user_version=5;COMMIT;')
 def validate_receipt(self,table,data,row_id):
  if table!='receipts': return
  data['estimated_amount']=amount(data.get('estimated_amount','')); data['actual_amount']=amount(data.get('actual_amount',''))
  for key in ('receipt_date','review_date'):
   if data.get(key): validate_date(data[key])
  if data.get('currency','USD') not in ('USD','CAD','EUR','GBP','AUD'): raise ValueError('Choose a supported currency')
  if data.get('status','Pending Review') not in RECEIPT_STATUSES: raise ValueError('Choose an approval status')
  supplier=str(data.get('supplier_name','') or '').strip()
  if not supplier and data.get('contact_id'):
   contacts=self.rows('SELECT name,company FROM contacts WHERE id=?',(data['contact_id'],))
   if contacts: supplier=contacts[0]['company'] or contacts[0]['name']
  if not supplier: raise ValueError('Enter the supplier name or choose a supplier contact')
  data['supplier_name']=supplier
  if row_id:
   old=self.rows('SELECT * FROM receipts WHERE id=?',(row_id,))[0]
   changed=any(data.get(key,old[key])!=old[key] for key in ('supplier_name','contact_id','currency','estimated_amount','actual_amount','attachment_path'))
   if old['status']=='Approved' and changed:
    data['status']='Pending Review'; data['reviewed_by']=''; data['review_date']=''
    note='Approval reset: supplier, price, currency or receipt file changed.'
    data['approval_notes']=note+(' '+data.get('approval_notes','') if data.get('approval_notes') else '')
  if data.get('status','Pending Review')=='Pending Review': data['review_date']=''
  else: data['review_date']=data.get('review_date') or date.today().isoformat()
 def receipt_rows(self,pid=None):
  rows=self.rows('SELECT r.*,p.name AS project,c.name AS supplier_contact FROM receipts r JOIN projects p ON p.id=r.project_id LEFT JOIN contacts c ON c.id=r.contact_id'+(' WHERE r.project_id=?' if pid else '')+' ORDER BY r.id DESC',(pid,) if pid else ())
  for row in rows: row.update(variance_amount=receipt_variance(row),comparison=receipt_comparison(row))
  return rows
 def attach_receipt(self,receipt_id,path):
  if not self.rows('SELECT id FROM receipts WHERE id=?',(receipt_id,)): raise ValueError('Receipt not found')
  source=Path(path)
  if not source.is_file(): raise ValueError('Attachment file does not exist')
  folder=self.path.parent/'documents'; folder.mkdir(exist_ok=True)
  target=folder/(uuid.uuid4().hex+source.suffix)
  shutil.copy2(source,target)
  try: self.save('receipts',dict(attachment_path=str(target.resolve()),attachment_name=source.name),receipt_id)
  except Exception:
   target.unlink(missing_ok=True); raise
  return target
 def receipt_report(self,pid):
  e=lambda value:html.escape(str(value if value is not None else ''))
  out='<h2>Supplier receipts — estimates and actual prices</h2>'
  for row in self.receipt_rows(pid):
   out+=f'<h3>{e(row["title"])}</h3><p>Supplier: {e(row["supplier_name"])} | Reference: {e(row["reference"])} | Date: {e(row["receipt_date"])}</p>'
   out+=f'<p>Currency: {e(row["currency"])} | Estimate: {e(row["estimated_amount"]) or "Not entered"} | Actual: {e(row["actual_amount"]) or "Not entered"} | Difference (actual − estimate): {e(row["variance_amount"]) or "Not available"} | {e(row["comparison"])}</p>'
   out+=f'<p>Approval: {e(row["status"])} | Reviewed by: {e(row["reviewed_by"])} | Review date: {e(row["review_date"])}</p><p>{e(row["approval_notes"])}</p>'
  return out
