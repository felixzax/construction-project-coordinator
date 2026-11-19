"""Discipline workspaces, meeting actions and bid estimating user interface."""
from .workspace_ui import compact_dialog
from datetime import date
from decimal import Decimal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,
 QTableWidget,QAbstractItemView,QHeaderView,QTableWidgetItem,QDialog,QFileDialog,QMessageBox)
from .development import DISCIPLINES, NEW_FIELDS, REGISTER_TYPES, line_totals, STATUSES
from .store import FIELDS, TASK_STATUSES
from .table import DataTable
from .permits import PERMIT_COLUMNS

DISCIPLINE_PAGES={
 'Architecture':['Architecture'],
 'Engineering':['Structural Engineering','Geotechnical Engineering'],
 'Electrical':['Electrical','Fire Protection'],
 'Plumbing':['Plumbing'],
 'Mechanical / HVAC':['Mechanical / HVAC'],
 'Site & Civil':['Civil Engineering','Site Work','Landscape','Utilities'],
 'Other Trades':['General','Interiors','Roofing','Concrete','Masonry','Steel','Demolition'],
}
REGISTER_PAGES={'RFIs':'RFI','Submittals':'Submittal','Permits':'Permit','Inspections':'Inspection','Punch & Changes':None}
NAVIGATION=['Dashboard','Projects','Hidden sections','Project Profile','Scope & Systems','Custom Information','Rebates & Incentives','Corrections','Violations','Tasks',*DISCIPLINE_PAGES,'Meetings','Contacts','Communications','Documents',*REGISTER_PAGES,'Bidding','Contracts','Change Orders','Approvals','Budgets','Receipts','Timeline','Search','Backup & Restore','Recovery & Data']

STATUS_CHOICES=STATUSES
EXTRA_OPTIONS={
 'discipline':DISCIPLINES,
 'drawing_type':['Plan Set','CAD / DWG','CAD / DXF','BIM / Revit','Site Plan','Floor Plan','Elevation','Section','Detail','Schedule','Specification','Shop Drawing','As-Built','Survey','Other'],
 'meeting_type':['Coordination','Design Review','Pre-Bid','Preconstruction','Site Progress','Owner / Contractor','Agency / Permit','Safety','Closeout'],
 'record_type':REGISTER_TYPES,
 'bid_type':['Lump Sum','Unit Price','Time & Materials','Design-Build','Allowance','Other'],
 'currency':['USD','CAD','EUR','GBP','AUD'],
 'item_type':['Base','Allowance','Alternate'],
 'quantity_basis':['Manual','Area (length × width)'],
 'unit':['each','sq ft','sq m','linear ft','linear m','cu yd','cu m','hour','day','ton','lot'],
}
DEFAULTS={
 'work_packages':{'status':'Not Started'},
 'meetings':{'meeting_date':date.today().isoformat(),'status':'Scheduled'},
 'registers':{'status':'Open'},
 'bid_packages':{'status':'Draft'},
 'bids':{'currency':'USD','status':'Draft','tax_percent':'0','markup_percent':'0','contingency_percent':'0','discount':'0'},
 'bid_items':{'quantity':'1','quantity_basis':'Manual','included':1,'item_type':'Base','unit':'each'},
}

class DevelopmentUI:
 def fill(self,title,rows):
  pid=self.project_filter.currentData() if hasattr(self,'project_filter') else None
  if pid:
   if title=='Projects': rows=[r for r in rows if r['id']==pid]
   elif title=='Contacts':
    ids={r['contact_id'] for r in self.store.rows('SELECT contact_id FROM project_contacts WHERE project_id=?',(pid,))}
    rows=[r for r in rows if r['id'] in ids]
   elif title=='Search':
    ids={r['contact_id'] for r in self.store.rows('SELECT contact_id FROM project_contacts WHERE project_id=?',(pid,))}
    rows=[r for r in rows if r.get('project_id')==pid or (r.get('type')=='contacts' and r['id'] in ids)]
   else: rows=[r for r in rows if r.get('project_id')==pid]
  super().fill(title,rows)
 def build_page(self,title):
  if title not in (*DISCIPLINE_PAGES,*REGISTER_PAGES,'Meetings','Bidding'): return super().build_page(title)
  page=QWidget(); layout=QVBoxLayout(page); heading=QLabel(title); heading.setObjectName('heading'); layout.addWidget(heading)
  descriptions={
   'Meetings':'Schedule meetings, record attendees, agenda, minutes and decisions. Convert meeting actions into assigned tasks.',
   'Bidding':'Select a trade package, add bidder estimates, then enter detailed cost items. Compare scope, exclusions and totals in each currency.',
  }
  text=descriptions.get(title,'Track discipline scope, consultant, area, outstanding requirements and deadlines.' if title in DISCIPLINE_PAGES else 'Track references, responsible contacts, deadlines, responses and approval status.')
  hint=QLabel(text); hint.setWordWrap(True); layout.addWidget(hint)
  bar=QHBoxLayout(); layout.addLayout(bar)
  self.button(bar,'+ New package' if title=='Bidding' else '+ New',lambda _,t=title:self.edit(t))
  self.button(bar,'Edit selected',lambda _,t=title:self.edit(t,True))
  if title=='Meetings': self.button(bar,'Create action task',self.meeting_task)
  if title=='Bidding':
   self.button(bar,'Compare bids',self.compare_bids); self.button(bar,'Export comparison CSV',self.export_comparison)
  else: self.button(bar,'Export CSV',lambda _,t=title:self.export_section(t,'csv'))
  entry=QLineEdit(); entry.setPlaceholderText('Filter this list…'); entry.textChanged.connect(self.refresh); setattr(self,'filter_'+title,entry); layout.addWidget(entry)
  table=self.make_table(title); layout.addWidget(table)
  table.doubleClicked.connect(lambda _,t=title:self.edit(t,True))
  if title=='Bidding':
   table.itemSelectionChanged.connect(self.refresh_bids)
   bid_label=QLabel('Bidder estimates for the selected package'); bid_label.setObjectName('subheading'); layout.addWidget(bid_label)
   bar=QHBoxLayout(); layout.addLayout(bar)
   self.button(bar,'+ Bidder estimate',lambda:self.edit_bid(False)); self.button(bar,'Edit estimate',lambda:self.edit_bid(True)); self.button(bar,'Cost items & totals',self.cost_items); self.button(bar,'Print estimate',self.print_bid)
   bids=self.make_table('Bids'); layout.addWidget(bids); bids.doubleClicked.connect(lambda _:self.cost_items())
   self.bid_summary=QLabel('Select a package to view bidder estimates.'); self.bid_summary.setWordWrap(True); layout.addWidget(self.bid_summary)
  self.stack.addWidget(page)
 def make_table(self,title):
  table=DataTable();  table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); table.horizontalHeader().setStretchLastSection(True); table.setAlternatingRowColors(True); self.tables[title]=table; return table
 def refresh(self,*args):
  # Rebuild the project selector without losing its current selection or emitting a refresh loop.
  pid=self.project_filter.currentData(); self.project_filter.blockSignals(True); self.project_filter.clear(); self.project_filter.addItem('All projects',None)
  for p in self.store.all('projects'): self.project_filter.addItem(p['name']+(' [Archived]' if p['archived'] else ''),p['id'])
  index=self.project_filter.findData(pid); self.project_filter.setCurrentIndex(max(0,index)); self.project_filter.blockSignals(False)
  package_id=None
  if self.tables.get('Bidding') and self.tables['Bidding'].currentRow()>=0:
   row=self.tables['Bidding'].currentRow(); old=self.data.get('Bidding',[])
   if row<len(old): package_id=old[row]['id']
  super().refresh(*args)
  names={r['id']:r['name'] for r in self.store.all('projects')}; people={r['id']:r['name'] for r in self.store.all('contacts')}
  work=self.store.all('work_packages'); registers=self.store.all('registers')
  for title in [*DISCIPLINE_PAGES,*REGISTER_PAGES,'Meetings','Bidding']:
   if title in DISCIPLINE_PAGES: rows=[dict(r) for r in work if r['discipline'] in DISCIPLINE_PAGES[title]]
   elif title in REGISTER_PAGES:
    kinds=[REGISTER_PAGES[title]] if REGISTER_PAGES[title] else ['Punch Item','Change Request']
    rows=[dict(r) for r in registers if r['record_type'] in kinds]
   else: rows=self.store.all('meetings' if title=='Meetings' else 'bid_packages')
   for r in rows:
    r['project']=names.get(r['project_id'],'')
    if 'contact_id' in r: r['responsible']=people.get(r['contact_id'],'')
   self.fill(title,rows)
  if package_id:
   for i,r in enumerate(self.data.get('Bidding',[])):
    if r['id']==package_id: self.tables['Bidding'].selectRow(i); break
  self.refresh_bids()
  # Include coordination deadlines and meetings in the operational dashboard and timeline.
  active={p['id'] for p in self.store.all('projects') if not p['archived']}
  extra=[]
  for table,label in [('work_packages','Coordination'),('registers','Register'),('bid_packages','Bid deadline'),('meetings','Meeting')]:
   for r in self.store.all(table):
    if r['project_id'] not in active or r['status'] in ('Completed','Approved','Closed','Cancelled','Awarded','Held'): continue
    deadline=r.get('deadline',r.get('meeting_date',''))
    extra.append(dict(_source_table=table,_source_id=r['id'],kind=label,project_id=r['project_id'],project=names.get(r['project_id'],''),item=r['title'],deadline=deadline,status=r['status'],responsible=people.get(r.get('contact_id'),'')))
  dash=self.data.get('Dashboard',[])+extra
  self.fill('Dashboard',sorted(dash,key=lambda r:r['deadline'] or '9999'))
  timeline=self.data.get('Timeline',[])
  for r in extra:
   timeline.append(dict(_source_table=r['_source_table'],_source_id=r['_source_id'],id=None,project_id=r['project_id'],title=r['item'],phase='',deadline=r['deadline'],status=r['status'],project=r['project'],kind=r['kind']))
  self.fill('Timeline',sorted(timeline,key=lambda r:r['deadline'] or '9999'))
 def choices(self,table):
  choices=super().choices(table); choices.update(EXTRA_OPTIONS)
  if table in STATUS_CHOICES: choices['status']=STATUS_CHOICES[table]
  choices['designer_id']=[('Unassigned',None)]+[(c['name'],c['id']) for c in self.store.all('contacts')]
  choices['meeting_id']=[('No meeting',None)]+[(m['title']+' — '+m['meeting_date'],m['id']) for m in self.store.all('meetings')]
  return choices
 def edit(self,title,existing=False):
  from .ui import Form
  if title not in (*DISCIPLINE_PAGES,*REGISTER_PAGES,'Meetings','Bidding'):
   if title=='Timeline' and existing:
    try:
     if self.selected(title).get('id') is None:
      QMessageBox.information(self,'Edit schedule','Edit this item in its discipline, meeting, register, bidding, corrections or violations section.'); return
    except ValueError: pass
   return super().edit(title,existing)
  def action():
   table='work_packages' if title in DISCIPLINE_PAGES else 'registers' if title in REGISTER_PAGES else 'meetings' if title=='Meetings' else 'bid_packages'
   if not self.store.all('projects'): raise ValueError('Create a project first')
   row=self.selected(title) if existing else {**DEFAULTS.get(table,{}),'project_id':self.project_filter.currentData()}
   choices=self.choices(table)
   if title in DISCIPLINE_PAGES:
    choices['discipline']=DISCIPLINE_PAGES[title]
   if title in REGISTER_PAGES:
    choices['record_type']=[REGISTER_PAGES[title]] if REGISTER_PAGES[title] else ['Punch Item','Change Request']
   fields=[k for k in FIELDS[table] if table!='registers' or k not in PERMIT_COLUMNS]
   form=Form(self,('Edit ' if existing else 'New ')+title,fields,row,choices)
   form.persist=lambda data:self.store.save(table,data,row['id'] if existing else None)
   form.enable_draft(table,row['id'] if existing else None)
   if form.exec(): self.refresh()
  self.guard(action)
 def refresh_bids(self):
  if 'Bids' not in self.tables: return
  row=self.tables['Bidding'].currentRow(); packages=self.data.get('Bidding',[])
  if row<0 or row>=len(packages):
   self.fill('Bids',[])
   if hasattr(self,'bid_summary'): self.bid_summary.setText('Select a package to view bidder estimates.')
   return
  package=packages[row]; rows=self.store.bid_comparison(package['id'])
  for r in rows: r.update(project_id=package['project_id'])
  self.fill('Bids',rows)
  if hasattr(self,'bid_summary'): self.bid_summary.setText(f'{package["title"]} · {len(rows)} estimates. Totals include checked items only. Compare currencies separately and review exclusions before awarding.')
 def edit_bid(self,existing=False):
  from .ui import Form
  def action():
   package=self.selected('Bidding'); row=self.selected('Bids') if existing else {**DEFAULTS['bids'],'package_id':package['id']}
   if existing: row=self.store.rows('SELECT * FROM bids WHERE id=?',(row['id'],))[0]
   choices=self.choices('bids'); choices['package_id']=[(package['title'],package['id'])]
   form=Form(self,'Edit bidder estimate' if existing else 'New bidder estimate',FIELDS['bids'],row,choices)
   form.persist=lambda data:self.store.save('bids',data,row['id'] if existing else None)
   form.enable_draft('bids',row['id'] if existing else None)
   if form.exec(): self.refresh()
  self.guard(action)
 def meeting_task(self):
  from .ui import Form
  def action():
   meeting=self.selected('Meetings'); data=dict(project_id=meeting['project_id'],meeting_id=meeting['id'],title='Action: '+meeting['title'],contact_id=meeting['contact_id'],status='Not Started',priority='Normal',notes='Meeting decisions: '+meeting['decisions']+'\nMinutes: '+meeting['minutes'])
   choices=self.choices('tasks'); choices['project_id']=[(meeting['project'],meeting['project_id'])]; choices['meeting_id']=[(meeting['title'],meeting['id'])]
   form=Form(self,'Create assigned meeting action',FIELDS['tasks'],data,choices); form.persist=lambda values:self.store.save('tasks',values); form.enable_draft('tasks')
   if form.exec(): self.refresh()
  self.guard(action)
 def cost_items(self):
  from .ui import Form
  def action():
   selected=self.selected('Bids'); bid_id=selected['id']
   dlg=QDialog(self); dlg.setWindowTitle('Cost items — '+selected['title']); dlg.resize(1200,720); layout=QVBoxLayout(dlg)
   hint=QLabel('Enter quantities or length × width in matching units. Waste applies to materials only. Labor = quantity × hours per unit × hourly rate. Unchecked alternates are excluded.'); hint.setWordWrap(True); layout.addWidget(hint)
   buttons=QHBoxLayout(); layout.addLayout(buttons); table=DataTable();  table.setEditTriggers(QAbstractItemView.NoEditTriggers); layout.addWidget(table); summary=QLabel(); summary.setWordWrap(True); summary.setTextInteractionFlags(Qt.TextSelectableByMouse); layout.addWidget(summary)
   items=[]
   def reload():
    items[:]=self.store.rows('SELECT * FROM bid_items WHERE bid_id=? ORDER BY id',(bid_id,)); display=[]
    for item in items:
     totals=line_totals(item)
     display.append(dict(title=item['title'],area=item['building_area'],material=item['material'],type=item['item_type'],included='Yes' if item['included'] else 'No',quantity=str(totals['effective_quantity']),unit=item['unit'],labor_hours=str(totals['labor_hours']),materials=str(totals['materials']),labor=str(totals['labor']),equipment=str(totals['equipment']),subcontract=str(totals['subcontract']),other=str(totals['other']),total=str(totals['direct_total'])))
    keys=list(display[0]) if display else []; table.setColumnCount(len(keys)); table.setRowCount(len(display)); table.setHorizontalHeaderLabels([k.replace('_',' ').title() for k in keys]); table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    for i,r in enumerate(display):
     for j,k in enumerate(keys): table.setItem(i,j,QTableWidgetItem(str(r[k])))
    totals=self.store.bid_totals(bid_id)
    summary.setText('  |  '.join(f'{k.replace("_"," ").title()}: {v}' for k,v in totals.items()))
   def edit_item(existing=False,duplicate=False):
    def perform():
     if existing or duplicate:
      i=table.currentRow()
      if i<0: raise ValueError('Select a cost item first')
      record=dict(items[i])
      if duplicate: record['title']+=' (copy)'
     else: record={**DEFAULTS['bid_items'],'bid_id':bid_id}
     choices=self.choices('bid_items'); choices['bid_id']=[(selected['title'],bid_id)]
     form=Form(dlg,'Edit cost item' if existing else 'New cost item',FIELDS['bid_items'],record,choices)
     form.persist=lambda values:self.store.save('bid_items',values,record['id'] if existing else None)
     form.enable_draft('bid_items',record['id'] if existing else None)
     if form.exec(): reload(); self.refresh_bids()
    self.guard(perform)
   def export_items():
    def perform():
     path,_=QFileDialog.getSaveFileName(dlg,'Export cost breakdown','bid-cost-items.csv','CSV (*.csv)')
     if path:
      rows=[]
      for item in items: rows.append({**item,**{k:str(v) for k,v in line_totals(item).items()}})
      self.store.export(path,rows)
    self.guard(perform)
   def delete_items(all_listed=False):
    def perform():
     indexes=range(len(items)) if all_listed else table.selected_record_rows()
     if self.confirm_delete([('bid_items',items[i]['id']) for i in indexes],'estimate cost items'): reload(); self.refresh_bids()
    self.guard(perform)
   table.delete_selected=lambda:delete_items(); table.delete_listed=lambda:delete_items(True)
   self.button(buttons,'Export DOCX',lambda:self.export_rows_dialog('Bid cost breakdown',[{**item,**{k:str(v) for k,v in line_totals(item).items()}} for item in items],'docx'))
   self.button(buttons,'Delete selected',lambda:delete_items()); self.button(buttons,'Delete all items',lambda:delete_items(True))
   self.button(buttons,'+ Cost item',lambda:edit_item()); self.button(buttons,'Edit selected',lambda:edit_item(True)); self.button(buttons,'Duplicate selected',lambda:edit_item(duplicate=True)); self.button(buttons,'Export cost breakdown CSV',export_items); self.button(buttons,'Close',dlg.accept); table.doubleClicked.connect(lambda _:edit_item(True)); reload(); compact_dialog(dlg,{'+ Cost item','Edit selected'}); dlg.exec(); self.refresh()
  self.guard(action)
 def compare_bids(self):
  import html
  def action():
   package=self.selected('Bidding'); rows=self.store.bid_comparison(package['id']); e=lambda v:html.escape(str(v))
   out='<h1>'+e(package['title'])+'</h1><p>Scope: '+e(package['scope'])+'</p><p>Totals are sorted within each currency. Check exclusions, included alternates and schedule before selecting a bidder.</p>'
   for row in rows:
    out+='<h2>'+e(row['title'])+' — '+e(row['currency'])+' '+e(row['total'])+'</h2><p>'+'<br>'.join(e(k)+': '+e(v) for k,v in row.items())+'</p>'
   self.show_text('Bid comparison',out,html=True)
  self.guard(action)
 def export_comparison(self):
  def action():
   package=self.selected('Bidding'); path,_=QFileDialog.getSaveFileName(self,'Export bid comparison','bid-comparison.csv','CSV (*.csv)')
   if path: self.store.export(path,self.store.bid_comparison(package['id']))
  self.guard(action)
 def export_page(self,title):
  def action():
   path,_=QFileDialog.getSaveFileName(self,'Export '+title,title+'.csv','CSV (*.csv)')
   if path: self.store.export(path,self.data[title])
  self.guard(action)
 def print_bid(self):
  from PySide6.QtGui import QTextDocument
  from PySide6.QtPrintSupport import QPrinter,QPrintPreviewDialog
  def action():
   bid=self.selected('Bids'); doc=QTextDocument(); doc.setHtml(self.store.bid_report(bid['id'])); printer=QPrinter(QPrinter.HighResolution); preview=QPrintPreviewDialog(printer,self); preview.paintRequested.connect(doc.print_); preview.exec()
  self.guard(action)
