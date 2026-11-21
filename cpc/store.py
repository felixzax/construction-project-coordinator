"""Local persistence and business rules. No network access."""
import csv
import html
import sqlite3
import shutil
import uuid
import tempfile
from contextlib import closing
from .city_permits import CityPermitStore
from .regulatory import RegulatoryStore
from .regulatory_schema import REG_FIELDS
from .privacy import check_values, check_attachment
from .work_orders import WorkOrderStore,WORK_ORDER_FIELDS
from .approvals import ApprovalStore,APPROVAL_FIELDS
from .navigation import NavigationStore
from .scope import ScopeStore,SCOPE_FIELDS,PROTECTED_SECTIONS
from .finance import FinanceStore, FINANCE_FIELDS, RECEIPT_FINANCE_COLUMNS
from .issues import IssueStore, ISSUE_FIELDS
from .receipts import ReceiptStore, RECEIPT_FIELDS, RECEIPT_PARTS_COLUMNS
from .recovery import RecoveryStore, RECOVERY_TABLES
from .permits import PermitStore, PERMIT_COLUMNS, REQUIREMENT_FIELDS
from .development import DevelopmentStore, NEW_FIELDS, ADDED_COLUMNS, validate_date
from datetime import date, datetime, timedelta
from pathlib import Path

TASK_STATUSES = ['Not Started', 'Waiting on Someone', 'In Progress', 'Submitted', 'Approved', 'Completed']
SCHEMA = '''
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT DEFAULT '', owner TEXT DEFAULT '', description TEXT DEFAULT '', phase TEXT DEFAULT 'Planning', status TEXT DEFAULT 'Active', archived INTEGER DEFAULT 0, updated TEXT);
CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT DEFAULT '', company TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS project_contacts(project_id INTEGER REFERENCES projects(id), contact_id INTEGER REFERENCES contacts(id), PRIMARY KEY(project_id,contact_id));
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), title TEXT NOT NULL, deadline TEXT DEFAULT '', priority TEXT DEFAULT 'Normal', contact_id INTEGER REFERENCES contacts(id), status TEXT DEFAULT 'Not Started', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), title TEXT NOT NULL, category TEXT DEFAULT 'Architectural Plans');
CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id), revision TEXT NOT NULL, submitted TEXT DEFAULT '', status TEXT DEFAULT 'Draft', requirements TEXT DEFAULT '', file_path TEXT DEFAULT '', resubmission INTEGER DEFAULT 0, created TEXT, UNIQUE(document_id,revision));
CREATE TABLE IF NOT EXISTS communications(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), contact_id INTEGER REFERENCES contacts(id), occurred TEXT NOT NULL, summary TEXT NOT NULL, follow_up TEXT DEFAULT '', status TEXT DEFAULT 'Open');
CREATE TABLE IF NOT EXISTS milestones(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), title TEXT NOT NULL, phase TEXT DEFAULT '', deadline TEXT DEFAULT '', status TEXT DEFAULT 'Planned');
CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY, project_id INTEGER REFERENCES projects(id), occurred TEXT, description TEXT);

'''
FIELDS = {
 'projects': ['name','address','owner','description','phase','status','archived'],
 'contacts': ['name','role','company','email','phone','notes'],
 'tasks': ['project_id','title','deadline','priority','contact_id','status','notes'],
 'documents': ['project_id','title','category'],
 'communications': ['project_id','contact_id','occurred','summary','follow_up','status'],
 'milestones': ['project_id','title','phase','deadline','status'],
}
FIELDS.update(REG_FIELDS)
FIELDS.update(NEW_FIELDS)
FIELDS['receipts']=RECEIPT_FIELDS
FIELDS['issues']=ISSUE_FIELDS
FIELDS['approvals']=APPROVAL_FIELDS
FIELDS['work_orders']=WORK_ORDER_FIELDS
FIELDS.update(FINANCE_FIELDS)
FIELDS.update(SCOPE_FIELDS)
FIELDS['finance_files'].extend(['owner_table','owner_id'])
FIELDS['receipts'].extend(RECEIPT_FINANCE_COLUMNS)
FIELDS['registers'].extend(PERMIT_COLUMNS)
FIELDS['permit_requirements']=REQUIREMENT_FIELDS+['completed_on']
for _table,_columns in ADDED_COLUMNS.items():
 FIELDS[_table].extend(_columns)

class Store(CityPermitStore,RegulatoryStore,WorkOrderStore,ApprovalStore,NavigationStore,ScopeStore,FinanceStore,IssueStore,ReceiptStore,RecoveryStore,PermitStore,DevelopmentStore):
 def __init__(self, path):
  self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
  self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row
  version=self.db.execute('PRAGMA user_version').fetchone()[0]
  if version not in (0,1,2,3,4,5,6,7,8,9,10,11,12):
   self.db.close(); raise ValueError('This database requires a newer version of the application')
  if version in range(1,12):
   safety=Path(str(self.path)+'.before-v1.12.0.sqlite3')
   # Never overwrite the first rollback copy on a retried migration.
   if not safety.exists():self.backup(safety)
  if version in range(1,11):
   legacy=Path(str(self.path)+'.before-v1.11.0.sqlite3')
   if not legacy.exists():self.backup(legacy)
  self.db.execute('PRAGMA foreign_keys=ON'); self.db.executescript(SCHEMA)
  self.migrate_development()
  self.migrate_permits()
  self.migrate_recovery()
  self.migrate_receipts()
  self.migrate_issues()
  self.migrate_finance()
  self.migrate_scope()
  self.migrate_navigation()
  self.migrate_approvals()
  self.migrate_work_orders()
  self.migrate_regulatory()
  self.db.execute("PRAGMA journal_mode=WAL")
  self.db.execute("PRAGMA synchronous=FULL")
  self.db.execute("PRAGMA busy_timeout=5000")
 def rows(self,sql,args=()): return [dict(r) for r in self.db.execute(sql,args)]
 def all(self,table):
  if table not in FIELDS: raise ValueError('Unknown table')
  return self.rows(f'SELECT * FROM {table} ORDER BY id DESC')
 def log(self,pid,message):
  check_values(message)
  now=datetime.now().isoformat(timespec='seconds')
  self.db.execute('INSERT INTO activity(project_id,occurred,description) VALUES(?,?,?)',(pid,now,message))
  self.db.execute('UPDATE projects SET updated=? WHERE id=?',(now,pid))
 def save(self,table,data,row_id=None):
  if table not in FIELDS: raise ValueError('Unknown table')
  check_values(data)
  profile_settings={k[4:]:v for k,v in data.items() if k in ('reg_cgp_subject','reg_jurisdiction')} if table=='project_profiles' else {}
  if profile_settings:
   from .regulatory import JURISDICTIONS
   if profile_settings.get('cgp_subject','Undecided') not in ('Undecided','Yes','No','Not Applicable') or profile_settings.get('jurisdiction','Other') not in JURISDICTIONS:raise ValueError('Invalid regulatory profile settings')
  data={k:v for k,v in data.items() if k in FIELDS[table]}
  if row_id:
   previous=self.rows(f'SELECT * FROM {table} WHERE id=?',(row_id,))
   if not previous: raise ValueError('Record not found')
   data={**{k:v for k,v in previous[0].items() if k in FIELDS[table]},**data}
  self.validate_development(table,data,row_id)
  self.validate_permit(table,data,row_id)
  self.validate_receipt(table,data,row_id)
  self.validate_issue(table,data,row_id)
  self.validate_finance(table,data,row_id)
  self.validate_scope(table,data,row_id)
  self.validate_approval(table,data,row_id)
  self.validate_work_order(table,data,row_id)
  self.validate_regulatory(table,data,row_id)
  self.validate_city(table,data,row_id)
  for key in ('name','title','summary'):
   if key in FIELDS[table] and not str(data.get(key,'')).strip(): raise ValueError(f'{key.title()} is required')
  for key in ('deadline','follow_up','occurred'):
   if data.get(key): validate_date(data[key])
  if table=='tasks' and data.get('status') not in TASK_STATUSES: raise ValueError('Invalid task status')
  with self.db:
   if row_id:
    if not self.db.execute(f'SELECT 1 FROM {table} WHERE id=?',(row_id,)).fetchone(): raise ValueError('Record not found')
    self.db.execute(f'UPDATE {table} SET '+','.join(f'{k}=?' for k in data)+' WHERE id=?',[*data.values(),row_id])
   else:
    row_id=self.db.execute(f'INSERT INTO {table} ('+','.join(data)+') VALUES ('+','.join('?' for _ in data)+')',list(data.values())).lastrowid
   if profile_settings:
    self.db.execute('INSERT OR IGNORE INTO reg_project_settings(project_id) VALUES(?)',(data['project_id'],))
    self.db.execute('UPDATE reg_project_settings SET '+','.join(k+'=?' for k in profile_settings)+' WHERE project_id=?', [*profile_settings.values(),data['project_id']])
   if table=='work_orders':self.log(data['project_id'],f'Work order #{row_id}: job valuation {data["job_valuation"] or "unknown"}; permit fee {data["permit_fee"] or "unknown"} {data["currency"]}; fee {data["fee_status"]}')
   if table=='approvals':self.approval_snapshot(row_id,'Record saved')
   pid=row_id if table=='projects' else self.project_for(table,data)
   if table=='issues' and pid:self.log(pid,f'{data.get("issue_type","Correction")} #{row_id}: {data.get("status","Open")}; required fix: {data["required_fix"]}')
   if table=='receipts' and pid: self.log(pid,f'Supplier receipt #{row_id}: {data["supplier_name"]}; estimate {data["estimated_amount"] or "unknown"}; actual {data["actual_amount"] or "unknown"} {data.get("currency","USD")}; {data.get("status","Pending Review")}')
   if pid: self.log(pid,f'{table.title()} #{row_id} saved: {data.get("name",data.get("title",data.get("summary","")))}')
  return row_id
 def associate(self,pid,cid):
  with self.db:
   self.db.execute('INSERT OR IGNORE INTO project_contacts VALUES(?,?)',(pid,cid)); self.log(pid,f'Contact #{cid} associated')
 def add_version(self,did,revision,submitted='',status='Draft',requirements='',file_path=''):
  if not revision.strip(): raise ValueError('Revision is required')
  if self.rows('SELECT id FROM versions WHERE document_id=? AND revision=?',(did,revision)):
   raise sqlite3.IntegrityError('This revision label already exists')
  if submitted: validate_date(submitted)
  if status not in ['Draft','Submitted','Approved','Changes Required']: raise ValueError('Invalid approval status')
  doc=self.rows('SELECT * FROM documents WHERE id=?',(did,))
  if not doc: raise ValueError('Document not found')
  previous=self.rows("SELECT status FROM versions WHERE document_id=? AND status IN ('Approved','Submitted') ORDER BY id DESC LIMIT 1",(did,))
  flag=int(bool(previous and previous[0]['status'] in ('Approved','Submitted')))
  check_values(dict(revision=revision,requirements=requirements))
  if file_path:
   check_attachment(file_path)
   source=Path(file_path)
   if not source.is_file(): raise ValueError('Document file does not exist')
   folder=self.path.parent/'documents'; folder.mkdir(exist_ok=True)
   target=folder/(uuid.uuid4().hex+source.suffix)
   shutil.copy2(source,target); file_path=str(target.resolve())
  with self.db:
   self.db.execute('INSERT INTO versions(document_id,revision,submitted,status,requirements,file_path,resubmission,created) VALUES(?,?,?,?,?,?,?,?)',(did,revision,submitted,status,requirements,file_path,flag,datetime.now().isoformat(timespec='seconds')))
   self.log(doc[0]['project_id'],f'Document {doc[0]["title"]}: revision {revision} recorded'+(' — review resubmission' if flag else ''))
 def versions(self,did): return self.rows('SELECT * FROM versions WHERE document_id=? ORDER BY id DESC',(did,))
 def search(self,query):
  result=[]
  for table,fields in FIELDS.items():
   cols=[f for f in fields if not f.endswith('_id') and f not in ('archived','included')]
   for row in self.rows(f'SELECT * FROM {table} WHERE '+ ' OR '.join(f'{c} LIKE ?' for c in cols),['%'+query+'%']*len(cols)):
    result.append({'type':table,'id':row['id'],'project_id':(row['id'] if table=='projects' else self.project_for(table,row)) or '','label':row.get('name',row.get('title',row.get('summary',row.get('original_name',''))))})
  for row in self.rows('SELECT v.*,d.project_id,d.title FROM versions v JOIN documents d ON d.id=v.document_id WHERE v.revision LIKE ? OR v.requirements LIKE ?',('%'+query+'%','%'+query+'%')):
   result.append({'type':'versions','id':row['id'],'project_id':row['project_id'],'label':row['title']+' / '+row['revision']+': '+row['requirements']})
  return result
 def outstanding(self,pid=None):
  return self.rows("SELECT t.*,p.name AS project,c.name AS responsible FROM tasks t JOIN projects p ON p.id=t.project_id LEFT JOIN contacts c ON c.id=t.contact_id WHERE t.status != 'Completed' AND p.archived=0"+(' AND t.project_id=?' if pid else '')+' ORDER BY deadline', (pid,) if pid else ())
 def backup(self,path):
  if Path(path).resolve()==self.path.resolve(): raise ValueError('Choose a different backup path')
  with closing(sqlite3.connect(path)) as dest: self.db.backup(dest)
 def restore(self,path):
  source=Path(path)
  if source.resolve()==self.path.resolve(): raise ValueError('Choose a different backup file')
  with tempfile.TemporaryDirectory() as folder:
   copy=Path(folder)/'restore.sqlite3'
   with closing(sqlite3.connect(f'{source.resolve().as_uri()}?mode=ro',uri=True)) as candidate:
    if candidate.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Invalid backup')
    version=candidate.execute('PRAGMA user_version').fetchone()[0]
    if version not in (1,2,3,4,5,6,7,8,9,10,11,12): raise ValueError('Unsupported backup version')
    # Validate the original schema before any CREATE TABLE statement can mask missing tables.
    for table in list(FIELDS)+['versions','activity','project_contacts']+RECOVERY_TABLES+['project_sections','project_section_order','approval_history']:
     if version<12 and table in REG_FIELDS:continue
     if version<11 and table=='work_orders':continue
     if version<10 and table in ('approvals','approval_history'):continue
     if version<9 and table=='project_section_order':continue
     if version<8 and table in (*SCOPE_FIELDS,'project_sections'):continue
     if version<7 and table in FINANCE_FIELDS:continue
     if version<6 and table=='issues':continue
     if version<5 and table=='receipts': continue
     if version<4 and table in RECOVERY_TABLES: continue
     if version==1 and table in NEW_FIELDS: continue
     if version<=2 and table=='permit_requirements': continue
     expected={r[1] for r in self.db.execute(f'PRAGMA table_info({table})')}
     if version<10 and table=='receipts':expected-=set(RECEIPT_PARTS_COLUMNS)
     if version<8 and table=='finance_files':expected-={'owner_table','owner_id'}
     if version<7 and table=='receipts':expected-=set(RECEIPT_FINANCE_COLUMNS)
     if version==1: expected-=set(ADDED_COLUMNS.get(table,{}))
     if version<=2 and table=='registers': expected-=set(PERMIT_COLUMNS)
     actual={r[1] for r in candidate.execute(f'PRAGMA table_info({table})')}
     if not expected.issubset(actual): raise ValueError('Backup schema mismatch')
    if candidate.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Backup has broken relationships')
    with closing(sqlite3.connect(copy)) as target: candidate.backup(target)
   restored=Store(copy)
   try:
    if restored.db.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Backup relationships are invalid')
    for attachment in restored.all('finance_files'):
     owner,rid=restored.attachment_owner(attachment);restored.attachment_parent(owner,rid)
    from .development_ui import NAVIGATION
    for setting in restored.rows('SELECT * FROM project_sections'):
     if setting['section'] in PROTECTED_SECTIONS or setting['section'] not in NAVIGATION or setting['hidden'] not in (0,1):raise ValueError('Backup has invalid section preferences')
    restored.validate_section_orders()
    self.backup(str(self.path)+'.before-restore.sqlite3')
    restored.db.backup(self.db)
   finally: restored.db.close()
 def export(self,path,rows):
  check_values(rows)
  with open(path,'w',newline='',encoding='utf-8-sig') as f:
   if not rows: return
   writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader()
   writer.writerows({k: ("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()} for row in rows)
 def report(self,pid):
  p=self.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
  e=lambda v:html.escape(str(v or ''))
  out=f'<h1>{e(p["name"])}</h1><p>{e(p["address"])}<br>Owner: {e(p["owner"])}<br>Phase: {e(p["phase"])} · {e(p["status"])}</p><p>{e(p["description"])}</p>'
  for title,rows in [('Outstanding tasks',self.outstanding(pid)),('Documents',self.rows('SELECT d.title,v.revision,v.status,v.requirements,v.resubmission FROM documents d LEFT JOIN versions v ON v.id=(SELECT MAX(id) FROM versions WHERE document_id=d.id) WHERE d.project_id=?',(pid,))),('Milestones',self.rows('SELECT title,phase,deadline,status FROM milestones WHERE project_id=? ORDER BY deadline',(pid,))),('Communication',self.rows('SELECT occurred,summary,follow_up,status FROM communications WHERE project_id=? ORDER BY occurred DESC',(pid,)))]:
   out+=f'<h2>{title}</h2>'
   for r in rows: out+='<p>'+' | '.join(f'{e(k)}: {e(v)}' for k,v in r.items() if k not in ('id','project_id','contact_id'))+'</p>'
  return out+self.development_report(pid)+self.permit_checklist_report(pid)+self.receipt_report(pid)+self.issue_report(pid)+self.finance_report(pid)+self.scope_report(pid)+self.approval_report(pid)+self.work_order_report(pid)
 def draft(self,comm):
  p=self.rows('SELECT name FROM projects WHERE id=?',(comm['project_id'],))[0]
  c=self.rows('SELECT name,email FROM contacts WHERE id=?',(comm['contact_id'],))
  name=c[0]['name'] if c else 'Team'
  return f'To: {c[0]["email"] if c else ""}\nSubject: Follow-up — {p["name"]}\n\nHello {name},\n\nI am following up regarding {p["name"]}:\n\n{comm["summary"]}\n\nPlease share an update on the outstanding items and your anticipated completion date.'+(f' We would appreciate a response by {comm["follow_up"]}.' if comm['follow_up'] else '')+'\n\nThank you for your assistance.\nBest regards,\nProject Coordination Team'
 def seed(self):
  if self.all('projects'): return
  p=self.save('projects',dict(name='Cedar Grove Retail Renovation',address='120 Example Avenue',owner='Cedar Grove Holdings (fictional)',description='Tenant improvements and permit coordination. Fictional demonstration project.',phase='Permitting',status='Active',archived=0))
  c=self.save('contacts',dict(name='Alex Morgan',role='Architect',company='Example Design Studio',email='alex@example.com',phone='555-0100',notes='Fictional sample contact'))
  self.associate(p,c)
  self.save('tasks',dict(project_id=p,title='Request revised accessibility plans',deadline=(date.today()-timedelta(days=2)).isoformat(),priority='High',contact_id=c,status='Waiting on Someone',notes='Confirm city review comments have been addressed.'))
  self.save('tasks',dict(project_id=p,title='Coordinate permit review',deadline=(date.today()+timedelta(days=7)).isoformat(),priority='Normal',contact_id=c,status='Not Started',notes=''))
  d=self.save('documents',dict(project_id=p,title='Architectural plan set',category='Architectural Plans'))
  self.add_version(d,'A','', 'Approved'); self.add_version(d,'B',requirements='Review accessibility revisions for resubmission')
  self.save('communications',dict(project_id=p,contact_id=c,occurred=date.today().isoformat(),summary='Requested revised accessibility sheets.',follow_up=(date.today()+timedelta(days=3)).isoformat(),status='Open'))
  self.save('milestones',dict(project_id=p,title='Permit decision',phase='Permitting',deadline=(date.today()+timedelta(days=21)).isoformat(),status='Planned'))

  self.seed_development(p,c)
  permit=self.save('registers',dict(project_id=p,title='Tenant improvement permit',record_type='Permit',jurisdiction_type='City',jurisdiction_name='Example City (fictional)',department='Building & Safety',requirements_url='https://example.com/permit-requirements',application_url='https://example.com/permit-application',notes='Fictional links for demonstration; replace with your jurisdiction website.'))
  self.save('permit_requirements',dict(register_id=permit,title='Complete permit application',source_url='https://example.com/permit-requirements',completed=0))
  self.save('permit_requirements',dict(register_id=permit,title='Prepare coordinated plan set',completed=1))

  self.save('receipts',dict(project_id=p,title='Example lighting materials receipt',supplier_name='Example Electrical Supply (fictional)',reference='DEMO-REC-001',discipline='Electrical',currency='USD',estimated_amount='1250.00',actual_amount='1295.50',status='Pending Review',notes='Fictional sample pricing; replace with supplier information.'))

  self.save('issues',dict(project_id=p,title='Accessibility plan correction',issue_type='Correction',required_fix='Revise accessible counter detail on sheet A-102',location='Sales counter',discipline='Architecture',contact_id=c,deadline=(date.today()+timedelta(days=7)).isoformat(),authority='Example City plan review (fictional)',status='Open'))
  self.save('issues',dict(project_id=p,title='Electrical panel clearance violation',issue_type='Violation',required_fix='Remove stored materials from the panel working clearance',location='Rear electrical room',discipline='Electrical',contact_id=c,priority='High',deadline=(date.today()-timedelta(days=1)).isoformat(),authority='Example inspector (fictional)',status='Open'))

  budget=self.save('budgets',dict(project_id=p,title='Electrical budget',discipline='Electrical',currency='USD',base_amount='10000',contingency_amount='1000'))
  self.save('contracts',dict(project_id=p,title='Electrical installation agreement',contractor_name='Example Electrical A (fictional)',budget_id=budget,discipline='Electrical',currency='USD',original_amount='7500',scope='Fictional installation scope',status='Active'))

  self.save('project_profiles',dict(project_id=p,title='Project profile',use_type='Commercial',project_type='Tenant Improvement',kitchen='Undecided',occupied_work='Yes',notes='Fictional example; verify all scope decisions with the project team.'))
  self.save('scope_items',dict(project_id=p,title='Heating / cooling equipment',category='Energy & Utilities',discipline='Mechanical / HVAC',system_type='HVAC',energy_source='Hybrid (electric / gas)',applicability='Yes',notes='Fictional example equipment; specifications to be confirmed.'))
  self.save('rebates',dict(project_id=p,title='Example utility equipment rebate (fictional)',provider='Example utility',requirements_url='https://example.com/rebate-requirements',application_url='https://example.com/rebate-application',notes='Fictional program; replace with current provider requirements.'))

  self.save('approvals',dict(project_id=p,title='Example lighting materials purchase',approval_type='Parts / Materials',discipline='Electrical',supplier_name='Example Electrical Supply (fictional)',price='1295.50',currency='USD',status='Pending Review',deadline=(date.today()+timedelta(days=5)).isoformat(),description='Fictional purchase request; review specifications and price before ordering.'))

  self.save('work_orders',dict(project_id=p,title='Example retail improvement work order',reference='DEMO-WO-001',job_valuation='25000',permit_fee='650',currency='USD',valuation_basis='Declared for Permit',fee_status='Estimated',permit_id=permit,discipline='General',status='Draft',scope='Fictional tenant improvement scope; verify valuation and fee with the jurisdiction.'))
