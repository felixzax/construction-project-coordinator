"""Local sidebar color markers, independent of records, visibility and order."""
import json,re
from PySide6.QtCore import Qt,QSettings
from PySide6.QtGui import QColor,QIcon,QPixmap,QPainter,QPen
from PySide6.QtWidgets import QColorDialog,QMenu

COLOR_ROLE=int(Qt.UserRole)+1
PALETTE={'Blue':'#60a5fa','Teal':'#2dd4bf','Green':'#4ade80','Amber':'#fbbf24','Orange':'#fb923c','Red':'#f87171','Purple':'#c084fc','Gray':'#a8b3c4'}
KEY='navigation/section_colors'
def valid_color(value):return isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value) is not None

def swatch(value):
 pixmap=QPixmap(16,16);pixmap.fill(Qt.transparent);painter=QPainter(pixmap);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(QPen(QColor('#94a3b8'),.6));painter.setBrush(QColor(value));painter.drawRoundedRect(2,2,12,12,3,3);painter.end();return QIcon(pixmap)

class SectionColorsUI:
 def section_colors(self):
  try:data=json.loads(self.appearance_settings.value(KEY,'{}'))
  except (ValueError,TypeError):return {}
  if not isinstance(data,dict):return {}
  return {k:v.lower() for k,v in data.items() if k in self.navigation and valid_color(v)}
 def save_section_colors(self,colors):
  if not isinstance(colors,dict) or any(k not in self.navigation or not valid_color(v) for k,v in colors.items()):raise ValueError('Choose a valid section and opaque color')
  previous=self.appearance_settings.value(KEY,'{}');self.appearance_settings.setValue(KEY,json.dumps({k:v.lower() for k,v in colors.items()},sort_keys=True));self.appearance_settings.sync()
  if self.appearance_settings.status()!=QSettings.NoError:
   self.appearance_settings.setValue(KEY,previous);raise ValueError('Unable to save section colors')
  self.apply_section_colors()
 def set_section_color(self,title,color=None):
  if title not in self.navigation:raise ValueError('Unknown section')
  colors=self.section_colors()
  if color is None:colors.pop(title,None)
  elif valid_color(color):colors[title]=color.lower()
  else:raise ValueError('Choose a valid color')
  self.save_section_colors(colors)
 def apply_section_colors(self):
  colors=self.section_colors()
  for name in ('nav','hidden_sections_list'):
   view=getattr(self,name,None)
   if view is None:continue
   for i in range(view.count()):
    item=view.item(i);title=item.data(Qt.UserRole);color=colors.get(title);item.setData(COLOR_ROLE,color)
    # Rebuild rather than append tooltips on every refresh.
    instruction='Hidden categories can be restored here' if title=='Hidden sections' else 'Drag or Alt+Up/Down to reorder; eye or Ctrl+H to hide/restore.'
    item.setToolTip(title+' — '+instruction+' Right-click for section colors.'+(' Color: '+color if color else ''))
    item.setData(Qt.AccessibleDescriptionRole,'Section color '+color if color else 'No section color')
   view.viewport().update()
 def choose_section_color(self,title):
  current=QColor(self.section_colors().get(title,'#60a5fa'));color=QColorDialog.getColor(current,self,'Section color — '+title)
  if color.isValid():self.guard(lambda:self.set_section_color(title,color.name(QColor.HexRgb)))
 def use_suggested_section_colors(self):
  # Stable category identities retain the same suggested color after dragging.
  explicit={'Architecture':'Blue','Engineering':'Teal','Electrical':'Amber','Plumbing':'Blue','Mechanical / HVAC':'Orange','Site & Civil':'Green','Other Trades':'Gray','Permits':'Purple','Regulatory & Permits':'Purple','Tasks':'Orange','Contacts':'Teal','Meetings':'Purple','Documents':'Blue','Budgets':'Green','Contracts':'Teal','Receipts':'Green','Corrections':'Red','Violations':'Red','Approvals':'Green'}
  names=list(PALETTE);self.save_section_colors({title:PALETTE[explicit.get(title,names[i%len(names)])] for i,title in enumerate(self.navigation)})
 def add_section_color_menu(self,menu,title):
  colors=QMenu('Section color',menu);menu.addMenu(colors);menu._section_color_menu=colors;selected=self.section_colors().get(title)
  action=colors.addAction('No color');action.setCheckable(True);action.setChecked(selected is None);action.triggered.connect(lambda:self.guard(lambda:self.set_section_color(title)))
  for label,value in PALETTE.items():
   action=colors.addAction(swatch(value),label);action.setCheckable(True);action.setChecked(selected==value);action.triggered.connect(lambda checked=False,v=value:self.guard(lambda:self.set_section_color(title,v)))
  colors.addSeparator();colors.addAction('Custom color…',lambda:self.choose_section_color(title));colors.addSeparator();colors.addAction('Use suggested colors for all sections',lambda:self.guard(self.use_suggested_section_colors));colors.addAction('Clear all section colors',lambda:self.guard(lambda:self.save_section_colors({})))
