"""Supplier receipts workspace."""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QFileDialog,QMessageBox,QAbstractItemView
from .table import DataTable
from .receipts import RECEIPT_STATUSES,RECEIPT_FORM_FIELDS,COST_CATEGORIES,PARTS_SOURCES,PAYMENT_RESPONSIBILITY,REIMBURSEMENT_STATUSES
from .finance import RECEIPT_FINANCE_COLUMNS

class ReceiptUI:
 def build_page(self,title):
  if title!='Receipts': return super().build_page(title)
  page=QWidget(); layout=QVBoxLayout(page); heading=QLabel('Receipts & Parts Costs'); heading.setObjectName('heading'); layout.addWidget(heading)
  hint=QLabel('Track parts/materials separately from labor: company purchases or stock, contractor/employee purchases and reimbursements. Include actual cost in its budget once; reimbursement is a portion of that cost, never an additional expense. Link parts to a contract only if its price already includes them; otherwise link directly to the budget. Blank prices mean unknown; 0 is a confirmed zero.'); hint.setWordWrap(True); layout.addWidget(hint)
  bar=QHBoxLayout(); layout.addLayout(bar); self.button(bar,'+ New receipt',lambda:self.edit('Receipts')); self.button(bar,'Edit selected',lambda:self.edit('Receipts',True)); self.button(bar,'Attach receipt file',self.attach_receipt_file); self.button(bar,'Open receipt file',self.open_receipt_file)
  self.filter_Receipts=QLineEdit(); self.filter_Receipts.setPlaceholderText('Filter by supplier, reference, approval status or receipt details…'); self.filter_Receipts.textChanged.connect(self.refresh); layout.addWidget(self.filter_Receipts)
  table=DataTable(); table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.setAlternatingRowColors(True); table.doubleClicked.connect(lambda _:self.edit('Receipts',True)); layout.addWidget(table); self.tables['Receipts']=table; self.stack.addWidget(page)
 def refresh(self,*args):
  super().refresh(*args)
  self.fill('Receipts',self.store.receipt_rows())
 def choices(self,table):
  choices=super().choices(table)
  if table=='receipts':choices.update(status=RECEIPT_STATUSES,cost_category=COST_CATEGORIES,source_type=PARTS_SOURCES,payment_responsibility=PAYMENT_RESPONSIBILITY,reimbursement_status=REIMBURSEMENT_STATUSES)
  return choices
 def edit(self,title,existing=False):
  if title!='Receipts': return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'): raise ValueError('Create a project first')
   row=self.selected('Receipts') if existing else dict(project_id=self.project_filter.currentData(),currency='USD',status='Pending Review',include_in_budget=1)
   fields=RECEIPT_FORM_FIELDS+list(RECEIPT_FINANCE_COLUMNS);first=['project_id','title','cost_category','source_type','supplier_name','contact_id','discipline','building_area','currency','estimated_amount','actual_amount','budget_id','contract_id','include_in_budget','payment_responsibility','purchaser_name','reimbursement_amount','reimbursement_status','reimbursed_date','reimbursement_notes','status']
   fields=first+[f for f in fields if f not in first]
   form=Form(self,'Edit parts / receipt cost' if existing else 'New parts / receipt cost',fields,row,self.choices('receipts'))
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
