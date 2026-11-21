"""Shared optional coordination tracking. No agency content or filing automation."""
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from .regulatory_schema import SCHEMA, REG_FIELDS
from .development import validate_date
from .permits import validate_url

REG_SECTION='Regulatory & Permits'
JURISDICTIONS=['City of Sacramento','Sacramento County unincorporated','Other']
REQUEST_STATUSES=['Requested','Received','In Review','Needs Changes','Approved','N/A']
ROLES=['Owner','LRP','DAR','DEP','QSD','QSP','QSD Delegate','QSP Delegate','Architect','Civil Engineer','Structural Engineer','MEP Engineer','Special Inspector','Agency Inspector','Plan Checker','Project Assistant','Other']
INSPECTION_KINDS=['Building','Fire','Special Inspection','Stormwater Weekly','Pre-storm','During-storm','Post-storm','QSD / Other']
DISCLAIMER='Local coordination records only, not a compliance determination; verify with the agency.'
PRIVACY_NOTE='Do not attach files containing logins, passwords or payment details; this app is not encrypted.'

class RegulatoryStore:
 def migrate_regulatory(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=12:return
  self.db.executescript('BEGIN IMMEDIATE;'+SCHEMA+'PRAGMA user_version=12;COMMIT;')
 def regulatory_settings(self,pid):
  rows=self.rows('SELECT * FROM reg_project_settings WHERE project_id=?',(pid,))
  return rows[0] if rows else dict(project_id=pid,cgp_subject='Undecided',jurisdiction='Other',sidebar_visible=0,notes='')
 def set_regulatory_settings(self,pid,**values):
  row=self.regulatory_settings(pid);row.update(values)
  return self.save('reg_project_settings',row,row.get('id'))
 def project_for(self,table,data):
  if table in REG_FIELDS:
   if 'project_id' in data:return data['project_id']
   for key,parent in [('register_id','registers'),('requirement_id','permit_requirements'),('cycle_id','reg_review_cycles'),('filing_id','reg_filings'),('wb_site_id','reg_wb_sites')]:
    if data.get(key):
     rows=self.rows(f'SELECT * FROM {parent} WHERE id=?',(data[key],))
     return self.project_for(parent,rows[0]) if rows else None
   return None
  return super().project_for(table,data)
 def validate_regulatory(self,table,data,row_id=None):
  if table=='registers' and row_id:
   old=self.rows('SELECT * FROM registers WHERE id=?',(row_id,))[0]
   linked=any(self.rows(f'SELECT id FROM {child} WHERE {fk}=? LIMIT 1',(row_id,)) for child,fk in [('reg_permit_details','register_id'),('reg_inspection_details','register_id'),('reg_document_requests','register_id'),('reg_tracker_steps','register_id'),('reg_review_cycles','register_id'),('reg_city_records','permit_register_id'),('reg_manual_charges','register_id')])
   if linked and (old['project_id']!=data.get('project_id') or old['record_type']!=data.get('record_type')):raise ValueError('Unlink regulatory tracking before changing project or register type')
  if table=='issues' and row_id and self.rows('SELECT id FROM reg_inspection_details WHERE correction_id=?',(row_id,)):
   old=self.rows('SELECT project_id FROM issues WHERE id=?',(row_id,))[0]
   if data.get('issue_type')!='Correction' or data.get('project_id')!=old['project_id']:raise ValueError('Unlink inspection tracking before changing correction type or project')
  if table not in REG_FIELDS:return
  pid=self.project_for(table,data)
  if row_id:
   previous=self.rows(f'SELECT * FROM {table} WHERE id=?',(row_id,))
   if previous and self.project_for(table,previous[0])!=pid:raise ValueError('Project ownership is fixed; create a new record')
  if 'project_id' in REG_FIELDS[table] and not self.rows('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Select an existing project')
  # Enforce same-project ownership for every cross-link, not just the UI choices.
  links={'register_id':'registers','permit_register_id':'registers','filing_id':'reg_filings','related_wb_filing_id':'reg_filings','wb_site_id':'reg_wb_sites','related_wb_site_id':'reg_wb_sites','cycle_id':'reg_review_cycles','correction_id':'issues','certifier_role_id':'reg_project_roles','requirement_id':'permit_requirements','parent_sub_id':'reg_city_records'}
  for key,parent in links.items():
   if data.get(key):
    rows=self.rows(f'SELECT * FROM {parent} WHERE id=?',(data[key],))
    if not rows or (pid and self.project_for(parent,rows[0])!=pid):raise ValueError('Linked record must belong to this project')
    if key in ('permit_register_id',) or (key=='register_id' and table in ('reg_permit_details','reg_document_requests')):
     if rows[0]['record_type']!='Permit':raise ValueError('Select a permit record')
    if table=='reg_inspection_details' and key=='register_id' and rows[0]['record_type']!='Inspection':raise ValueError('Select an inspection record')
    if key=='correction_id' and rows[0]['issue_type']!='Correction':raise ValueError('Select an existing Correction')
  for key in ('contact_id','requested_from_contact_id','prepared_by_contact_id'):
   if data.get(key) and not self.rows('SELECT id FROM contacts WHERE id=?',(data[key],)):raise ValueError('Select an existing contact')
  for key,value in data.items():
   if value and (key.endswith('_date') or key in ('needed_by','deadline','occurred','calculated_on','start_date','end_date','construction_start','grading_complete','final_stabilization','report_period_start','report_period_end')):validate_date(value)
   if key.endswith('_json'):
    try:json.loads(value)
    except (TypeError,ValueError):raise ValueError('Invalid metadata JSON') from None
  if table=='reg_sources':validate_url(data.get('url',''))
  if table=='reg_project_roles':
   if data.get('role') not in ROLES:raise ValueError('Select a coordination role')
   previous=self.rows('SELECT * FROM reg_project_roles WHERE id=?',(row_id,)) if row_id else []
   if previous and data.get('contact_id')!=previous[0]['contact_id']:
    data.update(eauthorization_status='Unknown',eauthorization_date='')
   if not data.get('contact_id') and data.get('eauthorization_status','Unknown')!='Unknown':raise ValueError('Assign a contact before recording authorization')
  if table=='reg_inspection_details':
   if data.get('inspection_kind','Building') not in INSPECTION_KINDS:raise ValueError('Select an inspection type')
   if data.get('jurisdiction','Other') not in JURISDICTIONS:raise ValueError('Select one jurisdiction')
   for key in ('qualifying_event','corrective_action'):
    if data.get(key,'Undecided') not in ('Undecided','Yes','No','Not Applicable'):raise ValueError('Invalid Yes/No value')
   if data.get('result') and not data.get('inspection_date'):raise ValueError('Record the performed inspection date with the result')
  if table=='reg_wb_sites' and self.regulatory_settings(pid)['cgp_subject']!='Yes':raise ValueError('Set Subject to CA Construction General Permit to Yes first')
  # Later phases own these workflows. Do not allow direct API use to bypass
  # certification checks which have not been implemented or verified yet.

  for key in ('amount','manual_fee','valuation_total','valuation_addition','valuation_remodel','r_value_text','k_text','ls_text','total_acres','disturbed_acres'):
   if data.get(key):
    try:value=Decimal(str(data[key]))
    except InvalidOperation:raise ValueError('Enter a non-negative decimal value') from None
    if not value.is_finite() or value<0:raise ValueError('Enter a non-negative decimal value')
 def regulatory_requests(self,pid):
  return self.rows('SELECT r.*,c.name AS requested_from FROM reg_document_requests r LEFT JOIN contacts c ON c.id=r.requested_from_contact_id WHERE r.project_id=? ORDER BY r.needed_by,r.id',(pid,))
 def regulatory_inspections(self,pid):
  return self.rows('SELECT r.id,r.project_id,r.title,r.deadline,r.status,r.contact_id,c.name AS inspector,d.id AS detail_id,d.inspection_kind,d.inspection_date,d.jurisdiction,d.result,d.qualifying_event,d.findings,d.corrective_action,d.correction_id,d.source_id,d.last_verified_date,d.if_applicable,d.verify_label,d.notes FROM registers r LEFT JOIN reg_inspection_details d ON d.register_id=r.id LEFT JOIN contacts c ON c.id=r.contact_id WHERE r.record_type=\'Inspection\' AND r.project_id=? ORDER BY r.deadline,r.id',(pid,))
 def regulatory_overview(self,pid,today=None):
  today=today or date.today();inspections=self.regulatory_inspections(pid)
  done=[r for r in inspections if r['inspection_date'] and r['inspection_date']<=today.isoformat() and r['result'] not in (None,'','Cancelled')]
  weekly=[r['inspection_date'] for r in done if r['inspection_kind']=='Stormwater Weekly']
  return dict(permits=self.rows('SELECT r.id,r.title,r.status,r.jurisdiction_type,r.jurisdiction_name,d.jurisdiction_key,d.stage FROM registers r LEFT JOIN reg_permit_details d ON d.register_id=r.id WHERE r.project_id=? AND r.record_type=\'Permit\'',(pid,)),
   open_document_requests=[r for r in self.regulatory_requests(pid) if r['status'] not in ('Approved','N/A')],
   passed_inspections=sum(r['result']=='Pass' for r in done),open_inspections=sum(r['result']!='Cancelled' and not (r in done and r['result']=='Pass') for r in inspections),
   days_since_weekly=(today-date.fromisoformat(max(weekly))).days if weekly else None,
   open_corrections=self.rows("SELECT * FROM issues WHERE project_id=? AND issue_type='Correction' AND status NOT IN('Resolved','Closed','Cancelled')",(pid,)),
   water_board=self.rows('SELECT wdid,status FROM reg_wb_sites WHERE project_id=?',(pid,)),upcoming=self.regulatory_deadlines(pid,today),waiting_on_agency=self.rows("SELECT * FROM reg_tracker_steps WHERE project_id=? AND status='Waiting on Agency' AND hidden=0 AND deleted=0",(pid,)))
 def regulatory_deadlines(self,pid,today=None):
  today=today or date.today();result=[]
  for table,date_key,closed in [('reg_document_requests','needed_by',('Approved','N/A')),('reg_tracker_steps','deadline',('Submitted','Approved','Terminated','Done','Completed','Cancelled')),('reg_filings','deadline',('Submitted','Approved','Terminated','Done'))]:
   for r in self.rows(f'SELECT * FROM {table} WHERE project_id=?',(pid,)):
    if r['status'] in closed or r.get('hidden') or r.get('deleted') or not r[date_key]:continue
    result.append(dict(table=table,id=r['id'],title=r.get('title',r.get('filing_type','')),deadline=r[date_key],status=r['status'],overdue=r[date_key]<today.isoformat() and r['status']!='Waiting on Agency'))
  return sorted(result,key=lambda r:(r['deadline'],r['table'],r['id']))
 def save_regulatory_inspection(self,register_id,values):
  # The existing inspection register remains the owner, including Files.
  rows=self.rows('SELECT id FROM reg_inspection_details WHERE register_id=?',(register_id,))
  return self.save('reg_inspection_details',dict(values,register_id=register_id),rows[0]['id'] if rows else None)
