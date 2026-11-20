"""Work orders with distinct construction valuation and jurisdiction permit fees."""
from datetime import date
import html
from .receipts import amount
from .finance import CURRENCIES
from .development import validate_date
from .permits import JURISDICTIONS

WORK_ORDER_STATUSES=['Draft','Ready','Scheduled','In Progress','On Hold','Completed','Cancelled']
FEE_STATUSES=['Unknown','Estimated','Assessed','Paid','Waived']
VALUATION_BASES=['Estimated','Declared for Permit','Contract Based','Other']
WORK_ORDER_FIELDS=['project_id','title','reference','site_address','currency','job_valuation','permit_fee','valuation_basis','fee_status','contractor_name','contact_id','contract_id','permit_id','jurisdiction_type','jurisdiction_name','discipline','building_area','status','issued_date','start_date','deadline','scope','notes']
WORK_ORDER_SCHEMA='''
CREATE TABLE work_orders(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,reference TEXT DEFAULT '',site_address TEXT DEFAULT '',currency TEXT DEFAULT 'USD',job_valuation TEXT DEFAULT '',permit_fee TEXT DEFAULT '',valuation_basis TEXT DEFAULT 'Estimated',fee_status TEXT DEFAULT 'Unknown',contractor_name TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),contract_id INTEGER REFERENCES contracts(id),permit_id INTEGER REFERENCES registers(id),jurisdiction_type TEXT DEFAULT 'Other',jurisdiction_name TEXT DEFAULT '',discipline TEXT DEFAULT 'General',building_area TEXT DEFAULT '',status TEXT DEFAULT 'Draft',issued_date TEXT DEFAULT '',start_date TEXT DEFAULT '',deadline TEXT DEFAULT '',scope TEXT DEFAULT '',notes TEXT DEFAULT '');
CREATE INDEX work_orders_project ON work_orders(project_id);
'''

class WorkOrderStore:
 def migrate_work_orders(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=11:return
  self.db.executescript('BEGIN IMMEDIATE;'+WORK_ORDER_SCHEMA+'PRAGMA user_version=11;COMMIT;')
 def validate_work_order(self,table,data,row_id):
  if table!='work_orders':return
  projects=self.rows('SELECT address FROM projects WHERE id=?',(data.get('project_id'),))
  if not projects:raise ValueError('Choose an existing project')
  old=self.rows('SELECT * FROM work_orders WHERE id=?',(row_id,))[0] if row_id else None
  if old and old['project_id']!=data['project_id']:raise ValueError('Create a new work order to move it to another project')
  if not str(data.get('site_address','') or '').strip():data['site_address']=projects[0]['address']
  data['job_valuation']=amount(data.get('job_valuation',''));data['permit_fee']=amount(data.get('permit_fee',''));data.setdefault('currency','USD');data.setdefault('status','Draft');data.setdefault('fee_status','Unknown');data.setdefault('valuation_basis','Estimated')
  if data['currency'] not in CURRENCIES:raise ValueError('Choose a supported currency')
  if data['status'] not in WORK_ORDER_STATUSES or data['fee_status'] not in FEE_STATUSES or data['valuation_basis'] not in VALUATION_BASES:raise ValueError('Choose a valid work order status, fee status and valuation basis')
  if data['fee_status']=='Waived':
   if data['permit_fee'] not in ('','0.00'):raise ValueError('A waived permit fee must be zero; clear the amount or enter 0')
   data['permit_fee']='0.00'
  if old and old['fee_status']=='Paid' and (old['permit_fee']!=data['permit_fee'] or old['currency']!=data['currency']):
   data['fee_status']='Assessed';data['notes']='Fee changed: confirm the new amount/payment status with the jurisdiction. '+str(data.get('notes','') or '')
  if data['fee_status']=='Paid' and data['permit_fee']=='':raise ValueError('Enter the permit fee before marking it Paid; use 0 for a confirmed zero')
  if data['fee_status']=='Unknown' and data['permit_fee']!='':data['fee_status']='Estimated'
  for key in ('issued_date','start_date','deadline'):
   if data.get(key):validate_date(data[key])
  if data.get('start_date') and data.get('deadline') and data['deadline']<data['start_date']:raise ValueError('Deadline cannot precede the start date')
  if data.get('contract_id'):
   rows=self.rows('SELECT project_id,currency FROM contracts WHERE id=?',(data['contract_id'],))
   if not rows or rows[0]['project_id']!=data['project_id'] or rows[0]['currency']!=data['currency']:raise ValueError('Related contract must match project and currency')
  if data.get('permit_id'):
   rows=self.rows("SELECT project_id,jurisdiction_type,jurisdiction_name FROM registers WHERE id=? AND record_type='Permit'",(data['permit_id'],))
   if not rows or rows[0]['project_id']!=data['project_id']:raise ValueError('Choose a permit from the same project')
   data['jurisdiction_type']=rows[0]['jurisdiction_type'];data['jurisdiction_name']=rows[0]['jurisdiction_name']
  if data.get('jurisdiction_type','Other') not in JURISDICTIONS:raise ValueError('Choose a jurisdiction type')
  if not str(data.get('contractor_name','') or '').strip() and data.get('contact_id'):
   rows=self.rows('SELECT company,name FROM contacts WHERE id=?',(data['contact_id'],))
   if rows:data['contractor_name']=rows[0]['company'] or rows[0]['name']
 def work_order_rows(self):
  return self.rows('SELECT w.*,p.name AS project,c.title AS contract,r.title AS permit FROM work_orders w JOIN projects p ON p.id=w.project_id LEFT JOIN contracts c ON c.id=w.contract_id LEFT JOIN registers r ON r.id=w.permit_id ORDER BY w.id DESC')
 def work_order_report(self,pid):
  e=lambda v:html.escape(str(v if v is not None else ''));out='<h2>Work orders — job valuation and permit fees</h2>'
  for row in self.work_order_rows():
   if row['project_id']==pid:out+='<p>'+' | '.join(e(k)+': '+e(v) for k,v in row.items() if k!='id' and not k.endswith('_id') and v not in ('',None))+'</p>'
  return out
