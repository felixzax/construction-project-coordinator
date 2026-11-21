"""Permit jurisdictions, reference links and user-maintained requirement checklists."""
from datetime import date
from urllib.parse import urlsplit
import html

JURISDICTIONS=['City','County','City & County','State','Other']
PERMIT_COLUMNS={
 'jurisdiction_type':"TEXT DEFAULT 'City'",'jurisdiction_name':"TEXT DEFAULT ''",
 'department':"TEXT DEFAULT ''",'application_url':"TEXT DEFAULT ''",
 'requirements_url':"TEXT DEFAULT ''",'requirements_reviewed':'INTEGER DEFAULT 0',
}
REQUIREMENT_FIELDS=['register_id','title','source_url','completed','notes']
PERMIT_SCHEMA='''
CREATE TABLE IF NOT EXISTS permit_requirements(
 id INTEGER PRIMARY KEY, register_id INTEGER NOT NULL REFERENCES registers(id),
 title TEXT NOT NULL, source_url TEXT DEFAULT '', completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
 completed_on TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS requirements_permit ON permit_requirements(register_id);
'''

def validate_url(value):
 if not value: return ''
 if any(c.isspace() or ord(c)<32 or ord(c)==127 for c in value) or '\\' in value:
  raise ValueError('Links cannot contain spaces or control characters')
 try:
  parsed=urlsplit(value)
  hostname=parsed.hostname
  parsed.port
 except ValueError:
  raise ValueError('Enter a valid https:// or http:// web link') from None
 if parsed.scheme not in ('https','http') or not hostname or parsed.username or parsed.password:
  raise ValueError('Enter an https:// or http:// web link without embedded login details')
 return value

class PermitStore:
 def migrate_permits(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=3: return
  self.db.executescript('BEGIN IMMEDIATE;'+PERMIT_SCHEMA)
  with self.db:
   present={r[1] for r in self.db.execute('PRAGMA table_info(registers)')}
   for name,kind in PERMIT_COLUMNS.items():
    if name not in present: self.db.execute(f'ALTER TABLE registers ADD COLUMN {name} {kind}')
   self.db.execute('PRAGMA user_version=3')
 def validate_permit(self,table,data,row_id):
  if table=='registers':
   for key in ('application_url','requirements_url'): validate_url(data.get(key,''))
   if data.get('jurisdiction_type','City') not in JURISDICTIONS: raise ValueError('Choose a jurisdiction type')
   if data.get('requirements_reviewed',0) not in (0,1): raise ValueError('Reviewed must be checked or unchecked')
   if row_id and data.get('record_type')!='Permit':
    if self.rows('SELECT id FROM permit_requirements WHERE register_id=? LIMIT 1',(row_id,)):
     raise ValueError('A permit with a checklist cannot be changed into a different register type')
   if row_id:
    linked=self.rows('SELECT project_id FROM issues WHERE permit_id=?',(row_id,))
    if linked and data.get('record_type')!='Permit':raise ValueError('A permit linked to corrections or violations must remain a permit')
    if any(row['project_id']!=data.get('project_id') for row in linked):raise ValueError('Unlink related corrections or violations before moving the permit to another project')
    orders=self.rows('SELECT project_id FROM work_orders WHERE permit_id=?',(row_id,))
    if orders and (data.get('record_type')!='Permit' or any(r['project_id']!=data.get('project_id') for r in orders)):raise ValueError('Unlink related work orders before changing permit type or project')
  if table=='permit_requirements':
   parent=self.rows('SELECT project_id,record_type FROM registers WHERE id=?',(data.get('register_id'),))
   if not parent or parent[0]['record_type']!='Permit': raise ValueError('Requirements must belong to a permit')
   validate_url(data.get('source_url',''))
   completed=data.get('completed',0)
   if completed not in (0,1): raise ValueError('Completed must be checked or unchecked')
   if row_id:
    old=self.rows('SELECT register_id,completed,completed_on FROM permit_requirements WHERE id=?',(row_id,))[0]
    if old['register_id']!=data['register_id']: raise ValueError('Create a new checklist item to move it to another permit')
    data['completed_on']=(old['completed_on'] or date.today().isoformat()) if completed else ''
   else: data['completed_on']=date.today().isoformat() if completed else ''
 def permit_requirements(self,permit_id):
  return self.rows("SELECT r.* FROM permit_requirements r LEFT JOIN reg_requirement_details d ON d.requirement_id=r.id WHERE r.register_id=? AND COALESCE(d.hidden,0)=0 AND COALESCE(d.deleted,0)=0 AND COALESCE(json_extract(d.details_json,'$.context_active'),1)=1 ORDER BY r.id",(permit_id,))
 def set_requirement_completed(self,requirement_id,completed):
  if type(completed) not in (bool,int) or completed not in (0,1): raise ValueError('Use a checked or unchecked state')
  return self.save('permit_requirements',{'completed':int(completed)},requirement_id)
 def permit_progress(self,permit_id):
  items=self.permit_requirements(permit_id);row=dict(total=len(items),checked=sum(r['completed'] for r in items))
  return f'{row["checked"]}/{row["total"]} checked'
 def permit_checklist_report(self,pid):
  e=lambda v:html.escape(str(v if v is not None else ''))
  out='<h2>Permit application checklists</h2>'
  for permit in self.rows("SELECT * FROM registers WHERE project_id=? AND record_type='Permit'",(pid,)):
   out+=f'<h3>{e(permit["title"])}</h3><p>{e(permit["jurisdiction_type"])}: {e(permit["jurisdiction_name"])} — {e(permit["department"])}</p>'
   for label,key in [('Application','application_url'),('Application requirements','requirements_url')]:
    value=permit[key]
    # Invalid historic/imported values remain plain text, never executable links.
    try: validate_url(value)
    except ValueError: value=''
    if value: out+=f'<p>{label}: <a href="{e(value)}">{e(value)}</a></p>'
   out+=f'<p>Requirements page reviewed: {"Yes" if permit["requirements_reviewed"] else "No"}; {e(self.permit_progress(permit["id"]))}</p><ul>'
   for item in self.permit_requirements(permit['id']):
    out+='<li>'+('[x] ' if item['completed'] else '[ ] ')+e(item['title'])+' — '+e(item['notes'])+' '+e(item['source_url'])+((' — checked '+e(item['completed_on'])) if item['completed_on'] else '')+'</li>'
   out+='</ul>'
  return out
