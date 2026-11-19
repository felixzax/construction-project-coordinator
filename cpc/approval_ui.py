"""Manual approval workspace, prices, review snapshots and supporting files."""
from datetime import date
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QAbstractItemView,QDialog
from .table import DataTable
from .approvals import APPROVAL_FIELDS,APPROVAL_STATUSES
from .workspace_ui import compact_dialog

class ApprovalUI:
 def build_page(self,title):
  if title!='Approvals':return super().build_page(title)
  page=QWidget();layout=QVBoxLayout(page);heading=QLabel('Approvals');heading.setObjectName('heading');layout.addWidget(heading)
  hint=QLabel('Record the cost of an item or work and its review decision. Price/scope changes or changed supporting files reset Approved records for review. Approval prices do not automatically add to budgets or authorize payments.');hint.setWordWrap(True);layout.addWidget(hint);bar=QHBoxLayout();layout.addLayout(bar)
  self.button(bar,'+ New',lambda:self.edit('Approvals'));self.button(bar,'Edit selected',lambda:self.edit('Approvals',True));self.button(bar,'Review history',self.approval_history_dialog)
  entry=QLineEdit();entry.setPlaceholderText('Filter by item, supplier, price or approval status…');entry.textChanged.connect(self.refresh);setattr(self,'filter_Approvals',entry);layout.addWidget(entry)
  table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setAlternatingRowColors(True);table.doubleClicked.connect(lambda _:self.edit('Approvals',True));layout.addWidget(table);self.tables[title]=table;self.stack.addWidget(page)
 def choices(self,table):
  choices=super().choices(table)
  if table=='approvals':
   choices['status']=APPROVAL_STATUSES;choices['approval_type']=['Parts / Materials','Equipment','Work','Proposal','Other'];choices['reviewer_id']=[('Unassigned',None)]+[(c['name'],c['id']) for c in self.store.all('contacts')]
  return choices
 def edit(self,title,existing=False):
  if title!='Approvals':return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'):raise ValueError('Create a project first')
   row=self.selected(title) if existing else dict(project_id=self.project_filter.currentData(),currency='USD',status='Draft',approval_type='Work');choices=self.choices('approvals');pid=row.get('project_id')
   choices['contract_id']=[('No related contract',None)]+[(c['title']+' / '+c['currency'],c['id']) for c in self.store.all('contracts') if not pid or c['project_id']==pid]
   form=Form(self,'Edit approval' if existing else 'New approval',APPROVAL_FIELDS,row,choices);form.inputs['approval_type'].setEditable(True);form.persist=lambda values:self.store.save('approvals',values,row['id'] if existing else None);form.enable_draft('approvals',row['id'] if existing else None)
   if form.exec():self.refresh()
  self.guard(action)
 def refresh(self,*args):
  super().refresh(*args);self.fill('Approvals',self.store.approval_rows());extra=[];active={p['id'] for p in self.store.all('projects') if not p['archived']}
  for row in self.store.approval_rows():
   if row['project_id'] in active and row['deadline'] and row['status'] not in ('Approved','Rejected','Withdrawn'):
    extra.append(dict(_source_table='approvals',_source_id=row['id'],kind='Approval',project_id=row['project_id'],project=row['project'],item=row['title'],deadline=row['deadline'],status=row['status'],responsible=row['reviewed_by'] or row['reviewer'] or ''))
  self.fill('Dashboard',sorted(self.data.get('Dashboard',[])+extra,key=lambda r:r.get('deadline') or '9999'))
  self.fill('Timeline',sorted(self.data.get('Timeline',[])+[dict(r,id=None,title=r['item'],phase='') for r in extra],key=lambda r:r.get('deadline') or '9999'))
 def approval_history_dialog(self):
  def action():
   record=self.selected('Approvals');rows=self.store.approval_events(record['id']);dialog=QDialog(self);dialog.setWindowTitle('Review history — '+record['title']);dialog.resize(1100,650);layout=QVBoxLayout(dialog);table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table);self.render_recovery_table(table,rows);bar=QHBoxLayout();layout.addLayout(bar)
   self.button(bar,'Export CSV',lambda:self.export_rows_dialog('Approval history',rows,'csv'));self.button(bar,'Export DOCX',lambda:self.export_rows_dialog('Approval history',rows,'docx'));self.button(bar,'Close',dialog.accept);compact_dialog(dialog,set());dialog.exec()
  self.guard(action)
