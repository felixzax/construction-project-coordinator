"""Project scope, customizable specifications, incentives and project navigation."""
import html
from .development import validate_date,number,money,DISCIPLINES

USES=['Undecided','Residential','Commercial','Mixed Use','Industrial','Institutional','Other']
ANSWERS=['Undecided','Yes','No','Not Applicable']
CATEGORIES=['Rooms & Amenities','Structure & Envelope','Vertical Access','Energy & Utilities','Site & Safety','Accessibility','Inspections & Closeout','Custom']
ENERGY=['Undecided','Electric','Natural Gas','Hybrid (electric / gas)','Solar','Propane','Oil','District Energy','Other','Not Applicable']
SCOPE_STATUS=['Not Started','Waiting on Someone','In Progress','Submitted','Approved','Completed','Not Applicable']
PROFILE_FIELDS=['project_id','title','use_type','project_type','occupancy','parcel_number','jurisdiction','zoning','construction_type','residential_units','stories','floor_area','area_unit','kitchen','bathroom','occupied_work','accessibility','fire_sprinklers','notes']
PROFILE_COLUMNS={'kitchen','bathroom','occupied_work','accessibility','fire_sprinklers'}
SCOPE_FIELDS={
 'project_profiles':PROFILE_FIELDS,
 'scope_items':['project_id','title','category','discipline','applicability','system_type','energy_source','status','building_area','manufacturer','model','quantity','unit','specifications','requirements','contact_id','deadline','hidden','notes'],
 'custom_fields':['project_id','scope_item_id','title','field_type','value','unit','is_required','notes'],
 'rebates':['project_id','title','provider','program_type','scope_item_id','eligibility','status','requirements_url','application_url','reference','contact_id','deadline','submitted','currency','estimated_amount','approved_amount','received_amount','requirements','notes'],
}
SCOPE_SCHEMA='''
CREATE TABLE project_profiles(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL UNIQUE REFERENCES projects(id),title TEXT NOT NULL DEFAULT 'Project profile',use_type TEXT DEFAULT 'Undecided',project_type TEXT DEFAULT 'Undecided',occupancy TEXT DEFAULT '',parcel_number TEXT DEFAULT '',jurisdiction TEXT DEFAULT '',zoning TEXT DEFAULT '',construction_type TEXT DEFAULT '',residential_units TEXT DEFAULT '',stories TEXT DEFAULT '',floor_area TEXT DEFAULT '',area_unit TEXT DEFAULT 'sq ft',kitchen TEXT DEFAULT 'Undecided',bathroom TEXT DEFAULT 'Undecided',occupied_work TEXT DEFAULT 'Undecided',accessibility TEXT DEFAULT 'Undecided',fire_sprinklers TEXT DEFAULT 'Undecided',notes TEXT DEFAULT '');
CREATE TABLE scope_items(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,category TEXT DEFAULT 'Custom',discipline TEXT DEFAULT 'General',applicability TEXT DEFAULT 'Undecided',system_type TEXT DEFAULT '',energy_source TEXT DEFAULT 'Undecided',status TEXT DEFAULT 'Not Started',building_area TEXT DEFAULT '',manufacturer TEXT DEFAULT '',model TEXT DEFAULT '',quantity TEXT DEFAULT '',unit TEXT DEFAULT '',specifications TEXT DEFAULT '',requirements TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),deadline TEXT DEFAULT '',hidden INTEGER DEFAULT 0,notes TEXT DEFAULT '');
CREATE TABLE custom_fields(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),scope_item_id INTEGER REFERENCES scope_items(id),title TEXT NOT NULL,field_type TEXT DEFAULT 'Text',value TEXT DEFAULT '',unit TEXT DEFAULT '',is_required INTEGER DEFAULT 0,notes TEXT DEFAULT '');
CREATE TABLE rebates(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,provider TEXT DEFAULT '',program_type TEXT DEFAULT 'Rebate',scope_item_id INTEGER REFERENCES scope_items(id),eligibility TEXT DEFAULT 'Undecided',status TEXT DEFAULT 'Researching',requirements_url TEXT DEFAULT '',application_url TEXT DEFAULT '',reference TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),deadline TEXT DEFAULT '',submitted TEXT DEFAULT '',currency TEXT DEFAULT 'USD',estimated_amount TEXT DEFAULT '',approved_amount TEXT DEFAULT '',received_amount TEXT DEFAULT '',requirements TEXT DEFAULT '',notes TEXT DEFAULT '');
CREATE TABLE project_sections(project_id INTEGER NOT NULL REFERENCES projects(id),section TEXT NOT NULL,hidden INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(project_id,section));
CREATE INDEX scope_project ON scope_items(project_id);
CREATE INDEX rebate_project ON rebates(project_id);
ALTER TABLE finance_files RENAME TO finance_files_v7;
CREATE TABLE finance_files(id INTEGER PRIMARY KEY,contract_id INTEGER REFERENCES contracts(id),budget_id INTEGER REFERENCES budgets(id),owner_table TEXT DEFAULT '',owner_id INTEGER,original_name TEXT NOT NULL,file_path TEXT NOT NULL,sha256 TEXT NOT NULL,byte_size INTEGER NOT NULL,added_date TEXT NOT NULL,notes TEXT DEFAULT '',CHECK((contract_id IS NOT NULL)+(budget_id IS NOT NULL)+(owner_table!='' AND owner_id IS NOT NULL)=1));
INSERT INTO finance_files(id,contract_id,budget_id,original_name,file_path,sha256,byte_size,added_date,notes) SELECT id,contract_id,budget_id,original_name,file_path,sha256,byte_size,added_date,notes FROM finance_files_v7;
DROP TABLE finance_files_v7;
'''
# Explicit starter prompts; these are coordination prompts, never jurisdictional code determinations.
STARTERS=[
 ('Kitchen / cooking','Rooms & Amenities','Architecture','Kitchen'),('Bathrooms / fixtures','Rooms & Amenities','Plumbing','Bathroom'),
 ('Foundation / framing','Structure & Envelope','Structural Engineering','Framing'),('Roof / floor trusses','Structure & Envelope','Structural Engineering','Trusses'),('Roofing / waterproofing','Structure & Envelope','Roofing','Roofing'),('Insulation / air sealing','Structure & Envelope','Architecture','Insulation'),('Windows / exterior doors','Structure & Envelope','Architecture','Windows'),
 ('Stairs, guards & handrails','Vertical Access','Structural Engineering','Stairs'),('Elevator / platform lift','Vertical Access','Architecture','Elevator / Lift'),
 ('Heating / cooling / ventilation','Energy & Utilities','Mechanical / HVAC','HVAC'),('Water heating','Energy & Utilities','Plumbing','Water Heater'),('Electrical service / panel','Energy & Utilities','Electrical','Electrical Service'),('Gas service / fuel piping','Energy & Utilities','Utilities','Gas Service'),('Solar generation','Energy & Utilities','Electrical','Solar'),('Battery storage','Energy & Utilities','Electrical','Battery'),('EV charging','Energy & Utilities','Electrical','EV Charger'),('Water / sewer / septic','Energy & Utilities','Plumbing','Plumbing'),
 ('Drainage / stormwater','Site & Safety','Civil Engineering','Stormwater'),('Fire alarm / sprinklers','Site & Safety','Fire Protection','Fire Protection'),('Site access / parking','Site & Safety','Site Work','Site Access'),
 ('Accessible routes / entrances','Accessibility','Architecture','Accessibility'),('Accessible fixtures / facilities','Accessibility','Architecture','Accessibility'),
 ('Required inspections / tests','Inspections & Closeout','General','Inspections'),('Commissioning / energy verification','Inspections & Closeout','Mechanical / HVAC','Commissioning'),('Occupancy / final sign-off','Inspections & Closeout','General','Occupancy'),('Warranties / manuals / training','Inspections & Closeout','General','Closeout'),
]
SYSTEM_TYPES=list(dict.fromkeys([r[3] for r in STARTERS]+['Other']))
PROTECTED_SECTIONS={'Dashboard','Projects','Search','Backup & Restore','Recovery & Data'}

class ScopeStore:
 def migrate_scope(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=8:return
  self.db.executescript('BEGIN IMMEDIATE;'+SCOPE_SCHEMA+'PRAGMA user_version=8;COMMIT;')
 def validate_scope(self,table,data,row_id):
  if table in SCOPE_FIELDS:
   if not self.rows('SELECT id FROM projects WHERE id=?',(data.get('project_id'),)):raise ValueError('Choose an existing project')
   if row_id:
    old=self.rows(f'SELECT project_id FROM {table} WHERE id=?',(row_id,))[0]
    if old['project_id']!=data['project_id']:raise ValueError('Create a new record to move it to a different project')
  if table=='project_profiles':
   data.setdefault('title','Project profile')
   if data.get('use_type','Undecided') not in USES:raise ValueError('Choose residential, commercial or another listed use')
   for key in PROFILE_COLUMNS:
    if data.get(key,'Undecided') not in ANSWERS:raise ValueError('Choose Yes, No, Undecided or Not Applicable')
   for key in ('stories','floor_area','residential_units'):
    if data.get(key):
     value=number(data[key],key)
     if key in ('stories','residential_units') and value!=int(value):raise ValueError('Stories and residential units must be whole numbers')
   if self.rows('SELECT id FROM project_profiles WHERE project_id=? AND id!=?',(data['project_id'],row_id or -1)):raise ValueError('This project already has a profile; edit it instead')
  if table=='scope_items':
   if data.get('applicability','Undecided') not in ANSWERS:raise ValueError('Choose applicability')
   if data.get('energy_source','Undecided') not in ENERGY:raise ValueError('Choose a supported energy source; describe other sources in specifications')
   if data.get('status','Not Started') not in SCOPE_STATUS:raise ValueError('Choose a scope status')
   if data.get('quantity'):number(data['quantity'],'Quantity')
   if data.get('hidden',0) not in (0,1):raise ValueError('Hidden must be checked or unchecked')
  if table in ('custom_fields','rebates') and data.get('scope_item_id'):
   parent=self.rows('SELECT project_id FROM scope_items WHERE id=?',(data['scope_item_id'],))
   if not parent or parent[0]['project_id']!=data['project_id']:raise ValueError('The system/specification must belong to this project')
  if table=='custom_fields':
   kind=data.get('field_type','Text');value=str(data.get('value','') or '').strip();data['value']=value
   if kind not in ('Text','Number','Yes / No','Date','URL'):raise ValueError('Choose a custom-field type')
   if data.get('is_required',0) not in (0,1):raise ValueError('Required must be checked or unchecked')
   if value:
    if kind=='Number':
     from decimal import Decimal,InvalidOperation
     try:valid=Decimal(value).is_finite()
     except InvalidOperation:valid=False
     if not valid:raise ValueError('Custom numeric value must be a finite number')
    if kind=='Yes / No' and value not in ANSWERS:raise ValueError('Use Yes, No, Undecided or Not Applicable')
    if kind=='Date':validate_date(value)
    if kind=='URL':self.scope_url(value)
  if table=='rebates':
   from .finance import CURRENCIES
   if data.get('eligibility','Undecided') not in ANSWERS:raise ValueError('Choose an eligibility state')
   if data.get('status','Researching') not in ('Researching','Preparing','Submitted','Approved','Received','Rejected','Closed'):raise ValueError('Choose an application status')
   if data.get('currency','USD') not in CURRENCIES:raise ValueError('Choose a supported currency')
   for key in ('estimated_amount','approved_amount','received_amount'):
    data[key]=str(money(number(data[key],key))) if data.get(key) not in ('',None) else ''
   for key in ('submitted','deadline'):
    if data.get(key):validate_date(data[key])
   for key in ('requirements_url','application_url'):
    if data.get(key):self.scope_url(data[key])
 def scope_url(self,value):
  from urllib.parse import urlsplit
  url=urlsplit(value)
  if url.scheme not in ('http','https') or not url.netloc or url.username or url.password:raise ValueError('Use an http(s) website link without credentials')
 def profile(self,pid):
  rows=self.rows('SELECT * FROM project_profiles WHERE project_id=?',(pid,));return rows[0] if rows else None
 def add_scope_starters(self,pid):
  if not self.rows('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Choose an existing project')
  existing={r['title'].casefold() for r in self.rows('SELECT title FROM scope_items WHERE project_id=?',(pid,))};count=0
  with self.db:
   for title,category,discipline,kind in STARTERS:
    if title.casefold() not in existing:
     self.db.execute('INSERT INTO scope_items(project_id,title,category,discipline,system_type) VALUES(?,?,?,?,?)',(pid,title,category,discipline,kind));count+=1
   if count:self.log(pid,f'Added {count} optional scope prompts; review applicability and local requirements')
  return count
 def scope_rows(self,table):
  rows=self.all(table);projects={p['id']:p['name'] for p in self.all('projects')};systems={s['id']:s['title'] for s in self.all('scope_items')};people={c['id']:c['name'] for c in self.all('contacts')}
  for row in rows:
   row['project']=projects.get(row['project_id'],'');row['responsible']=people.get(row.get('contact_id'),'')
   if 'scope_item_id' in row:row['system']=systems.get(row['scope_item_id'],'Project-wide')
   if table=='custom_fields':row['completion']='Missing required value' if row['is_required'] and row['value'] in ('','Undecided') else 'Recorded' if row['value'] else 'Optional / blank'
  return rows
 def change_rows(self):
  return self.rows('SELECT x.*,c.project_id,c.title AS contract,c.currency,p.name AS project FROM contract_changes x JOIN contracts c ON c.id=x.contract_id JOIN projects p ON p.id=c.project_id ORDER BY x.id DESC')
 def hidden_sections(self,pid):return {r['section'] for r in self.rows('SELECT section FROM project_sections WHERE project_id=? AND hidden=1',(pid,))} if pid else set()
 def set_hidden_sections(self,pid,sections):
  from .development_ui import NAVIGATION
  if not self.rows('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Select a project first')
  sections=set(sections)
  if sections-set(NAVIGATION) or sections & PROTECTED_SECTIONS:raise ValueError('Essential navigation cannot be hidden')
  with self.db:
   self.db.execute('DELETE FROM project_sections WHERE project_id=?',(pid,))
   self.db.executemany('INSERT INTO project_sections(project_id,section,hidden) VALUES(?,?,1)',[(pid,s) for s in sorted(sections)]);self.log(pid,'Project navigation preferences saved; hidden sections retain all data')
 def scope_report(self,pid):
  e=lambda v:html.escape(str(v if v is not None else ''));out='<h2>Project profile, scope and incentives</h2>'
  for table,label in [('project_profiles','Profile'),('scope_items','Systems & requirements'),('custom_fields','Custom information'),('rebates','Rebates & incentives')]:
   out+='<h3>'+label+'</h3>'
   for row in self.scope_rows(table):
    if row['project_id']==pid:out+='<p>'+' | '.join(e(k)+': '+e(v) for k,v in row.items() if k!='id' and not k.endswith('_id') and v not in ('',None))+'</p>'
  return out
