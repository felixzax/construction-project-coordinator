"""Stable long-form compliance exports; legacy export layouts remain intact."""
import html,json
from .regulatory import DISCLAIMER
from .city_permits import metadata

class ComplianceStore:
 def compliance_groups(self,pid):
  exists=any(self.rows(f'SELECT id FROM {t} WHERE project_id=? LIMIT 1',(pid,)) for t in ('reg_wb_sites','reg_project_roles','reg_document_requests','reg_tracker_steps','reg_filings'))
  exists=exists or bool(self.rows('SELECT d.id FROM reg_permit_details d JOIN registers r ON r.id=d.register_id WHERE r.project_id=? LIMIT 1',(pid,))) or bool(self.rows('SELECT d.id FROM reg_inspection_details d JOIN registers r ON r.id=d.register_id WHERE r.project_id=? LIMIT 1',(pid,)))
  if not exists:return {}
  permits=self.rows('SELECT r.id,r.title,d.* FROM registers r JOIN reg_permit_details d ON d.register_id=r.id WHERE r.project_id=?',(pid,));groups={'Permits':permits,'Tracker':[],'Filings':self.rows('SELECT * FROM reg_filings WHERE project_id=?',(pid,)),'R-factor':[],'Inspections':self.regulatory_inspections(pid),'Document Requests':self.regulatory_requests(pid),'Roles':self.rows('SELECT * FROM reg_project_roles WHERE project_id=?',(pid,)),'Checklist':[],'Review Cycles':[],'Discipline Reviews':[],'Charges':[],'Revised Fields':[],'Site Coverage':[],'Sources':[]}
  for p in permits:
   rid=p['register_id'];groups['Tracker']+=self.city_steps(rid,True);groups['Checklist']+=self.city_checklist(rid,True);groups['Review Cycles']+=self.city_cycles(rid);groups['Charges']+=self.city_charges(rid)
  groups['Tracker'] += [r for r in self.rows('SELECT * FROM reg_tracker_steps WHERE project_id=? AND register_id IS NULL',(pid,)) if not r['deleted']]
  for cycle in groups['Review Cycles']:groups['Discipline Reviews']+=self.rows('SELECT * FROM reg_cycle_reviews WHERE cycle_id=?',(cycle['id'],))
  site=self.water_site(pid)
  if site:
   groups['Site Coverage']=[site];groups['R-factor']=self.water_periods(site['id'])
   summary=self.water_r_summary(site['id']);groups['R Summary']=[dict(title='Overall manual R factor',source_id=groups['R-factor'][0].get('source_id') if groups['R-factor'] else None,last_verified_date=groups['R-factor'][0].get('last_verified_date','') if groups['R-factor'] else '',**summary)]
   groups['Rules']=self.rows('SELECT * FROM reg_rules WHERE deleted=0')
  for filing in groups['Filings']:groups['Revised Fields']+=self.rows('SELECT * FROM reg_filing_changes WHERE filing_id=?',(filing['id'],))
  source_ids={r.get('source_id') for records in groups.values() for r in records if r.get('source_id')}
  groups['Sources']=[r for r in self.all('reg_sources') if r['id'] in source_ids]
  settings=self.regulatory_settings(pid)
  if any(groups.values()):groups['Project applicability']=[settings]
  return groups
 def compliance_rows(self,pid,section='All',record_ids=None):
  groups=self.compliance_groups(pid);sources={r['id']:r for r in self.all('reg_sources')};contacts={r['id']:r['name'] for r in self.all('contacts')};rows=[]
  for kind,records in groups.items():
   if section!='All' and kind!=section:continue
   for record in records:
    if record_ids is not None and record.get('id') not in record_ids:continue
    discipline=record.get('discipline','')
    rid=record.get('register_id') or record.get('permit_register_id')
    if kind=='Inspections':rid=record['id']
    if record.get('cycle_id'):
     cycles=self.rows('SELECT register_id FROM reg_review_cycles WHERE id=?',(record['cycle_id'],));rid=cycles[0]['register_id'] if cycles else rid
    if rid:
     parents=self.rows('SELECT discipline FROM registers WHERE id=?',(rid,));discipline=parents[0]['discipline'] if parents else discipline
    if kind in ('Site Coverage','R-factor','R Summary','Filings','Revised Fields','Rules') or metadata(record).get('water_site_id') or record.get('filing_id') or record.get('inspection_kind') in ('Stormwater Weekly','Pre-storm','During-storm','Post-storm','QSD / Other'):discipline='Civil Engineering'
    if kind=='Filings' and record.get('regulatory_lane')=='County CEQA':discipline='General'
    source=sources.get(record.get('source_id'),{});base=dict(kind=kind,department=discipline or 'General',title=record.get('title') or record.get('filing_type') or record.get('role') or record.get('wdid') or record.get('field_name') or kind,status=record.get('status',record.get('state','')),deadline=record.get('deadline',record.get('needed_by','')),source_document=source.get('title',record.get('source_document','')),source_revision_date=source.get('document_revision_date',record.get('document_revision_date','')) or 'Verify / see source title',source_link=source.get('url',record.get('reference_url',record.get('source_url',''))),last_verified_date=record.get('last_verified_date',''),if_applicable=record.get('if_applicable',''),verify_label=record.get('verify_label','Verify applicability'))
    for key,value in record.items():
     if key in ('id','project_id','detail_id','source_id','template_item_id','inputs_fingerprint','r_inputs_fingerprint') or value is None or value=='':continue
     if key.endswith('_id'):
      if key in ('contact_id','requested_from_contact_id','prepared_by_contact_id'):value=contacts.get(value,'Unassigned');key=key[:-3]+'_name'
      else:continue
     if key=='details_json':
      try:details=json.loads(value)
      except ValueError:details={}
      for k,v in details.items():
       if k.endswith('_id') or k in ('context_active','context_key','generated_charges','user_hidden'):continue
       if v not in ('',None):rows.append(dict(base,department={'Structural':'Structural Engineering','Civil':'Civil Engineering'}.get(details.get('seal_discipline'),details.get('seal_discipline') or base['department']) if k.startswith('seal_') else base['department'],field='Person Responsible for Seal' if k=='seal_person_name' else k.replace('_',' '),value=json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else str(v)))
      continue
     if key.endswith('_json'):
      key=key[:-5]
      try:value=json.loads(value)
      except (TypeError,ValueError):pass
     if isinstance(value,(dict,list)):value=json.dumps(value,ensure_ascii=False)
     rows.append(dict(base,field=key.replace('_',' '),value=str(value)))
  return rows
 def compliance_report(self,pid):
  rows=self.compliance_rows(pid)
  if not rows:return ''
  e=lambda v:html.escape(str(v or ''))
  out='<h2>Regulatory &amp; Permits — coordination report</h2><p>'+e(DISCLAIMER)+'</p><table border="1" cellspacing="0" cellpadding="4"><tr><th>Section / Record</th><th>Field</th><th>Value</th><th>Source / verified</th></tr>'
  for r in rows:out+='<tr><td>'+e(r['kind']+' / '+r['title'])+'</td><td>'+e(r['field'])+'</td><td>'+e(r['value'])+'</td><td>'+e(r['source_document']+' | '+r['source_revision_date']+' | '+r['source_link']+' | '+r['last_verified_date'])+'</td></tr>'
  return out+'</table>'
 def compliance_department_rows(self,disciplines,pid=None,query=''):
  projects=[p['id'] for p in self.all('projects') if not pid or p['id']==pid];rows=[];projects_by_id={p['id']:p['name'] for p in self.all('projects')}
  for project in projects:
   for r in self.compliance_rows(project):
    # Water/shared site work is explicitly civil; permit work uses its existing
    # register discipline. No empty legacy export changes without actual records.
    if r['department'] not in disciplines:continue
    if query and query.casefold() not in ' '.join(str(v) for v in r.values()).casefold():continue
    rows.append(dict(record_type='Regulatory — '+r['kind'],project=projects_by_id[project],title=r['title'],discipline=r['department'],building_area='',responsible='',status=r['status'],deadline=r['deadline'],details=r['field']+': '+r['value']+' | source: '+r['source_document']+' | revision: '+r['source_revision_date']+' | verified: '+r['last_verified_date'],source_url=r['source_link'],currency='',total='',job_valuation='',permit_fee='',fee_status='',**{k:'' for k in ['site_address','location','required_fix','authority','code_reference','resolved_date','quantity','unit','material','material_unit_cost','labor_hours','labor_rate','material_cost','labor_cost','equipment_cost','subcontract_cost','included','estimated_amount','actual_amount','variance_amount']}))
  return rows
