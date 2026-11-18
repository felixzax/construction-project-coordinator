"""Permit checklist editing and explicit browser links."""
from .workspace_ui import compact_dialog
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QCheckBox,
 QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QFileDialog)
from .permits import JURISDICTIONS,PERMIT_COLUMNS,REQUIREMENT_FIELDS,validate_url
from .store import FIELDS
from .table import DataTable

class PermitUI:
 def build_page(self,title):
  super().build_page(title)
  if title=='Permits':
   page=self.stack.widget(self.stack.count()-1); bar=QHBoxLayout(); page.layout().insertLayout(3,bar)
   self.button(bar,'Application checklist',self.permit_checklist)
   self.button(bar,'Open requirements page',lambda:self.open_permit_link('requirements_url'))
   self.button(bar,'Open application page',lambda:self.open_permit_link('application_url'))
 def choices(self,table):
  choices=super().choices(table); choices['jurisdiction_type']=JURISDICTIONS; return choices
 def fill(self,title,rows):
  if title=='Permits':
   rows=[dict(r,checklist_progress=self.store.permit_progress(r['id'])) for r in rows]
  return super().fill(title,rows)
 def edit(self,title,existing=False):
  if title!='Permits': return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'): raise ValueError('Create a project first')
   row=self.selected('Permits') if existing else dict(project_id=self.project_filter.currentData(),record_type='Permit',status='Open',jurisdiction_type='City',requirements_reviewed=0)
   choices=self.choices('registers'); choices['record_type']=['Permit']
   primary=['project_id','title','jurisdiction_type','jurisdiction_name','department','requirements_url','requirements_reviewed','application_url']
   fields=primary+[key for key in FIELDS['registers'] if key not in primary]
   form=Form(self,'Edit permit application' if existing else 'New permit application',fields,row,choices)
   form.persist=lambda values:self.store.save('registers',values,row['id'] if existing else None)
   form.enable_draft('registers',row['id'] if existing else None)
   if form.exec(): self.refresh()
  self.guard(action)
 def open_web_link(self,value):
  if not value: raise ValueError('Add a website link first using Edit selected')
  validate_url(value)
  if not QDesktopServices.openUrl(QUrl(value)): raise ValueError('Windows could not open the default browser')
 def open_permit_link(self,key):
  self.guard(lambda:self.open_web_link(self.selected('Permits')[key]))
 def permit_checklist(self):
  from .ui import Form
  def action():
   permit=self.selected('Permits'); permit_id=permit['id']
   dlg=QDialog(self); dlg.setWindowTitle('Permit application checklist — '+permit['title']); dlg.resize(1000,700); layout=QVBoxLayout(dlg)
   jurisdiction=QLabel(f'{permit["jurisdiction_type"]}: {permit["jurisdiction_name"]} · {permit["department"]}'); jurisdiction.setTextFormat(Qt.PlainText); layout.addWidget(jurisdiction)
   intro=QLabel('Use the jurisdiction website to identify current requirements, add each requirement below, and check it off when ready. Checking items does not submit or approve the permit.'); intro.setWordWrap(True); layout.addWidget(intro)
   for label,key in [('Application requirements','requirements_url'),('Application page','application_url')]:
    bar=QHBoxLayout(); layout.addLayout(bar); bar.addWidget(QLabel(label)); link=QLineEdit(permit[key]); link.setReadOnly(True); bar.addWidget(link)
    self.button(bar,'Open',lambda _,key=key:self.guard(lambda:self.open_web_link(permit[key])))
   reviewed=QCheckBox('I reviewed the city/county application requirements page'); reviewed.setChecked(bool(permit['requirements_reviewed'])); layout.addWidget(reviewed)
   def review_changed(checked):
    def perform(): self.store.save('registers',{'requirements_reviewed':int(checked)},permit_id)
    self.guard(perform)
   reviewed.toggled.connect(review_changed)
   bar=QHBoxLayout(); layout.addLayout(bar)
   table=DataTable(); table.setColumnCount(5); table.setHorizontalHeaderLabels(['Ready','Requirement','Source link','Checked on','Notes']);  table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive); table.horizontalHeader().setStretchLastSection(True); layout.addWidget(table)
   progress=QLabel(); layout.addWidget(progress); items=[]
   def reload(selected_id=None):
    items[:]=self.store.permit_requirements(permit_id); table.blockSignals(True); table.setRowCount(len(items))
    for i,item in enumerate(items):
     check=QTableWidgetItem(); check.setData(Qt.UserRole,item['id']); check.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable|Qt.ItemIsUserCheckable); check.setCheckState(Qt.Checked if item['completed'] else Qt.Unchecked); table.setItem(i,0,check)
     for j,key in enumerate(['title','source_url','completed_on','notes'],1): table.setItem(i,j,QTableWidgetItem(item[key]))
     if item['id']==selected_id: table.selectRow(i)
    table.setColumnWidth(0,65); table.setColumnWidth(1,260); table.setColumnWidth(2,300); table.setColumnWidth(3,110); table.blockSignals(False)
    progress.setText(self.store.permit_progress(permit_id)+' — readiness checklist only; permit status is updated separately.')
   def changed(cell):
    if cell.column()!=0: return
    def perform(): self.store.set_requirement_completed(cell.data(Qt.UserRole),cell.checkState()==Qt.Checked)
    selected_id=cell.data(Qt.UserRole); self.guard(perform); reload(selected_id)
   table.itemChanged.connect(changed)
   def edit_requirement(existing=False):
    def perform():
     if existing:
      row=table.currentRow()
      if row<0: raise ValueError('Select a requirement first')
      record=items[row]
     else: record=dict(register_id=permit_id,completed=0)
     choices={'register_id':[(permit['title'],permit_id)]}
     form=Form(dlg,'Edit application requirement' if existing else 'New application requirement',REQUIREMENT_FIELDS,record,choices)
     form.persist=lambda values:self.store.save('permit_requirements',values,record['id'] if existing else None)
     form.enable_draft('permit_requirements',record['id'] if existing else None)
     if form.exec(): reload()
    self.guard(perform)
   def open_source():
    def perform():
     row=table.currentRow()
     if row<0: raise ValueError('Select a requirement first')
     self.open_web_link(items[row]['source_url'] or permit['requirements_url'])
    self.guard(perform)
   def export():
    def perform():
     path,_=QFileDialog.getSaveFileName(dlg,'Export permit checklist','permit-checklist.csv','CSV (*.csv)')
     if path:
      rows=[dict(permit=permit['title'],jurisdiction_type=permit['jurisdiction_type'],jurisdiction_name=permit['jurisdiction_name'],department=permit['department'],requirements_url=permit['requirements_url'],requirement=item['title'],source_url=item['source_url'],completed='Yes' if item['completed'] else 'No',completed_on=item['completed_on'],notes=item['notes']) for item in items]
      self.store.export(path,rows)
    self.guard(perform)
   def remove_requirements(all_listed=False):
    def perform():
     indexes=range(len(items)) if all_listed else table.selected_record_rows()
     if self.confirm_delete([('permit_requirements',items[i]['id']) for i in indexes],'permit requirements'): reload()
    self.guard(perform)
   table.delete_selected=lambda:remove_requirements(); table.delete_listed=lambda:remove_requirements(True)
   self.button(bar,'Export DOCX',lambda:self.export_rows_dialog('Permit checklist',[dict(item,permit=permit['title'],jurisdiction=permit['jurisdiction_name'],requirements_url=permit['requirements_url']) for item in items],'docx'))
   self.button(bar,'Delete selected',lambda:remove_requirements()); self.button(bar,'Delete all requirements',lambda:remove_requirements(True))
   self.button(bar,'+ Requirement',lambda:edit_requirement()); self.button(bar,'Edit selected',lambda:edit_requirement(True)); self.button(bar,'Open source link',open_source); self.button(bar,'Export checklist CSV',export); self.button(bar,'Close',dlg.accept)
   table.doubleClicked.connect(lambda _:edit_requirement(True)); reload(); compact_dialog(dlg,{'+ Requirement','Edit selected'}); dlg.exec(); self.refresh()
  self.guard(action)
