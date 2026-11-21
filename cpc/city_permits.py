"""Phase 3 manual City/County coordination using the existing schema 12 only."""
import json
import re
from decimal import Decimal,InvalidOperation
from pathlib import Path
from .privacy import check_values
from .development import validate_date
from .regulatory import JURISDICTIONS

CITY,COUNTY,OTHER=JURISDICTIONS
USES=['Residential','Commercial']
WORK_TYPES=['New Construction','Addition','Remodel / TI','Kitchen / Bath','ADU','Garage Conversion','Patio Cover','Fence / Block Wall','Manufactured Home','Solar','EV Charging','Pool','Master Plan','Revision','Deferred','Other']
FAMILIES=['Building','Fire Development Services','Operational Permit Inspections','Fire Code Enforcement','Engineering','Planning','Fire (verify district)']
STEP_STATUS=['Not Started','In Progress','Waiting on Agency','Changes Required','Submitted','Approved','Done','Not Applicable']
DISCIPLINES=['Building','Life-Safety','Plumbing','Mechanical','Electrical','Fire','Planning','Development Engineering','Utilities','Landscape','Air Quality','Construction Debris']
CONTEXT_FIELDS=('jurisdiction_key','occupancy_type','work_type','permit_family')

def catalog():return json.loads(Path(__file__).with_name('permit_catalog.json').read_text(encoding='utf-8'))
def metadata(row):return json.loads(row.get('details_json') or '{}')
def context_key(values):return '|'.join(values[k] for k in CONTEXT_FIELDS)
def applicable_items(values):
 return [i for i in catalog()['items'] if i['jurisdiction']==values['jurisdiction_key'] and (not i['uses'] or values['occupancy_type'] in i['uses']) and (not i['works'] or values['work_type'] in i['works']) and values['permit_family'] in i['families']]

class CityPermitStore:
 def _city_put(self,table,values,row_id=None):
  """Validated raw write inside the caller's single transaction (no nested commit)."""
  from .store import FIELDS
  check_values(values);data={k:v for k,v in values.items() if k in FIELDS[table]}
  if row_id:
   prior=self.rows(f'SELECT * FROM {table} WHERE id=?',(row_id,))
   if not prior:raise ValueError('Record not found')
   data={**{k:v for k,v in prior[0].items() if k in FIELDS[table]},**data}
  self.validate_development(table,data,row_id);self.validate_permit(table,data,row_id);self.validate_regulatory(table,data,row_id)
  self.validate_city(table,data,row_id,context_change=True)
  self.validate_water(table,data,row_id)
  for k in ('title',)+{'reg_tracker_steps':('step_key',),'reg_templates':('template_key',),'reg_template_items':('item_key',)}.get(table,()):
   if k in FIELDS[table] and not str(data.get(k,'')).strip():raise ValueError(k.replace('_',' ').title()+' is required')
  if row_id:self.db.execute(f'UPDATE {table} SET '+','.join(k+'=?' for k in data)+' WHERE id=?',[*data.values(),row_id]);return row_id
  return self.db.execute(f'INSERT INTO {table} ('+','.join(data)+') VALUES ('+','.join('?' for _ in data)+')',list(data.values())).lastrowid
 def city_details(self,register_id):
  rows=self.rows('SELECT * FROM reg_permit_details WHERE register_id=?',(register_id,))
  if not rows:raise ValueError('Set up this permit in City & County first')
  return rows[0]
 def validate_city(self,table,data,row_id=None,context_change=False):
  fixed={'reg_review_cycles':'register_id','reg_cycle_reviews':'cycle_id','reg_tracker_steps':'register_id'}
  if row_id and table in fixed:
   old=self.rows(f'SELECT * FROM {table} WHERE id=?',(row_id,))[0];key=fixed[table]
   if old[key]!=data.get(key):raise ValueError('Parent link is fixed; create a new tracking record')
  if table=='reg_permit_details':
   for k,opts in [('jurisdiction_key',JURISDICTIONS),('occupancy_type',USES),('work_type',WORK_TYPES),('permit_family',FAMILIES)]:
    if data.get(k) not in opts:raise ValueError('Choose a valid '+k.replace('_',' '))
   if row_id and not context_change:
    old=self.rows('SELECT * FROM reg_permit_details WHERE id=?',(row_id,))[0]
    if any(data[k]!=old[k] for k in CONTEXT_FIELDS):raise ValueError('Use the confirmed jurisdiction/template swap workflow')
   if int(data.get('cycle_no',1))<1:raise ValueError('Cycle number must be positive')
   self.validate_city_limits(metadata(data).get('file_limits_mb',{}))
  if table=='reg_review_cycles':
   context=metadata(data);context.setdefault('jurisdiction_key',self.city_details(data['register_id'])['jurisdiction_key']);data['details_json']=json.dumps(context)
   try:n=int(data.get('cycle_no',1))
   except (TypeError,ValueError):raise ValueError('Cycle must be a positive whole number') from None
   if n<1 or str(n)!=str(data.get('cycle_no',1)):raise ValueError('Cycle must be a positive whole number')
  if table=='reg_city_records':
   details=self.city_details(data['permit_register_id'])
   if details['jurisdiction_key']!=CITY:raise ValueError('PLN/SUB/COM/RES/FPP/MP records belong only to City of Sacramento permits')
   if data.get('record_kind') not in ('PLN','SUB','COM','RES','FPP','MP'):raise ValueError('Choose a City record type')
   if data.get('parent_sub_id'):
    parent=self.rows('SELECT * FROM reg_city_records WHERE id=?',(data['parent_sub_id'],))[0]
    if parent['record_kind']!='SUB' or parent['permit_register_id']!=data['permit_register_id'] or data['record_kind'] not in ('COM','RES','FPP','MP'):raise ValueError('Link a permit record to a SUB for this same permit')
   if row_id and data.get('record_kind')!='SUB' and self.rows('SELECT id FROM reg_city_records WHERE parent_sub_id=?',(row_id,)):raise ValueError('A linked SUB must remain a SUB')
  if table=='reg_tracker_steps' and data.get('register_id'):
   parent=self.rows('SELECT record_type FROM registers WHERE id=?',(data['register_id'],))
   if not parent or parent[0]['record_type']!='Permit':raise ValueError('Tracker must link to a permit')
  if table=='registers' and row_id:
   extension=self.rows('SELECT * FROM reg_permit_details WHERE register_id=?',(row_id,))
   if extension:
    expected={'City':CITY,'County':COUNTY,'Other':OTHER}.get(data.get('jurisdiction_type'))
    if expected!=extension[0]['jurisdiction_key'] or (expected!=OTHER and data.get('jurisdiction_name')!=expected):raise ValueError('Change this jurisdiction in City & County with confirmation')
 def validate_city_limits(self,limits):
  if not isinstance(limits,dict):raise ValueError('Invalid file-size limit settings')
  for key,value in limits.items():
   if key not in ('APP','PLANS','SUPP','REPLY'):raise ValueError('Unknown file category')
   if value in ('',None):continue
   try:n=Decimal(str(value))
   except InvalidOperation:raise ValueError('File limits must be positive decimal MB values') from None
   if not n.is_finite() or n<=0:raise ValueError('File limits must be positive decimal MB values')
 def configure_city_permit(self,values,register_id=None,confirmed=False):
  """Create/opt in/update. No catalog data is seeded by merely opening the app."""
  values=dict(values);check_values(values)
  title=str(values.get('title','')).strip()
  if not title:raise ValueError('Permit title is required')
  previous=self.rows('SELECT * FROM reg_permit_details WHERE register_id=?',(register_id,)) if register_id else []
  old=previous[0] if previous else None
  data={**(old or {}),**{k:v for k,v in values.items() if k not in ('id','register_id')}}
  config=metadata(old or {})
  for key in ('seal_contact_id','seal_discipline','seal_notes'):
   if key in values:config[key]=values[key]
  if config.get('seal_contact_id'):
   contact=self.rows('SELECT name FROM contacts WHERE id=?',(config['seal_contact_id'],))
   if not contact:raise ValueError('Select an existing person responsible for seal')
   config['seal_person_name']=contact[0]['name']
  elif 'seal_contact_id' in values:config['seal_person_name']=''
  data['details_json']=json.dumps(config)
  data.setdefault('jurisdiction_key',OTHER);data.setdefault('occupancy_type','Residential');data.setdefault('work_type','Other');data.setdefault('permit_family','Building')
  changed=bool(old and any(data[k]!=old[k] for k in CONTEXT_FIELDS))
  if changed and not confirmed:raise ValueError('Confirm jurisdiction/template swap before saving')
  parent=self.rows('SELECT * FROM registers WHERE id=?',(register_id,))[0] if register_id else None
  pid=parent['project_id'] if parent else values.get('project_id')
  if not self.rows('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Select an existing project')
  if parent and parent['record_type']!='Permit':raise ValueError('Select an existing Permit')
  # Validate all new configuration before modifying any original rows.
  self.validate_city('reg_permit_details',data,old['id'] if old else None,True)
  with self.db:
   if changed:
    # Preserve edits, checks, files and original IDs. Inactive generated rows are
    # excluded by both the new list and the canonical checklist reader.
    for row in self.rows("SELECT d.* FROM reg_requirement_details d JOIN permit_requirements r ON r.id=d.requirement_id WHERE r.register_id=? AND d.origin='Template'",(register_id,)):
     details=metadata(row);details['context_active']=False
     self.db.execute('UPDATE reg_requirement_details SET details_json=? WHERE id=?',(json.dumps(details),row['id']))
    for step in self.rows('SELECT * FROM reg_tracker_steps WHERE register_id=? AND template_item_id IS NOT NULL',(register_id,)):
     meta=metadata(step);meta['context_active']=False;self.db.execute('UPDATE reg_tracker_steps SET hidden=1,details_json=? WHERE id=?',(json.dumps(meta),step['id']))
    data['current_template_id']=None
   # Internal confirmed workflow may synchronize the legacy jurisdiction fields.
   kind={CITY:'City',COUNTY:'County',OTHER:'Other'}[data['jurisdiction_key']]
   if parent:
    if changed or not old:
     self.db.execute('UPDATE registers SET title=?,jurisdiction_type=?,jurisdiction_name=? WHERE id=?',(title,kind,data['jurisdiction_key'],register_id))
    else:
     self.db.execute('UPDATE registers SET title=? WHERE id=?',(title,register_id))
   else:
    register_id=self._city_put('registers',dict(project_id=pid,title=title,record_type='Permit',jurisdiction_type=kind,jurisdiction_name=data['jurisdiction_key'],status='Open'))
   data['register_id']=register_id
   self._city_put('reg_permit_details',data,old['id'] if old else None)
   if changed:self._add_city_standard(register_id)
   self.log(pid,f'City/County permit #{register_id} configured'+(' — confirmed template swap; user items retained' if changed else ''))
  return register_id
 def _catalog_template(self,details):
  key=context_key(details)
  prior=self.rows('SELECT * FROM reg_templates WHERE template_key=?',(key,))
  if prior:return prior[0]['id']
  return self._city_put('reg_templates',dict(template_key=key,jurisdiction_key=details['jurisdiction_key'],occupancy_type=details['occupancy_type'],work_type=details['work_type'],permit_family=details['permit_family'],title=' / '.join(details[k] for k in CONTEXT_FIELDS),builtin=1,details_json=json.dumps({'catalog_verified':catalog()['verified_date']})))
 def _catalog_source(self,key):
  source=catalog()['sources'][key]
  prior=self.rows("SELECT id FROM reg_sources WHERE source_kind=? AND url=?",(source['source_kind'],source['url']))
  if prior:return prior[0]['id']
  source=dict(source,notes=source['notes']+' Source SHA-256: '+source['sha256'])
  return self._city_put('reg_sources',source)
 def _add_city_standard(self,register_id):
  details=self.city_details(register_id);parent=self.rows('SELECT * FROM registers WHERE id=?',(register_id,))[0];pid=parent['project_id'];template=self._catalog_template(details);count=0
  for pos,item in enumerate(applicable_items(details)):
   source=self._catalog_source(item['source']);existing=self.rows('SELECT * FROM reg_template_items WHERE template_id=? AND item_key=?',(template,item['key']))
   tid=existing[0]['id'] if existing else self._city_put('reg_template_items',dict(template_id=template,item_key=item['key'],title=item['title'],check_kind=item['check_kind'],source_id=source,last_verified_date=item['last_verified_date'],if_applicable=item['if_applicable'],verify_label=item['verify_label'],sort_order=pos,details_json=json.dumps(item)))
   if self.rows('SELECT id FROM reg_template_tombstones WHERE project_id=? AND register_id=? AND template_item_key=?',(pid,register_id,item['key'])):continue
   if item['check_kind']=='Checklist':
    old=self.rows('SELECT d.* FROM reg_requirement_details d JOIN permit_requirements r ON r.id=d.requirement_id WHERE r.register_id=? AND d.template_key=?',(register_id,item['key']))
    if old:
     meta=metadata(old[0]);meta['context_active']=True;self.db.execute('UPDATE reg_requirement_details SET details_json=? WHERE id=?',(json.dumps(meta),old[0]['id']));continue
    req=self._city_put('permit_requirements',dict(register_id=register_id,title=item['title'],source_url=item['url'],completed=0,notes=item['notes']))
    self._city_put('reg_requirement_details',dict(requirement_id=req,template_item_id=tid,template_key=item['key'],origin='Template',jurisdiction_key=details['jurisdiction_key'],source_id=source,last_verified_date=item['last_verified_date'],if_applicable=item['if_applicable'],verify_label=item['verify_label'],details_json=json.dumps({'context_active':True,'locator':item['locator']})))
   elif item['check_kind']=='Tracker':
    old=self.rows('SELECT * FROM reg_tracker_steps WHERE register_id=? AND step_key=?',(register_id,item['key']))
    if old:
     # A user-hidden step remains hidden on repeated Add; context changes restore
     # its saved visibility using its metadata, not its current inactive flag.
     if not metadata(old[0]).get('context_active',True) or metadata(old[0]).get('context_key')!=context_key(details):
      meta=metadata(old[0]);meta['context_key']=context_key(details);meta['context_active']=True
      self.db.execute('UPDATE reg_tracker_steps SET hidden=?,details_json=? WHERE id=?',(int(meta.get('user_hidden',False)),json.dumps(meta),old[0]['id']))
     continue
    self._city_put('reg_tracker_steps',dict(project_id=pid,register_id=register_id,template_item_id=tid,step_key=item['key'],title=item['title'],source_id=source,last_verified_date=item['last_verified_date'],if_applicable=item['if_applicable'],verify_label=item['verify_label'],sort_order=pos,details_json=json.dumps({'context_key':context_key(details),'user_hidden':False,'context_active':True,'locator':item['locator']})))
   else:
    # Charges are manual suggestions. Stable key in metadata prevents duplication.
    config=metadata(self.city_details(register_id));charges=config.setdefault('generated_charges',{});existing_id=charges.get(item['key'])
    if existing_id and self.rows('SELECT id FROM reg_manual_charges WHERE id=?',(existing_id,)):continue
    charge_id=self._city_put('reg_manual_charges',dict(project_id=pid,register_id=register_id,title=item['title'],source_id=source,last_verified_date=item['last_verified_date'],if_applicable=1,verify_label=item['verify_label'],notes=item['notes']))
    charges[item['key']]=charge_id;self.db.execute('UPDATE reg_permit_details SET details_json=? WHERE register_id=?',(json.dumps(config),register_id))
   count+=1
  self.db.execute('UPDATE reg_permit_details SET current_template_id=? WHERE register_id=?',(template,register_id));return count
 def add_city_standard(self,register_id):
  with self.db:
   count=self._add_city_standard(register_id);self.log(self.rows('SELECT project_id FROM registers WHERE id=?',(register_id,))[0]['project_id'],f'Added {count} missing City/County coordination items')
  return count
 def city_checklist(self,register_id,include_hidden=False):
  details=self.city_details(register_id)
  rows=self.rows('SELECT r.*,d.id AS detail_id,d.template_key,d.origin,d.jurisdiction_key,d.hidden,d.deleted,d.source_id,d.last_verified_date,d.if_applicable,d.verify_label,d.details_json,s.title AS source_document,s.document_revision_date,s.url AS reference_url FROM permit_requirements r LEFT JOIN reg_requirement_details d ON d.requirement_id=r.id LEFT JOIN reg_sources s ON s.id=d.source_id WHERE r.register_id=? ORDER BY r.id',(register_id,))
  return [r for r in rows if not r['deleted'] and (r['origin']!='Template' or (r['jurisdiction_key']==details['jurisdiction_key'] and metadata(r).get('context_active',True))) and (include_hidden or not r['hidden'])]
 def city_steps(self,register_id,include_hidden=False):
  details=self.city_details(register_id)
  rows=self.rows('SELECT r.*,s.title AS source_document,s.document_revision_date,s.url AS source_url FROM reg_tracker_steps r LEFT JOIN reg_sources s ON s.id=r.source_id WHERE register_id=? ORDER BY sort_order,r.id',(register_id,))
  return [r for r in rows if not r['deleted'] and (not r['template_item_id'] or metadata(r).get('context_key')==context_key(details) and metadata(r).get('context_active',True)) and (include_hidden or not r['hidden'])]
 def set_city_item_hidden(self,kind,row_id,hidden):
  with self.db:
   if kind=='checklist':
    row=self.rows('SELECT * FROM permit_requirements WHERE id=?',(row_id,))[0];details=self.rows('SELECT * FROM reg_requirement_details WHERE requirement_id=?',(row_id,))
    if details:self._city_put('reg_requirement_details',dict(hidden=int(hidden)),details[0]['id'])
    else:self._city_put('reg_requirement_details',dict(requirement_id=row_id,origin='User',jurisdiction_key=self.city_details(row['register_id'])['jurisdiction_key'],hidden=int(hidden)))
   else:
    row=self.rows('SELECT * FROM reg_tracker_steps WHERE id=?',(row_id,))[0];meta=metadata(row);meta['user_hidden']=bool(hidden);self._city_put('reg_tracker_steps',dict(hidden=int(hidden),details_json=json.dumps(meta)),row_id)
 def delete_city_item(self,kind,row_id):
  """The shared deletion transaction records stable-key tombstones and a backup."""
  if kind not in ('checklist','tracker'):raise ValueError('Choose checklist or tracker')
  return self.delete_records([('permit_requirements' if kind=='checklist' else 'reg_tracker_steps',row_id)])
 def city_file_warnings(self,register_id,path,cycle_no=1,naming_basis='Address',prefix='',upload_record_kind='SUB'):
  details=self.city_details(register_id)
  if details['jurisdiction_key']!=CITY or details['permit_family']!='Building':return ['Verify file requirements with this jurisdiction; City EPC checks are not applied.']
  path=Path(path);name=path.name;warnings=[]
  if upload_record_kind!='SUB':warnings.append('City EPC uploads/resubmittals belong to SUB; do not upload to '+upload_record_kind+'.')
  try:cycle=int(cycle_no)
  except (TypeError,ValueError):raise ValueError('Cycle must be a positive whole number') from None
  if cycle<1:raise ValueError('Cycle must be a positive whole number')
  if cycle==1:
   pattern=r'.+-CYC1-(APP|PLANS|SUPP)\.pdf'
   if naming_basis=='APN':pattern=r'\d{3}-\d{4}-\d{3}-\d{4}-CYC1-(APP|PLANS|SUPP)\.pdf'
   if prefix and naming_basis!='APN':pattern=re.escape(prefix)+r'-CYC1-(APP|PLANS|SUPP)\.pdf'
  else:pattern=rf'(COM|RES|MP)-\d{{7}}-CYC{cycle}-(APP|PLANS|SUPP|REPLY)\.pdf'
  if not re.fullmatch(pattern,name,re.I):warnings.append('Verify City file naming: '+('address/APN/master-plan-name-CYC1-APP/PLANS/SUPP.pdf' if cycle==1 else f'COM/RES/MP-1234567-CYC{cycle}-APP/PLANS/SUPP/REPLY.pdf')+'. FPP naming is not verified.')
  category=re.search(r'-(APP|PLANS|SUPP|REPLY)\.pdf$',name,re.I)
  limits={'APP':'50','PLANS':'300','SUPP':'150','REPLY':''};limits.update(metadata(details).get('file_limits_mb',{}))
  if category:
   kind=category.group(1).upper();limit=limits[kind]
   if limit not in ('',None) and Decimal(path.stat().st_size)>Decimal(str(limit))*Decimal(1000000):warnings.append(f'{kind} exceeds editable {limit} MB warning limit (decimal MB). Coordinate with intake; no submission is performed.')
   if kind=='REPLY' and limit in ('',None):warnings.append('REPLY size limit is unverified; verify with City intake.')
  warnings.append('Manual checks only: PDF security/portfolios, flattened layers/comments, bookmarks, legibility, orientation, scale, north arrow, vector origin and required signatures. PDFs are not parsed.')
  return warnings
 def city_cycle_warnings(self,register_id,cycle_no,stage='',app_changed=False,supp_changed=False):
  details=self.city_details(register_id)
  if details['jurisdiction_key']!=CITY:return ['Verify cycle / resubmittal requirements with County BPI or the selected jurisdiction.']
  n=int(cycle_no);out=[]
  if n>=2:
   out+=['Prepare discipline-organized REPLY plus CDD-0270. Submit a complete revised PLANS set; complete SUPP if affected; APP only if changed. Verify any unaffected-file exception with intake.','Cycle 2+: manually verify signed design professional stamps and absence of Preliminary / Bid Set Only / Not for Construction limitations.']
   if stage!='Plan Check Wait':out.append('Wait for Plan Check Wait before resubmitting; verify all required disciplines have completed review.')
  if n>3:out.append('CDD-0270: more than three review cycles may incur additional hourly fees. Record amounts manually; no fee is calculated.')
  return out
 def city_revision_guidance(self,register_id,issued,expanding,deferred=False):
  details=self.city_details(register_id)
  if details['jurisdiction_key']!=CITY:return 'Verify revision / deferred / new-permit procedure with the selected jurisdiction. City instructions do not apply.'
  if issued!='Yes':return 'No issued permit confirmed: verify mid-review scope changes with intake and explain them in REPLY. Do not use the issued-permit revision/deferred path.'
  if expanding=='Yes':return 'Expanding an issued scope likely needs a new separate permit. Verify with City intake; the app makes no permit determination.'
  if expanding!='No':return 'Scope expansion is unknown. Verify with City intake before selecting a revision path.'
  return ('Deferred: confirm the deferral was approved and listed on the original cover sheet. ' if deferred else 'Revision to an issued permit: ')+'Use CDD-0269 and a new SUB; affected plan sheets only, clouded with delta and date, signed/stamped by the same licensed professional as the issued set. Include the change-summary letter and revised supporting documents where affected. Verify with intake; nothing is submitted.'
 def save_city_checklist(self,register_id,values,row_id=None):
  details=self.city_details(register_id);values=dict(values)
  if row_id:
   old=self.rows('SELECT * FROM permit_requirements WHERE id=?',(row_id,))
   if not old or old[0]['register_id']!=register_id:raise ValueError('Select an item on this permit')
  with self.db:
   rid=self._city_put('permit_requirements',dict(values,register_id=register_id),row_id)
   oldmeta=self.rows('SELECT * FROM reg_requirement_details WHERE requirement_id=?',(rid,))
   meta={k:values[k] for k in ('source_id','last_verified_date','if_applicable','verify_label') if k in values}
   if oldmeta:self._city_put('reg_requirement_details',meta,oldmeta[0]['id'])
   else:self._city_put('reg_requirement_details',dict(meta,requirement_id=rid,origin='User',jurisdiction_key=details['jurisdiction_key']))
   self.log(self.rows('SELECT project_id FROM registers WHERE id=?',(register_id,))[0]['project_id'],f'Permit checklist item #{rid} saved')
  return rid
 def city_cycles(self,register_id):
  jurisdiction=self.city_details(register_id)['jurisdiction_key']
  return [r for r in self.rows('SELECT * FROM reg_review_cycles WHERE register_id=? ORDER BY cycle_no',(register_id,)) if metadata(r).get('jurisdiction_key',jurisdiction)==jurisdiction]
 def add_city_disciplines(self,cycle_id):
  cycle=self.rows('SELECT * FROM reg_review_cycles WHERE id=?',(cycle_id,))[0]
  if self.city_details(cycle['register_id'])['jurisdiction_key']!=CITY or metadata(cycle).get('jurisdiction_key')!=CITY:raise ValueError('No City discipline list is imported for County or Other')
  with self.db:
   source=self._catalog_source('0270');count=0
   for name in DISCIPLINES:
    if self.rows('SELECT id FROM reg_cycle_reviews WHERE cycle_id=? AND discipline=?',(cycle_id,name)):continue
    self._city_put('reg_cycle_reviews',dict(cycle_id=cycle_id,discipline=name,source_id=source,last_verified_date=catalog()['verified_date'],verify_label='Verified source / verify applicability',if_applicable=1));count+=1
  return count
 def city_charges(self,register_id):
  details=self.city_details(register_id);generated=metadata(details).get('generated_charges',{}).values()
  return [r for r in self.rows('SELECT * FROM reg_manual_charges WHERE register_id=? ORDER BY id',(register_id,)) if details['jurisdiction_key']==CITY or r['id'] not in generated]
 def set_city_file_limits(self,register_id,values):
  self.validate_city_limits(values);details=self.city_details(register_id);config=metadata(details);config['file_limits_mb']=values
  return self.save('reg_permit_details',dict(details_json=json.dumps(config)),details['id'])
 def city_source_register(self):
  data=catalog();rows=[]
  for item in data['items']:
   source=data['sources'][item['source']]
   rows.append(dict(item_key=item['key'],item=item['title'],jurisdiction=item['jurisdiction'],kind=item['check_kind'],uses='; '.join(item['uses']) or 'Both',work_types='; '.join(item['works']) or 'All / verify',permit_families='; '.join(item['families']),source_document=source['title'],source_revision_date=source['document_revision_date'] or 'Not stated — verify',source_link=source['url'],form_link=item['url'],last_verified_date=item['last_verified_date'],if_applicable=item['if_applicable'],verification=item['verify_label'],locator=item['locator'],conflicts=source['conflict_notes'].strip(),source_sha256=source['sha256']))
  return rows
