"""Local persistence and business rules. No network access."""
import csv
import html
import sqlite3
import shutil
import uuid
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
PRAGMA user_version=1;
'''
FIELDS = {
 'projects': ['name','address','owner','description','phase','status','archived'],
 'contacts': ['name','role','company','email','phone','notes'],
 'tasks': ['project_id','title','deadline','priority','contact_id','status','notes'],
 'documents': ['project_id','title','category'],
 'communications': ['project_id','contact_id','occurred','summary','follow_up','status'],
 'milestones': ['project_id','title','phase','deadline','status'],
}
class Store:
 def __init__(self, path):
  self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
  self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row
  self.db.execute('PRAGMA foreign_keys=ON'); self.db.executescript(SCHEMA)
 def rows(self,sql,args=()): return [dict(r) for r in self.db.execute(sql,args)]
 def all(self,table):
  if table not in FIELDS: raise ValueError('Unknown table')
  return self.rows(f'SELECT * FROM {table} ORDER BY id DESC')
 def log(self,pid,message):
  now=datetime.now().isoformat(timespec='seconds')
  self.db.execute('INSERT INTO activity(project_id,occurred,description) VALUES(?,?,?)',(pid,now,message))
  self.db.execute('UPDATE projects SET updated=? WHERE id=?',(now,pid))
 def save(self,table,data,row_id=None):
  if table not in FIELDS: raise ValueError('Unknown table')
  data={k:v for k,v in data.items() if k in FIELDS[table]}
  for key in ('name','title','summary'):
   if key in FIELDS[table] and not str(data.get(key,'')).strip(): raise ValueError(f'{key.title()} is required')
  for key in ('deadline','follow_up','occurred'):
   if data.get(key): date.fromisoformat(data[key])
  if table=='tasks' and data.get('status') not in TASK_STATUSES: raise ValueError('Invalid task status')
  with self.db:
   if row_id:
    if not self.db.execute(f'SELECT 1 FROM {table} WHERE id=?',(row_id,)).fetchone(): raise ValueError('Record not found')
    self.db.execute(f'UPDATE {table} SET '+','.join(f'{k}=?' for k in data)+' WHERE id=?',[*data.values(),row_id])
   else:
    row_id=self.db.execute(f'INSERT INTO {table} ('+','.join(data)+') VALUES ('+','.join('?' for _ in data)+')',list(data.values())).lastrowid
   pid=row_id if table=='projects' else data.get('project_id')
   if pid: self.log(pid,f'{table.title()} #{row_id} saved: {data.get("name",data.get("title",data.get("summary","")))}')
  return row_id
 def associate(self,pid,cid):
  with self.db:
   self.db.execute('INSERT OR IGNORE INTO project_contacts VALUES(?,?)',(pid,cid)); self.log(pid,f'Contact #{cid} associated')
 def add_version(self,did,revision,submitted='',status='Draft',requirements='',file_path=''):
  if not revision.strip(): raise ValueError('Revision is required')
  if submitted: date.fromisoformat(submitted)
  if status not in ['Draft','Submitted','Approved','Changes Required']: raise ValueError('Invalid approval status')
  doc=self.rows('SELECT * FROM documents WHERE id=?',(did,))
  if not doc: raise ValueError('Document not found')
  previous=self.rows('SELECT status FROM versions WHERE document_id=? ORDER BY id DESC LIMIT 1',(did,))
  flag=int(bool(previous and previous[0]['status'] in ('Approved','Submitted')))
  if file_path:
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
   cols=[f for f in fields if f not in ('archived','project_id','contact_id')]
   for row in self.rows(f'SELECT * FROM {table} WHERE '+ ' OR '.join(f'{c} LIKE ?' for c in cols),['%'+query+'%']*len(cols)):
    result.append({'type':table,'id':row['id'],'project_id':row.get('project_id',row['id'] if table=='projects' else ''),'label':row.get('name',row.get('title',row.get('summary','')))})
  for row in self.rows('SELECT v.*,d.project_id,d.title FROM versions v JOIN documents d ON d.id=v.document_id WHERE v.revision LIKE ? OR v.requirements LIKE ?',('%'+query+'%','%'+query+'%')):
   result.append({'type':'versions','id':row['id'],'project_id':row['project_id'],'label':row['title']+' / '+row['revision']+': '+row['requirements']})
  return result
 def outstanding(self,pid=None):
  return self.rows("SELECT t.*,p.name AS project,c.name AS responsible FROM tasks t JOIN projects p ON p.id=t.project_id LEFT JOIN contacts c ON c.id=t.contact_id WHERE t.status != 'Completed' AND p.archived=0"+(' AND t.project_id=?' if pid else '')+' ORDER BY deadline', (pid,) if pid else ())
 def backup(self,path):
  if Path(path).resolve()==self.path.resolve(): raise ValueError('Choose a different backup path')
  with sqlite3.connect(path) as dest: self.db.backup(dest)
 def restore(self,path):
  source=Path(path)
  if source.resolve()==self.path.resolve(): raise ValueError('Choose a different backup file')
  with sqlite3.connect(f'{source.resolve().as_uri()}?mode=ro',uri=True) as candidate:
   if candidate.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Invalid backup')
   if candidate.execute('PRAGMA user_version').fetchone()[0]!=1: raise ValueError('Unsupported backup version')
   for table in list(FIELDS)+['versions','activity','project_contacts']:
    expected={r[1] for r in self.db.execute(f'PRAGMA table_info({table})')}
    actual={r[1] for r in candidate.execute(f'PRAGMA table_info({table})')}
    if not expected.issubset(actual): raise ValueError('Backup schema mismatch')
   if candidate.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('Backup has broken relationships')
   self.backup(str(self.path)+'.before-restore.sqlite3')
   candidate.backup(self.db)
 def export(self,path,rows):
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
  return out
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
