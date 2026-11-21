"""Progressive disclosure of project-specific coordination information."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QCheckBox,QButtonGroup,QDialog,QDialogButtonBox,QScrollArea,QAbstractItemView,QMessageBox
from .scope import SCOPE_FIELDS,USES,ANSWERS,CATEGORIES,ENERGY,SCOPE_STATUS,SYSTEM_TYPES,PROTECTED_SECTIONS
from .table import DataTable

PAGES={'Project Profile':'project_profiles','Scope & Systems':'scope_items','Custom Information':'custom_fields','Rebates & Incentives':'rebates','Change Orders':'contract_changes'}

class AnswerChecks(QWidget):
 changed=Signal()
 def __init__(self,value='Undecided'):
  super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);self.group=QButtonGroup(self);self.group.setExclusive(True);self.boxes={}
  for answer in ANSWERS:
   box=QCheckBox(answer);self.group.addButton(box);layout.addWidget(box);self.boxes[answer]=box;box.toggled.connect(lambda checked:self.changed.emit() if checked else None)
  self.boxes[value if value in ANSWERS else 'Undecided'].setChecked(True)
 def value(self):return next((key for key,box in self.boxes.items() if box.isChecked()),'Undecided')

class ScopeUI:
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  toolbar=self.addToolBar('Project view');toolbar.setMovable(False)
  toolbar.addAction('Customize project sections',self.customize_sections)
  toolbar.addAction('Show all project sections',self.show_all_sections)
 def build_page(self,title):
  if title in PAGES:
   page=QWidget();layout=QVBoxLayout(page);heading=QLabel(title);heading.setObjectName('heading');layout.addWidget(heading)
   hints={
    'Project Profile':'Residential, commercial or mixed use; key Yes/No decisions start Undecided. Record occupancy and site assumptions, then track detailed systems separately.',
    'Scope & Systems':'Coordinate stairs, trusses, elevators, kitchens, energy systems and other scope. Optional starter prompts are not a complete code checklist; verify requirements with your professionals and jurisdiction.',
    'Custom Information':'Add project-wide or system-specific fields with a type, value, unit and required flag. Blank required fields remain visible as missing.',
    'Rebates & Incentives':'Track provider links, eligibility, required documents, deadlines and estimated/approved/received amounts. These records do not reduce budgets automatically.',
    'Change Orders':'Project-wide view of contract change orders. Only Approved changes adjust the related contract commitment. Attach supporting estimates, agreements and approvals.',
   }
   hint=QLabel(hints[title]);hint.setWordWrap(True);layout.addWidget(hint);bar=QHBoxLayout();layout.addLayout(bar)
   self.button(bar,'+ New',lambda _,t=title:self.edit(t));self.button(bar,'Edit selected',lambda _,t=title:self.edit(t,True))
   if title=='Scope & Systems':
    self.button(bar,'Add standard prompts',self.add_scope_prompts);self.button(bar,'Add custom field',self.add_system_field);self.button(bar,'Hide / show selected items',self.toggle_scope_items)
    filters=QHBoxLayout();layout.addLayout(filters);self.scope_category=QComboBox();self.scope_category.addItems(['All categories',*CATEGORIES]);self.scope_category.currentTextChanged.connect(self.refresh);filters.addWidget(self.scope_category)
    self.show_hidden_scope=QCheckBox('Include hidden items');self.show_hidden_scope.toggled.connect(self.refresh);filters.addWidget(self.show_hidden_scope)
   if title=='Rebates & Incentives':
    self.button(bar,'Open requirements link',lambda:self.open_rebate_link('requirements_url'));self.button(bar,'Open application link',lambda:self.open_rebate_link('application_url'))
   entry=QLineEdit();entry.setPlaceholderText('Filter records…');entry.textChanged.connect(self.refresh);setattr(self,'filter_'+title,entry);layout.addWidget(entry)
   table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setAlternatingRowColors(True);table.doubleClicked.connect(lambda _,t=title:self.edit(t,True));layout.addWidget(table);self.tables[title]=table;self.stack.addWidget(page)
  else:super().build_page(title)
  # Reuse one versioned file manager throughout project records and department work.
  supported={'Work Orders','Approvals','Projects','Tasks','Communications','Documents','Timeline','Meetings','Bidding','Contracts','Budgets','Receipts','Corrections','Violations',*PAGES}
  from .development_ui import DISCIPLINE_PAGES,REGISTER_PAGES
  if title in supported|set(DISCIPLINE_PAGES)|set(REGISTER_PAGES) and title not in ('Contracts','Budgets'):
   page=self.stack.widget(self.stack.count()-1);bar=QHBoxLayout();page.layout().addLayout(bar);self.button(bar,'Files — add / edit / save copy',lambda _,t=title:self.record_files(t))
   if title=='Projects':self.button(bar,'Project setup',self.open_project_setup)
 def choices(self,table):
  choices=super().choices(table)
  choices.update(use_type=USES,project_type=['Undecided','New Construction','Renovation','Addition','Tenant Improvement','Change of Use','Site Development','Other'],area_unit=['sq ft','sq m'],applicability=ANSWERS,energy_source=ENERGY,system_type=SYSTEM_TYPES,field_type=['Text','Number','Yes / No','Date','URL'],program_type=['Rebate','Tax Credit','Grant','Utility Incentive','Other'],eligibility=ANSWERS)
  if table=='scope_items':choices['category']=CATEGORIES
  choices['scope_item_id']=[('Project-wide / none',None)]+[(s['title']+' — '+s['project'],s['id']) for s in self.store.scope_rows('scope_items')]
  if table=='scope_items':choices['status']=SCOPE_STATUS
  if table=='rebates':choices['status']=['Researching','Preparing','Submitted','Approved','Received','Rejected','Closed']
  return choices
 def edit(self,title,existing=False,initial=None):
  if title not in PAGES:return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'):raise ValueError('Create a project first')
   table=PAGES[title];pid=self.project_filter.currentData();row=self.selected(title) if existing else (dict(initial) if initial is not None else dict(project_id=pid))
   if title=='Project Profile' and not existing and pid:
    prior=self.store.profile(pid)
    if prior:row=prior
   if table=='project_profiles':row.setdefault('title','Project profile')
   fields=SCOPE_FIELDS.get(table)
   if table=='project_profiles':
    settings=self.store.regulatory_settings(row.get('project_id'));row.update(reg_cgp_subject=settings['cgp_subject'],reg_jurisdiction=settings['jurisdiction']);fields=[*fields,'reg_cgp_subject','reg_jurisdiction']
   if fields is None:
    from .finance import FINANCE_FIELDS
    fields=FINANCE_FIELDS[table]
   choices=self.choices(table)
   if table=='project_profiles':
    from .regulatory import JURISDICTIONS
    choices.update(reg_cgp_subject=ANSWERS,reg_jurisdiction=JURISDICTIONS)
   if table=='contract_changes':
    choices['contract_id']=[(c['title']+' — '+c['currency'],c['id']) for c in self.store.all('contracts') if not pid or c['project_id']==pid]
    if not choices['contract_id']:raise ValueError('Create a contract for this project first')
   if table in ('custom_fields','rebates') and pid:
    choices['scope_item_id']=[('Project-wide / none',None)]+[(s['title'],s['id']) for s in self.store.all('scope_items') if s['project_id']==pid]
   form=Form(self,('Edit ' if row.get('id') else 'New ')+title,fields,row,choices)
   # Free-entry choices preserve compatibility while accepting project-specific vocabulary.
   for key in ('category','system_type','unit','program_type','project_type'):
    widget=form.inputs.get(key)
    if isinstance(widget,QComboBox):widget.setEditable(True)
   form.persist=lambda values:self.store.save(table,values,row.get('id'));form.enable_draft(table,row.get('id'))
   if form.exec():self.refresh()
  self.guard(action)
 def refresh(self,*args):
  super().refresh(*args)
  for title,table in PAGES.items():
   rows=self.store.change_rows() if table=='contract_changes' else self.store.scope_rows(table)
   if table=='scope_items':
    category=self.scope_category.currentText();self.scope_category.blockSignals(True);self.scope_category.clear();self.scope_category.addItems(['All categories',*dict.fromkeys(CATEGORIES+[r['category'] for r in rows])]);self.scope_category.setCurrentText(category);self.scope_category.blockSignals(False)
    if not self.show_hidden_scope.isChecked():rows=[r for r in rows if not r['hidden']]
    category=self.scope_category.currentText()
    if category!='All categories':rows=[r for r in rows if r['category']==category]
   self.fill(title,rows)
  names={p['id']:p['name'] for p in self.store.all('projects') if not p['archived']};extra=[]
  for table,label in [('scope_items','System requirement'),('rebates','Rebate deadline')]:
   for row in self.store.scope_rows(table):
    done=row['status'] in ('Completed','Approved','Not Applicable') if table=='scope_items' else row['status'] in ('Received','Rejected','Closed')
    if table=='scope_items' and row['applicability'] in ('No','Not Applicable'):done=True
    if not done and row['deadline'] and row['project_id'] in names:
     extra.append(dict(_source_table=table,_source_id=row['id'],kind=label,project_id=row['project_id'],project=names[row['project_id']],item=row['title'],deadline=row['deadline'],status=row['status'],responsible=row['responsible']))
  self.fill('Dashboard',sorted(self.data.get('Dashboard',[])+extra,key=lambda r:r['deadline'] or '9999'))
  timeline=self.data.get('Timeline',[])+[dict(r,id=None,title=r['item'],phase='') for r in extra];self.fill('Timeline',sorted(timeline,key=lambda r:r['deadline'] or '9999'))
  self.apply_section_visibility()
 def selected_project_id(self):
  pid=self.project_filter.currentData()
  if not pid:raise ValueError('Select a project in the Project workspace dropdown first')
  return pid
 def customize_sections(self):
  def action():
   pid=self.project_filter.currentData();dlg=QDialog(self);dlg.setWindowTitle('Visible sections — '+self.project_filter.currentText());dlg.resize(580,700);layout=QVBoxLayout(dlg);hint=QLabel('Checked sections appear in this project. Hiding preserves records, files, deadlines and reports. The All projects view has a separate preference. Hidden sections always remains available.');hint.setWordWrap(True);layout.addWidget(hint)
   scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();boxes_layout=QVBoxLayout(body);scroll.setWidget(body);layout.addWidget(scroll);hidden=self.navigation_hidden();boxes={}
   for title in self.navigation:
    box=QCheckBox('Plans & CAD' if title=='Documents' else title);box.setChecked(title not in hidden);box.setEnabled(title not in PROTECTED_SECTIONS);boxes_layout.addWidget(box);boxes[title]=box
   bar=QHBoxLayout();layout.addLayout(bar)
   minimal=PROTECTED_SECTIONS|{'Dashboard','Projects','Search','Backup & Restore','Recovery & Data','Project Profile','Scope & Systems','Tasks','Documents','Permits','Contracts','Budgets','Timeline'}
   self.button(bar,'Minimal view',lambda:[box.setChecked(title in minimal) for title,box in boxes.items()]);self.button(bar,'Show all',lambda:[box.setChecked(True) for box in boxes.values()])
   buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);layout.addWidget(buttons);buttons.accepted.connect(dlg.accept);buttons.rejected.connect(dlg.reject)
   if dlg.exec():self.save_navigation_hidden([title for title,box in boxes.items() if not box.isChecked()]);self.refresh()
  self.guard(action)
 def add_scope_prompts(self):
  def action():
   pid=self.selected_project_id()
   if QMessageBox.question(self,'Add optional standard prompts?','Add missing coordination prompts for rooms, structure, stairs, elevators, utilities, energy, accessibility and closeout? All begin Undecided. Existing records are preserved; this is not a complete regulatory checklist.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
   count=self.store.add_scope_starters(pid);self.refresh();self.statusBar().showMessage(f'Added {count} optional scope prompts.',8000)
  self.guard(action)
 def toggle_scope_items(self):
  def action():
   indexes=self.tables['Scope & Systems'].selected_record_rows()
   if not indexes:raise ValueError('Select at least one system')
   rows=[self.data['Scope & Systems'][i] for i in indexes];hidden=not all(r['hidden'] for r in rows)
   for row in rows:self.store.save('scope_items',{'hidden':int(hidden)},row['id'])
   self.refresh()
  self.guard(action)
 def add_system_field(self):
  def action():
   row=self.selected('Scope & Systems');self.edit('Custom Information',initial=dict(project_id=row['project_id'],scope_item_id=row['id']))
  self.guard(action)
 def open_rebate_link(self,key):
  def action():
   from PySide6.QtCore import QUrl
   from PySide6.QtGui import QDesktopServices
   row=self.selected('Rebates & Incentives');url=row[key]
   if not url:raise ValueError('Add a program website link first')
   self.store.scope_url(url)
   if QMessageBox.question(self,'Open program website?',url,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
    if not QDesktopServices.openUrl(QUrl(url)):raise ValueError('Windows could not open the website')
  self.guard(action)
 def record_files(self,title):
  def action():
   record=self.selected(title);table,rid=self.source_target(title,record)
   saved=self.store.attachment_parent(table,rid);self.finance_file_manager(title,table,saved)
  self.guard(action)
 def open_project_setup(self):
  def action():
   project=self.selected('Projects');self.project_filter.setCurrentIndex(self.project_filter.findData(project['id']));self.navigate('Project Profile');self.edit('Project Profile')
  self.guard(action)
