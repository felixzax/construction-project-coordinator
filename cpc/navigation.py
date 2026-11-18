"""Durable per-project section order, independent of visibility and project records."""
ORDER_AREAS=('sidebar','hidden')
ORDER_SCHEMA='''
CREATE TABLE project_section_order(project_id INTEGER NOT NULL REFERENCES projects(id),area TEXT NOT NULL CHECK(area IN ('sidebar','hidden')),section TEXT NOT NULL,position INTEGER NOT NULL CHECK(position>=0),PRIMARY KEY(project_id,area,section),UNIQUE(project_id,area,position));
'''

def normalized_order(value,defaults):
 if not isinstance(value,(list,tuple)):value=[]
 result=[]
 for section in value:
  if isinstance(section,str) and section in defaults and section not in result:result.append(section)
 return result+[section for section in defaults if section not in result]

class NavigationStore:
 def migrate_navigation(self):
  if self.db.execute('PRAGMA user_version').fetchone()[0]>=9:return
  self.db.executescript('BEGIN IMMEDIATE;'+ORDER_SCHEMA+'PRAGMA user_version=9;COMMIT;')
 def section_order(self,pid,area):
  from .development_ui import NAVIGATION
  if area not in ORDER_AREAS:raise ValueError('Choose sidebar or hidden order')
  rows=self.rows('SELECT section FROM project_section_order WHERE project_id=? AND area=? ORDER BY position',(pid,area))
  return normalized_order([r['section'] for r in rows],NAVIGATION)
 def set_section_order(self,pid,area,sections):
  from .development_ui import NAVIGATION
  if area not in ORDER_AREAS:raise ValueError('Choose sidebar or hidden order')
  if not self.rows('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Select an existing project')
  if not isinstance(sections,(list,tuple)) or any(not isinstance(s,str) or s not in NAVIGATION for s in sections) or len(set(sections))!=len(sections):raise ValueError('Section order must contain known, unique categories')
  order=normalized_order(sections,NAVIGATION)
  with self.db:
   self.db.execute('DELETE FROM project_section_order WHERE project_id=? AND area=?',(pid,area))
   self.db.executemany('INSERT INTO project_section_order(project_id,area,section,position) VALUES(?,?,?,?)',[(pid,area,s,i) for i,s in enumerate(order)])
 def validate_section_orders(self):
  from .development_ui import NAVIGATION
  groups={}
  for row in self.rows('SELECT * FROM project_section_order ORDER BY position'):
   if row['area'] not in ORDER_AREAS or row['section'] not in NAVIGATION or not isinstance(row['position'],int) or row['position']<0:raise ValueError('Backup has invalid section ordering')
   groups.setdefault((row['project_id'],row['area']),[]).append(row)
  for rows in groups.values():
   if len({r['section'] for r in rows})!=len(rows) or [r['position'] for r in rows]!=list(range(len(rows))):raise ValueError('Backup has duplicate or incomplete section positions')
