"""Scrollable navigation with direct hide/restore controls and one hidden drawer."""
import json
from PySide6.QtCore import Qt,QEvent,QObject,QRect,QSize,QPointF
from PySide6.QtGui import QPainter,QPainterPath,QPen,QColor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QListWidget,QListWidgetItem,QStyledItemDelegate,QAbstractItemView,QMenu
from .scope import PROTECTED_SECTIONS
from .section_list import SectionList
from .navigation import normalized_order

HIDDEN='Hidden sections'
def label(title):return 'Plans & CAD' if title=='Documents' else title

def eye_rect(rect):return QRect(rect.right()-31,rect.top()+(rect.height()-26)//2,27,26)
def paint_eye(painter,rect,restore=False):
 painter.save();painter.setRenderHint(QPainter.Antialiasing);painter.setPen(QPen(QColor('#aac9e9'),1.6));painter.setBrush(Qt.NoBrush)
 center=QPointF(rect.center());x=center.x();y=center.y();path=QPainterPath();path.moveTo(x-9,y);path.cubicTo(x-4,y-7,x+4,y-7,x+9,y);path.cubicTo(x+4,y+7,x-4,y+7,x-9,y);painter.drawPath(path);painter.drawEllipse(QPointF(x,y),2.5,2.5)
 if not restore:painter.drawLine(QPointF(x-8,y-8),QPointF(x+8,y+8))
 painter.restore()

class EyeDelegate(QStyledItemDelegate):
 def __init__(self,parent,restore=False):super().__init__(parent);self.restore=restore
 def paint(self,painter,option,index):
  from PySide6.QtWidgets import QStyleOptionViewItem
  copy=QStyleOptionViewItem(option);self.initStyleOption(copy,index)
  title=index.data(Qt.UserRole)
  if title not in PROTECTED_SECTIONS:
   copy.rect=option.rect.adjusted(0,0,-31,0);super().paint(painter,copy,index);paint_eye(painter,eye_rect(option.rect),self.restore)
  else:super().paint(painter,option,index)
 def sizeHint(self,option,index):return QSize(220,36)

class EyeEvents(QObject):
 def __init__(self,parent,view,callback):
  super().__init__(parent);self.view=view;self.callback=callback;self.suppress_release=False;view.viewport().installEventFilter(self);view.installEventFilter(self)
 def eventFilter(self,obj,event):
  if obj is self.view.viewport() and event.type()==QEvent.MouseButtonPress and event.button()==Qt.LeftButton:
   item=self.view.itemAt(event.position().toPoint())
   if item and item.data(Qt.UserRole) not in PROTECTED_SECTIONS and eye_rect(self.view.visualItemRect(item)).contains(event.position().toPoint()):
    self.suppress_release=True;self.callback(item.data(Qt.UserRole));return True
  if obj is self.view.viewport() and event.type()==QEvent.MouseButtonRelease and self.suppress_release:
   self.suppress_release=False;return True
  if obj is self.view and event.type()==QEvent.KeyPress and event.key()==Qt.Key_H and event.modifiers() & Qt.ControlModifier:
   item=self.view.currentItem()
   if item and item.data(Qt.UserRole) not in PROTECTED_SECTIONS:self.callback(item.data(Qt.UserRole))
   return True
  return super().eventFilter(obj,event)

class SidebarUI:
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.nav.setFixedWidth(250);self.nav.setAccessibleName('Project sections; drag or Alt+Up/Down to reorder, Ctrl+H to hide');self.nav.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel);self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
  self.nav.setItemDelegate(EyeDelegate(self.nav));self._nav_eye_events=EyeEvents(self,self.nav,self.hide_sidebar_section)
  for i in range(self.nav.count()):
   item=self.nav.item(i);title=item.data(Qt.UserRole);item.setToolTip('Hidden categories can be restored here' if title==HIDDEN else f'{label(title)} — hold and drag to reorder; eye or Ctrl+H to hide; Alt+Up/Down to move')
  self.hidden_sections_list.setItemDelegate(EyeDelegate(self.hidden_sections_list,restore=True));self._hidden_eye_events=EyeEvents(self,self.hidden_sections_list,self.restore_sidebar_section)
  self.nav.setContextMenuPolicy(Qt.CustomContextMenu);self.nav.customContextMenuRequested.connect(self.sidebar_menu)
  self.hidden_sections_list.setContextMenuPolicy(Qt.CustomContextMenu);self.hidden_sections_list.customContextMenuRequested.connect(self.hidden_menu)
  self.nav.order_changed=lambda order:self.reorder_sections('sidebar',order)
  self.hidden_sections_list.order_changed=lambda order:self.reorder_sections('hidden',order)
  self.apply_section_visibility()
 def build_page(self,title):
  if title!=HIDDEN:return super().build_page(title)
  page=QWidget();layout=QVBoxLayout(page);heading=QLabel(HIDDEN);heading.setObjectName('heading');layout.addWidget(heading);self.hidden_sections_hint=QLabel();self.hidden_sections_hint.setWordWrap(True);layout.addWidget(self.hidden_sections_hint)
  self.hidden_sections_list=SectionList();self.hidden_sections_list.setAccessibleName('Hidden sections; drag or Alt+Up/Down to reorder, eye or Ctrl+H to restore');self.hidden_sections_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel);self.hidden_sections_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);layout.addWidget(self.hidden_sections_list)
  self.hidden_sections_list.itemDoubleClicked.connect(lambda item:self.restore_sidebar_section(item.data(Qt.UserRole)))
  self.button(layout,'Restore selected',self.restore_selected_section);self.button(layout,'Restore all sections',self.show_all_sections);self.stack.addWidget(page)
 def navigation_hidden(self):
  pid=self.project_filter.currentData()
  if pid:hidden=self.store.hidden_sections(pid)
  else:
   try:hidden=set(json.loads(self.appearance_settings.value('navigation/all_projects_hidden','[]')))
   except (TypeError,ValueError):hidden=set()
  return hidden & (set(self.navigation)-PROTECTED_SECTIONS)
 def save_navigation_hidden(self,sections):
  sections=set(sections)-PROTECTED_SECTIONS;pid=self.project_filter.currentData()
  if pid:self.store.set_hidden_sections(pid,sections)
  else:
   from PySide6.QtCore import QSettings
   self.appearance_settings.setValue('navigation/all_projects_hidden',json.dumps(sorted(sections)));self.appearance_settings.sync()
   if self.appearance_settings.status()!=QSettings.NoError:raise ValueError('Unable to save sidebar preference')
 def nav_item(self,title):
  return next((self.nav.item(i) for i in range(self.nav.count()) if self.nav.item(i).data(Qt.UserRole)==title),None)
 def navigate(self,title):
  item=self.nav_item(title)
  if item is not None:self.nav.setCurrentItem(item)
 def change_page(self,index):
  if index<0:return
  item=self.nav.item(index);title=item.data(Qt.UserRole)
  if title not in self.navigation:return
  self.current=title;self.stack.setCurrentIndex(self.navigation.index(title));self.refresh()
 def saved_section_order(self,area):
  pid=self.project_filter.currentData()
  if pid:return self.store.section_order(pid,area)
  try:order=json.loads(self.appearance_settings.value('navigation/all_projects_'+area+'_order','[]'))
  except (TypeError,ValueError):order=[]
  return normalized_order(order,self.navigation)
 def save_section_order(self,area,order):
  pid=self.project_filter.currentData()
  if pid:self.store.set_section_order(pid,area,order)
  else:
   from PySide6.QtCore import QSettings
   self.appearance_settings.setValue('navigation/all_projects_'+area+'_order',json.dumps(order));self.appearance_settings.sync()
   if self.appearance_settings.status()!=QSettings.NoError:raise ValueError('Unable to save section order')
 def reorder_sections(self,area,visible_order):
  try:
   hidden=self.navigation_hidden();old=self.saved_section_order(area)
   active=[s for s in old if (s not in hidden if area=='sidebar' else s in hidden)]
   if len(visible_order)!=len(active) or set(visible_order)!=set(active):raise ValueError('The visible categories changed; try the drag again')
   iterator=iter(visible_order);order=[next(iterator) if s in active else s for s in old]
   self.save_section_order(area,order);self.apply_section_visibility();return True
  except Exception as ex:
   self.apply_section_visibility();self.statusBar().showMessage('Section order was not saved: '+str(ex),10000);return False
 def reset_section_order(self):
  def action():
   self.save_section_order('sidebar',list(self.navigation));self.save_section_order('hidden',list(self.navigation));self.apply_section_visibility()
  self.guard(action)
 def apply_section_visibility(self):
  hidden=self.navigation_hidden();selected=self.nav.currentItem().data(Qt.UserRole) if self.nav.currentItem() else 'Dashboard';scroll=self.nav.verticalScrollBar().value();order=self.saved_section_order('sidebar');self.nav.blockSignals(True)
  if [self.nav.item(i).data(Qt.UserRole) for i in range(self.nav.count())]!=order:
   items={}
   while self.nav.count():
    item=self.nav.takeItem(0);items[item.data(Qt.UserRole)]=item
   for title in order:self.nav.addItem(items[title])
  for i in range(self.nav.count()):
   item=self.nav.item(i);title=item.data(Qt.UserRole);item.setHidden(title in hidden)
   if title==HIDDEN:item.setText(f'Hidden sections ({len(hidden)})')
  if selected in hidden or selected not in self.navigation:selected=next(s for s in order if s not in hidden)
  item=self.nav_item(selected);self.nav.setCurrentItem(item);self.nav.blockSignals(False);self.current=selected;self.stack.setCurrentIndex(self.navigation.index(selected));self.nav.verticalScrollBar().setValue(scroll)
  context='project:'+str(self.project_filter.currentData()) if self.project_filter.currentData() else 'all'
  self.nav.set_order_context(context)
  if hasattr(self,'hidden_sections_list'):
   current=self.hidden_sections_list.currentItem();chosen=current.data(Qt.UserRole) if current else None;scroll=self.hidden_sections_list.verticalScrollBar().value();self.hidden_sections_list.clear()
   for title in self.saved_section_order('hidden'):
    if title in hidden:
     item=QListWidgetItem(label(title));item.setData(Qt.UserRole,title);item.setToolTip(f'Drag to reorder; click the eye to restore {label(title)}');self.hidden_sections_list.addItem(item)
     if title==chosen:self.hidden_sections_list.setCurrentItem(item)
   self.hidden_sections_list.set_order_context(context);self.hidden_sections_list.verticalScrollBar().setValue(scroll)
   context_name=self.project_filter.currentText();self.hidden_sections_hint.setText(f'{len(hidden)} hidden section(s) for {context_name}. Hold and drag a category to reorder. Click the eye, double-click or use Ctrl+H to restore. Alt+Up/Down also reorders.' if hidden else f'No hidden sections for {context_name}. Use the eye beside a sidebar category to move it here. Hold and drag categories to reorder the sidebar.')
 def hide_sidebar_section(self,title):
  def action():
   if title not in self.navigation or title in PROTECTED_SECTIONS:return
   hidden=self.navigation_hidden();hidden.add(title);self.save_navigation_hidden(hidden);self.apply_section_visibility();self.statusBar().showMessage(label(title)+' moved to Hidden sections. All records are preserved.',7000)
  self.guard(action)
 def restore_sidebar_section(self,title):
  def action():
   hidden=self.navigation_hidden();hidden.discard(title);self.save_navigation_hidden(hidden);self.apply_section_visibility();self.statusBar().showMessage(label(title)+' restored to the sidebar.',7000)
  self.guard(action)
 def restore_selected_section(self):
  item=self.hidden_sections_list.currentItem()
  if item:self.restore_sidebar_section(item.data(Qt.UserRole))
 def show_all_sections(self):
  self.guard(lambda:(self.save_navigation_hidden([]),self.apply_section_visibility()))
 def sidebar_menu(self,point):
  item=self.nav.itemAt(point)
  if not item or item.data(Qt.UserRole) in PROTECTED_SECTIONS:return
  menu=QMenu(self.nav);menu.addAction('Hide section\tCtrl+H',lambda:self.hide_sidebar_section(item.data(Qt.UserRole)));menu.exec(self.nav.viewport().mapToGlobal(point))
 def hidden_menu(self,point):
  item=self.hidden_sections_list.itemAt(point)
  if not item:return
  title=item.data(Qt.UserRole);menu=QMenu(self.hidden_sections_list);menu.addAction('Restore to sidebar\tCtrl+H',lambda:self.restore_sidebar_section(title));menu.exec(self.hidden_sections_list.viewport().mapToGlobal(point))
