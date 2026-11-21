"""City & County screens; all external links require a confirmation."""
import json
import uuid
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QTabWidget,QToolButton,QMenu,QTextBrowser,QCheckBox,QLineEdit,QAbstractItemView,QMessageBox,QFileDialog)
from .city_permits import CITY,COUNTY,OTHER,USES,WORK_TYPES,FAMILIES,STEP_STATUS,DISCIPLINES,metadata,catalog
from .regulatory import JURISDICTIONS,DISCLAIMER,PRIVACY_NOTE
from .permits import validate_url
from .table import DataTable

CONFIG_FIELDS=['project_id','title','jurisdiction_key','occupancy_type','work_type','permit_family','local_reference','fire_district','stage','valuation_total','valuation_addition','valuation_remodel','currency','related_wb_site_id','related_wb_filing_id','notes']

class CityPermitUI:
 def build_city_tab(self,layout):
  bar=QHBoxLayout();layout.addLayout(bar);self.city_permit_select=QComboBox();self.city_permit_select.setMinimumWidth(300);self.city_permit_select.currentIndexChanged.connect(self.refresh_city_lists);bar.addWidget(self.city_permit_select,1)
  self.button(bar,'New permit',lambda:self.edit_city_config());self.button(bar,'Set up / Edit',lambda:self.edit_city_config(True));self.button(bar,'Files',self.city_permit_files)
  more=QToolButton();more.setText('More');more.setPopupMode(QToolButton.InstantPopup);menu=QMenu(more)
  for label,action in [('Add standard checklist / tracker',self.add_city_prompts),('Open official portal',self.open_city_portal),('Source / revision register',self.show_city_sources),('Delete permit',self.delete_city_permit)]:menu.addAction(label,action)
  more.setMenu(menu);bar.addWidget(more)
  self.city_context=QLabel('Select a project, then create or select a permit. Existing permits can be explicitly set up here.');self.city_context.setWordWrap(True);layout.addWidget(self.city_context)
  self.city_inner_tabs=QTabWidget();layout.addWidget(self.city_inner_tabs);self.city_tables={};self.city_rows={};self.city_filters={};self.city_hidden={}
  for name in ('Tracker','Checklist','Review Cycles','City Records','Manual Charges'):
   page=QWidget();column=QVBoxLayout(page);self.city_inner_tabs.addTab(page,name);actions=QHBoxLayout();column.addLayout(actions)
   self.button(actions,'New',lambda _,n=name:self.edit_city_row(n));self.button(actions,'Edit',lambda _,n=name:self.edit_city_row(n,True))
   if name=='Review Cycles':self.button(actions,'Discipline reviews',self.city_cycle_reviews);self.button(actions,'Cycle warnings',self.city_cycle_warning_screen)
   else:
    more=QToolButton();more.setText('More');more.setPopupMode(QToolButton.InstantPopup);menu=QMenu(more)
    if name in ('Tracker','Checklist'):
     menu.addAction('Hide / show selected',lambda checked=False,n=name:self.city_toggle_hidden(n));menu.addAction('Open source',lambda checked=False,n=name:self.open_city_item_source(n))
    if name=='Checklist':menu.addAction('Check / uncheck selected',self.city_toggle_completed)
    menu.addAction('Files',lambda checked=False,n=name:self.city_row_files(n));menu.addAction('Delete selected',lambda checked=False,n=name:self.city_delete_row(n));more.setMenu(menu);actions.addWidget(more)
   actions.addStretch()
   entry=QLineEdit();entry.setPlaceholderText('Filter records…');entry.textChanged.connect(self.refresh_city_lists);column.addWidget(entry);self.city_filters[name]=entry
   if name in ('Tracker','Checklist'):
    hidden=QCheckBox('Include hidden items for this template');hidden.toggled.connect(self.refresh_city_lists);column.addWidget(hidden);self.city_hidden[name]=hidden
   table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setAlternatingRowColors(True);table.doubleClicked.connect(lambda _,n=name:self.edit_city_row(n,True));table.delete_selected=lambda checked=False,n=name:self.city_delete_row(n);column.addWidget(table);self.city_tables[name]=table
  files=QWidget();column=QVBoxLayout(files);self.city_inner_tabs.addTab(files,'File checks');note=QLabel('Warnings only; no files are submitted or resubmitted. Ordinary signed/stamped PDFs may be stored in Files. '+PRIVACY_NOTE);note.setWordWrap(True);column.addWidget(note)
  self.button(column,'Check a local file name / size',self.city_check_file_screen);self.button(column,'Edit size warning limits',self.city_limits_screen);self.button(column,'Open permit Files',self.city_permit_files);column.addStretch()
  revisions=QWidget();column=QVBoxLayout(revisions);self.city_inner_tabs.addTab(revisions,'Revision guidance');note=QLabel('Use a manual decision aid for revisions, deferred work and possible scope expansion. It does not decide permit requirements.');note.setWordWrap(True);column.addWidget(note);self.button(column,'Review revision / deferred questions',self.city_revision_screen);column.addStretch()
 def refresh(self,*args):
  super().refresh(*args)
  if hasattr(self,'city_permit_select'):
   selected=self.city_permit_select.currentData();pid=self.project_filter.currentData();self.city_permit_select.blockSignals(True);self.city_permit_select.clear();self.city_permit_select.addItem('Select a permit…',None)
   for r in self.store.all('registers'):
    if r['project_id']==pid and r['record_type']=='Permit':self.city_permit_select.addItem(r['title'],r['id'])
   ix=self.city_permit_select.findData(selected);self.city_permit_select.setCurrentIndex(max(0,ix));self.city_permit_select.blockSignals(False);self.refresh_city_lists()
 def city_selected_id(self):
  rid=self.city_permit_select.currentData()
  if not rid:raise ValueError('Select a permit first')
  return rid
 def city_parent(self):return self.store.rows('SELECT * FROM registers WHERE id=?',(self.city_selected_id(),))[0]
 def refresh_city_lists(self,*args):
  if not hasattr(self,'city_tables'):return
  rid=self.city_permit_select.currentData();rows={n:[] for n in self.city_tables}
  details=self.store.rows('SELECT * FROM reg_permit_details WHERE register_id=?',(rid,)) if rid else []
  if details:
   d=details[0];self.city_context.setText(' | '.join(d[k] for k in ('jurisdiction_key','occupancy_type','work_type','permit_family'))+'\n'+DISCLAIMER)
   rows={'Tracker':self.store.city_steps(rid,self.city_hidden['Tracker'].isChecked()),'Checklist':self.store.city_checklist(rid,self.city_hidden['Checklist'].isChecked()),'Review Cycles':self.store.city_cycles(rid),'City Records':self.store.rows('SELECT * FROM reg_city_records WHERE permit_register_id=?',(rid,)) if d['jurisdiction_key']==CITY else [],'Manual Charges':self.store.city_charges(rid)}
  else:self.city_context.setText('Use Set up / Edit to choose one jurisdiction for this permit. No standard items are added automatically.')
  for name,table in self.city_tables.items():
   query=self.city_filters[name].text().casefold();data=[r for r in rows[name] if query in ' '.join(str(v or '') for v in r.values()).casefold()];self.city_rows[name]=data
   contacts={r['id']:r['name'] for r in self.store.all('contacts')};sources={r['id']:r for r in self.store.all('reg_sources')}
   columns={'Tracker':['title','status','deadline','occurred_date','responsible','notes','source_document','document_revision_date','last_verified_date','if_applicable','verify_label','hidden'],'Checklist':['title','completed','completed_on','notes','source_document','document_revision_date','source_url','last_verified_date','if_applicable','verify_label','hidden'],'Review Cycles':['cycle_no','stage','submitted_date','agency_response_date','notes'],'City Records':['record_kind','reference','parent_sub_reference','notes'],'Manual Charges':['title','amount','currency','status','paid_date','notes','source_document','document_revision_date','last_verified_date','verify_label']}
   display=[]
   for record in data:
    r=dict(record);r['responsible']=contacts.get(r.get('contact_id'),'');source=sources.get(r.get('source_id'),{});r.setdefault('source_document',source.get('title',''));r.setdefault('document_revision_date',source.get('document_revision_date',''))
    if name=='City Records':
     parents=[p['reference'] or 'SUB' for p in rows[name] if p['id']==r['parent_sub_id']];r['parent_sub_reference']=parents[0] if parents else ''
    display.append({k:r.get(k) if r.get(k) is not None else '' for k in columns[name]})
   self.render_recovery_table(table,display)
 def city_selected_row(self,name):
  i=self.city_tables[name].currentRow()
  if i<0:raise ValueError('Select a '+name+' record')
  return self.city_rows[name][i]
 def city_choices(self):
  pid=self.project_filter.currentData();choices=self.regulatory_choices(pid);rid=self.city_permit_select.currentData()
  choices.update(currency=['USD','CAD','EUR','GBP','AUD'],jurisdiction_key=JURISDICTIONS,occupancy_type=USES,work_type=WORK_TYPES,permit_family=FAMILIES,register_id=[(self.city_permit_select.currentText(),rid)],permit_register_id=[(self.city_permit_select.currentText(),rid)],status=STEP_STATUS,record_kind=['PLN','SUB','COM','RES','FPP','MP'],parent_sub_id=[('No parent SUB',None)]+[(r['reference'] or 'SUB #'+str(r['id']),r['id']) for r in self.store.rows("SELECT * FROM reg_city_records WHERE permit_register_id=? AND record_kind='SUB'",(rid,))],related_wb_site_id=[('None / Phase 4',None)]+[(r['wdid'],r['id']) for r in self.store.all('reg_wb_sites') if r['project_id']==pid],related_wb_filing_id=[('None / Phase 4',None)]+[(r['reference'] or r['filing_type'],r['id']) for r in self.store.all('reg_filings') if r['project_id']==pid])
  return choices
 def edit_city_config(self,existing=False,values=None,draft_key=None):
  def action():
   pid=self.selected_project_id();parent=self.city_parent() if existing else None;rid=parent['id'] if parent else None
   old=self.store.rows('SELECT * FROM reg_permit_details WHERE register_id=?',(rid,)) if rid else []
   row=dict(project_id=pid,title=parent['title'] if parent else '',jurisdiction_key=self.store.regulatory_settings(pid)['jurisdiction'],occupancy_type='Residential',work_type='Other',permit_family='Building',currency='USD')
   if old:row.update(old[0])
   if values:row.update(values)
   self.city_config_form(row,rid,draft_key)
  self.guard(action)
 def city_config_form(self,row,register_id=None,draft_key=None):
  from .ui import Form
  form=Form(self,'City & County permit setup',CONFIG_FIELDS,row,self.city_choices())
  def persist(values):
   old=self.store.rows('SELECT * FROM reg_permit_details WHERE register_id=?',(register_id,)) if register_id else []
   changed=old and any(values[k]!=old[0][k] for k in ('jurisdiction_key','occupancy_type','work_type','permit_family'))
   if changed:
    text='Change template context from\n'+ ' / '.join(old[0][k] for k in ('jurisdiction_key','occupancy_type','work_type','permit_family'))+'\nto\n'+' / '.join(values[k] for k in ('jurisdiction_key','occupancy_type','work_type','permit_family'))+'?\n\nUser-added items, edits, prior checks and Files are preserved. Old generated items are kept inactive; only matching/new template items appear. A City check never approves a County requirement. Nothing is submitted.'
    if QMessageBox.question(form,'Confirm jurisdiction / template swap',text,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:raise ValueError('Template swap cancelled; no records changed')
   rid=self.store.configure_city_permit(values,register_id,confirmed=bool(changed));self.refresh();self.city_permit_select.setCurrentIndex(self.city_permit_select.findData(rid))
  form.persist=persist;form.enable_draft('registers',register_id,extra={'city_action':'config'},key=draft_key)
  if form.exec():self.refresh()
 def add_city_prompts(self):
  def action():
   rid=self.city_selected_id();d=self.store.city_details(rid)
   if QMessageBox.question(self,'Add standard coordination items?', 'Add only missing items for '+d['jurisdiction_key']+' / '+d['occupancy_type']+' / '+d['work_type']+' / '+d['permit_family']+'?\nExisting edits/checks and deleted items are preserved. Verify applicability and source dates with the agency.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
   count=self.store.add_city_standard(rid);self.refresh();self.statusBar().showMessage(f'Added {count} coordination items. Verify applicability.',8000)
  self.guard(action)
 def city_show_message(self,title,text):
  dlg=QDialog(self);dlg.setWindowTitle(title);dlg.resize(850,580);layout=QVBoxLayout(dlg);browser=QTextBrowser();browser.setOpenLinks(False);browser.setPlainText(DISCLAIMER+'\n\n'+text);layout.addWidget(browser);self.button(layout,'Close',dlg.accept);dlg.exec()
 def city_form(self,title,fields,row,table,persist,choices=None,extra=None,key=None):
  from .ui import Form
  form=Form(self,title,fields,row,choices or self.city_choices());form.persist=persist;form.enable_draft(table,row.get('id'),extra=extra,key=key)
  if form.exec():self.refresh()
 def edit_city_row(self,name,existing=False,values=None,draft_key=None):
  def action():
   rid=self.city_selected_id();d=self.store.city_details(rid);p=self.city_parent();row=dict(self.city_selected_row(name)) if existing else dict(project_id=p['project_id'],register_id=rid,permit_register_id=rid)
   if values:row.update(values)
   if name=='Checklist':
    fields=['title','source_url','completed','notes','source_id','last_verified_date','if_applicable','verify_label'];table='permit_requirements';save=lambda v:self.store.save_city_checklist(rid,v,row.get('id'))
   elif name=='Tracker':
    fields=['title','status','deadline','occurred_date','contact_id','notes','source_id','last_verified_date','if_applicable','verify_label'];table='reg_tracker_steps'
    row.setdefault('step_key','user.'+uuid.uuid4().hex);save=lambda v:self.store.save(table,dict(v,project_id=p['project_id'],register_id=rid,step_key=row['step_key']),row.get('id'))
   elif name=='Review Cycles':
    fields=['cycle_no','stage','submitted_date','agency_response_date','notes'];table='reg_review_cycles';row.setdefault('cycle_no',max([r['cycle_no'] for r in self.store.city_cycles(rid)],default=0)+1);save=lambda v:self.store.save(table,dict(v,project_id=p['project_id'],register_id=rid),row.get('id'))
   elif name=='City Records':
    if d['jurisdiction_key']!=CITY:raise ValueError('City record types are not imported into County or Other permits')
    fields=['record_kind','reference','parent_sub_id','notes'];table='reg_city_records';save=lambda v:self.store.save(table,dict(v,project_id=p['project_id'],permit_register_id=rid),row.get('id'))
   else:
    fields=['title','amount','currency','status','paid_date','source_id','last_verified_date','if_applicable','verify_label','notes'];table='reg_manual_charges';row.setdefault('currency','USD');save=lambda v:self.store.save(table,dict(v,project_id=p['project_id'],register_id=rid),row.get('id'))
   choices=self.city_choices()
   if name=='Manual Charges':choices['status']=['Unpaid','Estimated','Invoiced','Paid','Not Applicable']
   self.city_form(name,fields,row,table,save,choices,extra={'city_action':'row','city_name':name,'register_id':rid},key=draft_key)
  self.guard(action)
 def city_toggle_completed(self):
  def action():
   row=self.city_selected_row('Checklist');self.store.set_requirement_completed(row['id'],not row['completed']);self.refresh()
  self.guard(action)
 def city_toggle_hidden(self,name):
  def action():
   row=self.city_selected_row(name);self.store.set_city_item_hidden('checklist' if name=='Checklist' else 'tracker',row['id'],not row['hidden']);self.refresh()
  self.guard(action)
 def city_delete_row(self,name):
  def action():
   ids=self.city_tables[name].selected_record_rows();table={'Tracker':'reg_tracker_steps','Checklist':'permit_requirements','City Records':'reg_city_records','Manual Charges':'reg_manual_charges','Review Cycles':'reg_review_cycles'}[name]
   if not ids:raise ValueError('Select a record')
   if self.confirm_delete([(table,self.city_rows[name][i]['id']) for i in ids],name):self.refresh()
  self.guard(action)
 def city_row_files(self,name):
  self.guard(lambda:self.finance_file_manager(name,{'Tracker':'reg_tracker_steps','Checklist':'permit_requirements','City Records':'reg_city_records','Manual Charges':'reg_manual_charges','Review Cycles':'reg_review_cycles'}[name],self.city_selected_row(name)))
 def city_permit_files(self):self.guard(lambda:self.finance_file_manager('Permit','registers',self.city_parent()))
 def delete_city_permit(self):
  def action():
   if self.confirm_delete([('registers',self.city_selected_id())],'permit and linked tracking'):self.refresh()
  self.guard(action)
 def confirm_city_link(self,url):
  validate_url(url)
  if not url:raise ValueError('No source link; add one after verifying')
  if QMessageBox.question(self,'Open official reference?',url+'\n\nOpen in your browser? No data is submitted by this app.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:QDesktopServices.openUrl(QUrl(url))
 def open_city_item_source(self,name):self.guard(lambda:self.confirm_city_link(self.city_selected_row(name).get('reference_url') or self.city_selected_row(name).get('source_url','')))
 def open_city_portal(self):
  def action():
   jurisdiction=self.store.city_details(self.city_selected_id())['jurisdiction_key']
   if jurisdiction==OTHER:raise ValueError('Other has no imported portal; add its verified link in the existing Permits section')
   self.confirm_city_link('https://aca.accela.com/sacramento/' if jurisdiction==CITY else 'https://aca-prod.accela.com/SACCO/')
  self.guard(action)
 def show_city_sources(self):
  dlg=QDialog(self);dlg.setWindowTitle('Phase 3 source / revision register');dlg.resize(1150,650);layout=QVBoxLayout(dlg);note=QLabel(DISCLAIMER+' Sources are dated snapshots; blank published revision dates stay Verify.');note.setWordWrap(True);layout.addWidget(note);table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table);self.render_recovery_table(table,self.store.city_source_register());self.button(layout,'Conflicts / qualifications',lambda:self.city_show_message('Source conflicts','\n\n'.join(c['description']+'\n'+c['resolution'] for c in catalog()['conflicts'])));self.button(layout,'Close',dlg.accept);dlg.exec()
 def city_check_file_screen(self):
  from .ui import Form
  def action():
   rid=self.city_selected_id();self.store.city_details(rid);path,_=QFileDialog.getOpenFileName(self,'Choose a local file to check')
   if not path:return
   form=Form(self,'City file-name / size check',['file_path','cycle_no','naming_basis','prefix','upload_record_kind'],dict(file_path=path,cycle_no='1',naming_basis='Address',upload_record_kind='SUB'),dict(naming_basis=['Address','APN','Master Plan'],upload_record_kind=['SUB','PLN','COM','RES','FPP','MP']))
   if form.exec():
    v=form.values();warnings=self.store.city_file_warnings(rid,v['file_path'],v['cycle_no'],v['naming_basis'],v['prefix'],v['upload_record_kind']);self.city_show_message('File warnings (no submission)', '\n\n'.join(warnings))
  self.guard(action)
 def city_limits_screen(self,values=None,draft_key=None):
  def action():
   rid=self.city_selected_id();d=self.store.city_details(rid)
   if d['jurisdiction_key']!=CITY:raise ValueError('City EPC limits do not apply to this jurisdiction')
   limits={'APP':'50','PLANS':'300','SUPP':'150','REPLY':''};limits.update(metadata(d).get('file_limits_mb',{}));row=values or {k.lower()+'_mb':v for k,v in limits.items()}
   self.city_form('Editable size warnings — decimal MB; blank = verify',['app_mb','plans_mb','supp_mb','reply_mb'],row,'reg_permit_details',lambda v:self.store.set_city_file_limits(rid,{k.upper().replace('_MB',''):n for k,n in v.items()}),extra={'city_action':'limits','register_id':rid},key=draft_key)
  self.guard(action)
 def city_cycle_warning_screen(self):
  def action():
   row=self.city_selected_row('Review Cycles');warnings=self.store.city_cycle_warnings(self.city_selected_id(),row['cycle_no'],row['stage']);self.city_show_message('Review cycle guidance','\n\n'.join(warnings) or 'No additional cycle warnings; verify with the agency.')
  self.guard(action)
 def city_revision_screen(self,values=None,draft_key=None):
  from .ui import Form
  def action():
   rid=self.city_selected_id();d=self.store.city_details(rid);row=values or metadata(d).get('revision_answers',{});form=Form(self,'Revision / deferred guidance',['issued','expanding','deferred'],row,dict(issued=['Unknown','Yes','No'],expanding=['Unknown','Yes','No'],deferred=['No','Yes']))
   def save(v):
    config=metadata(d);config['revision_answers']=v;self.store.save('reg_permit_details',dict(details_json=json.dumps(config)),d['id'])
   form.persist=save;form.enable_draft('reg_permit_details',extra={'city_action':'revision','register_id':rid},key=draft_key)
   if form.exec():
    v=form.values();text=self.store.city_revision_guidance(rid,v['issued'],v['expanding'],v['deferred']=='Yes');sources='CDD-0269 rev 2026-01-01; EPC Guide v27 rev 2020-02-12' if d['jurisdiction_key']==CITY else 'Verify with the selected jurisdiction; no City revision rules imported'
    self.city_show_message('Revision guidance — verify with intake',text+'\n\nSources: '+sources+'. Nothing is submitted.')
  self.guard(action)
 def city_cycle_reviews(self):
  def action():
   cycle=self.city_selected_row('Review Cycles');dlg=QDialog(self);dlg.setWindowTitle('Cycle '+str(cycle['cycle_no'])+' — discipline reviews');dlg.resize(1050,650);layout=QVBoxLayout(dlg);note=QLabel(DISCLAIMER);layout.addWidget(note);table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table);bar=QHBoxLayout();layout.addLayout(bar);rows=[]
   def reload():rows[:]=self.store.rows('SELECT r.*,s.document_revision_date,s.url AS source_url FROM reg_cycle_reviews r LEFT JOIN reg_sources s ON s.id=r.source_id WHERE cycle_id=?',(cycle['id'],));self.render_recovery_table(table,rows)
   def edit(existing=False):
    def perform():
     if existing:
      i=table.currentRow()
      if i<0:raise ValueError('Select a discipline')
      row=rows[i]
     else:row=dict(cycle_id=cycle['id'])
     choices=self.city_choices()
     if self.store.city_details(cycle['register_id'])['jurisdiction_key']==CITY:choices['discipline']=DISCIPLINES
     self.city_form('Discipline review',['discipline','status','contact_id','due_date','response_date','notes','source_id','last_verified_date','if_applicable','verify_label'],row,'reg_cycle_reviews',lambda v:self.store.save('reg_cycle_reviews',dict(v,cycle_id=cycle['id']),row.get('id')),choices,extra={'city_action':'discipline','cycle_id':cycle['id'],'register_id':cycle['register_id']});reload()
    self.guard(perform)
   def standards():
    self.guard(lambda:(self.store.add_city_disciplines(cycle['id']),reload()))
   def delete():
    def perform():
     i=table.currentRow()
     if i<0:raise ValueError('Select a discipline')
     if self.confirm_delete([('reg_cycle_reviews',rows[i]['id'])],'discipline review'):reload()
    self.guard(perform)
   self.button(bar,'New',lambda:edit());self.button(bar,'Edit',lambda:edit(True));
   if self.store.city_details(cycle['register_id'])['jurisdiction_key']==CITY:self.button(bar,'Add City disciplines',standards)
   self.button(bar,'Delete',delete);self.button(bar,'Close',dlg.accept);reload();dlg.exec()
  self.guard(action)
 def resume_city_draft(self,draft):
  values=draft['values'];extra=draft['metadata'];action=extra['city_action'];rid=extra.get('register_id') or draft['row_id']
  if action=='config':return self.edit_city_config(bool(draft['row_id']),values,draft['id'])
  pid=self.store.rows('SELECT project_id FROM registers WHERE id=?',(rid,))
  if not pid:raise ValueError('The permit was deleted; restore a recovery snapshot first')
  self.project_filter.setCurrentIndex(self.project_filter.findData(pid[0]['project_id']));self.city_permit_select.setCurrentIndex(self.city_permit_select.findData(rid))
  if action=='limits':return self.city_limits_screen(values,draft['id'])
  if action=='revision':return self.city_revision_screen(values,draft['id'])
  if action=='row':
   # Reuse row editor with a recovered ID even if its current filter hides it.
   values=dict(values,id=draft['row_id']) if draft['row_id'] else values
   return self.edit_city_row(extra['city_name'],False,values,draft['id'])
  if action=='discipline':
   row=dict(values,id=draft['row_id']) if draft['row_id'] else values
   return self.city_form('Recover discipline review',['discipline','status','contact_id','due_date','response_date','notes','source_id','last_verified_date','if_applicable','verify_label'],row,'reg_cycle_reviews',lambda v:self.store.save('reg_cycle_reviews',dict(v,cycle_id=extra['cycle_id']),draft['row_id']),extra=extra,key=draft['id'])
