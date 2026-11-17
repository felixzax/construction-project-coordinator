"""Supplier receipts workspace."""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QFileDialog,QMessageBox,QAbstractItemView
from .table import DataTable
from .receipts import RECEIPT_STATUSES,RECEIPT_FORM_FIELDS
from .finance import RECEIPT_FINANCE_COLUMNS

class ReceiptUI:
 def build_page(self,title):
  if title!='Receipts': return super().build_page(title)
  page=QWidget(); layout=QVBoxLayout(page); heading=QLabel('Supplier Receipts'); heading.setObjectName('heading'); layout.addWidget(heading)
  hint=QLabel('Compare the supplier estimate with the actual price, then record approval. Blank prices mean unknown; enter 0 for a confirmed zero price. Changing an approved supplier, price, currency or attachment resets approval for review.'); hint.setWordWrap(True); layout.addWidget(hint)
  bar=QHBoxLayout(); layout.addLayout(bar); self.button(bar,'+ New receipt',lambda:self.edit('Receipts')); self.button(bar,'Edit selected',lambda:self.edit('Receipts',True)); self.button(bar,'Attach receipt file',self.attach_receipt_file); self.button(bar,'Open receipt file',self.open_receipt_file)
  self.filter_Receipts=QLineEdit(); self.filter_Receipts.setPlaceholderText('Filter by supplier, reference, approval status or receipt details…'); self.filter_Receipts.textChanged.connect(self.refresh); layout.addWidget(self.filter_Receipts)
  table=DataTable(); table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.setAlternatingRowColors(True); table.doubleClicked.connect(lambda _:self.edit('Receipts',True)); layout.addWidget(table); self.tables['Receipts']=table; self.stack.addWidget(page)
 def refresh(self,*args):
  super().refresh(*args)
  self.fill('Receipts',self.store.receipt_rows())
 def choices(self,table):
  choices=super().choices(table)
  if table=='receipts': choices['status']=RECEIPT_STATUSES
  return choices
 def edit(self,title,existing=False):
  if title!='Receipts': return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'): raise ValueError('Create a project first')
   row=self.selected('Receipts') if existing else dict(project_id=self.project_filter.currentData(),currency='USD',status='Pending Review',include_in_budget=1)
   form=Form(self,'Edit supplier receipt' if existing else 'New supplier receipt',RECEIPT_FORM_FIELDS+list(RECEIPT_FINANCE_COLUMNS),row,self.choices('receipts'))
   form.persist=lambda values:self.store.save('receipts',values,row['id'] if existing else None); form.enable_draft('receipts',row['id'] if existing else None)
   if form.exec(): self.refresh()
  self.guard(action)
 def attach_receipt_file(self):
  def action():
   row=self.selected('Receipts'); path,_=QFileDialog.getOpenFileName(self,'Attach supplier receipt or quote')
   if path:
    self.store.attach_receipt(row['id'],path); self.refresh(); self.statusBar().showMessage('Receipt file copied locally. An existing approval is reset for review.',10000)
  self.guard(action)
 def open_receipt_file(self):
  def action():
   from pathlib import Path
   path=self.selected('Receipts')['attachment_path']
   if not path or not Path(path).is_file(): raise ValueError('Attach a receipt file first, or restore its retained copy')
   if QMessageBox.question(self,'Open receipt attachment?','Open this file with its Windows application?\n'+path,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)): raise ValueError('Windows could not open the attachment')
  self.guard(action)
