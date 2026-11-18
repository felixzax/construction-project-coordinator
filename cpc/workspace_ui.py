"""Compact command rows: primary record actions, More, and Export."""
from PySide6.QtWidgets import QHBoxLayout,QPushButton,QToolButton,QMenu,QToolBar

class WorkspaceUI:
 def __init__(self,*args,**kwargs):
  self.command_menus={};self.primary_commands={}
  super().__init__(*args,**kwargs)
  # Existing keyboard/menu actions remain available without repeated toolbars.
  for toolbar in self.findChildren(QToolBar):self.removeToolBar(toolbar);toolbar.hide()
  self.sections_button=QToolButton(self);self.sections_button.setText('Sections');self.sections_button.setPopupMode(QToolButton.InstantPopup);menu=QMenu(self.sections_button);menu.addAction('Customize visible sections…',self.customize_sections);menu.addAction('Restore all hidden sections',self.show_all_sections);menu.addSeparator();menu.addAction('Reset section order',self.reset_section_order);self.sections_button.setMenu(menu)
  self.project_controls.addWidget(self.sections_button)
 def build_page(self,title):
  super().build_page(title)
  page=self.stack.widget(self.stack.count()-1);layout=page.layout();buttons=[]
  def collect(parent):
   for i in range(parent.count()-1,-1,-1):
    item=parent.itemAt(i)
    if isinstance(item.widget(),QPushButton):
     widget=item.widget();buttons.insert(0,widget);parent.takeAt(i);widget.hide()
    elif item.layout():
     child=item.layout();collect(child)
     if child.count()==0:parent.takeAt(i)
  collect(layout)
  if not buttons:return
  # Retain original callbacks on hidden button objects; QAction delegates to click().
  header=QHBoxLayout();heading=layout.takeAt(0).widget();header.addWidget(heading);header.addStretch();primary=[];secondary=[];exports=[]
  for button in buttons:
   text=button.text()
   if text.startswith('Export'):exports.append(button)
   elif (text.startswith('+ New') or text=='Edit selected' or text.startswith('Files —') or title=='Hidden sections' and text=='Restore selected') and len(primary)<3:primary.append(button)
   else:secondary.append(button)
  for button in primary:
   text=button.text();button.setText('Files' if text.startswith('Files —') else 'Edit' if text=='Edit selected' else text.replace('+ New','New',1));button.setToolTip(text);header.addWidget(button);button.show()
  self.primary_commands[title]=primary;menus={}
  def action(menu,button,text=None):
   item=menu.addAction(text or button.text());item.triggered.connect(lambda checked=False,b=button:b.click());return item
  if secondary:
   menu=QMenu(page);menu._submenus=[];remove=None
   for button in secondary:
    if button.text().startswith(('Delete','Discard')):
     if remove is None:
      menu.addSeparator();remove=QMenu('Delete / discard…',menu);menu.addMenu(remove);menu._submenus.append(remove)
     action(remove,button)
    else:action(menu,button)
   tool=QToolButton(page);tool.setText('More');tool.setAccessibleName(title+' more actions');tool.setPopupMode(QToolButton.InstantPopup);tool.setMenu(menu);header.addWidget(tool);menus['More']=menu
  if exports:
   menu=QMenu(page)
   has_listed=any('listed records CSV' in b.text() or 'department report CSV' in b.text() for b in exports)
   for button in exports:
    text=button.text()
    if text=='Export CSV' and has_listed and title!='Projects':continue
    if title=='Projects' and text=='Export CSV':text='All projects — CSV'
    else:text=text.removeprefix('Export ').replace('listed records ','Listed records — ').replace('department report ','Department report — ')
    action(menu,button,text)
   tool=QToolButton(page);tool.setText('Export');tool.setAccessibleName(title+' export');tool.setPopupMode(QToolButton.InstantPopup);tool.setMenu(menu);header.addWidget(tool);menus['Export']=menu
  self.command_menus[title]=menus;layout.insertLayout(0,header)


def compact_dialog(dialog,primary_labels):
 """Keep frequent commands visible; use menus for retained secondary callbacks."""
 buttons=[]
 def collect(layout):
  for i in range(layout.count()-1,-1,-1):
   item=layout.itemAt(i)
   if isinstance(item.widget(),QPushButton):
    button=item.widget();layout.takeAt(i);button.hide();buttons.insert(0,button)
   elif item.layout():
    child=item.layout();collect(child)
    if not child.count():layout.takeAt(i)
 collect(dialog.layout());bar=QHBoxLayout();secondary=[];exports=[];close=[]
 for button in buttons:
  text=button.text()
  if text=='Close':close.append(button)
  elif text in primary_labels:bar.addWidget(button);button.show()
  elif text.startswith('Export'):exports.append(button)
  else:secondary.append(button)
 dialog.compact_commands={}
 for title,items in [('More',secondary),('Export',exports)]:
  if not items:continue
  menu=QMenu(dialog);menu._submenus=[];delete=None
  for button in items:
   parent=menu
   if button.text().startswith(('Delete','Discard')):
    if delete is None:
     menu.addSeparator();delete=QMenu('Delete / discard…',menu);menu.addMenu(delete);menu._submenus.append(delete)
    parent=delete
   item=parent.addAction(button.text().removeprefix('Export ') if title=='Export' else button.text());item.triggered.connect(lambda checked=False,b=button:b.click())
  tool=QToolButton(dialog);tool.setText(title);tool.setPopupMode(QToolButton.InstantPopup);tool.setMenu(menu);bar.addWidget(tool);dialog.compact_commands[title]=menu
 bar.addStretch()
 for button in close:bar.addWidget(button);button.show()
 dialog.layout().addLayout(bar)
