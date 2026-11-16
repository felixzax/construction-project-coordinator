"""Windows-style cell selection, keyboard copy and record deletion hooks."""
import csv
import io
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication,QTableWidget,QAbstractItemView,QMenu

class DataTable(QTableWidget):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.setSelectionMode(QAbstractItemView.ExtendedSelection)
  self.setSelectionBehavior(QAbstractItemView.SelectItems)
  self.delete_selected=None; self.delete_listed=None
  self.setContextMenuPolicy(Qt.CustomContextMenu); self.customContextMenuRequested.connect(self.menu)
 def copy_selection(self):
  selected=self.selectedIndexes()
  if not selected: return ''
  cells={(i.row(),i.column()) for i in selected}; rows=sorted({i.row() for i in selected}); columns=sorted({i.column() for i in selected})
  output=io.StringIO(); writer=csv.writer(output,delimiter='\t',lineterminator='\n')
  for row in rows:
   values=[]
   for column in columns:
    item=self.item(row,column)
    value=item.text() if item and (row,column) in cells else ''
    if item and (row,column) in cells and item.data(Qt.CheckStateRole) is not None:
     value='Yes' if item.checkState()==Qt.Checked else 'No'
    values.append(value)
   writer.writerow(values)
  text=output.getvalue().removesuffix('\n'); QApplication.clipboard().setText(text); return text
 def keyPressEvent(self,event):
  if event.matches(QKeySequence.Copy): self.copy_selection(); event.accept(); return
  if event.matches(QKeySequence.SelectAll): self.selectAll(); event.accept(); return
  if event.key()==Qt.Key_Delete and self.delete_selected:
   self.delete_selected(); event.accept(); return
  super().keyPressEvent(event)
 def menu(self,point):
  menu=QMenu(self); menu.addAction('Copy\tCtrl+C',self.copy_selection); menu.addAction('Select all\tCtrl+A',self.selectAll)
  if self.delete_selected:
   menu.addSeparator(); menu.addAction('Delete selected records\tDelete',self.delete_selected)
  if self.delete_listed: menu.addAction('Delete all listed records',self.delete_listed)
  menu.exec(self.viewport().mapToGlobal(point))
 def selected_record_rows(self): return sorted({i.row() for i in self.selectedIndexes()})
