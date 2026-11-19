"""Refresh, recovery, drafts and explicit, backed-up delete controls."""
from .workspace_ui import compact_dialog
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QAction,QKeySequence,QPixmapCache
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QMessageBox,QInputDialog,QApplication,QTableWidgetItem)
from .store import FIELDS
from .table import DataTable

class RecoveryUI:
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  menu=self.menuBar().addMenu('Edit')
  copy=QAction('Copy',self); copy.setShortcut(QKeySequence.Copy); copy.triggered.connect(self.copy_focused); menu.addAction(copy)
  select=QAction('Select all',self); select.setShortcut(QKeySequence.SelectAll); select.triggered.connect(self.select_focused); menu.addAction(select)
  view=self.menuBar().addMenu('Refresh & Recovery')
  refresh=QAction('Refresh and clear display cache',self); refresh.setShortcut('F5'); refresh.triggered.connect(self.refresh_from_disk); view.addAction(refresh)
  recovery=QAction('Recovery workspace',self); recovery.triggered.connect(lambda:self.navigate('Recovery & Data')); view.addAction(recovery)
  toolbar=self.addToolBar('Refresh'); toolbar.setMovable(False); toolbar.addAction(refresh); toolbar.addAction(recovery)
  self.snapshot_timer=QTimer(self); self.snapshot_timer.setInterval(120000); self.snapshot_timer.timeout.connect(self.periodic_snapshot)
  if getattr(self.store,'_session_started',False): self.snapshot_timer.start()
 def copy_focused(self):
  widget=QApplication.focusWidget()
  if isinstance(widget,DataTable): widget.copy_selection()
  elif hasattr(widget,'copy'): widget.copy()
 def select_focused(self):
  widget=QApplication.focusWidget()
  if hasattr(widget,'selectAll'): widget.selectAll()
 def build_page(self,title):
  if title=='Recovery & Data':
   page=QWidget(); layout=QVBoxLayout(page); heading=QLabel('Recovery & Data'); heading.setObjectName('heading'); layout.addWidget(heading)
   hint=QLabel('Refresh clears temporary display caches and reloads saved records. Forms autosave drafts after a 750 ms pause or every 10 seconds while typing. Saved records are committed immediately. Recovery snapshots preserve the database; document files remain in the documents folder.'); hint.setWordWrap(True); layout.addWidget(hint)
   bar=QHBoxLayout(); layout.addLayout(bar); self.button(bar,'Refresh / clear cache (F5)',self.refresh_from_disk); self.button(bar,'Save recovery snapshot',self.manual_snapshot); self.button(bar,'Delete ALL application data',self.delete_application_data)
   layout.addWidget(QLabel('Unfinished forms — resume to review and Save, or discard a selected draft'))
   self.draft_table=DataTable(); layout.addWidget(self.draft_table); bar=QHBoxLayout(); layout.addLayout(bar); self.button(bar,'Resume selected draft',self.resume_draft); self.button(bar,'Discard selected drafts',self.discard_drafts)
   self.draft_table.delete_selected=self.discard_drafts
   layout.addWidget(QLabel('Database recovery snapshots — restoring replaces the current database'))
   self.snapshot_table=DataTable(); layout.addWidget(self.snapshot_table); bar=QHBoxLayout(); layout.addLayout(bar); self.button(bar,'Restore selected snapshot',self.restore_snapshot)
   self.stack.addWidget(page); return
  super().build_page(title)
  if title in self.tables:
   table=self.tables[title]; table.delete_selected=lambda t=title:self.delete_page(t,False); table.delete_listed=lambda t=title:self.delete_page(t,True)
   page=self.stack.widget(self.stack.count()-1); bar=QHBoxLayout(); page.layout().addLayout(bar)
   self.button(bar,'Copy selected cells',table.copy_selection); self.button(bar,'Delete selected records',lambda _,t=title:self.delete_page(t,False)); self.button(bar,'Delete all listed',lambda _,t=title:self.delete_page(t,True))
   if title=='Bidding':
    bids=self.tables['Bids']; bids.delete_selected=lambda:self.delete_page('Bids'); bids.delete_listed=lambda:self.delete_page('Bids',True)
    self.button(bar,'Delete selected bidder estimates',lambda:self.delete_page('Bids'))
 def refresh(self,*args):
  super().refresh(*args)
  if hasattr(self,'draft_table'): self.reload_recovery_lists()
 def reload_recovery_lists(self):
  self._draft_rows=self.store.drafts(); self._snapshot_rows=self.store.recovery_snapshots()
  self.render_recovery_table(self.draft_table,[dict(form=r['target_table'],record=r['row_id'] or 'New',title=r['values'].get('title',r['values'].get('name',r['values'].get('revision',''))),updated=r['updated']) for r in self._draft_rows])
  self.render_recovery_table(self.snapshot_table,[dict(snapshot=r['name'],size_bytes=r['bytes']) for r in self._snapshot_rows])
 def render_recovery_table(self,table,rows):
  keys=list(rows[0]) if rows else []; table.setColumnCount(len(keys)); table.setRowCount(len(rows)); table.setHorizontalHeaderLabels([k.replace('_',' ').title() for k in keys])
  for i,row in enumerate(rows):
   for j,key in enumerate(keys): table.setItem(i,j,QTableWidgetItem(str(row[key])))
  table.resizeColumnsToContents(); table.horizontalHeader().setStretchLastSection(True)
 def source_target(self,title,row):
  from .development_ui import DISCIPLINE_PAGES,REGISTER_PAGES
  if row.get('_source_table'): return row['_source_table'],row['_source_id']
  if title=='Search': return row['type'],row['id']
  mapping={'Approvals':'approvals','Project Profile':'project_profiles','Scope & Systems':'scope_items','Custom Information':'custom_fields','Rebates & Incentives':'rebates','Change Orders':'contract_changes','Projects':'projects','Tasks':'tasks','Contacts':'contacts','Communications':'communications','Documents':'documents','Meetings':'meetings','Bidding':'bid_packages','Bids':'bids','Receipts':'receipts','Corrections':'issues','Violations':'issues','Contracts':'contracts','Budgets':'budgets'}
  if title in DISCIPLINE_PAGES: return 'work_packages',row['id']
  if title in REGISTER_PAGES: return 'registers',row['id']
  if title=='Timeline':
   if row.get('id') is None: raise ValueError('Delete this entry from its source section')
   return ('tasks' if row['kind']=='Task' else 'milestones'),row['id']
  if title not in mapping: raise ValueError('Delete this entry from its source section')
  return mapping[title],row['id']
 def confirm_delete(self,targets,label):
  targets=list(set(targets)); summary=self.store.deletion_summary(targets)
  if not summary: raise ValueError('No saved records selected')
  detail=', '.join(f'{n} {table.replace("_"," ")}' for table,n in summary.items())
  answer=QMessageBox.question(self,'Delete records?',f'Delete {label}?\n\nThis removes {detail}. Related child records are included. Contacts are unassigned from work when deleted. A recovery snapshot is saved first; retained document files are kept.\n\nContinue?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
  if answer!=QMessageBox.Yes: return False
  path=self.store.delete_records(targets); self.statusBar().showMessage('Deleted. Recovery snapshot: '+str(path),12000); return True
 def delete_page(self,title,all_listed=False):
  def action():
   rows=self.data.get(title,[]); indexes=range(len(rows)) if all_listed else self.tables[title].selected_record_rows()
   targets=[self.source_target(title,rows[i]) for i in indexes]
   if not targets: raise ValueError('Select at least one record')
   if self.confirm_delete(targets,('all listed records in ' if all_listed else 'selected records in ')+title): self.refresh()
  self.guard(action)
 def delete_application_data(self):
  def action():
   text,ok=QInputDialog.getText(self,'Delete ALL application data','This removes every project, contact, task, document record, permit, meeting, bid, contract, budget, approval/history, receipt/parts cost, correction, violation and recovery draft across ALL projects. A database recovery snapshot is created first; attached files and snapshots are kept.\nType DELETE ALL to continue:')
   if ok and text=='DELETE ALL':
    path=self.store.delete_all_data(); self.refresh(); self.statusBar().showMessage('All application records deleted. Recovery snapshot: '+str(path),15000)
  self.guard(action)
 def refresh_from_disk(self):
  def action():
   from .ui import Form
   for widget in QApplication.topLevelWidgets():
    if isinstance(widget,Form): widget.save_recovery_draft()
   self.store.clear_display_cache(); QPixmapCache.clear(); self.data.clear(); self.refresh(); self.statusBar().showMessage('Refreshed saved data and cleared display caches. Records and drafts are preserved.',8000)
  self.guard(action)
 def periodic_snapshot(self):
  try: self.store.recovery_snapshot('automatic')
  except Exception as ex: self.statusBar().showMessage('Automatic recovery snapshot failed: '+str(ex),15000)
 def manual_snapshot(self):
  def action():
   path=self.store.recovery_snapshot('automatic'); self.reload_recovery_lists(); self.statusBar().showMessage('Recovery snapshot saved: '+str(path),10000)
  self.guard(action)
 def restore_snapshot(self):
  def action():
   row=self.snapshot_table.currentRow()
   if row<0: raise ValueError('Select a recovery snapshot')
   snapshot=self._snapshot_rows[row]
   if QMessageBox.question(self,'Restore snapshot?','Replace current records with '+snapshot['name']+'? A safety copy of current records is created first.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
    self.store.restore(snapshot['path']); self.refresh(); self.statusBar().showMessage('Recovery snapshot restored.',8000)
  self.guard(action)
 def discard_drafts(self):
  def action():
   rows=self.draft_table.selected_record_rows()
   if not rows: raise ValueError('Select a draft')
   if QMessageBox.question(self,'Discard drafts?',f'Discard {len(rows)} selected unfinished forms?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
    for i in rows: self.store.discard_draft(self._draft_rows[i]['id'])
    self.reload_recovery_lists()
  self.guard(action)
 def resume_draft(self):
  from .ui import Form
  def action():
   index=self.draft_table.currentRow()
   if index<0: raise ValueError('Select an unfinished form')
   draft=self._draft_rows[index]; table=draft['target_table']; rid=draft['row_id']; values=draft['values']; extra=draft['metadata']
   if table=='receipts':values.setdefault('include_in_budget',1)
   if table not in FIELDS and table!='__versions__': raise ValueError('Unsupported recovery form type')
   if table!='__versions__' and rid and not self.store.rows(f'SELECT id FROM {table} WHERE id=?',(rid,)):
    raise ValueError('The original record was deleted. Restore its recovery snapshot first or discard this draft.')
   if table=='__versions__':
    fields=['revision','submitted','status','requirements','file_path']; choices={'status':['Draft','Submitted','Approved','Changes Required']}
   else:
    fields=[key for key in FIELDS[table] if key not in ('completed_on','attachment_path','attachment_name')]; choices=self.choices(table)
    if table=='bids': choices['package_id']=[(p['title'],p['id']) for p in self.store.all('bid_packages')]
    if table=='bid_items': choices['bid_id']=[(p['title'],p['id']) for p in self.store.all('bids')]
    if table=='permit_requirements': choices['register_id']=[(p['title'],p['id']) for p in self.store.all('registers') if p['record_type']=='Permit']
   form=Form(self,'Recover unfinished form',fields,values,choices)
   if table=='__versions__': form.persist=lambda data:self.store.add_version(extra['document_id'],**data)
   else: form.persist=lambda data:self.store.save(table,data,rid)
   form.enable_draft(table,rid,extra,key=draft['id'])
   if form.exec(): self.refresh()
  self.guard(action)
 def history(self):
  from PySide6.QtWidgets import QDialog
  def action():
   document=self.selected('Documents'); dlg=QDialog(self); dlg.setWindowTitle('Version history — '+document['title']); dlg.resize(1050,600); layout=QVBoxLayout(dlg); table=DataTable(); layout.addWidget(table); bar=QHBoxLayout(); layout.addLayout(bar); rows=[]
   def reload():
    rows[:]=self.store.versions(document['id']); self.render_recovery_table(table,[{k:v for k,v in row.items() if k not in ('id','document_id')} for row in rows])
   def remove(all_listed=False):
    def perform():
     indexes=range(len(rows)) if all_listed else table.selected_record_rows()
     if self.confirm_delete([('versions',rows[i]['id']) for i in indexes],'document revisions'): reload()
    self.guard(perform)
   table.delete_selected=lambda:remove(); table.delete_listed=lambda:remove(True)
   def save_original():
    def perform():
     from PySide6.QtWidgets import QFileDialog
     i=table.currentRow()
     if i<0:raise ValueError('Select a revision')
     row=rows[i];extension=Path(row['file_path']).suffix
     path,_=QFileDialog.getSaveFileName(dlg,'Save retained revision copy','revision-'+str(row['id'])+extension,'Original file (*'+extension+')')
     if path:self.store.save_revision_copy(row['id'],path)
    self.guard(perform)
   self.button(bar,'Save selected original file…',save_original)
   self.button(bar,'Export CSV',lambda:self.export_rows_dialog('Document revisions',rows,'csv')); self.button(bar,'Export DOCX',lambda:self.export_rows_dialog('Document revisions',rows,'docx')); self.button(bar,'Copy selected cells',table.copy_selection); self.button(bar,'Delete selected revisions',lambda:remove()); self.button(bar,'Delete all revisions',lambda:remove(True)); self.button(bar,'Close',dlg.accept); reload(); compact_dialog(dlg,{'Save selected original file…'}); dlg.exec(); self.refresh()
  self.guard(action)
 def closeEvent(self,event):
  try: self.store.end_session()
  except Exception as ex:
   QMessageBox.warning(self,'Recovery snapshot unavailable','Saved records are committed, but the final recovery snapshot could not be created: '+str(ex))
  self.snapshot_timer.stop(); super().closeEvent(event)
