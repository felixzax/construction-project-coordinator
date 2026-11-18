"""Local appearance preferences and consistent Qt widget palettes."""
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor,QPalette,QAction,QActionGroup
from PySide6.QtWidgets import QApplication,QToolButton

THEMES={
 'dark':dict(window='#151b24',panel='#1d2633',base='#111925',alternate='#222e3e',text='#e5edf7',muted='#aebdd0',border='#40516a',button='#29384b',hover='#354c67',selected='#285c91',selection_text='#ffffff',sidebar='#101a28',heading='#d1e5ff',error_bg='#48252c',error_text='#ffbbc3',warning_bg='#41351c',warning_text='#ffe09a',success='#8edcaf',pending='#ffe09a'),
 'light':dict(window='#f3f5f8',panel='#ffffff',base='#ffffff',alternate='#eef3f8',text='#182c40',muted='#52677c',border='#b8c8d5',button='#ffffff',hover='#e0eef8',selected='#286492',selection_text='#ffffff',sidebar='#17324d',heading='#17324d',error_bg='#fde3df',error_text='#92232d',warning_bg='#fff0d0',warning_text='#77500d',success='#21663e',pending='#79580e'),
}

def settings_for(folder):return QSettings(str(Path(folder)/'appearance.ini'),QSettings.IniFormat)
def saved_theme(settings):
 value=settings.value('appearance/theme','dark')
 return value if value in THEMES else 'dark'
def tokens(app=None):
 app=app or QApplication.instance();return THEMES.get(app.property('cpcTheme') if app else 'dark',THEMES['dark'])

def apply_theme(app,name):
 if name not in THEMES:raise ValueError('Choose Light or Dark')
 t=THEMES[name];palette=QPalette()
 roles={'Window':'window','WindowText':'text','Base':'base','AlternateBase':'alternate','ToolTipBase':'panel','ToolTipText':'text','Text':'text','Button':'button','ButtonText':'text','BrightText':'selection_text','Highlight':'selected','HighlightedText':'selection_text','Link':'heading','LinkVisited':'muted','PlaceholderText':'muted','Light':'border','Midlight':'hover','Dark':'base','Mid':'border','Shadow':'base'}
 for group in (QPalette.Active,QPalette.Inactive,QPalette.Disabled):
  for role,key in roles.items():palette.setColor(group,getattr(QPalette,role),QColor(t[key]))
 for role in (QPalette.WindowText,QPalette.Text,QPalette.ButtonText):palette.setColor(QPalette.Disabled,role,QColor(t['muted']))
 app.setPalette(palette);app.setProperty('cpcTheme',name)
 app.setStyleSheet('''
 QWidget { font-family: "Segoe UI"; font-size: 10pt; color: %(text)s; }
 QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget > QWidget { background: %(window)s; }
 QMenuBar, QMenu, QToolBar, QStatusBar { background: %(panel)s; color: %(text)s; }
 QMenuBar::item:selected, QMenu::item:selected { background: %(selected)s; color: %(selection_text)s; }
 QMenu::item:disabled, QWidget:disabled { color: %(muted)s; }
 QToolBar { border: 0; spacing: 6px; padding: 4px; }
 QToolButton { background: %(button)s; border: 1px solid %(border)s; padding: 6px 8px; border-radius: 4px; }
 QToolButton:hover, QToolButton:checked { background: %(hover)s; }
 QListWidget { background: %(sidebar)s; color: #eff5fc; border: 0; padding: 12px; }
 QListWidget::item { padding: 7px 5px; }
 QListWidget::item:selected { background: %(selected)s; color: #ffffff; border-radius: 5px; }
 QLabel#heading { font-size: 24pt; font-weight: 600; color: %(heading)s; padding: 12px 0; }
 QLabel#subheading { font-size: 12pt; font-weight: 600; color: %(heading)s; }
 QPushButton { padding: 8px 12px; border: 1px solid %(border)s; border-radius: 4px; background: %(button)s; }
 QPushButton:hover { background: %(hover)s; }
 QPushButton:pressed { background: %(selected)s; color: %(selection_text)s; }
 QPushButton:default { border: 2px solid %(selected)s; }
 QPushButton:focus, QToolButton:focus { border: 2px solid %(selected)s; }
 QTableWidget, QTableView { background: %(base)s; alternate-background-color: %(alternate)s; color: %(text)s; border: 1px solid %(border)s; gridline-color: %(border)s; selection-background-color: %(selected)s; selection-color: %(selection_text)s; }
 QHeaderView::section, QTableCornerButton::section { background: %(button)s; color: %(text)s; padding: 8px; border: 0; }
 QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox { background: %(base)s; color: %(text)s; padding: 6px; border: 1px solid %(border)s; border-radius: 3px; selection-background-color: %(selected)s; selection-color: %(selection_text)s; }
 QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid %(selected)s; }
 QComboBox QAbstractItemView { background: %(panel)s; color: %(text)s; selection-background-color: %(selected)s; selection-color: %(selection_text)s; }
 QCheckBox { spacing: 6px; }
 QCheckBox::indicator { width: 16px; height: 16px; }
 QToolTip { background: %(panel)s; color: %(text)s; border: 1px solid %(border)s; padding: 5px; }
 QScrollBar { background: %(window)s; }
 QScrollBar::handle { background: %(border)s; border-radius: 3px; min-width: 20px; min-height: 20px; }
 ''' % t)

class ThemeUI:
 def __init__(self,store,*args,theme_settings=None,**kwargs):
  self.appearance_settings=theme_settings or settings_for(store.path.parent)
  app=QApplication.instance()
  if app.style().objectName().lower()!='fusion':app.setStyle('Fusion')
  if app.property('cpcTheme')!=saved_theme(self.appearance_settings):apply_theme(app,saved_theme(self.appearance_settings))
  super().__init__(store,*args,**kwargs)
  view=self.menuBar().addMenu('View');appearance=view.addMenu('Appearance');group=QActionGroup(self);group.setExclusive(True);self.theme_actions={}
  for name in ('dark','light'):
   action=QAction(name.title(),self);action.setCheckable(True);action.setChecked(app.property('cpcTheme')==name);group.addAction(action);appearance.addAction(action);self.theme_actions[name]=action
   action.triggered.connect(lambda checked,n=name:self.choose_theme(n) if checked else None)
  self.dark_mode_action=QAction('Switch to Light mode' if app.property('cpcTheme')=='dark' else 'Switch to Dark mode',self);self.dark_mode_action.setCheckable(True);self.dark_mode_action.setChecked(app.property('cpcTheme')=='dark');self.dark_mode_action.toggled.connect(lambda checked:self.choose_theme('dark' if checked else 'light'))
  self.theme_button=QToolButton(self);self.theme_button.setDefaultAction(self.dark_mode_action);self.project_controls.addWidget(self.theme_button)
 def choose_theme(self,name):
  def action():
   if name not in THEMES:raise ValueError('Choose Light or Dark')
   self.appearance_settings.setValue('appearance/theme',name);self.appearance_settings.sync()
   if self.appearance_settings.status()!=QSettings.NoError:raise ValueError('Unable to save appearance preference')
   apply_theme(QApplication.instance(),name)
   for key,item in self.theme_actions.items():item.setChecked(key==name)
   self.dark_mode_action.blockSignals(True);self.dark_mode_action.setChecked(name=='dark');self.dark_mode_action.blockSignals(False)
   self.dark_mode_action.setText('Switch to Light mode' if name=='dark' else 'Switch to Dark mode')
   self.dark_mode_action.setToolTip('Current theme: '+name.title()+'. '+self.dark_mode_action.text())
   self.refresh()
  self.guard(action)
