"""Work-order entry with adjacent valuation/permit-fee fields and standard files."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QAbstractItemView
from .table import DataTable
from .work_orders import WORK_ORDER_FIELDS,WORK_ORDER_STATUSES,FEE_STATUSES,VALUATION_BASES
from .permits import JURISDICTIONS

class WorkOrderUI:
 def build_page(self,title):
  if title!='Work Orders':return super().build_page(title)
  page=QWidget();layout=QVBoxLayout(page);heading=QLabel('Work Orders');heading.setObjectName('heading');layout.addWidget(heading)
  hint=QLabel('Record construction job valuation and its separate permit fee side by side. Amounts are entered manually; the jurisdiction determines valuation requirements and fees. These are coordination figures, not extra budget actuals or payment instructions.');hint.setWordWrap(True);layout.addWidget(hint);bar=QHBoxLayout();layout.addLayout(bar)
  self.button(bar,'+ New',lambda:self.edit(title));self.button(bar,'Edit selected',lambda:self.edit(title,True))
  entry=QLineEdit();entry.setPlaceholderText('Filter by work order, address, contractor, valuation or permit…');entry.textChanged.connect(self.refresh);setattr(self,'filter_'+title,entry);layout.addWidget(entry)
  table=DataTable();table.setEditTriggers(QAbstractItemView.NoEditTriggers);table.setAlternatingRowColors(True);table.doubleClicked.connect(lambda _:self.edit(title,True));layout.addWidget(table);self.tables[title]=table;self.stack.addWidget(page)
 def choices(self,table):
  choices=super().choices(table)
  if table=='work_orders':
   choices.update(status=WORK_ORDER_STATUSES,fee_status=FEE_STATUSES,valuation_basis=VALUATION_BASES,jurisdiction_type=JURISDICTIONS)
   choices['permit_id']=[('No linked permit',None)]+[(r['title'],r['id']) for r in self.store.all('registers') if r['record_type']=='Permit']
  return choices
 def edit(self,title,existing=False):
  if title!='Work Orders':return super().edit(title,existing)
  from .ui import Form
  def action():
   if not self.store.all('projects'):raise ValueError('Create a project first')
   row=self.selected(title) if existing else dict(project_id=self.project_filter.currentData(),currency='USD',status='Draft',valuation_basis='Estimated',fee_status='Unknown',jurisdiction_type='Other')
   choices=self.choices('work_orders');choices['permit_id']=[('No linked permit',None)]+[(r['title'],r['id']) for r in self.store.all('registers') if r['record_type']=='Permit']
   form=Form(self,'Edit work order' if existing else 'New work order',WORK_ORDER_FIELDS,row,choices)
   def sync_project():
    pid=form.inputs['project_id'].currentData();projects=self.store.rows('SELECT address FROM projects WHERE id=?',(pid,));previous=getattr(form,'_default_address','');address=projects[0]['address'] if projects else ''
    if not form.inputs['site_address'].text() or form.inputs['site_address'].text()==previous:form.inputs['site_address'].setText(address)
    form._default_address=address
    for key,rows,label in [('contract_id',[c for c in self.store.all('contracts') if c['project_id']==pid],'No related contract'),('permit_id',[r for r in self.store.all('registers') if r['record_type']=='Permit' and r['project_id']==pid],'No linked permit')]:
     widget=form.inputs[key];selected=widget.currentData();widget.blockSignals(True);widget.clear();widget.addItem(label,None)
     for item in rows:widget.addItem(item['title'],item['id'])
     widget.setCurrentIndex(max(0,widget.findData(selected)));widget.blockSignals(False)
    sync_permit()
   def sync_permit():
    permit_id=form.inputs['permit_id'].currentData();rows=self.store.rows("SELECT jurisdiction_type,jurisdiction_name FROM registers WHERE id=? AND record_type='Permit'",(permit_id,)) if permit_id else []
    form.inputs['jurisdiction_type'].setEnabled(not rows);form.inputs['jurisdiction_name'].setReadOnly(bool(rows))
    if rows:form.inputs['jurisdiction_type'].setCurrentText(rows[0]['jurisdiction_type']);form.inputs['jurisdiction_name'].setText(rows[0]['jurisdiction_name'])
   form.inputs['project_id'].currentIndexChanged.connect(sync_project);form.inputs['permit_id'].currentIndexChanged.connect(sync_permit);sync_project()
   form.persist=lambda values:self.store.save('work_orders',values,row['id'] if existing else None);form.enable_draft('work_orders',row['id'] if existing else None)
   if form.exec():self.refresh()
  self.guard(action)
 def refresh(self,*args):
  super().refresh(*args);rows=self.store.work_order_rows();self.fill('Work Orders',rows);active={p['id'] for p in self.store.all('projects') if not p['archived']};extra=[]
  for row in rows:
   if row['project_id'] in active and row['deadline'] and row['status'] not in ('Completed','Cancelled'):
    extra.append(dict(_source_table='work_orders',_source_id=row['id'],kind='Work order',project_id=row['project_id'],project=row['project'],item=row['title'],deadline=row['deadline'],status=row['status'],responsible=row['contractor_name']))
  self.fill('Dashboard',sorted(self.data.get('Dashboard',[])+extra,key=lambda r:r.get('deadline') or '9999'))
  self.fill('Timeline',sorted(self.data.get('Timeline',[])+[dict(r,id=None,title=r['item'],phase='') for r in extra],key=lambda r:r.get('deadline') or '9999'))
