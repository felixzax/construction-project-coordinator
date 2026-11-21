"""Manual Water Board workspace using existing forms, Files and recovery."""
import json,uuid
from datetime import date
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTabWidget,QLineEdit,QCheckBox,QAbstractItemView,QMessageBox,QDialog,QTextBrowser,QComboBox,QApplication,QToolButton,QMenu
from .table import DataTable
from .water_board import SITE_STATUSES,FILING_TYPES,FILING_STATUSES,READY,annual_dates,water_catalog
from .city_permits import metadata
from .regulatory import DISCLAIMER,PRIVACY_NOTE

SITE_FIELDS=['project_id','wdid','regional_board','permit_type','risk_level','sediment_risk','receiving_water_risk','combined_risk','total_acres','disturbed_acres','construction_start','grading_complete','final_stabilization','status','location_address','latitude','longitude','erosion_enabled','k_text','ls_text','notes']
FILING_FIELDS=['filing_type','reference','prepared_by_contact_id','certifier_role_id','readiness_flag','status','deadline','submitted_date','decision_date','manual_fee','currency','reason_for_change','site_information_changed','risk_changed','inactive_status_changed','owner_information_changed','acreage_increased','report_period_start','report_period_end','notes','source_id','last_verified_date','if_applicable','verify_label','override_reason']
PERIOD_FIELDS=['position','start_date','end_date','r_value_text','calculated_on','notes','water_recalculated']
RULE_FIELDS=['title','body','applies_to_role','source_id','last_verified_date','if_applicable','verify_label']

class WaterUI:
 def build_water_tab(self,layout):
  self.water_hint=QLabel('Set Subject to CA Construction General Permit in Project Profile to Yes to create site records. No acreage-based determination is made.');self.water_hint.setWordWrap(True);layout.addWidget(self.water_hint)
  bar=QHBoxLayout();layout.addLayout(bar);self.button(bar,'Site coverage',self.edit_water_site);self.button(bar,'Site Files',self.water_site_files);self.button(bar,'Open SMARTS',lambda:self.guard(lambda:self.confirm_city_link('https://smarts.waterboards.ca.gov/')));self.button(bar,'Delete site',self.delete_water_site);bar.addStretch()
  tabs=QTabWidget();layout.addWidget(tabs);self.water_tabs=tabs;self.water_tables={};self.water_rows={};self.water_filters={};self._water_exports={}
  for name in ('Filings','R-factor','Checklist','Rules & References'):
   page=QWidget();column=QVBoxLayout(page);tabs.addTab(page,name.replace('&','&&'));bar=QHBoxLayout();column.addLayout(bar)
   if name=='R-factor':
    for label,fn in [('Generate periods',self.generate_water_ui),('New period',lambda:self.edit_water_row('R-factor')),('Edit',lambda:self.edit_water_row('R-factor',True)),('Copy dates',self.copy_water_dates),('Copy overall R',self.copy_water_total),('Use in draft COI',self.use_water_r_ui)]:self.button(bar,label,fn)
    self.button(column,'Open EPA calculator (manual use only)',lambda:self.guard(lambda:self.confirm_city_link('https://lew.epa.gov/')))
    self.water_total=QLabel();self.water_total.setWordWrap(True);column.addWidget(self.water_total)
    note=QLabel('Method requested: Water Board guide rev 12/30/2020; retrieved guide February 2024. Verify current guide before filing. Type EPA outputs manually; this app does not calculate rainfall erosivity. Construction dates mean initial disturbance through final stabilization.');note.setWordWrap(True);column.addWidget(note)
   else:
    self.button(bar,'New',lambda _,n=name:self.edit_water_row(n));self.button(bar,'Edit',lambda _,n=name:self.edit_water_row(n,True))
    if name=='Filings':self.button(bar,'New annual period',self.new_water_annual);self.button(bar,'Revised fields',self.water_revised_fields)
    if name in ('Checklist','Rules & References'):self.button(bar,'Add standard items',lambda _,n=name:self.add_water_prompts_ui(n));self.button(bar,'Hide / show',lambda _,n=name:self.water_hide_ui(n))
   self.button(bar,'Delete',lambda _,n=name:self.water_delete_ui(n))
   if name!='Rules & References':self.button(bar,'Files',lambda _,n=name:self.water_files_ui(n))
   menu=QMenu(page);primary={'Generate periods','Edit'} if name=='R-factor' else {'New','Edit'}
   for index in range(bar.count()-1,-1,-1):
    button=bar.itemAt(index).widget()
    if button and hasattr(button,'text') and button.text() not in primary:
     bar.takeAt(index);button.hide();action=menu.addAction(button.text());action.triggered.connect(lambda checked=False,b=button:b.click())
   if name=='Rules & References' or name=='Checklist':menu.addAction('Open source',lambda checked=False,n=name:self.water_open_source(n))
   for kind in ('csv','docx'):menu.addAction('Export '+kind.upper(),lambda checked=False,n=name,k=kind:self.export_rows_dialog(n,self._water_exports.get(n,[]),k))
   tool=QToolButton(page);tool.setText('More');tool.setPopupMode(QToolButton.InstantPopup);tool.setMenu(menu);bar.addWidget(tool);bar.addStretch()
   filter=QLineEdit();filter.setPlaceholderText('Filter…');filter.textChanged.connect(self.refresh_water);column.addWidget(filter);self.water_filters[name]=filter
   table=DataTable();table.setAlternatingRowColors(True);table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.doubleClicked.connect(lambda _,n=name:self.edit_water_row(n,True));table.delete_selected=lambda n=name:self.water_delete_ui(n);column.addWidget(table);self.water_tables[name]=table
  self.water_show_hidden=QCheckBox('Include hidden checklist and rules');self.water_show_hidden.toggled.connect(self.refresh_water);layout.addWidget(self.water_show_hidden)
 def refresh(self,*args):
  super().refresh(*args)
  if hasattr(self,'water_tables'):self.refresh_water()
  if hasattr(self,'compliance_hint'):self.refresh_compliance()
  # Append regulatory dates only; legacy rows and their status behavior remain.
  extra=[];projects={p['id']:p for p in self.store.all('projects') if not p['archived']}
  for pid,project in projects.items():
   for row in self.store.regulatory_deadlines(pid):
    extra.append(dict(_source_table=row['table'],_source_id=row['id'],_reg_no_overdue=row['status']=='Waiting on Agency',project_id=pid,project=project['name'],kind='Regulatory',item=row['title'],title=row['title'],deadline=row['deadline'],status=row['status'],responsible=''))
  if extra:
   self.fill('Dashboard',sorted(self.data.get('Dashboard',[])+extra,key=lambda r:r.get('deadline') or '9999'))
   self.fill('Timeline',sorted(self.data.get('Timeline',[])+[dict(r,id=None,phase='Regulatory') for r in extra],key=lambda r:r.get('deadline') or '9999'))
 def refresh_water(self,*args):
  if not hasattr(self,'water_show_hidden'):return
  pid=self.project_filter.currentData();site=self.store.water_site(pid) if pid else None;show=self.water_show_hidden.isChecked();rows={n:[] for n in self.water_tables}
  if pid:rows['Filings']=self.store.rows('SELECT * FROM reg_filings WHERE project_id=? ORDER BY deadline,id',(pid,))
  if site:
   progress=self.store.water_weekly_progress(pid);self.water_hint.setText(f"WDID: {site['wdid'] or 'Verify'} | {site['status']} | "+progress['message']+(' — OVERDUE COORDINATION / VERIFY' if progress['overdue'] else '')+'\n'+DISCLAIMER)
   rows['Filings']=self.store.rows('SELECT * FROM reg_filings WHERE project_id=? ORDER BY deadline,id',(pid,));rows['R-factor']=self.store.water_periods(site['id'])
   rows['Checklist']=[r for r in self.store.rows('SELECT * FROM reg_tracker_steps WHERE project_id=? AND register_id IS NULL',(pid,)) if metadata(r).get('water_site_id')==site['id'] and not r['deleted'] and (show or not r['hidden'])]
   try:summary=self.store.water_r_summary(site['id']);text=summary['state']+' | '+summary['arithmetic']+'\n'+'; '.join(summary['warnings'])
   except ValueError as e:summary={};text=str(e)
   if summary.get('erosion_estimate'):text+='\nOptional R × K × LS: '+summary['erosion_estimate']+' (verify; no risk thresholds)'
   if summary.get('waiver_hint'):text+='\nR < 5 and disturbed acres < 5: verify Low Erosivity Waiver applicability; not an eligibility decision.'
   self.water_total.setText(text+'\nEnter this value as the R factor in the NOI/COI Risk tab.')
  else:self.water_hint.setText('Select a project and record site coverage. CGP must be Yes to create a site; no requirements are inferred.');self.water_total.setText('No site / R inputs. County CEQA records may still be tracked in Filings.')
  rows['Rules & References']=[r for r in self.store.all('reg_rules') if not r['deleted'] and (show or not r['hidden'])]
  sources={r['id']:r for r in self.store.all('reg_sources')};contacts={r['id']:r['name'] for r in self.store.all('contacts')};roles={r['id']:r for r in self.store.all('reg_project_roles')}
  for name,table in self.water_tables.items():
   query=self.water_filters[name].text().casefold();data=[r for r in rows[name] if query in ' '.join(str(v or '') for v in r.values()).casefold()];self.water_rows[name]=data;display=[]
   for original in data:
    r=dict(original);source=sources.get(r.get('source_id'),{});r.update(source_document=source.get('title',''),source_revision_date=source.get('document_revision_date','') or 'Month-only / verify; see source title',source_link=source.get('url',''))
    if name=='Filings':
     r['prepared_by']=contacts.get(r.get('prepared_by_contact_id'),'');role=roles.get(r.get('certifier_role_id'),{});r['certifier']=contacts.get(role.get('contact_id'),'')+' '+role.get('role','')
    if name=='R-factor':
     for key in ('start_date','end_date'):
      if r.get(key):r[key]=date.fromisoformat(r[key]).strftime('%m/%d/%Y')
    excluded={'id','project_id','wb_site_id','source_id','template_item_id','register_id','filing_id','cycle_id','step_key','rule_key','inputs_fingerprint','r_inputs_fingerprint'}
    display.append({k:v if v is not None else '' for k,v in r.items() if k not in excluded and not k.endswith('_json') and not k.endswith('_id')})
   for r in display:
    for key in ('needs_recalculation','if_applicable','hidden','builtin','deleted'):
     if key in r:r[key]='Yes' if r[key] else 'No'
    if 'r_value_text' in r:r['R value (manual EPA input)']=r.pop('r_value_text')
   self._water_exports[name]=display;self.render_recovery_table(table,display)
 def water_require_site(self):
  pid=self.selected_project_id();site=self.store.water_site(pid)
  if not site:raise ValueError('Create site coverage first')
  return site
 def water_selected(self,name):
  i=self.water_tables[name].currentRow()
  if i<0:raise ValueError('Select a record')
  return self.water_rows[name][i]
 def water_choices(self):
  pid=self.project_filter.currentData();choices=self.regulatory_choices(pid);contacts=choices['contact_id'];choices.update(prepared_by_contact_id=contacts,certifier_role_id=[('Unassigned',None)]+[(r['role']+' — '+next((c['name'] for c in self.store.all('contacts') if c['id']==r['contact_id']),'Unassigned'),r['id']) for r in self.store.all('reg_project_roles') if r['project_id']==pid],filing_type=FILING_TYPES,readiness_flag=READY,status=FILING_STATUSES,permit_type=['','Traditional','Linear'],risk_level=['','1','2','3'],currency=['USD','CAD','EUR','GBP','AUD']);return choices
 def edit_water_site(self,values=None,draft_key=None):
  from .ui import Form
  def action():
   pid=self.selected_project_id();site=self.store.water_site(pid);row=dict(site) if site else dict(project_id=pid,status='Not Started');row.update(values or {});choices=self.water_choices();choices['status']=SITE_STATUSES
   form=Form(self,'Water Board site coverage',SITE_FIELDS,row,choices);form.persist=lambda v:self.store.save('reg_wb_sites',v,site['id'] if site else None);form.enable_draft('reg_wb_sites',site['id'] if site else None,extra={'water_action':'site','project_id':pid},key=draft_key)
   if form.exec():self.refresh()
  self.guard(action)
 def edit_water_row(self,name,existing=False,values=None,draft_key=None,row_id=None):
  from .ui import Form
  def action():
   site=self.store.water_site(self.selected_project_id()) if name=='Filings' else self.water_require_site() if name!='Rules & References' else None;row=dict(self.water_selected(name)) if existing else {};table={'Filings':'reg_filings','R-factor':'reg_rfactor_periods','Checklist':'reg_tracker_steps','Rules & References':'reg_rules'}[name]
   if row_id:
    records=self.store.rows(f'SELECT * FROM {table} WHERE id=?',(row_id,))
    if not records:raise ValueError('Original record deleted; restore snapshot first')
    row.update(records[0])
   row.update(values or {});choices=self.water_choices()
   if name=='Filings':
    fields=FILING_FIELDS;row.setdefault('filing_type','NOI' if site else 'CEQA Notice of Determination');
    if not site:choices['filing_type']=['CEQA Notice of Determination']
    row.setdefault('status','Draft');row.setdefault('readiness_flag','Not Ready');row.setdefault('currency','USD');row.setdefault('fields_changed_json','[]')
    changes=json.loads(row['fields_changed_json'])
    for k in ('site_information_changed','risk_changed','inactive_status_changed','owner_information_changed','acreage_increased'):row.setdefault(k,k in changes)
    row['override_reason']=metadata(row).get('override_reason',row.get('override_reason',''))
   elif name=='R-factor':fields=PERIOD_FIELDS;row.setdefault('position',max([r['position'] for r in self.store.water_periods(site['id'])],default=0)+1)
   elif name=='Rules & References':
    if row.get('builtin'):raise ValueError('Standard rules are read-only. Add your own editable rule; use Hide to remove a standard rule from view.')
    fields=RULE_FIELDS
   else:fields=['title','status','deadline','occurred_date','contact_id','notes','source_id','last_verified_date','if_applicable','verify_label'];choices['status']=['Not Started','In Progress','Waiting on Agency','Submitted','Approved','Done','Not Applicable']
   form=Form(self,name,fields,row,choices)
   def persist(v):
    if name=='Filings':
     config=metadata(row);config['override_reason']=v.pop('override_reason','');changed=[k for k in ('site_information_changed','risk_changed','inactive_status_changed','owner_information_changed','acreage_increased') if v.pop(k,False)];v['fields_changed_json']=json.dumps(changed);v.update(project_id=self.selected_project_id(),wb_site_id=site['id'] if site else None,details_json=json.dumps(config));self.store.save(table,v,row.get('id'))
    elif name=='R-factor':
     v['r_value_text']=form.inputs['r_value_text'].text();confirmed=bool(v.pop('water_recalculated',False));self.store.save_r_period(dict(v,wb_site_id=site['id']),row.get('id'),confirmed)
    elif name=='Checklist':self.store.save(table,dict(v,project_id=site['project_id'],step_key=row.get('step_key','user.'+uuid.uuid4().hex),details_json=json.dumps({'water_site_id':site['id'],'discipline':'Site & Civil'})),row.get('id'))
    else:self.store.save(table,dict(v,rule_key=row.get('rule_key','user.'+uuid.uuid4().hex)),row.get('id'))
   form.persist=persist;form.enable_draft(table,row.get('id'),extra={'water_action':'row','water_name':name,'project_id':self.project_filter.currentData()},key=draft_key)
   if form.exec():self.refresh()
  self.guard(action)
 def generate_water_ui(self):
  def action():
   site=self.water_require_site();replace=bool(self.store.water_periods(site['id']))
   if replace and QMessageBox.question(self,'Replace R periods?','A recovery snapshot is created. Existing R values will be replaced with blank periods; retained file evidence moves to the site. Continue?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
   self.store.generate_water_periods(site['id'],replace);self.refresh()
  self.guard(action)
 def copy_water_dates(self):
  def action():
   row=self.water_selected('R-factor');fmt=lambda s:date.fromisoformat(s).strftime('%m/%d/%Y');QApplication.clipboard().setText(fmt(row['start_date'])+' – '+fmt(row['end_date']))
  self.guard(action)
 def copy_water_total(self):
  def action():
   summary=self.store.water_r_summary(self.water_require_site()['id'])
   if summary['state']!='Complete':raise ValueError('R total is '+summary['state'])
   QApplication.clipboard().setText(summary['total'])
  self.guard(action)
 def use_water_r_ui(self):
  from .ui import Form
  def action():
   site=self.water_require_site();choices=[(r['reference'] or 'Draft COI #'+str(r['id']),r['id']) for r in self.store.rows("SELECT * FROM reg_filings WHERE wb_site_id=? AND filing_type='COI (Site)' AND status='Draft' AND readiness_flag='Not Ready'",(site['id'],))]
   if not choices:raise ValueError('Create a Not Ready draft Site COI first')
   form=Form(self,'Copy overall R to draft COI',['filing_id'],choices={'filing_id':choices})
   if form.exec():self.store.use_r_in_coi(site['id'],form.values()['filing_id']);self.refresh()
  self.guard(action)
 def new_water_annual(self):
  from .ui import Form
  def action():
   self.water_require_site();today=date.today();year=today.year-1 if today.month>=7 else today.year-2;form=Form(self,'Annual report period — verify applicability',['start_year'],dict(start_year=str(year)))
   if form.exec():
    start,end,due=annual_dates(int(form.values()['start_year']));self.edit_water_row('Filings',values=dict(filing_type='Annual Report',report_period_start=start,report_period_end=end,deadline=due,notes='Verify applicability including active WDID duration; period is coordination only.'))
  self.guard(action)
 def add_water_prompts_ui(self,name):
  def action():
   site=self.water_require_site()
   if QMessageBox.question(self,'Add standard Verify items?','Add missing dated-source items only? Verify all applicability with the current permit / Regional Water Board.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
   self.store.add_water_standards(site['project_id'],'rules' if name=='Rules & References' else 'checklist');self.refresh()
  self.guard(action)
 def water_hide_ui(self,name):
  def action():
   row=self.water_selected(name);table='reg_rules' if name=='Rules & References' else 'reg_tracker_steps'
   # Standard rules are read-only text; their display visibility remains editable.
   with self.store.db:self.store.db.execute(f'UPDATE {table} SET hidden=? WHERE id=?',(int(not row['hidden']),row['id']))
   self.refresh()
  self.guard(action)
 def water_delete_ui(self,name):
  def action():
   table={'Filings':'reg_filings','R-factor':'reg_rfactor_periods','Checklist':'reg_tracker_steps','Rules & References':'reg_rules'}[name];indexes=self.water_tables[name].selected_record_rows();targets=[(table,self.water_rows[name][i]['id']) for i in indexes]
   if not targets:raise ValueError('Select records to delete')
   if self.confirm_delete(targets,name):self.refresh()
  self.guard(action)
 def water_files_ui(self,name):
  def action():
   row=self.water_selected(name);table={'Filings':'reg_filings','R-factor':'reg_rfactor_periods','Checklist':'reg_tracker_steps'}[name]
   if name=='Filings' and row['filing_type'].startswith('COI'):self.city_show_message('COI attachment guidance','Guide: ≤100 MB, file name ≤30 characters, special-character rules and required documents must be verified. Files are stored locally only. '+PRIVACY_NOTE)
   self.finance_file_manager(name,table,row)
  self.guard(action)
 def water_site_files(self):self.guard(lambda:self.finance_file_manager('Site coverage','reg_wb_sites',self.water_require_site()))
 def water_revised_fields(self):
  def action():
   filing=self.water_selected('Filings');dlg=QDialog(self);dlg.setWindowTitle('Revised filing fields');dlg.resize(950,600);layout=QVBoxLayout(dlg);table=DataTable();layout.addWidget(table);bar=QHBoxLayout();layout.addLayout(bar);rows=[]
   def reload():rows[:]=self.store.rows('SELECT * FROM reg_filing_changes WHERE filing_id=?',(filing['id'],));self.render_recovery_table(table,rows)
   def edit(existing=False):
    from .ui import Form
    def perform():
     if filing['status']!='Draft':raise ValueError('Only draft filing revised values can be changed')
     if existing:
      if table.currentRow()<0:raise ValueError('Select a revised field')
      row=rows[table.currentRow()]
     else:row={}
     form=Form(self,'Revised field',['field_name','previous_value','revised_value','notes'],row);form.persist=lambda v:self.store.save('reg_filing_changes',dict(v,filing_id=filing['id']),row.get('id'));form.enable_draft('reg_filing_changes',row.get('id'),extra={'filing_id':filing['id']})
     if form.exec():reload()
    self.guard(perform)
   self.button(bar,'New',lambda:edit());self.button(bar,'Edit',lambda:edit(True));self.button(bar,'Close',dlg.accept);reload();dlg.exec()
  self.guard(action)
 def resume_water_draft(self,draft):
  extra=draft['metadata'];pid=extra.get('project_id');ix=self.project_filter.findData(pid)
  if ix<0:raise ValueError('Project deleted; restore snapshot first')
  self.project_filter.setCurrentIndex(ix)
  if extra['water_action']=='site':return self.edit_water_site(draft['values'],draft['id'])
  return self.edit_water_row(extra['water_name'],values=draft['values'],draft_key=draft['id'],row_id=draft['row_id'])

 def water_open_source(self,name):
  def action():
   row=self.water_selected(name);sources=self.store.rows('SELECT url FROM reg_sources WHERE id=?',(row.get('source_id'),))
   if not sources:raise ValueError('Add a verified source first')
   self.confirm_city_link(sources[0]['url'])
  self.guard(action)

 def delete_water_site(self):
  def action():
   site=self.water_require_site()
   if self.confirm_delete([('reg_wb_sites',site['id'])],'site coverage, filings and linked R periods'):self.refresh()
  self.guard(action)
