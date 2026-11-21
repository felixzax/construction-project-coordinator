"""Optional shared tracker. Later-phase tabs deliberately contain no agency text."""
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTabWidget,QTextBrowser,QLineEdit,QAbstractItemView,QMessageBox
from .table import DataTable
from .regulatory import REG_SECTION,DISCLAIMER,PRIVACY_NOTE,JURISDICTIONS,ROLES,REQUEST_STATUSES,INSPECTION_KINDS
from .regulatory_schema import REG_FIELDS

EDIT_FIELDS={
 'Roles':['project_id','contact_id','role','delegate_for_role','eauthorization_status','eauthorization_date','notes'],
 'Document Requests':['project_id','title','register_id','filing_id','requested_from_contact_id','needed_by','status','notes','source_id','last_verified_date','if_applicable','verify_label'],
 'Inspections':['register_id','inspection_kind','inspection_date','jurisdiction','result','qualifying_event','findings','corrective_action','correction_id','source_id','last_verified_date','if_applicable','verify_label','notes'],
 'References':REG_FIELDS['reg_sources'],
}
TABLES={'Roles':'reg_project_roles','Document Requests':'reg_document_requests','Inspections':'reg_inspection_details','References':'reg_sources'}

class RegulatoryUI:
 def navigation_hidden(self):
  hidden=super().navigation_hidden();pid=self.project_filter.currentData()
  visible=bool(self.store.regulatory_settings(pid)['sidebar_visible']) if pid else self.appearance_settings.value('regulatory/all_projects_visible',False,type=bool)
  if not visible:hidden.add(REG_SECTION)
  return hidden
 def save_navigation_hidden(self,sections):
  pid=self.project_filter.currentData();visible=int(REG_SECTION not in sections)
  if pid:
   if self.store.regulatory_settings(pid)['sidebar_visible']!=visible:self.store.set_regulatory_settings(pid,sidebar_visible=visible)
  else:self.appearance_settings.setValue('regulatory/all_projects_visible',bool(visible))
  super().save_navigation_hidden(sections)
 def build_page(self,title):
  if title!=REG_SECTION:return super().build_page(title)
  page=QWidget();layout=QVBoxLayout(page);heading=QLabel(title);heading.setObjectName('heading');layout.addWidget(heading)
  for text in (DISCLAIMER,'Never store passwords, security-question answers, portal logins, digital signature/certificate files or eAuthorization secrets. eAuthorization: flag and date only.',PRIVACY_NOTE):
   label=QLabel(text);label.setWordWrap(True);layout.addWidget(label)
  self.reg_tabs=QTabWidget();layout.addWidget(self.reg_tabs);self.reg_tables={};self.reg_rows={};self.reg_filters={}
  self.reg_overview=QTextBrowser();self.reg_tabs.addTab(self.reg_overview,'Overview')
  for name in ('City & County','Water Board','Roles','Document Requests','Inspections','Reports','References'):
   tab=QWidget();column=QVBoxLayout(tab);self.reg_tabs.addTab(tab,name.replace('&','&&'))
   if name not in TABLES:
    text={'City & County':'Permit templates and checkers are reserved for Phase 3. Existing permit records remain in Permits.','Water Board':'Site and filing workflows are reserved for Phase 4. Set the CGP choice in Project Profile; no requirements have been added.','Reports':'Compliance CSV/DOCX and project report integration are reserved for Phase 5. Existing exports remain available.'}[name]
    note=QLabel(text);note.setWordWrap(True);column.addWidget(note);column.addStretch();continue
   bar=QHBoxLayout();column.addLayout(bar)
   if name=='Inspections':
    self.button(bar,'New inspection',lambda:self.edit('Inspections'))
    self.button(bar,'Edit result / details',lambda:self.edit_regulatory('Inspections',True))
   else:
    self.button(bar,'New',lambda _,n=name:self.edit_regulatory(n))
    self.button(bar,'Edit',lambda _,n=name:self.edit_regulatory(n,True))
   self.button(bar,'Delete',lambda _,n=name:self.delete_regulatory(n))
   if name in ('Document Requests','Inspections'):self.button(bar,'Files',lambda _,n=name:self.regulatory_files(n))
   if name=='References':self.button(bar,'Open source link',self.open_regulatory_source)
   if name=='Roles':
    hint=QLabel('One contact may hold several roles. eAuthorization stores only Unknown / Yes / No and a date. Do not attach an authorization form.');hint.setWordWrap(True);column.addWidget(hint)
   if name=='Inspections':
    hint=QLabel('New inspection uses the existing Inspections register. Select it here to add result details; inspector, deadline and register status are edited in Inspections. Photos use that same record’s Files.');hint.setWordWrap(True);column.addWidget(hint)
   entry=QLineEdit();entry.setPlaceholderText('Filter…');entry.textChanged.connect(self.refresh_regulatory);column.addWidget(entry);self.reg_filters[name]=entry
   table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setAlternatingRowColors(True);table.doubleClicked.connect(lambda _,n=name:self.edit_regulatory(n,True));table.delete_selected=lambda n=name:self.delete_regulatory(n);table.delete_listed=lambda n=name:self.delete_regulatory(n,True);column.addWidget(table);self.reg_tables[name]=table
  self.stack.addWidget(page)
 def refresh(self,*args):
  super().refresh(*args)
  if hasattr(self,'reg_tables'):self.refresh_regulatory()
 def refresh_regulatory(self,*args):
  pid=self.project_filter.currentData()
  if not pid:
   self.reg_overview.setPlainText('Select a project in Project workspace to view its coordination overview. References are global.');data={n:[] for n in TABLES}
  else:
   overview=self.store.regulatory_overview(pid)
   lines=[DISCLAIMER,'',f"Inspections: {overview['passed_inspections']} passed; {overview['open_inspections']} open",'Days since last performed weekly stormwater inspection: '+str(overview['days_since_weekly'] if overview['days_since_weekly'] is not None else 'No recorded inspection'),f"Open document requests: {len(overview['open_document_requests'])}",f"Open corrections: {len(overview['open_corrections'])}",'','Permit stages (separate jurisdictions):']
   lines += [f"{r['title']} | {r['jurisdiction_key'] or r['jurisdiction_name'] or r['jurisdiction_type']} | {r['stage'] or r['status']}" for r in overview['permits']]
   lines += ['','Water Board: '+('; '.join(r['wdid']+' '+r['status'] for r in overview['water_board']) or 'No site record; workflow deferred to Phase 4'),'','Outstanding deadlines:']
   lines += [f"{r['deadline']} | {r['title']} | {r['status']}"+(' | OVERDUE' if r['overdue'] else '') for r in overview['upcoming']]
   lines += ['','Waiting on Agency (never overdue):']+[r['title'] for r in overview['waiting_on_agency']]
   self.reg_overview.setPlainText('\n'.join(lines))
   data={'Roles':self.store.rows('SELECT r.*,c.name AS contact FROM reg_project_roles r LEFT JOIN contacts c ON c.id=r.contact_id WHERE project_id=?',(pid,)),'Document Requests':self.store.regulatory_requests(pid),'Inspections':self.store.regulatory_inspections(pid)}
  data['References']=self.store.all('reg_sources')
  for name,table in self.reg_tables.items():
   query=self.reg_filters[name].text().casefold();rows=[r for r in data.get(name,[]) if query in ' '.join(str(v or '') for v in r.values()).casefold()];self.reg_rows[name]=rows
   self.render_recovery_table(table,[{k:v for k,v in r.items() if k not in ('id','project_id','detail_id')} for r in rows])
 def selected_regulatory(self,name):
  i=self.reg_tables[name].currentRow()
  if i<0:raise ValueError('Select a record')
  return self.reg_rows[name][i]
 def regulatory_choices(self,pid):
  contacts=[('Unassigned',None)]+[(c['name'],c['id']) for c in self.store.all('contacts')]
  permits=[('No permit',None)]+[(r['title'],r['id']) for r in self.store.all('registers') if r['project_id']==pid and r['record_type']=='Permit']
  return dict(project_id=[(p['name'],p['id']) for p in self.store.all('projects') if p['id']==pid],contact_id=contacts,requested_from_contact_id=contacts,role=ROLES,eauthorization_status=['Unknown','Yes','No'],register_id=permits,filing_id=[('No filing',None)]+[(r['reference'] or r['filing_type'],r['id']) for r in self.store.all('reg_filings') if r['project_id']==pid],status=REQUEST_STATUSES,jurisdiction=JURISDICTIONS,inspection_kind=INSPECTION_KINDS,result=['','Pass','Fail','Correction','Partial','Cancelled'],qualifying_event=['Undecided','Yes','No','Not Applicable'],corrective_action=['Undecided','Yes','No','Not Applicable'],correction_id=[('No correction',None)]+[(r['title'],r['id']) for r in self.store.all('issues') if r['project_id']==pid and r['issue_type']=='Correction'],source_id=[('No source / verify',None)]+[(r['title'],r['id']) for r in self.store.all('reg_sources')],verification_status=['Verify','Verified','Conflict'],verify_label=['Verify','Verified'])
 def edit_regulatory(self,name,existing=False):
  from .ui import Form
  def action():
   pid=self.selected_project_id() if name!='References' else None
   row=self.selected_regulatory(name).copy() if existing else dict(project_id=pid)
   choices=self.regulatory_choices(pid)
   if name=='Inspections':
    row['register_id']=row.pop('id');row['id']=row.pop('detail_id',None)
    choices['register_id']=[(row['title'],row['register_id'])]
   form=Form(self,name,EDIT_FIELDS[name],row,choices)
   form.persist=lambda values:self.store.save(TABLES[name],values,row.get('id'))
   form.enable_draft(TABLES[name],row.get('id'))
   if form.exec():self.refresh()
  self.guard(action)
 def delete_regulatory(self,name,all_listed=False):
  def action():
   indexes=range(len(self.reg_rows[name])) if all_listed else self.reg_tables[name].selected_record_rows()
   targets=[('registers' if name=='Inspections' else TABLES[name],self.reg_rows[name][i]['id']) for i in indexes]
   if not targets:raise ValueError('Select a record')
   if self.confirm_delete(targets,name):self.refresh()
  self.guard(action)
 def regulatory_files(self,name):
  def action():
   row=self.selected_regulatory(name);table='registers' if name=='Inspections' else TABLES[name]
   self.finance_file_manager(name,table,row)
  self.guard(action)
 def open_regulatory_source(self):
  def action():
   from .permits import validate_url
   url=self.selected_regulatory('References')['url'];validate_url(url)
   if not url:raise ValueError('Add a source URL first')
   if QMessageBox.question(self,'Open external source?',url+'\n\nOpen in your browser? No data is submitted by this app.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:QDesktopServices.openUrl(QUrl(url))
  self.guard(action)
