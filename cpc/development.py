"""Development coordination schema and deterministic estimating calculations."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, time
import html

DISCIPLINES = ['General', 'Architecture', 'Structural Engineering', 'Civil Engineering',
               'Geotechnical Engineering', 'Electrical', 'Plumbing', 'Mechanical / HVAC',
               'Fire Protection', 'Site Work', 'Landscape', 'Interiors', 'Roofing',
               'Concrete', 'Masonry', 'Steel', 'Demolition', 'Utilities']
REGISTER_TYPES = ['RFI', 'Submittal', 'Permit', 'Inspection', 'Punch Item', 'Change Request']
NEW_FIELDS = {
 'work_packages': ['project_id','title','discipline','building_area','contact_id','status','deadline','scope','requirements','notes'],
 'meetings': ['project_id','title','meeting_type','meeting_date','start_time','location','contact_id','attendees','agenda','minutes','decisions','status'],
 'registers': ['project_id','title','record_type','reference','discipline','building_area','contact_id','status','submitted','deadline','response','notes'],
 'bid_packages': ['project_id','title','discipline','building_area','bid_type','scope','deadline','status','notes'],
 'bids': ['package_id','title','contact_id','currency','status','received','valid_until','tax_percent','markup_percent','contingency_percent','discount','exclusions','schedule_notes','notes'],
 'bid_items': ['bid_id','title','item_type','building_area','specification','material','quantity_basis','quantity','length','width','unit','waste_percent','material_unit_cost','labor_hours_per_unit','labor_rate','equipment_unit_cost','subcontract_unit_cost','other_cost','included','notes'],
}
NEW_SCHEMA = '''
CREATE TABLE IF NOT EXISTS work_packages(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,discipline TEXT DEFAULT 'General',building_area TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),status TEXT DEFAULT 'Not Started',deadline TEXT DEFAULT '',scope TEXT DEFAULT '',requirements TEXT DEFAULT '',notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS meetings(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,meeting_type TEXT DEFAULT 'Coordination',meeting_date TEXT NOT NULL,start_time TEXT DEFAULT '',location TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),attendees TEXT DEFAULT '',agenda TEXT DEFAULT '',minutes TEXT DEFAULT '',decisions TEXT DEFAULT '',status TEXT DEFAULT 'Scheduled');
CREATE TABLE IF NOT EXISTS registers(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,record_type TEXT DEFAULT 'RFI',reference TEXT DEFAULT '',discipline TEXT DEFAULT 'General',building_area TEXT DEFAULT '',contact_id INTEGER REFERENCES contacts(id),status TEXT DEFAULT 'Open',submitted TEXT DEFAULT '',deadline TEXT DEFAULT '',response TEXT DEFAULT '',notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS bid_packages(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES projects(id),title TEXT NOT NULL,discipline TEXT DEFAULT 'General',building_area TEXT DEFAULT '',bid_type TEXT DEFAULT 'Lump Sum',scope TEXT DEFAULT '',deadline TEXT DEFAULT '',status TEXT DEFAULT 'Draft',notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS bids(id INTEGER PRIMARY KEY,package_id INTEGER NOT NULL REFERENCES bid_packages(id),title TEXT NOT NULL,contact_id INTEGER REFERENCES contacts(id),currency TEXT DEFAULT 'USD',status TEXT DEFAULT 'Draft',received TEXT DEFAULT '',valid_until TEXT DEFAULT '',tax_percent TEXT DEFAULT '0',markup_percent TEXT DEFAULT '0',contingency_percent TEXT DEFAULT '0',discount TEXT DEFAULT '0',exclusions TEXT DEFAULT '',schedule_notes TEXT DEFAULT '',notes TEXT DEFAULT '');
CREATE UNIQUE INDEX IF NOT EXISTS one_award_per_package ON bids(package_id) WHERE status='Awarded';
CREATE TABLE IF NOT EXISTS bid_items(id INTEGER PRIMARY KEY,bid_id INTEGER NOT NULL REFERENCES bids(id),title TEXT NOT NULL,item_type TEXT DEFAULT 'Base',building_area TEXT DEFAULT '',specification TEXT DEFAULT '',material TEXT DEFAULT '',quantity_basis TEXT DEFAULT 'Manual',quantity TEXT DEFAULT '1',length TEXT DEFAULT '0',width TEXT DEFAULT '0',unit TEXT DEFAULT 'each',waste_percent TEXT DEFAULT '0',material_unit_cost TEXT DEFAULT '0',labor_hours_per_unit TEXT DEFAULT '0',labor_rate TEXT DEFAULT '0',equipment_unit_cost TEXT DEFAULT '0',subcontract_unit_cost TEXT DEFAULT '0',other_cost TEXT DEFAULT '0',included INTEGER DEFAULT 1,notes TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS work_project ON work_packages(project_id);
CREATE INDEX IF NOT EXISTS meetings_project ON meetings(project_id);
CREATE INDEX IF NOT EXISTS register_project ON registers(project_id);
CREATE INDEX IF NOT EXISTS bid_package_project ON bid_packages(project_id);
CREATE INDEX IF NOT EXISTS bids_package ON bids(package_id);
CREATE INDEX IF NOT EXISTS items_bid ON bid_items(bid_id);
'''
ADDED_COLUMNS = {
 'tasks': {'discipline':"TEXT DEFAULT 'General'", 'building_area':"TEXT DEFAULT ''", 'meeting_id':'INTEGER REFERENCES meetings(id)'},
 'documents': {'discipline':"TEXT DEFAULT 'General'", 'sheet_number':"TEXT DEFAULT ''", 'drawing_type':"TEXT DEFAULT 'Plan Set'", 'building_area':"TEXT DEFAULT ''", 'scale':"TEXT DEFAULT ''", 'designer_id':'INTEGER REFERENCES contacts(id)', 'issue_purpose':"TEXT DEFAULT ''"},
 'contacts': {'discipline':"TEXT DEFAULT 'General'"},
}
BID_NUMBERS = ['tax_percent','markup_percent','contingency_percent','discount']
ITEM_NUMBERS = ['quantity','length','width','waste_percent','material_unit_cost','labor_hours_per_unit','labor_rate','equipment_unit_cost','subcontract_unit_cost','other_cost']
CENT = Decimal('0.01')
STATUSES = {
 'work_packages':['Not Started','Waiting on Someone','In Progress','Submitted','Approved','Completed'],
 'meetings':['Scheduled','Held','Cancelled'],
 'registers':['Open','In Review','Submitted','Approved','Changes Required','Closed','Cancelled'],
 'bid_packages':['Draft','Invited','Evaluating','Awarded','Closed','Cancelled'],
 'bids':['Draft','Invited','Received','Shortlisted','Awarded','Declined','Withdrawn'],
}

def validate_date(value):
 if value and date.fromisoformat(value).isoformat()!=value:
  raise ValueError('Dates must use YYYY-MM-DD')


def number(value, name='Value'):
 try:
  result=Decimal(str(value if value not in ('',None) else '0'))
 except InvalidOperation:
  raise ValueError(f'{name.replace("_"," ").title()} must be a number') from None
 if not result.is_finite() or result < 0 or result > Decimal('1000000000'):
  raise ValueError(f'{name.replace("_"," ").title()} must be between 0 and 1,000,000,000')
 if result.as_tuple().exponent < -6:
  raise ValueError(f'{name.replace("_"," ").title()} supports at most 6 decimal places')
 return result

def money(value):
 value=Decimal(value)
 if abs(value)>Decimal('1000000000000000'): raise ValueError('Derived cost is too large; check the quantity and unit rates')
 return value.quantize(CENT, rounding=ROUND_HALF_UP)

def line_totals(item):
 n=lambda key:number(item.get(key,'0'),key)
 quantity=n('length')*n('width') if item.get('quantity_basis')=='Area (length × width)' else n('quantity')
 material_quantity=quantity*(1+n('waste_percent')/100)
 labor_hours=quantity*n('labor_hours_per_unit')
 result={'effective_quantity':quantity, 'material_quantity':material_quantity, 'labor_hours':labor_hours,
         'materials':money(material_quantity*n('material_unit_cost')),
         'labor':money(labor_hours*n('labor_rate')),
         'equipment':money(quantity*n('equipment_unit_cost')),
         'subcontract':money(quantity*n('subcontract_unit_cost')),
         'other':money(n('other_cost'))}
 result['direct_total']=sum((result[k] for k in ['materials','labor','equipment','subcontract','other']),Decimal(0))
 return result

class DevelopmentStore:
 def migrate_development(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]==2: return
  self.db.executescript('BEGIN IMMEDIATE;'+NEW_SCHEMA)
  with self.db:
   for table,cols in ADDED_COLUMNS.items():
    present={r[1] for r in self.db.execute(f'PRAGMA table_info({table})')}
    for name,kind in cols.items():
     if name not in present: self.db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
   self.db.execute("UPDATE documents SET discipline='Architecture' WHERE discipline='General' AND category='Architectural Plans'")
   self.db.execute('PRAGMA user_version=2')
 def project_for(self,table,data):
  if table=='projects': return data.get('id')
  if 'project_id' in data: return data['project_id']
  if table=='bids':
   rows=self.rows('SELECT project_id FROM bid_packages WHERE id=?',(data.get('package_id'),))
  elif table=='bid_items':
   rows=self.rows('SELECT p.project_id FROM bids b JOIN bid_packages p ON p.id=b.package_id WHERE b.id=?',(data.get('bid_id'),))
  else: return None
  return rows[0]['project_id'] if rows else None
 def validate_development(self,table,data,row_id):
  for key in ('meeting_date','received','valid_until','submitted'):
   if data.get(key): validate_date(data[key])
  if table=='meetings':
   if not data.get('meeting_date'): raise ValueError('Meeting date is required')
   if data.get('start_time') and time.fromisoformat(data['start_time']).isoformat(timespec='minutes')!=data['start_time']:
    raise ValueError('Start time must use HH:MM (24-hour local time)')
  if table in STATUSES and data.get('status',STATUSES[table][0]) not in STATUSES[table]: raise ValueError('Unknown status')
  if table=='registers' and data.get('record_type','RFI') not in REGISTER_TYPES: raise ValueError('Unknown register type')
  if table=='tasks' and data.get('meeting_id'):
   meeting=self.rows('SELECT project_id FROM meetings WHERE id=?',(data['meeting_id'],))
   if not meeting or meeting[0]['project_id']!=data.get('project_id'): raise ValueError('Task and meeting must belong to the same project')
  if row_id and table in ('bid_packages','bids','bid_items','meetings'):
   relation={'bid_packages':'project_id','bids':'package_id','bid_items':'bid_id','meetings':'project_id'}[table]
   current=self.rows(f'SELECT {relation} FROM {table} WHERE id=?',(row_id,))
   if current and relation in data and data[relation]!=current[0][relation]:
    raise ValueError('This parent association is fixed. Create a new record to move it to another project/package.')
  if table in ('bids','bid_items'):
   for key in (BID_NUMBERS if table=='bids' else ITEM_NUMBERS):
    default='1' if key=='quantity' else '0'
    value=number(data.get(key,default),key)
    if key.endswith('_percent') and value>100: raise ValueError(f'{key} cannot exceed 100%')
    data[key]=str(value)
  if table=='bids':
   if data.get('currency','USD') not in ('USD','CAD','EUR','GBP','AUD'): raise ValueError('Unsupported currency')
   if data.get('received') and data.get('valid_until') and data['valid_until']<data['received']: raise ValueError('Valid-until date cannot precede received date')
   if data.get('status')=='Awarded':
    others=self.rows("SELECT id FROM bids WHERE package_id=? AND status='Awarded' AND id!=?",(data.get('package_id'),row_id or -1))
    if others: raise ValueError('This package already has an awarded bid. Change its status before awarding another.')
   if not row_id and number(data.get('discount',0))>0:
    raise ValueError('Add bid items before applying a discount')
   if row_id:
    self.bid_totals(row_id, overrides=data)
  if table=='bid_items':
   if data.get('quantity_basis','Manual') not in ('Manual','Area (length × width)'): raise ValueError('Unknown quantity basis')
   if data.get('item_type','Base') not in ('Base','Allowance','Alternate'): raise ValueError('Unknown item type')
   if data.get('included',1) not in (0,1): raise ValueError('Included must be yes or no')
   line_totals(data)
   if data.get('bid_id'): self.bid_totals(data['bid_id'],replacement=(row_id,data))
 def bid_totals(self,bid_id,overrides=None,replacement=None):
  rows=self.rows('SELECT * FROM bids WHERE id=?',(bid_id,))
  if not rows: raise ValueError('Bid not found')
  bid=dict(rows[0]); bid.update(overrides or {})
  items=self.rows('SELECT * FROM bid_items WHERE bid_id=? ORDER BY id',(bid_id,))
  if replacement:
   rid,new=replacement
   items=[i for i in items if i['id']!=rid]+[new]
  totals={k:Decimal(0) for k in ['materials','labor','equipment','subcontract','other','labor_hours']}
  included=0
  for item in items:
   if not item.get('included',1): continue
   included+=1; line=line_totals(item)
   for key in totals: totals[key]+=line[key]
  subtotal=sum((totals[k] for k in ['materials','labor','equipment','subcontract','other']),Decimal(0))
  tax=money(totals['materials']*number(bid.get('tax_percent',0))/100)
  markup=money(subtotal*number(bid.get('markup_percent',0))/100)
  contingency=money(subtotal*number(bid.get('contingency_percent',0))/100)
  discount=money(number(bid.get('discount',0)))
  before_discount=subtotal+tax+markup+contingency
  if discount>before_discount: raise ValueError('Discount cannot exceed the total before discount')
  totals.update(subtotal=subtotal,tax=tax,markup=markup,contingency=contingency,discount=discount,total=before_discount-discount,included_items=included,currency=bid['currency'])
  return totals
 def bid_comparison(self,package_id):
  rows=self.rows('SELECT b.*,c.name AS bidder FROM bids b LEFT JOIN contacts c ON c.id=b.contact_id WHERE package_id=?',(package_id,))
  result=[]
  for bid in rows:
   totals=self.bid_totals(bid['id'])
   result.append(dict(id=bid['id'],title=bid['title'],bidder=bid['bidder'] or 'Unassigned',currency=bid['currency'],status=bid['status'],**{k:str(totals[k]) for k in ('materials','labor','equipment','subcontract','other','subtotal','tax','markup','contingency','discount','total')},pricing_status='Priced' if totals['included_items'] else 'No included cost items',included_items=totals['included_items'],received=bid['received'],valid_until=bid['valid_until'],exclusions=bid['exclusions'],schedule_notes=bid['schedule_notes']))
  return sorted(result,key=lambda r:(r['currency'],r['included_items']==0,Decimal(r['total'])))
 def bid_report(self,bid_id):
  bid=self.rows('SELECT b.*,p.title AS package,p.project_id FROM bids b JOIN bid_packages p ON p.id=b.package_id WHERE b.id=?',(bid_id,))[0]
  project=self.rows('SELECT name FROM projects WHERE id=?',(bid['project_id'],))[0]
  e=lambda v:html.escape(str(v if v is not None else ''))
  out=f'<h1>Bid estimate: {e(bid["title"])}</h1><p>{e(project["name"])} / {e(bid["package"])} · {e(bid["currency"])} · {e(bid["status"])}</p><p>Exclusions: {e(bid["exclusions"])}</p><p>Schedule: {e(bid["schedule_notes"])}</p><table border="1" cellspacing="0" cellpadding="5"><tr><th>Item / Area / Material</th><th>Type / Included</th><th>Quantity</th><th>Materials</th><th>Labor</th><th>Equipment</th><th>Subcontract</th><th>Other</th><th>Direct total</th></tr>'
  for item in self.rows('SELECT * FROM bid_items WHERE bid_id=? ORDER BY id',(bid_id,)):
   t=line_totals(item)
   out+='<tr>'+''.join('<td>'+e(v)+'</td>' for v in [item['title']+' / '+item['building_area']+' / '+item['material'],item['item_type']+(' / Included' if item['included'] else ' / Excluded'),str(t['effective_quantity'])+' '+item['unit'],t['materials'],t['labor'],t['equipment'],t['subcontract'],t['other'],t['direct_total']])+'</tr>'
  out+='</table><h2>Totals (included items only)</h2>'
  totals=self.bid_totals(bid_id)
  out+=''.join(f'<p>{e(k.replace("_"," ").title())}: {e(v)}</p>' for k,v in totals.items())
  out+='<p>Material waste applies only to material quantity. Tax applies only to materials. Markup and contingency each apply to direct subtotal, without compounding. All quantities and unit rates are user supplied; no unit conversion or market pricing is performed.</p>'
  return out
 def development_report(self,pid):
  e=lambda v:html.escape(str(v if v is not None else ''))
  out=''
  for title,table in [('Discipline coordination','work_packages'),('Meetings','meetings'),('RFIs / Submittals / Permits / Inspections','registers'),('Bid packages','bid_packages')]:
   out+=f'<h2>{title}</h2>'
   for row in self.rows(f'SELECT * FROM {table} WHERE project_id=?',(pid,)):
    out+='<p>'+' | '.join(f'{e(k)}: {e(v)}' for k,v in row.items() if k not in ('id','project_id','contact_id'))+'</p>'
  out+='<h2>Bid comparisons (separate currencies; estimates only)</h2>'
  for package in self.rows('SELECT id,title FROM bid_packages WHERE project_id=?',(pid,)):
   out+=f'<h3>{e(package["title"])}</h3>'
   for bid in self.bid_comparison(package['id']):
    out+=f'<p>{e(bid["title"])} — {e(bid["currency"])} {e(bid["total"])} — {e(bid["status"])} — exclusions: {e(bid["exclusions"])}</p>'
  return out
 def seed_development(self,pid,cid):
  due=date.today().isoformat()
  for discipline,title in [('Architecture','Coordinate accessibility and plan comments'),('Structural Engineering','Review roof equipment loads'),('Electrical','Coordinate panel schedule and lighting'),('Plumbing','Coordinate fixture count and riser diagrams'),('Mechanical / HVAC','Coordinate rooftop HVAC clearances'),('Civil Engineering','Confirm drainage and utility connections')]:
   self.save('work_packages',dict(project_id=pid,title=title,discipline=discipline,building_area='Retail suite',contact_id=cid,status='In Progress',deadline=due,scope='Fictional example coordination scope',requirements='Confirm drawings and responsible consultant',notes='Sample only'))
  self.save('meetings',dict(project_id=pid,title='Weekly design coordination',meeting_type='Design Review',meeting_date=due,start_time='09:00',location='Example site office',contact_id=cid,attendees='Alex Morgan; Casey Rivera (fictional)',agenda='Review MEP clashes and permit comments',minutes='Discussed roof equipment loads and service clearances.',decisions='Request coordinated drawing set.',status='Scheduled'))
  self.save('registers',dict(project_id=pid,title='Confirm electrical service clearance',record_type='RFI',reference='RFI-001',discipline='Electrical',building_area='Service room',contact_id=cid,status='Open',submitted=due,deadline=due,response='',notes='Fictional sample'))
  package=self.save('bid_packages',dict(project_id=pid,title='Retail electrical works',discipline='Electrical',building_area='Retail suite',bid_type='Unit Price',scope='Supply and install lighting and branch circuits',deadline=due,status='Invited',notes='Fictional sample. User-entered prices, not market rates.'))
  for title,person,material,rate in [('Example Electrical A','Casey Rivera','85.00','65'),('Example Electrical B','Taylor Brooks','82.00','70')]:
   bidder=self.save('contacts',dict(name=person,role='Contractor',company=title+' (fictional)',email=person.split()[0].lower()+'@example.com',discipline='Electrical',notes='Fictional bidder; prices are demonstration inputs only'))
   self.associate(pid,bidder)
   bid=self.save('bids',dict(package_id=package,title=title,contact_id=bidder,currency='USD',status='Received',tax_percent='8',markup_percent='10',contingency_percent='5'))
   self.save('bid_items',dict(bid_id=bid,title='LED lighting installation',item_type='Base',building_area='Sales floor',specification='26 51 00',material='Example LED fixtures',quantity_basis='Manual',quantity='20',unit='each',waste_percent='5',material_unit_cost=material,labor_hours_per_unit='0.5',labor_rate=rate,equipment_unit_cost='2',included=1))
