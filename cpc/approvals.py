"""Manual item/work cost approvals with retained decision snapshots."""
from datetime import date,datetime
import html
import json
from .development import validate_date
from .receipts import amount,RECEIPT_PARTS_COLUMNS
from .finance import CURRENCIES

APPROVAL_STATUSES=['Draft','Pending Review','Approved','Rejected','Needs Changes','Withdrawn']
APPROVAL_FIELDS=['project_id','title','approval_type','reference','discipline','building_area','supplier_name','contact_id','contract_id','description','currency','price','status','submitted','deadline','reviewer_id','reviewed_by','review_date','decision_notes','notes']
APPROVAL_SCHEMA='''
CREATE TABLE approvals(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,approval_type TEXT DEFAULT 'Work',reference TEXT DEFAULT '',discipline TEXT DEFAULT 'General',building_area TEXT DEFAULT '',supplier_name TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),contract_id INTEGER REFERENCES contracts(id),description TEXT DEFAULT '',currency TEXT DEFAULT 'USD',price TEXT DEFAULT '',status TEXT DEFAULT 'Draft',submitted TEXT DEFAULT '',deadline TEXT DEFAULT '',reviewer_id INTEGER REFERENCES contacts(id),reviewed_by TEXT DEFAULT '',review_date TEXT DEFAULT '',decision_notes TEXT DEFAULT '',notes TEXT DEFAULT '');
CREATE TABLE approval_history(id INTEGER PRIMARY KEY,approval_id INTEGER NOT NULL REFERENCES approvals(id),occurred TEXT NOT NULL,event TEXT NOT NULL,snapshot TEXT NOT NULL);
CREATE INDEX approvals_project ON approvals(project_id);
'''

class ApprovalStore:
 def migrate_approvals(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=10:return
  self.db.executescript('BEGIN IMMEDIATE;'+APPROVAL_SCHEMA)
  with self.db:
   for key,kind in RECEIPT_PARTS_COLUMNS.items():self.db.execute(f'ALTER TABLE receipts ADD COLUMN {key} {kind}')
   self.db.execute('PRAGMA user_version=10')
 def validate_approval(self,table,data,row_id):
  if table!='approvals':return
  if not self.rows('SELECT id FROM projects WHERE id=?',(data.get('project_id'),)):raise ValueError('Choose an existing project')
  data['decision_notes']=str(data.get('decision_notes','') or '')
  data['price']=amount(data.get('price',''));data.setdefault('status','Draft');data.setdefault('currency','USD')
  if data['status'] not in APPROVAL_STATUSES:raise ValueError('Choose an approval status')
  if data['currency'] not in CURRENCIES:raise ValueError('Choose a supported currency')
  for key in ('submitted','deadline','review_date'):
   if data.get(key):validate_date(data[key])
  if data.get('reviewer_id'):
   people=self.rows('SELECT name FROM contacts WHERE id=?',(data['reviewer_id'],))
   if not people:raise ValueError('Choose an existing reviewer')
   if not str(data.get('reviewed_by','') or '').strip():data['reviewed_by']=people[0]['name']
  if data.get('contract_id'):
   parents=self.rows('SELECT project_id,currency FROM contracts WHERE id=?',(data['contract_id'],))
   if not parents or parents[0]['project_id']!=data['project_id'] or parents[0]['currency']!=data['currency']:raise ValueError('Related contract must match project and currency')
  if row_id:
   old=self.rows('SELECT * FROM approvals WHERE id=?',(row_id,))[0]
   if old['project_id']!=data['project_id']:raise ValueError('Create a new approval to move it to another project')
   critical=('title','approval_type','supplier_name','contact_id','contract_id','description','currency','price','building_area','discipline')
   if old['status']=='Approved' and any(data.get(k,old[k])!=old[k] for k in critical):
    data.update(status='Pending Review',reviewed_by='',review_date='');data['decision_notes']='Approval reset: the item, scope, price, supplier or contract context changed. '+data.get('decision_notes','')
  if data['status']=='Approved' and data['price']=='':raise ValueError('Enter the item/work price before approving; use 0 for a confirmed zero cost')
  if data['status'] in ('Approved','Rejected','Needs Changes'):data['review_date']=data.get('review_date') or date.today().isoformat()
  else:data['review_date']=''
 def approval_snapshot(self,approval_id,event):
  record=self.rows('SELECT * FROM approvals WHERE id=?',(approval_id,))[0]
  files=self.finance_files('approvals',approval_id);record['supporting_files']=[dict(id=f['id'],name=f['original_name'],sha256=f['sha256']) for f in files]
  self.db.execute('INSERT INTO approval_history(approval_id,occurred,event,snapshot) VALUES(?,?,?,?)',(approval_id,datetime.now().isoformat(timespec='seconds'),event,json.dumps(record,ensure_ascii=False)))
 def approval_evidence_changed(self,approval_id):
  row=self.rows('SELECT * FROM approvals WHERE id=?',(approval_id,))[0]
  if row['status']=='Approved':
   self.db.execute("UPDATE approvals SET status='Pending Review',reviewed_by='',review_date='',decision_notes=? WHERE id=?",('Approval reset: supporting files changed. '+row['decision_notes'],approval_id));self.log(row['project_id'],'Approval reset for review after supporting files changed')
  self.approval_snapshot(approval_id,'Supporting files changed')
 def approval_rows(self):
  return self.rows('SELECT a.*,p.name AS project,c.title AS contract,r.name AS reviewer FROM approvals a JOIN projects p ON p.id=a.project_id LEFT JOIN contracts c ON c.id=a.contract_id LEFT JOIN contacts r ON r.id=a.reviewer_id ORDER BY a.id DESC')
 def approval_events(self,approval_id):
  result=[]
  for row in self.rows('SELECT * FROM approval_history WHERE approval_id=? ORDER BY id DESC',(approval_id,)):
   snapshot=json.loads(row['snapshot']);result.append(dict(occurred=row['occurred'],event=row['event'],**{k:snapshot.get(k,'') for k in ('title','description','price','currency','status','reviewed_by','review_date','decision_notes')},supporting_files='; '.join(f['name'] for f in snapshot.get('supporting_files',[]))))
  return result
 def approval_report(self,pid):
  e=lambda value:html.escape(str(value if value is not None else ''));out='<h2>Item and work approvals</h2>'
  for row in self.approval_rows():
   if row['project_id']==pid:out+='<p>'+' | '.join(e(k)+': '+e(v) for k,v in row.items() if k!='id' and not k.endswith('_id') and v not in ('',None))+'</p>'
  return out
