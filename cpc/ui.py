import os
import sys
from datetime import date, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtGui import QColor, QTextDocument
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QStackedWidget,QTableWidget,QTableWidgetItem,QHeaderView,QLineEdit,QDialog,QDialogButtonBox,QFormLayout,QComboBox,QTextEdit,QFileDialog,QMessageBox,QCheckBox,QAbstractItemView,QScrollArea)
from PySide6.QtPrintSupport import QPrinter,QPrintPreviewDialog
from .store import Store, FIELDS, TASK_STATUSES
from .permit_ui import PermitUI
from .development_ui import DevelopmentUI, NAVIGATION, EXTRA_OPTIONS
from .development import line_totals

VERSION='1.2.0'
OPTIONS={'phase':['Planning','Design','Permitting','Construction','Inspection','Closeout'],'priority':['Low','Normal','High','Urgent'],'category':['Architectural Plans','Engineering Drawings','Permit','Cut Sheet','Estimate','Approval','CAD File','BIM Model','Site Plan','Survey','Specification','Shop Drawing','As-Built','Other'],'role':['Architect','Engineer','Contractor','City Official','County Official','Business Owner','Electrical Engineer','Plumbing Engineer','Mechanical Engineer','Civil Engineer','Structural Engineer','Surveyor','Estimator','Supplier','Developer','Other']}
class Form(QDialog):
 def __init__(self,parent,title,fields,record=None,choices=None):
  super().__init__(parent); self.setWindowTitle(title); self.resize(670,720); self.inputs={}; self.persist=None; layout=QVBoxLayout(self)
  scroll=QScrollArea(); scroll.setWidgetResizable(True); body=QWidget(); form=QFormLayout(body); scroll.setWidget(body); layout.addWidget(scroll)
  for key in fields:
   value=(record or {}).get(key,''); opts=(choices or {}).get(key,OPTIONS.get(key))
   if opts is not None:
    widget=QComboBox()
    for item in opts:
     label,val=item if isinstance(item,tuple) else (item,item)
     widget.addItem(str(label),val)
    ix=widget.findData(value)
    if ix>=0: widget.setCurrentIndex(ix)
    elif value not in ('',None): widget.addItem(str(value),value); widget.setCurrentIndex(widget.count()-1)
   elif key in ('archived','included','completed','requirements_reviewed'): widget=QCheckBox(); widget.setChecked(bool(value))
   elif key in ('notes','description','summary','requirements','scope','attendees','agenda','minutes','decisions','response','exclusions','schedule_notes'):
    widget=QTextEdit(); widget.setPlainText(str(value or '')); widget.setMaximumHeight(110)
   else:
    widget=QLineEdit(str(value or ''))
    if key in ('deadline','follow_up','occurred','submitted','received','valid_until','meeting_date'): widget.setPlaceholderText('YYYY-MM-DD (blank allowed except required dates)')
   labels={'project_id':'Project','contact_id':'Responsible contact / bidder','designer_id':'Designer / consultant','meeting_id':'Related meeting','package_id':'Trade bid package','bid_id':'Bid estimate','labor_rate':'Labor hourly rate','material_unit_cost':'Material cost per unit','equipment_unit_cost':'Equipment cost per unit','subcontract_unit_cost':'Subcontract cost per unit','other_cost':'Other fixed cost','included':'Include in bid total','register_id':'Permit application','jurisdiction_name':'City / county name','requirements_url':'Application requirements link','application_url':'Application / portal link','requirements_reviewed':'Requirements page reviewed','source_url':'Requirement source link','completed':'Requirement ready','building_area':'Building / floor / area','tax_percent':'Material tax (%)','markup_percent':'Markup (%)','contingency_percent':'Contingency (%)','waste_percent':'Material waste (%)'}
   self.inputs[key]=widget; form.addRow(labels.get(key,key.replace('_',' ').title()),widget)
   if key=='file_path':
    browse=QPushButton('Choose document file…'); browse.clicked.connect(lambda _,w=widget:self.browse(w)); form.addRow('',browse)
  if 'material_unit_cost' in fields:
   self.preview=QLabel(); self.preview.setWordWrap(True); layout.addWidget(self.preview)
   for widget in self.inputs.values():
    if isinstance(widget,QLineEdit): widget.textChanged.connect(self.update_cost_preview)
    elif isinstance(widget,QComboBox): widget.currentIndexChanged.connect(self.update_cost_preview)
    elif isinstance(widget,QCheckBox): widget.toggled.connect(self.update_cost_preview)
   self.update_cost_preview()
  buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
 def accept(self):
  if self.persist is not None:
   try: self.persist(self.values())
   except Exception as ex:
    QMessageBox.warning(self,'Please review this entry',str(ex)); return
  super().accept()
 def update_cost_preview(self,*args):
  try:
   result=line_totals(self.values()); self.preview.setText('Preview: '+ ' | '.join(f'{k.replace("_"," ")}: {v}' for k,v in result.items()))
  except ValueError as ex: self.preview.setText(str(ex))
 def browse(self,widget):
  path,_=QFileDialog.getOpenFileName(self,'Document file')
  if path: widget.setText(path)
 def values(self):
  return {k:(w.currentData() if isinstance(w,QComboBox) else int(w.isChecked()) if isinstance(w,QCheckBox) else w.toPlainText() if isinstance(w,QTextEdit) else w.text().strip()) for k,w in self.inputs.items()}

class BaseWindow(QMainWindow):
 def __init__(self,store):
  super().__init__(); self.store=store; self.setWindowTitle(f'Construction Project Coordinator · {VERSION}'); self.resize(1280,800); self.tables={}; self.data={}; self.current='Dashboard'
  root=QWidget(); self.setCentralWidget(root); outer=QHBoxLayout(root)
  self.nav=QListWidget(); self.nav.setFixedWidth(210); self.nav.addItems(NAVIGATION); self.nav.item(NAVIGATION.index('Documents')).setText('Plans & CAD'); outer.addWidget(self.nav)
  content=QWidget(); column=QVBoxLayout(content); outer.addWidget(content,1)
  project_bar=QHBoxLayout(); project_bar.addWidget(QLabel('Project workspace:')); self.project_filter=QComboBox(); self.project_filter.addItem('All projects',None); self.project_filter.setMinimumWidth(300); project_bar.addWidget(self.project_filter); project_bar.addStretch(); column.addLayout(project_bar)
  self.stack=QStackedWidget(); column.addWidget(self.stack,1)
  for title in NAVIGATION: self.build_page(title)
  self.nav.currentRowChanged.connect(self.change_page); self.nav.setCurrentRow(0); self.refresh()
  self.project_filter.currentIndexChanged.connect(self.refresh)
  self.statusBar().showMessage(f'Local data: {store.path} · Version {VERSION}')
 def button(self,layout,label,fn):
  b=QPushButton(label); b.clicked.connect(fn); layout.addWidget(b); return b
 def build_page(self,title):
  page=QWidget(); layout=QVBoxLayout(page); heading=QLabel('Plans, CAD & Documents' if title=='Documents' else title); heading.setObjectName('heading'); layout.addWidget(heading); bar=QHBoxLayout(); layout.addLayout(bar)
  if title in ['Projects','Tasks','Contacts','Communications','Documents','Timeline']:
   self.button(bar,'+ New',lambda _,t=title:self.edit(t)); self.button(bar,'Edit selected',lambda _,t=title:self.edit(t,True))
  if title=='Projects':
   self.button(bar,'Archive / Unarchive',self.archive); self.button(bar,'Link contact',self.link_contact); self.button(bar,'Activity',self.activity); self.button(bar,'Print report',self.print_report); self.button(bar,'Export CSV',lambda:self.export('projects'))
  if title=='Tasks': self.button(bar,'Export outstanding CSV',lambda:self.export('tasks'))
  if title=='Communications': self.button(bar,'Copy email draft',self.email_draft)
  if title=='Documents':
   self.button(bar,'Add revision',self.revision); self.button(bar,'Version history',self.history); self.button(bar,'Open latest file',self.open_file)
  if title=='Search':
   self.search_input=QLineEdit(); self.search_input.setPlaceholderText('Search projects, contacts, tasks, documents and revision requirements'); bar.addWidget(self.search_input); self.search_input.textChanged.connect(self.refresh)
  if title=='Backup & Restore':
   layout.addWidget(QLabel('Backups contain all local records. The documents folder must be backed up separately.\nRestore replaces current records and first creates a safety copy beside the database.'))
   self.button(bar,'Back up database',self.backup); self.button(bar,'Restore database',self.restore); layout.addStretch()
  else:
   if title not in ('Dashboard','Search'):
    entry=QLineEdit(); entry.setPlaceholderText('Filter this list…'); entry.textChanged.connect(self.refresh); setattr(self,'filter_'+title,entry); layout.addWidget(entry)
   if title=='Dashboard': self.dashboard_summary=QLabel(); layout.addWidget(self.dashboard_summary)
   table=QTableWidget(); table.setSelectionBehavior(QAbstractItemView.SelectRows); table.setSelectionMode(QAbstractItemView.SingleSelection); table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); table.horizontalHeader().setStretchLastSection(True); table.setAlternatingRowColors(True); table.setWordWrap(False); layout.addWidget(table); self.tables[title]=table
   if title in ['Projects','Tasks','Contacts','Communications','Documents','Timeline']: table.doubleClicked.connect(lambda _,t=title:self.edit(t,True))
  self.stack.addWidget(page)
 def change_page(self,index): self.stack.setCurrentIndex(index); self.current=self.nav.item(index).text(); self.refresh()
 def fill(self,title,rows):
  query=getattr(self,'filter_'+title,None)
  if query and query.text(): rows=[r for r in rows if query.text().lower() in ' '.join(str(v) for v in r.values()).lower()]
  self.data[title]=rows; table=self.tables[title]; keys=[k for k in rows[0] if k!='id' and not k.startswith('_') and not k.endswith('_id')] if rows else []
  preferred=['title','name','label','project','bidder','currency','total','status','discipline','building_area','deadline','responsible']
  if title=='Permits': preferred=['title','project','jurisdiction_type','jurisdiction_name','department','status','checklist_progress','requirements_reviewed','requirements_url','application_url','reference','responsible','deadline']
  keys=[k for k in preferred if k in keys]+[k for k in keys if k not in preferred]
  table.setColumnCount(len(keys)); table.setRowCount(len(rows)); table.setHorizontalHeaderLabels([k.replace('_',' ').title() for k in keys])
  for i,r in enumerate(rows):
   overdue=bool(r.get('deadline') and r['deadline']<date.today().isoformat() and r.get('status') not in ('Completed','Approved'))
   for j,key in enumerate(keys):
    value=('✓ Reviewed' if r[key] else 'Not reviewed') if key=='requirements_reviewed' else (r[key] if r[key] is not None else '')
    item=QTableWidgetItem(str(value)); table.setItem(i,j,item)
    if overdue: item.setBackground(QColor('#fde3df')); item.setForeground(QColor('#9b2525'))
  table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive); table.resizeColumnsToContents()
  for j in range(len(keys)): table.setColumnWidth(j,min(320,max(80,table.columnWidth(j))))
 def refresh(self,*args):
  s=self.store; projects=s.all('projects'); contacts=s.all('contacts'); names={p['id']:p['name'] for p in projects}; people={p['id']:p['name'] for p in contacts}
  self.fill('Projects',projects); self.fill('Contacts',contacts)
  for title,table in [('Tasks','tasks'),('Communications','communications'),('Documents','documents'),('Timeline','milestones')]:
   rows=s.all(table)
   for r in rows:
    r['project']=names.get(r['project_id'],'')
    if 'contact_id' in r: r['responsible']=people.get(r['contact_id'],'')
    if table=='documents':
     versions=s.versions(r['id']); latest=versions[0] if versions else {}; r.update(revision=latest.get('revision',''),approval=latest.get('status',''),requirements=latest.get('requirements',''),review_resubmission='YES' if latest.get('resubmission') else '')
   if title=='Timeline':
    rows=sorted(rows,key=lambda r:r['deadline'] or '9999')
    for t in s.all('tasks'): rows.append(dict(id=t['id'],project_id=t['project_id'],title='Task: '+t['title'],phase=names.get(t['project_id'],''),deadline=t['deadline'],status=t['status'],project=names.get(t['project_id'],''),kind='Task'))
    rows=[dict(r,kind=r.get('kind','Milestone')) for r in rows]; rows.sort(key=lambda r:r['deadline'] or '9999')
   self.fill(title,rows)
  selected_project=self.project_filter.currentData()
  tasks=s.outstanding(selected_project); today=date.today().isoformat(); upcoming=(date.today()+timedelta(days=7)).isoformat(); overdue=sum(bool(t['deadline'] and t['deadline']<today) for t in tasks)
  follow=s.rows("SELECT c.*,p.name AS project FROM communications c JOIN projects p ON p.id=c.project_id WHERE c.status='Open' AND c.follow_up != '' AND c.follow_up<=? AND p.archived=0",(upcoming,))
  if selected_project: follow=[c for c in follow if c['project_id']==selected_project]
  summary_projects=[p for p in projects if not selected_project or p['id']==selected_project]
  recent=sorted([p for p in summary_projects if not p['archived']],key=lambda p:p['updated'] or '',reverse=True)[:5]
  self.dashboard_summary.setText(f'{sum(not p["archived"] for p in summary_projects)} active projects  ·  {len(tasks)} outstanding tasks  ·  {overdue} overdue  ·  {len(follow)} follow-ups due within 7 days\nRecently updated: '+', '.join(p['name'] for p in recent))
  rows=[dict(kind='Task',project_id=t['project_id'],project=t['project'],item=t['title'],deadline=t['deadline'],status=t['status'],responsible=t['responsible']) for t in tasks]
  rows += [dict(kind='Follow-up',project_id=c['project_id'],project=c['project'],item=c['summary'],deadline=c['follow_up'],status=c['status'],responsible=people.get(c['contact_id'],'')) for c in follow]
  self.fill('Dashboard',sorted(rows,key=lambda r:r['deadline'] or '9999'))
  self.fill('Search',s.search(self.search_input.text()) if self.search_input.text().strip() else [])
 def selected(self,title):
  i=self.tables[title].currentRow()
  if i<0: raise ValueError('Select a row first')
  return self.data[title][i]
 def guard(self,fn):
  try: return fn()
  except Exception as ex: QMessageBox.warning(self,'Unable to complete action',str(ex))
 def choices(self,table):
  choices={'project_id':[(p['name']+(' [Archived]' if p['archived'] else ''),p['id']) for p in self.store.all('projects')],'contact_id':[('Unassigned',None)]+[(c['name'],c['id']) for c in self.store.all('contacts')]}
  choices['status']=TASK_STATUSES if table=='tasks' else ['Active','On Hold','Completed','Cancelled'] if table=='projects' else ['Open','Closed'] if table=='communications' else ['Planned','In Progress','Completed']
  return choices
 def edit(self,title,existing=False):
  def action():
   table={'Projects':'projects','Tasks':'tasks','Contacts':'contacts','Communications':'communications','Documents':'documents','Timeline':'milestones'}[title]
   row=self.selected(title) if existing else {'project_id':self.project_filter.currentData()}
   if title=='Timeline' and row and row.get('kind')=='Task':
    table='tasks'; row=self.store.rows('SELECT * FROM tasks WHERE id=?',(row['id'],))[0]
   if 'project_id' in FIELDS[table] and not self.store.all('projects'): raise ValueError('Create a project first')
   if not existing and table=='communications': row['occurred']=date.today().isoformat()
   form=Form(self,('Edit ' if existing else 'New ')+table,FIELDS[table],row,self.choices(table))
   if form.exec():
    self.store.save(table,form.values(),row['id'] if existing else None); self.refresh()
  self.guard(action)
 def archive(self):
  def action():
   r=self.selected('Projects'); self.store.save('projects',{k:(int(not r['archived']) if k=='archived' else r[k]) for k in FIELDS['projects']},r['id']); self.refresh()
  self.guard(action)
 def link_contact(self):
  def action():
   p=self.selected('Projects'); form=Form(self,'Associate contact',['contact_id'],choices={'contact_id':[(c['name'],c['id']) for c in self.store.all('contacts')]})
   if form.exec():
    cid=form.values()['contact_id']
    if cid is None: raise ValueError('Create a contact first')
    self.store.associate(p['id'],cid); self.refresh()
  self.guard(action)
 def show_text(self,title,text,html=False,copy=False):
  dlg=QDialog(self); dlg.setWindowTitle(title); dlg.resize(850,600); layout=QVBoxLayout(dlg); view=QTextEdit(); view.setReadOnly(True); view.setHtml(text) if html else view.setPlainText(text); layout.addWidget(view)
  if copy: self.button(layout,'Copy to clipboard',lambda:QApplication.clipboard().setText(text))
  self.button(layout,'Close',dlg.accept); dlg.exec()
 def activity(self):
  def action():
   p=self.selected('Projects'); rows=self.store.rows('SELECT occurred,description FROM activity WHERE project_id=? ORDER BY id DESC',(p['id'],)); linked=self.store.rows('SELECT c.name,c.role FROM contacts c JOIN project_contacts pc ON pc.contact_id=c.id WHERE pc.project_id=?',(p['id'],)); self.show_text('Project activity and team','Project contacts:\n'+'\n'.join(f'{r["name"]} — {r["role"]}' for r in linked)+'\n\nActivity:\n'+'\n'.join(f'{r["occurred"]} — {r["description"]}' for r in rows))
  self.guard(action)
 def revision(self):
  def action():
   d=self.selected('Documents'); form=Form(self,'Record immutable document revision',['revision','submitted','status','requirements','file_path'],choices={'status':['Draft','Submitted','Approved','Changes Required']})
   if form.exec(): self.store.add_version(d['id'],**form.values()); self.refresh()
  self.guard(action)
 def history(self):
  def action():
   d=self.selected('Documents'); self.show_text('Version history — '+d['title'],'\n\n'.join('\n'.join(f'{k}: {v}' for k,v in r.items()) for r in self.store.versions(d['id'])) or 'No revisions recorded.')
  self.guard(action)
 def open_file(self):
  def action():
   from PySide6.QtCore import QUrl
   from PySide6.QtGui import QDesktopServices
   versions=self.store.versions(self.selected('Documents')['id']); path=versions[0]['file_path'] if versions else ''
   if not path or not Path(path).is_file(): raise ValueError('The latest revision has no accessible linked file')
   if QMessageBox.question(self,'Open document','Open this retained revision? Do not overwrite it; record edits as a new revision.\n'+path)==QMessageBox.Yes: QDesktopServices.openUrl(QUrl.fromLocalFile(path))
  self.guard(action)
 def email_draft(self): self.guard(lambda:self.show_text('Follow-up email draft',self.store.draft(self.selected('Communications')),copy=True))
 def export(self,kind):
  def action():
   path,_=QFileDialog.getSaveFileName(self,'Export CSV',kind+'.csv','CSV (*.csv)')
   if path: self.store.export(path,self.store.outstanding() if kind=='tasks' else self.store.all('projects'))
  self.guard(action)
 def print_report(self):
  def action():
   doc=QTextDocument(); doc.setHtml(self.store.report(self.selected('Projects')['id'])); printer=QPrinter(QPrinter.HighResolution); preview=QPrintPreviewDialog(printer,self); preview.paintRequested.connect(doc.print_); preview.exec()
  self.guard(action)
 def backup(self):
  def action():
   path,_=QFileDialog.getSaveFileName(self,'Back up database','coordinator-backup.sqlite3','SQLite (*.sqlite3)')
   if path: self.store.backup(path); QMessageBox.information(self,'Backup complete',path)
  self.guard(action)
 def restore(self):
  def action():
   path,_=QFileDialog.getOpenFileName(self,'Restore database','','SQLite (*.sqlite3)')
   if path and QMessageBox.question(self,'Replace local data?','Restore this backup and replace all current records? A safety backup will be created.')==QMessageBox.Yes: self.store.restore(path); self.refresh(); QMessageBox.information(self,'Restore complete','Database restored successfully.')
  self.guard(action)

class Window(PermitUI,DevelopmentUI,BaseWindow):
 pass

def main():
 app=QApplication(sys.argv); app.setOrganizationName('Construction Project Coordinator'); app.setApplicationName('Construction Project Coordinator'); app.setStyle('Fusion')
 app.setStyleSheet('QWidget { font-family: Segoe UI; font-size: 10pt; } QMainWindow { background:#f3f5f8; } QListWidget { background:#17324d; color:white; border:0; padding:12px; } QListWidget::item { padding:13px 5px; } QListWidget::item:selected { background:#2b658b; border-radius:5px; } QLabel#heading { font-size:24pt; font-weight:600; color:#17324d; padding:12px 0; } QPushButton { padding:8px 12px; border:1px solid #bdcbd6; border-radius:4px; background:white; } QPushButton:hover { background:#e0eef8; } QTableWidget { background:white; border:1px solid #d9e1e8; gridline-color:#e9edf2; } QHeaderView::section { background:#e7eef4; padding:8px; border:0; } QLineEdit,QComboBox,QTextEdit { padding:6px; border:1px solid #b8c8d5; border-radius:3px; }')
 path=Path(os.environ.get('CPC_DATA_DIR') or QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))/'coordinator.sqlite3'
 store=Store(path)
 if not store.all('projects'):
  if QMessageBox.question(None,'Welcome','Load fictional sample projects and contacts? Choose No to start with an empty workspace.')==QMessageBox.Yes: store.seed()
 window=Window(store); window.show(); result=app.exec(); store.db.close(); return result
