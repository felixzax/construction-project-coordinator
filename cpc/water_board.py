"""Local-only Water Board coordination. No certification or agency submission."""
from datetime import date,datetime
from pathlib import Path
import json,re,uuid
from .rfactor import decimal_value,fingerprint,generate_periods,evaluate,period_flags
SITE_STATUSES=['Not Started','NOI Draft','Active','Inactive','NOT Filed','Terminated']
FILING_TYPES=['NOI','COI (Site)','COI (Organization)','NOT','Annual Report','SWPPP Amendment','CEQA Notice of Determination']
FILING_STATUSES=['Draft','Not Submitted','Submitted','Approved','Returned','Denied','Remanded']
READY=['Not Ready','Ready']

def water_catalog():return json.loads(Path(__file__).with_name('water_catalog.json').read_text(encoding='utf-8'))
def annual_dates(year):return f'{int(year)}-07-01',f'{int(year)+1}-06-30',f'{int(year)+1}-09-01'

class WaterBoardStore:
 def water_site(self,pid):
  rows=self.rows('SELECT * FROM reg_wb_sites WHERE project_id=?',(pid,));return rows[0] if rows else None
 def water_periods(self,site_id):return self.rows('SELECT * FROM reg_rfactor_periods WHERE wb_site_id=? ORDER BY position,id',(site_id,))
 def water_r_summary(self,site_id):
  site=self.rows('SELECT * FROM reg_wb_sites WHERE id=?',(site_id,))
  if not site:raise ValueError('Create site coverage first')
  return evaluate(site[0],self.water_periods(site_id))
 def validate_water(self,table,data,row_id=None,recalculated=False):
  if table=='reg_wb_sites':
   if data.get('status','Not Started') not in SITE_STATUSES:raise ValueError('Invalid site status')
   if data.get('permit_type','') not in ('','Traditional','Linear'):raise ValueError('Choose Traditional / Linear or leave Verify')
   if data.get('risk_level','') not in ('','1','2','3'):raise ValueError('Risk level must be blank or 1–3; verify manually')
   for k in ('total_acres','disturbed_acres','k_text','ls_text'):decimal_value(data.get(k,''),k,True)
   for k,lo,hi in [('latitude',-90,90),('longitude',-180,180)]:
    if data.get(k):
     from decimal import Decimal,InvalidOperation
     try:n=Decimal(str(data[k]))
     except InvalidOperation:raise ValueError('Invalid coordinate') from None
     if not n.is_finite() or not lo<=n<=hi:raise ValueError('Coordinate is outside valid range')
   if data.get('construction_start') and data.get('final_stabilization') and data['final_stabilization']<data['construction_start']:raise ValueError('Final stabilization cannot precede construction start')
   data['r_inputs_fingerprint']=fingerprint(data)
  if table=='reg_rfactor_periods':
   site=self.rows('SELECT * FROM reg_wb_sites WHERE id=?',(data.get('wb_site_id'),))
   if not site:raise ValueError('Select a site')
   try:position=int(data.get('position',0))
   except (ValueError,TypeError):raise ValueError('Position must be a positive integer') from None
   if position<1 or str(position)!=str(data.get('position')):raise ValueError('Position must be a positive integer')
   if data.get('end_date','')<data.get('start_date',''):raise ValueError('Period end cannot precede start')
   value=decimal_value(data.get('r_value_text',''),'R value',True)
   old=self.rows('SELECT * FROM reg_rfactor_periods WHERE id=?',(row_id,)) if row_id else []
   if old and old[0]['wb_site_id']!=data['wb_site_id']:raise ValueError('Site link is fixed')
   changed=not old or old[0]['r_value_text']!=data.get('r_value_text','')
   if (changed or recalculated) and value is not None:data.update(inputs_fingerprint=fingerprint(site[0]),needs_recalculation=0)
   elif old and any(data[k]!=old[0][k] for k in ('start_date','end_date')):data['needs_recalculation']=1
   data['verification_flags_json']=json.dumps(period_flags(data['start_date'],data['end_date']))
  if table=='reg_filings':
   if data.get('filing_type') not in FILING_TYPES or data.get('status','Draft') not in FILING_STATUSES or data.get('readiness_flag','Not Ready') not in READY:raise ValueError('Invalid filing type/status/readiness')
   is_ceqa=data['filing_type']=='CEQA Notice of Determination'
   if is_ceqa:data['wb_site_id']=None
   data['regulatory_lane']='County CEQA' if is_ceqa else 'Water Board'
   if not is_ceqa and not data.get('wb_site_id'):raise ValueError('Select a Water Board site')
   if not is_ceqa and self.regulatory_settings(data['project_id'])['cgp_subject']!='Yes' and data.get('status') in ('Submitted',):raise ValueError('CGP applicability must be Yes to record a new submission')
   old=self.rows('SELECT * FROM reg_filings WHERE id=?',(row_id,)) if row_id else []
   if old and ((not is_ceqa and old[0]['wb_site_id']!=data.get('wb_site_id')) or old[0]['filing_type']!=data['filing_type']):raise ValueError('Filing type and site are fixed; create a new filing')
   changed=json.loads(data.get('fields_changed_json') or '[]')
   if not isinstance(changed,list) or any(not isinstance(v,str) for v in changed):raise ValueError('Changed fields must be a list of labels')
   advanced=data.get('readiness_flag')=='Ready' or data.get('status')=='Submitted'
   certification_required=advanced
   if old and old[0]['status']=='Submitted' and data.get('status')=='Submitted' and all(data.get(k)==old[0].get(k) for k in ('reason_for_change','certifier_role_id','fields_changed_json')):certification_required=False
   if data['filing_type'].startswith('COI') and certification_required:
    roles=self.rows('SELECT r.*,c.name AS contact_name FROM reg_project_roles r JOIN contacts c ON c.id=r.contact_id WHERE r.id=? AND r.project_id=?',(data.get('certifier_role_id'),data['project_id']))
    if not str(data.get('reason_for_change','')).strip():raise ValueError('COI requires a reason for change. This blocker cannot be overridden.')
    if not roles or roles[0]['role'] not in ('LRP','DAR') or roles[0]['eauthorization_status']!='Yes':raise ValueError('COI requires an assigned LRP/DAR certifier with eAuthorization Yes. DEP cannot certify. This blocker cannot be overridden.')
    r=roles[0];data.update(certifier_name_snapshot=r['contact_name'],certifier_role_snapshot=r['role'],certifier_eauth_snapshot='Yes',certifier_eauth_date_snapshot=r['eauthorization_date'])
   if data['filing_type']=='Annual Report':
    start=data.get('report_period_start','');end=data.get('report_period_end','')
    if not start or not end:raise ValueError('Annual report period start and end are required')
    expected=annual_dates(date.fromisoformat(start).year)
    if not data.get('deadline'):data['deadline']=expected[2]
   warnings=self.water_filing_warnings(data,row_id)
   details=json.loads(data.get('details_json') or '{}')
   if advanced and warnings and not str(details.get('override_reason','')).strip():raise ValueError('Review warnings and enter a typed override reason: '+'; '.join(warnings))
  if table=='reg_filing_changes':
   filing=self.rows('SELECT status,readiness_flag FROM reg_filings WHERE id=?',(data.get('filing_id'),))
   if not filing or filing[0]['status']!='Draft' or filing[0]['readiness_flag']=='Ready':raise ValueError('Only Not Ready draft filing values can be edited')
  if table=='reg_rules':
   if row_id:
    old=self.rows('SELECT builtin FROM reg_rules WHERE id=?',(row_id,))
    if old and old[0]['builtin']:raise ValueError('Standard source rules are read-only; add your own editable rule')
 def water_filing_warnings(self,data,row_id=None):
  warnings=[]
  if data.get('filing_type','').startswith('COI'):
   if row_id:
    for f in self.finance_files('reg_filings',row_id):warnings+=self.water_attachment_warnings(f['original_name'],f['byte_size'])
   if data.get('wb_site_id'):
    summary=self.water_r_summary(data['wb_site_id'])
    if summary['state']!='Complete':warnings.append('R-factor '+summary['state']+'; verify risk information')
    warnings+=summary['warnings']
  if data.get('filing_type')=='Annual Report' and data.get('report_period_start'):
   expected=annual_dates(date.fromisoformat(data['report_period_start']).year)
   if (data.get('report_period_start'),data.get('report_period_end'),data.get('deadline'))!=expected:warnings.append('Annual period/date differs from July 1–June 30 / September 1; verify applicability and record reason')
  return warnings
 def water_attachment_warnings(self,name,byte_size):
  result=[]
  if len(name)>30:result.append('COI file name exceeds 30 characters (including extension): verify')
  if re.search(r'[^A-Za-z0-9._ -]',name):result.append('COI file name has special characters: verify permitted naming')
  if byte_size>100*1000000:result.append('COI attachment exceeds 100 MB: verify')
  return result
 def water_after_save(self,table,data,row_id):
  if table=='reg_project_roles' and (data.get('eauthorization_status')!='Yes' or not data.get('contact_id')):
   self.db.execute("UPDATE reg_filings SET readiness_flag='Not Ready' WHERE certifier_role_id=? AND status IN('Draft','Not Submitted','Returned','Remanded')",(row_id,))
  if table=='reg_wb_sites':
   self.db.execute("UPDATE reg_rfactor_periods SET needs_recalculation=1 WHERE wb_site_id=? AND r_value_text!='' AND inputs_fingerprint!=?",(row_id,fingerprint(data)))
  if table=='reg_filings':
   if not data.get('source_id'):
    key={'NOI':'noi','COI (Site)':'coi','COI (Organization)':'org','Annual Report':'annual','NOT':'not','SWPPP Amendment':'order'}.get(data.get('filing_type'))
    if key:
     data['source_id']=self._water_source(key);data['last_verified_date']=water_catalog()['verified_date'];self.db.execute('UPDATE reg_filings SET source_id=?,last_verified_date=? WHERE id=?',(data['source_id'],data['last_verified_date'],row_id))
   details=json.loads(data.get('details_json') or '{}');warnings=self.water_filing_warnings(data,row_id)
   if warnings and details.get('override_reason') and (data.get('readiness_flag')=='Ready' or data.get('status')=='Submitted'):
    self._city_put('reg_rule_overrides',dict(project_id=data['project_id'],record_table=table,record_id=row_id,warning_code='filing-warning',reason=details['override_reason'],occurred=date.today().isoformat(),details_json=json.dumps({'warnings':warnings})))
   if data.get('filing_type')=='Annual Report' and data.get('status')=='Submitted':
    start,end,due=annual_dates(date.fromisoformat(data['report_period_start']).year+1)
    if not self.rows("SELECT id FROM reg_filings WHERE wb_site_id=? AND filing_type='Annual Report' AND report_period_start=? AND report_period_end=?",(data['wb_site_id'],start,end)):
     self._city_put('reg_filings',dict(project_id=data['project_id'],wb_site_id=data['wb_site_id'],filing_type='Annual Report',report_period_start=start,report_period_end=end,deadline=due,source_id=data.get('source_id'),last_verified_date=data.get('last_verified_date',''),verify_label='Verify annual applicability',notes='Next period created from previous report marked Submitted locally. Verify applicability; no agency submission performed.'))
 def save_r_period(self,data,row_id=None,recalculated=False):
  with self.db:
   values=dict(data,water_recalculated=recalculated)
   if not row_id:values.setdefault('source_id',self._water_source('r'));values.setdefault('last_verified_date',water_catalog()['verified_date'])
   return self.save('reg_rfactor_periods',values,row_id)
 def generate_water_periods(self,site_id,replace=False):
  site=self.rows('SELECT * FROM reg_wb_sites WHERE id=?',(site_id,))[0];generated=generate_periods(site['construction_start'],site['final_stabilization']);existing=self.water_periods(site_id)
  if existing and not replace:raise ValueError('Periods already exist; confirm replacing them first')
  if existing:self.recovery_snapshot('before-delete')
  with self.db:
   if existing:
    # Original period file references stay as local site evidence.
    ids=[r['id'] for r in existing]
    for rid in ids:self.db.execute("UPDATE finance_files SET owner_table='reg_wb_sites',owner_id=? WHERE owner_table='reg_rfactor_periods' AND owner_id=?",(site_id,rid))
    for rid in ids:self.db.execute("DELETE FROM form_drafts WHERE target_table='reg_rfactor_periods' AND row_id=?",(rid,))
    self.db.execute('DELETE FROM reg_rfactor_periods WHERE wb_site_id=?',(site_id,))
   source=self._water_source('r')
   for n,row in enumerate(generated,1):self._city_put('reg_rfactor_periods',dict(wb_site_id=site_id,position=n,start_date=row['start_date'],end_date=row['end_date'],source_id=source,last_verified_date=water_catalog()['verified_date']))
  return len(generated)
 def use_r_in_coi(self,site_id,filing_id):
  summary=self.water_r_summary(site_id)
  if summary['state']!='Complete':raise ValueError('Only a complete, current R total can be copied')
  filing=self.rows('SELECT * FROM reg_filings WHERE id=?',(filing_id,))
  if not filing or filing[0]['wb_site_id']!=site_id or filing[0]['filing_type']!='COI (Site)' or filing[0]['status']!='Draft' or filing[0]['readiness_flag']=='Ready':raise ValueError('Choose a Not Ready DRAFT Site COI for this site')
  with self.db:
   old=self.rows("SELECT id FROM reg_filing_changes WHERE filing_id=? AND field_name='R factor'",(filing_id,))
   self._city_put('reg_filing_changes',dict(filing_id=filing_id,field_name='R factor',revised_value=summary['total'],notes='Copied manual period sum only. Verify in SMARTS; not submitted.'),old[0]['id'] if old else None)
   self.log(filing[0]['project_id'],f'R total copied to draft COI #{filing_id}; nothing submitted')
  return summary['total']
 def water_weekly_progress(self,pid,today=None):
  site=self.water_site(pid);days=self.regulatory_overview(pid,today)['days_since_weekly']
  return dict(days_since_weekly=days,overdue=bool(site and site['status']=='Active' and (days is None or days>7)),message='No performed weekly inspection recorded' if days is None else f'{days} days since performed weekly inspection')
 def _water_source(self,key):
  source=water_catalog()['sources'][key];prior=self.rows('SELECT id FROM reg_sources WHERE url=?',(source['url'],))
  return prior[0]['id'] if prior else self._city_put('reg_sources',source)
 def add_water_standards(self,pid,kind='checklist'):
  site=self.water_site(pid)
  if not site or self.regulatory_settings(pid)['cgp_subject']!='Yes':raise ValueError('Create an applicable CGP site first')
  count=0
  with self.db:
   for item in water_catalog()['items']:
    if item['kind']!=kind:continue
    source=self._water_source(item['source'])
    if kind=='rules':
     if self.rows('SELECT id FROM reg_rules WHERE rule_key=?',(item['key'],)):continue
     self._city_put('reg_rules',dict(rule_key=item['key'],title=item['title'],body=item['body'],applies_to_role=item.get('role',''),source_id=source,last_verified_date=water_catalog()['verified_date'],if_applicable=1,verify_label=item['verify_label'],origin='Guide',builtin=1,details_json=json.dumps({'source_key':item['source']})))
    else:
     if self.rows('SELECT id FROM reg_tracker_steps WHERE project_id=? AND step_key=?',(pid,item['key'])):continue
     self._city_put('reg_tracker_steps',dict(project_id=pid,step_key=item['key'],title=item['title'],notes=item['body'],source_id=source,last_verified_date=water_catalog()['verified_date'],if_applicable=1,verify_label=item['verify_label'],details_json=json.dumps({'water_site_id':site['id'],'discipline':'Site & Civil'})))
    count+=1
  return count
