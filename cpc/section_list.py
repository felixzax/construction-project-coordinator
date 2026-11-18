"""Identity-based list dragging with theme-aware insertion and row highlights."""
import json
import uuid
from PySide6.QtCore import Qt,QMimeData,QPoint,QRect,QTimer
from PySide6.QtGui import QDrag,QPainter,QColor,QPen,QCursor
from PySide6.QtWidgets import QListWidget,QAbstractItemView,QApplication

MIME='application/x-cpc-section-order'
DROP_COLORS={'dark':('#9bcaff','#315a83'),'light':('#367bb9','#8ab3d7')}

class SectionList(QListWidget):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.order_changed=None;self.order_context='';self._drag_token=uuid.uuid4().hex;self._drop_boundary=None;self._drop_row=None;self._drag_pos=None;self._drag_section=None
  self.setDragEnabled(True);self.setAcceptDrops(True);self.setDragDropMode(QAbstractItemView.DragDrop);self.setDefaultDropAction(Qt.MoveAction);self.setDropIndicatorShown(False);self.setDragDropOverwriteMode(False)
  self._scroll_timer=QTimer(self);self._scroll_timer.setInterval(30);self._scroll_timer.timeout.connect(self._scroll_drag)
 def visible_sections(self):return [self.item(i).data(Qt.UserRole) for i in range(self.count()) if not self.item(i).isHidden()]
 def set_order_context(self,value):
  if self.order_context!=value:self.clear_drop_preview()
  self.order_context=value
 def drag_mime(self,section):
  data=QMimeData();data.setData(MIME,json.dumps(dict(token=self._drag_token,context=self.order_context,section=section)).encode('utf-8'));return data
 def valid_drag(self,mime):
  if not self.order_changed or not mime.hasFormat(MIME):return None
  try:data=json.loads(bytes(mime.data(MIME)).decode('utf-8'))
  except (ValueError,UnicodeError):return None
  if not isinstance(data,dict) or data.get('token')!=self._drag_token or data.get('context')!=self.order_context:return None
  section=data.get('section');return section if section in self.visible_sections() else None
 def startDrag(self,supportedActions):
  item=self.currentItem()
  if item is None or item.isHidden() or not self.order_changed:return
  rect=self.visualItemRect(item);drag=QDrag(self);drag.setMimeData(self.drag_mime(item.data(Qt.UserRole)));drag.setPixmap(self.viewport().grab(rect));point=self.viewport().mapFromGlobal(QCursor.pos())-rect.topLeft();drag.setHotSpot(QPoint(max(0,min(rect.width()-1,point.x())),max(0,min(rect.height()-1,point.y()))))
  try:drag.exec(Qt.MoveAction)
  finally:self.clear_drop_preview()
 def dragEnterEvent(self,event):
  if self.valid_drag(event.mimeData()):event.setDropAction(Qt.MoveAction);event.accept()
  else:event.ignore()
 def update_drop_preview(self,point,section):
  visible=[self.item(i) for i in range(self.count()) if not self.item(i).isHidden()];boundary=len(visible)
  for i,item in enumerate(visible):
   if point.y()<self.visualItemRect(item).center().y():boundary=i;break
  self._drop_boundary=boundary;self._drag_pos=QPoint(point);self._drag_section=section
  self._drop_row=self.visualItemRect(visible[min(boundary,len(visible)-1)]) if visible else QRect(2,2,self.viewport().width()-4,30)
  self.viewport().update()
 def dragMoveEvent(self,event):
  section=self.valid_drag(event.mimeData())
  if not section:self.clear_drop_preview();event.ignore();return
  self.update_drop_preview(event.position().toPoint(),section);self._scroll_timer.start();event.setDropAction(Qt.MoveAction);event.accept()
 def _scroll_drag(self):
  if self._drag_pos is None:return
  bar=self.verticalScrollBar();old=bar.value();y=self._drag_pos.y()
  if y<28:bar.setValue(old-12)
  elif y>self.viewport().height()-28:bar.setValue(old+12)
  if bar.value()!=old:self.update_drop_preview(self._drag_pos,self._drag_section)
 def dragLeaveEvent(self,event):self.clear_drop_preview();event.accept()
 def clear_drop_preview(self):
  self._scroll_timer.stop();self._drop_boundary=None;self._drop_row=None;self._drag_pos=None;self._drag_section=None;self.viewport().update()
 def dropEvent(self,event):
  section=self.valid_drag(event.mimeData())
  if not section:self.clear_drop_preview();event.ignore();return
  self.update_drop_preview(event.position().toPoint(),section);order=self.visible_sections();old=list(order);source=order.index(section);boundary=self._drop_boundary
  order.pop(source)
  if source<boundary:boundary-=1
  order.insert(boundary,section);self.clear_drop_preview()
  if order!=old and self.order_changed(order) is False:event.ignore();return
  event.setDropAction(Qt.MoveAction);event.accept()
 def paintEvent(self,event):
  super().paintEvent(event)
  if self._drop_boundary is None:return
  visible=[self.item(i) for i in range(self.count()) if not self.item(i).isHidden()]
  if not visible:return
  rect=self._drop_row;line=rect.top() if self._drop_boundary<len(visible) else rect.bottom()+1;line=max(2,min(self.viewport().height()-3,line));mode=QApplication.instance().property('cpcTheme');edge,fill=DROP_COLORS.get(mode,DROP_COLORS['dark']);painter=QPainter(self.viewport());painter.setRenderHint(QPainter.Antialiasing)
  tint=QColor(fill);tint.setAlpha(100);painter.fillRect(rect.adjusted(2,1,-2,-1),tint);painter.setPen(QPen(QColor(edge),2));painter.setBrush(Qt.NoBrush);painter.drawRoundedRect(rect.adjusted(2,1,-3,-2),4,4);painter.setPen(QPen(QColor(edge),3));painter.drawLine(5,line,self.viewport().width()-6,line);painter.end()
 def keyPressEvent(self,event):
  if event.modifiers() & Qt.AltModifier and event.key() in (Qt.Key_Up,Qt.Key_Down) and self.order_changed:
   item=self.currentItem();order=self.visible_sections();section=item.data(Qt.UserRole) if item else None
   if section in order:
    index=order.index(section);target=index+(-1 if event.key()==Qt.Key_Up else 1)
    if 0<=target<len(order):order[index],order[target]=order[target],order[index];self.order_changed(order)
   event.accept();return
  super().keyPressEvent(event)
