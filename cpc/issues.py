"""Project corrections and violations requiring corrective work."""
from datetime import date
from pathlib import Path
import html
import shutil
import uuid
from .development import validate_date

ISSUE_TYPES=['Correction','Violation']
ISSUE_STATUSES=['Open','Assigned','In Progress','Ready for Review','Resolved','Closed','Cancelled']
CLOSED_ISSUE_STATUSES=('Resolved','Closed','Cancelled')
ISSUE_FIELDS=['project_id','title','issue_type','site_address','location','required_fix','description','reference','sheet_reference','code_reference','authority','permit_id','discipline','contact_id','priority','reported_by','reported_date','deadline','status','resolved_date','resolution_notes','attachment_path','attachment_name']
ISSUE_FORM_FIELDS=[field for field in ISSUE_FIELDS if field not in ('attachment_path','attachment_name')]
ISSUE_SCHEMA='''
CREATE TABLE IF NOT EXISTS issues(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,issue_type TEXT NOT NULL DEFAULT 'Correction',site_address TEXT DEFAULT '',location TEXT DEFAULT '',required_fix TEXT NOT NULL,description TEXT DEFAULT '',reference TEXT DEFAULT '',sheet_reference TEXT DEFAULT '',code_reference TEXT DEFAULT '',authority TEXT DEFAULT '',permit_id INTEGER REFERENCES registers(id),discipline TEXT DEFAULT 'General',contact_id INTEGER REFERENCES contacts(id),priority TEXT DEFAULT 'Normal',reported_by TEXT DEFAULT '',reported_date TEXT DEFAULT '',deadline TEXT DEFAULT '',status TEXT DEFAULT 'Open',resolved_date TEXT DEFAULT '',resolution_notes TEXT DEFAULT '',attachment_path TEXT DEFAULT '',attachment_name TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS issues_project ON issues(project_id);
CREATE INDEX IF NOT EXISTS issues_status ON issues(status);
'''

class IssueStore:
 def migrate_issues(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=6: return
  self.db.executescript('BEGIN IMMEDIATE;'+ISSUE_SCHEMA+'PRAGMA user_version=6;COMMIT;')
 def validate_issue(self,table,data,row_id):
  if table!='issues': return
  if data.get('issue_type','Correction') not in ISSUE_TYPES: raise ValueError('Choose Correction or Violation')
  if data.get('status','Open') not in ISSUE_STATUSES: raise ValueError('Choose an issue status')
  if data.get('priority','Normal') not in ('Low','Normal','High','Urgent'): raise ValueError('Choose an issue priority')
  if not str(data.get('required_fix','')).strip(): raise ValueError('Describe the required fix')
  project=self.rows('SELECT address FROM projects WHERE id=?',(data.get('project_id'),))
  if not project: raise ValueError('Choose an existing project')
  if not str(data.get('site_address','') or '').strip(): data['site_address']=project[0]['address']
  if data.get('permit_id'):
   permits=self.rows("SELECT project_id FROM registers WHERE id=? AND record_type='Permit'",(data['permit_id'],))
   if not permits or permits[0]['project_id']!=data['project_id']: raise ValueError('The linked permit must belong to the same project')
  for key in ('reported_date','resolved_date'):
   if data.get(key): validate_date(data[key])
  if not data.get('reported_date'): data['reported_date']=date.today().isoformat()
  if data.get('status','Open') in ('Resolved','Closed'):
   data['resolved_date']=data.get('resolved_date') or date.today().isoformat()
   if data['resolved_date']<data['reported_date']: raise ValueError('Resolution date cannot precede reported date')
  else: data['resolved_date']=''
 def issue_rows(self,kind=None,pid=None):
  clauses=[];args=[]
  if kind:clauses.append('i.issue_type=?');args.append(kind)
  if pid:clauses.append('i.project_id=?');args.append(pid)
  sql='SELECT i.*,p.name AS project,p.address AS project_address,c.name AS responsible,r.reference AS permit_reference FROM issues i JOIN projects p ON p.id=i.project_id LEFT JOIN contacts c ON c.id=i.contact_id LEFT JOIN registers r ON r.id=i.permit_id'
  if clauses:sql+=' WHERE '+' AND '.join(clauses)
  return self.rows(sql+' ORDER BY i.id DESC',args)
 def attach_issue(self,issue_id,path):
  from .privacy import check_attachment
  check_attachment(path)
  if not self.rows('SELECT id FROM issues WHERE id=?',(issue_id,)): raise ValueError('Correction or violation not found')
  source=Path(path)
  if not source.is_file():raise ValueError('Evidence file does not exist')
  folder=self.path.parent/'documents';folder.mkdir(exist_ok=True);target=folder/(uuid.uuid4().hex+source.suffix)
  shutil.copy2(source,target)
  try:self.save('issues',dict(attachment_path=str(target.resolve()),attachment_name=source.name),issue_id)
  except Exception:target.unlink(missing_ok=True);raise
  return target
 def issue_report(self,pid):
  e=lambda value:html.escape(str(value if value is not None else ''))
  out='<h2>Corrections and violations to address</h2>'
  for row in self.issue_rows(pid=pid):
   out+=f'<h3>{e(row["issue_type"])}: {e(row["title"])}</h3>'
   for key in ('site_address','location','required_fix','status','priority','deadline','responsible','authority','reference','sheet_reference','code_reference','resolved_date','resolution_notes'):
    out+=f'<p>{e(key.replace("_"," ").title())}: {e(row[key])}</p>'
  return out
