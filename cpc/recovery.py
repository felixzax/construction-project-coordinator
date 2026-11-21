"""Durable drafts, recovery snapshots and transactional, backed-up deletion."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import json
import os
import sqlite3
import uuid

RECOVERY_SCHEMA='''
CREATE TABLE IF NOT EXISTS form_drafts(id TEXT PRIMARY KEY,target_table TEXT NOT NULL,row_id INTEGER,payload TEXT NOT NULL,extra TEXT NOT NULL DEFAULT '{}',updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS app_session(id INTEGER PRIMARY KEY CHECK(id=1),active INTEGER NOT NULL DEFAULT 0,started TEXT DEFAULT '',last_clean TEXT DEFAULT '');
INSERT OR IGNORE INTO app_session(id) VALUES(1);
'''
RECOVERY_TABLES=['form_drafts','app_session']

def now(): return datetime.now().isoformat(timespec='seconds')
def chunks(values,size=400):
 values=list(values)
 for start in range(0,len(values),size): yield values[start:start+size]
def marks(values): return ','.join('?' for _ in values)

class RecoveryStore:
 def migrate_recovery(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=4: return
  self.db.executescript('BEGIN IMMEDIATE;'+RECOVERY_SCHEMA+'PRAGMA user_version=4;COMMIT;')
 def start_session(self):
  previous=self.db.execute('SELECT active FROM app_session WHERE id=1').fetchone()[0]
  with self.db: self.db.execute('UPDATE app_session SET active=1,started=? WHERE id=1',(now(),))
  self._session_started=True
  self.recovery_snapshot('startup')
  return bool(previous)
 def end_session(self):
  if not getattr(self,'_session_started',False): return
  self.recovery_snapshot('automatic')
  with self.db: self.db.execute('UPDATE app_session SET active=0,last_clean=? WHERE id=1',(now(),))
  self._session_started=False
 def recovery_snapshot(self,reason='automatic'):
  if reason not in ('automatic','startup','before-delete'): raise ValueError('Unknown recovery snapshot type')
  folder=self.path.parent/'recovery'; folder.mkdir(exist_ok=True)
  stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
  path=folder/f'{reason}-{stamp}-{uuid.uuid4().hex[:6]}.sqlite3'
  temporary=path.with_suffix('.partial')
  try:
   self.backup(temporary)
   with closing(sqlite3.connect(temporary)) as candidate:
    if candidate.execute('PRAGMA quick_check').fetchone()[0]!='ok': raise ValueError('Recovery snapshot verification failed')
   os.replace(temporary,path)
  finally:
   if temporary.exists(): temporary.unlink()
  keep=10 if reason=='before-delete' else 5
  old=sorted(folder.glob(reason+'-*.sqlite3'),reverse=True)[keep:]
  for file in old:
   try: file.unlink()
   except OSError: pass
  return path
 def recovery_snapshots(self):
  folder=self.path.parent/'recovery'
  return [dict(path=str(p),name=p.name,bytes=p.stat().st_size) for p in sorted(folder.glob('*.sqlite3'),reverse=True)] if folder.exists() else []
 def save_draft(self,key,table,row_id,values,extra=None):
  from .store import FIELDS
  if table not in FIELDS and table!='__versions__': raise ValueError('Unknown form type')
  from .privacy import check_values
  check_values(values);check_values(extra or {})
  encoded=json.dumps(values,ensure_ascii=False); metadata=json.dumps(extra or {},ensure_ascii=False)
  with self.db:
   self.db.execute('INSERT INTO form_drafts(id,target_table,row_id,payload,extra,updated) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,extra=excluded.extra,updated=excluded.updated',(key,table,row_id,encoded,metadata,now()))
 def discard_draft(self,key):
  with self.db: self.db.execute('DELETE FROM form_drafts WHERE id=?',(key,))
 def drafts(self):
  rows=self.rows('SELECT * FROM form_drafts ORDER BY updated DESC')
  for row in rows: row['values']=json.loads(row['payload']); row['metadata']=json.loads(row['extra'])
  return rows
 def _delete_plan(self,targets):
  from .store import FIELDS
  allowed=set(FIELDS)|{'versions','activity'}
  plan={}
  for table,row_id in targets:
   if table not in allowed: raise ValueError('Unknown record type')
   if not isinstance(row_id,int): raise ValueError('Select a saved record')
   if self.db.execute(f'SELECT 1 FROM {table} WHERE id=?',(row_id,)).fetchone(): plan.setdefault(table,set()).add(row_id)
  links=[('approvals','approval_history','approval_id'),('scope_items','custom_fields','scope_item_id'),('contracts','contract_changes','contract_id'),('contracts','finance_files','contract_id'),('budgets','finance_files','budget_id'),('documents','versions','document_id'),('registers','permit_requirements','register_id'),('bid_packages','bids','package_id'),('bids','bid_items','bid_id')]
  for table,fields in FIELDS.items():
   if 'project_id' in fields: links.append(('projects',table,'project_id'))
  from .regulatory_schema import REG_FIELDS
  # Include cascading metadata in the plan so polymorphic Files and drafts
  # are removed and the confirmation lists the actual records affected.
  for child in REG_FIELDS:
   for fk in self.db.execute(f'PRAGMA foreign_key_list({child})'):
    if fk[6]=='CASCADE':links.append((fk[2],child,fk[3]))
  links.append(('projects','activity','project_id'))
  changed=True
  while changed:
   changed=False
   for parent,child,fk in links:
    for batch in chunks(plan.get(parent,())):
     ids={r['id'] for r in self.rows(f'SELECT id FROM {child} WHERE {fk} IN ({marks(batch)})',batch)}
     new=ids-plan.get(child,set())
     if new: plan.setdefault(child,set()).update(new); changed=True
   for parent,ids in list(plan.items()):
    for batch in chunks(ids):
     files={r['id'] for r in self.rows(f'SELECT id FROM finance_files WHERE owner_table=? AND owner_id IN ({marks(batch)})',[parent,*batch])}
     new=files-plan.get('finance_files',set())
     if new:plan.setdefault('finance_files',set()).update(new);changed=True
  return plan
 def deletion_summary(self,targets):
  return {table:len(ids) for table,ids in self._delete_plan(targets).items()}
 def delete_records(self,targets,all_data=False):
  from .store import FIELDS
  plan=self._delete_plan(targets)
  if not plan and not all_data: return None
  backup=self.recovery_snapshot('before-delete')
  changed_approvals=set()
  for batch in chunks(plan.get('finance_files',())):
   changed_approvals.update(r['owner_id'] for r in self.rows(f"SELECT owner_id FROM finance_files WHERE owner_table='approvals' AND id IN ({marks(batch)})",batch))
  affected=set()
  for table,ids in plan.items():
   for batch in chunks(ids):
    for row in self.rows(f'SELECT * FROM {table} WHERE id IN ({marks(batch)})',batch):
     pid=row['id'] if table=='projects' else self.project_for(table,row)
     if pid: affected.add(pid)
  with self.db:
   # Preserve explicit deletion of generated City/County checklist and tracker
   # items across idempotent Add and future context switches.
   for table in ('permit_requirements','reg_tracker_steps'):
    for rid in plan.get(table,()):
     if table=='permit_requirements':
      items=self.rows('SELECT r.register_id,d.template_key AS item_key FROM permit_requirements r JOIN reg_requirement_details d ON d.requirement_id=r.id WHERE r.id=? AND d.origin=\'Template\'',(rid,))
     else:items=self.rows('SELECT register_id,step_key AS item_key FROM reg_tracker_steps WHERE id=? AND template_item_id IS NOT NULL',(rid,))
     for item in items:
      if item['register_id'] in plan.get('registers',()):continue
      pid=self.rows('SELECT project_id FROM registers WHERE id=?',(item['register_id'],))[0]['project_id']
      self.db.execute('INSERT OR IGNORE INTO reg_template_tombstones(project_id,register_id,template_item_key,reason,occurred) VALUES(?,?,?,?,?)',(pid,item['register_id'],item['item_key'],'User deletion',now()))
   for batch in chunks(plan.get('scope_items',())):self.db.execute(f'UPDATE rebates SET scope_item_id=NULL WHERE scope_item_id IN ({marks(batch)})',batch)
   for batch in chunks(plan.get('bids',())):self.db.execute(f'UPDATE contracts SET bid_id=NULL WHERE bid_id IN ({marks(batch)})',batch)
   for batch in chunks(plan.get('contracts',())):
    self.db.execute(f'UPDATE receipts SET contract_id=NULL WHERE contract_id IN ({marks(batch)})',batch)
    self.db.execute(f'UPDATE approvals SET contract_id=NULL WHERE contract_id IN ({marks(batch)})',batch)
    self.db.execute(f'UPDATE work_orders SET contract_id=NULL WHERE contract_id IN ({marks(batch)})',batch)
   for batch in chunks(plan.get('budgets',())):
    self.db.execute(f'UPDATE contracts SET budget_id=NULL WHERE budget_id IN ({marks(batch)})',batch)
    self.db.execute(f'UPDATE receipts SET budget_id=NULL WHERE budget_id IN ({marks(batch)})',batch)
   for batch in chunks(plan.get('contacts',())):
    self.db.execute(f"UPDATE reg_project_roles SET eauthorization_status='Unknown',eauthorization_date='' WHERE contact_id IN ({marks(batch)})",batch)
    for table,fields in FIELDS.items():
     for fk in ('contact_id','designer_id','reviewer_id','requested_from_contact_id','prepared_by_contact_id'):
      if fk in fields: self.db.execute(f'UPDATE {table} SET {fk}=NULL WHERE {fk} IN ({marks(batch)})',batch)
    self.db.execute(f'DELETE FROM project_contacts WHERE contact_id IN ({marks(batch)})',batch)
   for batch in chunks(plan.get('registers',())):
    self.db.execute(f'UPDATE issues SET permit_id=NULL WHERE permit_id IN ({marks(batch)})',batch)
    self.db.execute(f'UPDATE work_orders SET permit_id=NULL WHERE permit_id IN ({marks(batch)})',batch)
   for batch in chunks(plan.get('meetings',())):
    self.db.execute(f'UPDATE tasks SET meeting_id=NULL WHERE meeting_id IN ({marks(batch)})',batch)
   for batch in chunks(plan.get('projects',())):
    self.db.execute(f'DELETE FROM project_section_order WHERE project_id IN ({marks(batch)})',batch)
    self.db.execute(f'DELETE FROM project_sections WHERE project_id IN ({marks(batch)})',batch)
    self.db.execute(f'DELETE FROM project_contacts WHERE project_id IN ({marks(batch)})',batch)
   from .regulatory_schema import REG_FIELDS
   order=['finance_files',*reversed(REG_FIELDS),'work_orders','approval_history','approvals','custom_fields','rebates','scope_items','project_profiles','contract_changes','issues','receipts','permit_requirements','bid_items','versions','tasks','communications','milestones','work_packages','registers','meetings','bids','bid_packages','documents','contracts','budgets','activity','projects','contacts']
   for table in order:
    for batch in chunks(plan.get(table,())): self.db.execute(f'DELETE FROM {table} WHERE id IN ({marks(batch)})',batch)
   for approval_id in changed_approvals-plan.get('approvals',set()):self.approval_evidence_changed(approval_id)
   # Existing discounts must still fit when deleting cost items. Failure rolls back the entire deletion.
   if plan.get('bid_items'):
    for bid in self.all('bids'): self.bid_totals(bid['id'])
   if plan.get('contract_changes'):
    for contract in self.all('contracts'):self.contract_totals(contract['id'])
   if all_data: self.db.execute('DELETE FROM form_drafts')
   else:
    for table,ids in plan.items():
     for batch in chunks(ids): self.db.execute(f'DELETE FROM form_drafts WHERE target_table=? AND row_id IN ({marks(batch)})',[table,*batch])
   for pid in affected-plan.get('projects',set()):
    self.log(pid,'Deleted records: '+', '.join(f'{len(ids)} {table}' for table,ids in plan.items()))
  return backup
 def delete_all_data(self):
  from .store import FIELDS
  targets=[(table,row['id']) for table in FIELDS for row in self.all(table)]
  return self.delete_records(targets,all_data=True)
 def clear_display_cache(self):
  # Frees SQLite's connection cache; committed records, drafts and recovery snapshots are untouched.
  self.db.execute('PRAGMA shrink_memory')
  self.db.execute('PRAGMA wal_checkpoint(PASSIVE)')
