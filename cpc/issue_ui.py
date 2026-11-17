"""Corrections and violations workspaces scoped to project/address."""
from datetime import date
from pathlib import Path
from PySide6.QtCore import QUrl,Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QFileDialog,QMessageBox,QAbstractItemView
from .table import DataTable
from .issues import ISSUE_STATUSES,ISSUE_FORM_FIELDS,CLOSED_ISSUE_STATUSES

ISSUE_PAGES={'Corrections':'Correction','Violations':'Violation'}

class IssueUI:
 def build_page(self,title):
  if title not in ISSUE_PAGES:
   super().build_page(title)
   if title=='Projects':
    page=self.stack.widget(self.stack.count()-1);bar=QHBoxLayout();page.layout().addLayout(bar)
    self.button(bar,'View corrections',lambda:self.show_project_issues('Corrections'));self.button(bar,'View violations',lambda:self.show_project_issues('Violations'))
   return
  page=QWidget();layout=QVBoxLayout(page);heading=QLabel('Project '+title);heading.setObjectName('heading');layout.addWidget(heading)
  hint=QLabel('Record the address, exact spot, required fix, responsible person and deadline. Use Resolved when corrected, and Closed after any required verification. These statuses are maintained by you.');hint.setWordWrap(True);layout.addWidget(hint)
  if not hasattr(self,'issue_summary_labels'):self.issue_summary_labels={}
  summary=QLabel();summary.setTextFormat(Qt.PlainText);summary.setWordWrap(True);layout.addWidget(summary);self.issue_summary_labels[title]=summary
  bar=QHBoxLayout();layout.addLayout(bar);self.button(bar,'+ Add '+ISSUE_PAGES[title].lower(),lambda _,t=title:self.edit(t));self.button(bar,'Edit selected',lambda _,t=title:self.edit(t,True));self.button(bar,'Attach notice / photo',lambda _,t=title:self.attach_issue_file(t));self.button(bar,'Open evidence',lambda _,t=title:self.open_issue_file(t))
  entry=QLineEdit();entry.setPlaceholderText('Filter by address, location, required fix, inspector, code or status…');entry.textChanged.connect(self.refresh);setattr(self,'filter_'+title,entry);layout.addWidget(entry)
  table=DataTable();table.setAlternatingRowColors(True);table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.doubleClicked.connect(lambda _,t=title:self.edit(t,True));layout.addWidget(table);self.tables[title]=table;self.stack.addWidget(page)
 def choices(self,table):
  choices=super().choices(table)
  if table=='issues':
   choices['status']=ISSUE_STATUSES;choices['issue_type']=['Correction','Violation']
   choices['permit_id']=[('No related permit',None)]+[(r['title'],r['id']) for r in self.store.all('registers') if r['record_type']=='Permit']
  return choices
 def refresh(self,*args):
  super().refresh(*args)
  pid=self.project_filter.currentData();extra=[];active={p['id'] for p in self.store.all('projects') if not p['archived']}
  for title,kind in ISSUE_PAGES.items():
   self.fill(title,self.store.issue_rows(kind))
   visible=self.data[title];open_count=sum(row['status'] not in CLOSED_ISSUE_STATUSES for row in visible)
   address='All project addresses'
   if pid:
    project=self.store.rows('SELECT address FROM projects WHERE id=?',(pid,))[0];address='Project address: '+(project['address'] or '(add an address in Projects → Edit)')
   self.issue_summary_labels[title].setText(f'{address} · {open_count} unresolved / {len(visible)} listed')
  for row in self.store.issue_rows():
   if row['project_id'] not in active or row['status'] in CLOSED_ISSUE_STATUSES:continue
   extra.append(dict(_source_table='issues',_source_id=row['id'],kind=row['issue_type'],project_id=row['project_id'],project=row['project'],item=row['title']+' — '+row['required_fix'],deadline=row['deadline'],status=row['status'],responsible=row['responsible']))
  self.fill('Dashboard',sorted(self.data.get('Dashboard',[])+extra,key=lambda row:row['deadline'] or '9999'))
  timeline=self.data.get('Timeline',[])
  for row in extra:timeline.append(dict(_source_table='issues',_source_id=row['_source_id'],id=None,project_id=row['project_id'],title=row['item'],phase='',deadline=row['deadline'],status=row['status'],project=row['project'],kind=row['kind']))
  self.fill('Timeline',sorted(timeline,key=lambda row:row['deadline'] or '9999'))
 def edit(self,title,existing=False):
  if title not in ISSUE_PAGES:return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'):raise ValueError('Create a project first and enter its address')
   row=self.selected(title) if existing else dict(project_id=self.project_filter.currentData(),issue_type=ISSUE_PAGES[title],status='Open',priority='Normal',reported_date=date.today().isoformat())
   choices=self.choices('issues');choices['issue_type']=[ISSUE_PAGES[title]]
   form=Form(self,('Edit ' if existing else 'Add ')+ISSUE_PAGES[title].lower(),ISSUE_FORM_FIELDS,row,choices)
   initial=self.store.rows('SELECT address FROM projects WHERE id=?',(form.inputs['project_id'].currentData(),))
   prior_address=[initial[0]['address'] if initial else '']
   def sync_project(*args):
    project_id=form.inputs['project_id'].currentData();projects=self.store.rows('SELECT address FROM projects WHERE id=?',(project_id,));new=projects[0]['address'] if projects else ''
    address=form.inputs['site_address']
    if not address.text().strip() or address.text()==prior_address[0]:address.setText(new)
    prior_address[0]=new
    permits=form.inputs['permit_id'];selected=permits.currentData();permits.clear();permits.addItem('No related permit',None)
    for p in self.store.rows("SELECT id,title FROM registers WHERE project_id=? AND record_type='Permit'",(project_id,)):permits.addItem(p['title'],p['id'])
    index=permits.findData(selected);permits.setCurrentIndex(max(0,index))
   sync_project();form.inputs['project_id'].currentIndexChanged.connect(sync_project)
   form.persist=lambda values:self.store.save('issues',values,row['id'] if existing else None);form.enable_draft('issues',row['id'] if existing else None)
   if form.exec():self.refresh()
  self.guard(action)
 def show_project_issues(self,title):
  def action():
   project=self.selected('Projects');self.project_filter.setCurrentIndex(self.project_filter.findData(project['id']));self.nav.setCurrentRow(self.navigation.index(title))
  self.guard(action)
 def attach_issue_file(self,title):
  def action():
   row=self.selected(title);path,_=QFileDialog.getOpenFileName(self,'Attach correction / violation notice or photo')
   if path:self.store.attach_issue(row['id'],path);self.refresh()
  self.guard(action)
 def open_issue_file(self,title):
  def action():
   path=self.selected(title)['attachment_path']
   if not path or not Path(path).is_file():raise ValueError('Attach a notice, photo or other evidence first')
   if QMessageBox.question(self,'Open evidence?','Open this file with its Windows application?\n'+path,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):raise ValueError('Windows could not open this file')
  self.guard(action)
