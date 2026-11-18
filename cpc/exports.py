"""CSV and Word exports for department coverage and visible section records."""
from datetime import datetime
from pathlib import Path


def write_docx(path,title,rows,project='All projects'):
 from docx import Document
 from docx.shared import Inches,Pt
 doc=Document(); section=doc.sections[0]; section.top_margin=Inches(.65); section.bottom_margin=Inches(.65)
 doc.styles['Normal'].font.name='Calibri'; doc.styles['Normal'].font.size=Pt(10)
 doc.core_properties.title=title; doc.core_properties.author='Construction Project Coordinator'; doc.core_properties.subject='Locally generated coordination report'
 doc.add_heading(title,0); doc.add_paragraph('Project: '+project); doc.add_paragraph('Generated: '+datetime.now().strftime('%Y-%m-%d %H:%M'))
 doc.add_paragraph(f'{len(rows)} record(s). Department reports include tagged related records; section reports include the listed records under current filters.')
 if not rows: doc.add_paragraph('No matching records.')
 for index,row in enumerate(rows,1):
  label=row.get('title') or row.get('name') or row.get('label') or row.get('requirement') or row.get('revision') or f'Record {index}'
  kind=row.get('record_type','')
  doc.add_heading((str(kind)+' — ' if kind else '')+str(label),2)
  table=doc.add_table(rows=0,cols=2); table.style='Light Shading Accent 1'
  for key,value in row.items():
   if key=='id' or key.startswith('_') or key.endswith('_id'): continue
   if value in ('',None): continue
   if key in ('completed','included','requirements_reviewed','hidden','is_required','include_in_budget') and value in (0,1): value='Yes' if value else 'No'
   cells=table.add_row().cells; cells[0].text=key.replace('_',' ').title(); cells[1].text=str(value)
 doc.save(path)


def department_rows(store,disciplines,project_id=None,query=''):
 projects={p['id']:p['name'] for p in store.all('projects')}; contacts={c['id']:c['name'] for c in store.all('contacts')}; result=[]
 def add(kind,row,details='',source_url='',currency='',total='',cost=None):
  pid=store.project_for('bids' if kind=='Bid estimate' else 'bid_items' if kind=='Cost item' else '',row)
  if pid is None: pid=row.get('project_id')
  if project_id and pid!=project_id: return
  record=dict(record_type=kind,title=row.get('title',row.get('name','')),project=projects.get(pid,''),discipline=row.get('discipline',''),building_area=row.get('building_area',''),responsible=contacts.get(row.get('contact_id',row.get('designer_id')),''),status=row.get('status',''),deadline=row.get('deadline',''),details=details,source_url=source_url,currency=currency,total=str(total))
  record.update({key:row.get(key,'') for key in ['site_address','location','required_fix','authority','code_reference','resolved_date']})
  record.update({key:'' for key in ['quantity','unit','material','material_unit_cost','labor_hours','labor_rate','material_cost','labor_cost','equipment_cost','subcontract_cost','included','estimated_amount','actual_amount','variance_amount']}); record.update(cost or {})
  if query and query.lower() not in ' '.join(str(v) for v in record.values()).lower(): return
  result.append(record)
 for table,kind in [('work_packages','Coordination'),('tasks','Task'),('documents','Plan / document'),('registers','Development register'),('bid_packages','Bid package'),('receipts','Supplier receipt'),('issues','Correction / violation'),('contracts','Contract'),('budgets','Budget'),('scope_items','System / requirement')]:
  for row in store.all(table):
   if row.get('discipline') not in disciplines: continue
   details=' | '.join(f'{key.replace("_"," ")}: {row[key]}' for key in ('scope','requirements','notes','reference','jurisdiction_type','jurisdiction_name','department','sheet_number','drawing_type','scale','issue_purpose','response','supplier_name','approval_notes','site_address','location','required_fix','code_reference','authority','resolution_notes','contractor_name','contract_number','system_type','energy_source','applicability','specifications','manufacturer','model') if row.get(key))
   url=row.get('requirements_url','')
   if table=='documents':
    versions=store.versions(row['id'])
    if versions:
     latest=versions[0]; row=dict(row,status=latest['status']); details+=' | Revision: '+latest['revision']+' | Requirements: '+latest['requirements']+' | File: '+latest['file_path']
   if table=='issues':kind=row['issue_type']
   if table in ('contracts','budgets'):
    values=store.contract_totals(row['id']) if table=='contracts' else store.budget_totals(row['id'])
    add(kind,row,details+' | '+' | '.join(k+': '+str(v) for k,v in values.items()),currency=row['currency'],total=values['adjusted_amount'] if table=='contracts' else values['total_budget'])
   elif table=='receipts':
    from .receipts import receipt_variance
    add(kind,row,details,url,currency=row['currency'],total=row['actual_amount'],cost={key:row.get(key,'') for key in ['estimated_amount','actual_amount']}|{'variance_amount':receipt_variance(row)})
   else: add(kind,row,details,url)
   if table=='registers' and row['record_type']=='Permit':
    for item in store.permit_requirements(row['id']):
     add('Permit requirement',dict(row,title=item['title'],status='Ready' if item['completed'] else 'Outstanding'),item['notes'],item['source_url'] or url)
   if table=='bid_packages':
    for bid in store.rows('SELECT * FROM bids WHERE package_id=?',(row['id'],)):
     totals=store.bid_totals(bid['id']); context=dict(row,title=bid['title'],contact_id=bid['contact_id'],status=bid['status'])
     add('Bid estimate',context,'Exclusions: '+bid['exclusions']+' | Schedule: '+bid['schedule_notes'],currency=bid['currency'],total=totals['total'])
     from .development import line_totals
     for item in store.rows('SELECT * FROM bid_items WHERE bid_id=? ORDER BY id',(bid['id'],)):
      values=line_totals(item); item_context=dict(context,title=item['title'],building_area=item['building_area'],status='Included' if item['included'] else 'Excluded')
      cost=dict(quantity=str(values['effective_quantity']),unit=item['unit'],material=item['material'],material_unit_cost=item['material_unit_cost'],labor_hours=str(values['labor_hours']),labor_rate=item['labor_rate'],material_cost=str(values['materials']),labor_cost=str(values['labor']),equipment_cost=str(values['equipment']),subcontract_cost=str(values['subcontract']),included=item['included'])
      add('Cost item',item_context,item['item_type']+' | Specification: '+item['specification']+' | Estimate: '+bid['title'],currency=bid['currency'],total=values['direct_total'],cost=cost)
 systems={r['id']:r for r in store.all('scope_items')}
 for table,label in [('custom_fields','Custom system information'),('rebates','Rebate / incentive')]:
  for row in store.all(table):
   system=systems.get(row['scope_item_id'])
   if not system or system['discipline'] not in disciplines:continue
   details=' | '.join(k.replace('_',' ')+': '+str(v) for k,v in row.items() if k not in ('id','project_id','scope_item_id','title') and v not in ('',None))
   add(label,dict(system,**{k:v for k,v in row.items() if k not in ('id','scope_item_id')}),details,source_url=row.get('requirements_url',''))
 for contact in store.all('contacts'):
  if contact.get('discipline') not in disciplines: continue
  links=store.rows('SELECT project_id FROM project_contacts WHERE contact_id=?',(contact['id'],))
  if not links and not project_id: links=[{'project_id':None}]
  for link in links:
   add('Contact',dict(contact,project_id=link['project_id'],contact_id=contact['id']),f'{contact["role"]} | {contact["company"]} | {contact["email"]} | {contact["phone"]}')
 return result


class ExportUI:
 def build_page(self,title):
  super().build_page(title)
  if title not in self.tables: return
  from PySide6.QtWidgets import QHBoxLayout
  page=self.stack.widget(self.stack.count()-1); bar=QHBoxLayout(); page.layout().addLayout(bar)
  from .development_ui import DISCIPLINE_PAGES
  label='department report' if title in DISCIPLINE_PAGES else 'listed records'
  self.button(bar,'Export '+label+' CSV',lambda _,t=title:self.export_section(t,'csv'))
  self.button(bar,'Export '+label+' DOCX',lambda _,t=title:self.export_section(t,'docx'))
 def rows_for_export(self,title):
  from .development_ui import DISCIPLINE_PAGES
  if title in DISCIPLINE_PAGES:
   return department_rows(self.store,DISCIPLINE_PAGES[title],self.project_filter.currentData(),getattr(self,'filter_'+title).text())
  rows=[]
  for row in self.data.get(title,[]):
   rows.append({k:v for k,v in row.items() if k!='id' and not k.startswith('_') and not k.endswith('_id')})
  return rows
 def export_section(self,title,kind):
  self.export_rows_dialog(title,self.rows_for_export(title),kind)
 def export_rows_dialog(self,title,rows,kind):
  from PySide6.QtWidgets import QFileDialog
  def action():
   suffix=kind.lower(); safe=''.join(c if c.isalnum() or c in '-_' else '-' for c in title)
   path,_=QFileDialog.getSaveFileName(self,'Export '+title,safe+'.'+suffix,'Word document (*.docx)' if suffix=='docx' else 'CSV (*.csv)')
   if not path: return
   if not Path(path).suffix: path+='.'+suffix
   if suffix=='docx': write_docx(path,title,rows,self.project_filter.currentText())
   else: self.store.export(path,rows)
   self.statusBar().showMessage('Exported '+str(len(rows))+' record(s) to '+path,10000)
  self.guard(action)
