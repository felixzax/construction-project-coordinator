"""Contracts/budgets, change orders and upload/download/edit file management."""
from .workspace_ui import compact_dialog
from pathlib import Path
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QDialog,QFileDialog,QMessageBox,QAbstractItemView
from .table import DataTable
from .finance import FINANCE_FIELDS,CONTRACT_STATUSES,CURRENCIES,FILE_FILTER,safe_name

FINANCE_PAGES={'Contracts':'contracts','Budgets':'budgets'}

class FinanceUI:
 def build_page(self,title):
  if title not in FINANCE_PAGES:return super().build_page(title)
  page=QWidget();layout=QVBoxLayout(page);heading=QLabel(title);heading.setObjectName('heading');layout.addWidget(heading)
  hint=QLabel('Manage scope, dates, agreed amounts, change orders and original/edited contract files.' if title=='Contracts' else 'Track allocations, contingency, actual receipt costs and remaining commitments. Link receipts to contracts to avoid counting a contract and its invoiced cost twice.');hint.setWordWrap(True);layout.addWidget(hint)
  bar=QHBoxLayout();layout.addLayout(bar);self.button(bar,'+ New',lambda _,t=title:self.edit(t));self.button(bar,'Edit selected',lambda _,t=title:self.edit(t,True));self.button(bar,'Files — add / edit / save copy',lambda _,t=title:self.finance_file_manager(t))
  if title=='Contracts':self.button(bar,'From awarded bid',self.create_from_bid);self.button(bar,'Change orders',self.change_orders)
  entry=QLineEdit();entry.setPlaceholderText('Filter records…');entry.textChanged.connect(self.refresh);setattr(self,'filter_'+title,entry);layout.addWidget(entry)
  table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setAlternatingRowColors(True);table.doubleClicked.connect(lambda _,t=title:self.edit(t,True));layout.addWidget(table);self.tables[title]=table;self.stack.addWidget(page)
 def choices(self,table):
  choices=super().choices(table);choices['currency']=CURRENCIES
  choices['budget_id']=[('Unallocated',None)]+[(b['title']+' / '+b['currency'],b['id']) for b in self.store.all('budgets')]
  choices['contract_id']=[('No contract',None)]+[(c['title']+' / '+c['currency'],c['id']) for c in self.store.all('contracts')]
  choices['bid_id']=[('No source bid',None)]+[(b['title']+' / '+b['currency'],b['id']) for b in self.store.all('bids') if b['status']=='Awarded']
  if table=='contracts':choices['status']=CONTRACT_STATUSES
  elif table=='budgets':choices['status']=['Active','Closed']
  elif table=='contract_changes':choices['status']=['Proposed','Approved','Rejected']
  return choices
 def refresh(self,*args):
  super().refresh(*args)
  for title,table in FINANCE_PAGES.items():self.fill(title,self.store.finance_rows(table))
 def edit(self,title,existing=False):
  if title not in FINANCE_PAGES:return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'):raise ValueError('Create a project first')
   table=FINANCE_PAGES[title];row=self.selected(title) if existing else dict(project_id=self.project_filter.currentData(),currency='USD',status='Draft' if table=='contracts' else 'Active')
   form=Form(self,('Edit ' if existing else 'New ')+title,FINANCE_FIELDS[table],row,self.choices(table));form.persist=lambda values:self.store.save(table,values,row['id'] if existing else None);form.enable_draft(table,row['id'] if existing else None)
   if form.exec():self.refresh()
  self.guard(action)
 def create_from_bid(self):
  from .ui import Form
  def action():
   choices=self.choices('contracts');choices['bid_id']=[item for item in choices['bid_id'] if item[1] is not None]
   if not choices['bid_id']:raise ValueError('Mark a bid Awarded in Bidding first')
   form=Form(self,'Create draft contract from awarded bid',['bid_id','budget_id'],choices=choices)
   if form.exec():self.store.contract_from_bid(form.values()['bid_id'],form.values()['budget_id']);self.refresh()
  self.guard(action)
 def change_orders(self):
  from .ui import Form
  def action():
   contract=self.selected('Contracts');dlg=QDialog(self);dlg.setWindowTitle('Change orders — '+contract['title']);dlg.resize(1000,650);layout=QVBoxLayout(dlg);table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table);bar=QHBoxLayout();layout.addLayout(bar);rows=[]
   def reload():rows[:]=self.store.rows('SELECT * FROM contract_changes WHERE contract_id=? ORDER BY id DESC',(contract['id'],));self.render_recovery_table(table,[{k:v for k,v in r.items() if k not in ('id','contract_id')} for r in rows])
   def edit(existing=False):
    def perform():
     if existing:
      i=table.currentRow()
      if i<0:raise ValueError('Select a change order')
      row=rows[i]
     else:row=dict(contract_id=contract['id'],status='Proposed')
     choices=self.choices('contract_changes');choices['contract_id']=[(contract['title'],contract['id'])]
     form=Form(dlg,'Change order',FINANCE_FIELDS['contract_changes'],row,choices);form.persist=lambda values:self.store.save('contract_changes',values,row['id'] if existing else None);form.enable_draft('contract_changes',row['id'] if existing else None)
     if form.exec():reload()
    self.guard(perform)
   def delete(all_rows=False):
    def perform():
     indexes=range(len(rows)) if all_rows else table.selected_record_rows()
     if self.confirm_delete([('contract_changes',rows[i]['id']) for i in indexes],'change orders'):reload()
    self.guard(perform)
   table.delete_selected=lambda:delete();table.delete_listed=lambda:delete(True)
   def files():
    def perform():
     i=table.currentRow()
     if i<0:raise ValueError('Select a change order')
     self.finance_file_manager('Change order','contract_changes',rows[i])
    self.guard(perform)
   self.button(bar,'Files',files)
   self.button(bar,'+ Change order',lambda:edit());self.button(bar,'Edit selected',lambda:edit(True));self.button(bar,'Delete selected',lambda:delete());self.button(bar,'Export DOCX',lambda:self.export_rows_dialog('Change orders',rows,'docx'));self.button(bar,'Export CSV',lambda:self.export_rows_dialog('Change orders',rows,'csv'));self.button(bar,'Close',dlg.accept);reload();compact_dialog(dlg,{'+ Change order','Edit selected','Files'});dlg.exec();self.refresh()
  self.guard(action)
 def finance_file_manager(self,title,parent_table=None,record=None):
  def action():
   owner_record=record if record is not None else self.selected(title);owner_table=parent_table or FINANCE_PAGES[title];dlg=QDialog(self);dlg.setWindowTitle(title+' files — '+owner_record.get('title',owner_record.get('name','Project')));dlg.resize(1150,700);layout=QVBoxLayout(dlg)
   hint=QLabel('Add files keeps an original local copy. Save a copy downloads the original bytes; Save all as ZIP includes every file. Text/CSV, basic DOCX and plain XLSX can be edited here. Supported conversions appear in Save as; complex files use their normal Windows app and can be re-imported as revised files.');hint.setWordWrap(True);layout.addWidget(hint)
   from .regulatory import PRIVACY_NOTE
   warning=QLabel(PRIVACY_NOTE);warning.setWordWrap(True);layout.addWidget(warning)
   table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(table);bar=QHBoxLayout();layout.addLayout(bar);rows=[];working_copies={}
   def reload():rows[:]=self.store.finance_files(owner_table,owner_record['id']);self.render_recovery_table(table,[dict(filename=r['original_name'],bytes=r['byte_size'],added=r['added_date'],notes=r['notes']) for r in rows])
   def selected():
    i=table.currentRow()
    if i<0:raise ValueError('Select a file')
    return rows[i]
   def upload():
    def perform():
     paths,_=QFileDialog.getOpenFileNames(dlg,'Add original files','',FILE_FILTER)
     if paths:self.store.import_finance_files(owner_table,owner_record['id'],paths);reload()
    self.guard(perform)
   def download():
    def perform():
     row=selected();path,_=QFileDialog.getSaveFileName(dlg,'Save original file copy',safe_name(row['original_name']),'Original file (*'+Path(row['original_name']).suffix+')')
     if path:self.store.save_finance_copy(row['id'],path)
    self.guard(perform)
   def zip_all():
    def perform():
     path,_=QFileDialog.getSaveFileName(dlg,'Save all original files','attachments.zip','ZIP (*.zip)')
     if path:self.store.export_finance_zip(owner_table,owner_record['id'],path)
    self.guard(perform)
   def open_file():
    def perform():
     selected_file=selected();row,_=self.store.checked_finance_file(selected_file['id'])
     if QMessageBox.question(dlg,'Open working copy?',f'Open a separate working copy of {row["original_name"]}? Save changes in that app, then use Import external edits.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
      path=self.store.finance_working_copy(row['id']);working_copies[row['id']]=path;working_path.setText(str(path))
      if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):raise ValueError('Windows could not open this file')
    self.guard(perform)
   def import_external():
    def perform():
     row=selected();path=working_copies.get(row['id'])
     if not path or not path.is_file():raise ValueError('Open a working copy first, or use Add files to import a revision saved elsewhere')
     self.store.import_finance_files(owner_table,owner_record['id'],[path],notes=f'External revision of attachment #{row["id"]}');reload()
    self.guard(perform)
   def edit_file():
    def perform():
     from .file_editor import FileEditor
     editor=FileEditor(self,self.store,selected()['id']);editor.exec();reload()
    self.guard(perform)
   def delete(all_rows=False):
    def perform():
     indexes=range(len(rows)) if all_rows else table.selected_record_rows()
     if self.confirm_delete([('finance_files',rows[i]['id']) for i in indexes],'attachment records (retained files remain on disk)'):reload()
    self.guard(perform)
   table.delete_selected=lambda:delete();table.delete_listed=lambda:delete(True)
   for label,callback in [('Add files…',upload),('Edit / convert…',edit_file),('Save a copy…',download),('Save all as ZIP…',zip_all),('Delete selected',lambda:delete()),('Close',dlg.accept)]:self.button(bar,label,callback)
   external=QHBoxLayout();layout.addLayout(external);self.button(external,'Open working copy',open_file);self.button(external,'Import external edits',import_external);working_path=QLineEdit();working_path.setReadOnly(True);working_path.setPlaceholderText('External working-copy path appears here');external.addWidget(working_path)
   reload();compact_dialog(dlg,{'Add files…','Edit / convert…','Save a copy…'});dlg.exec();self.refresh()
  self.guard(action)
