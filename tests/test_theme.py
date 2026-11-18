import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette,QColor
from cpc.store import Store
from cpc.ui import Window,Form
from cpc.theme import saved_theme,settings_for,THEMES

@pytest.fixture
def app():return QApplication.instance() or QApplication([])
@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');s.seed();yield s;s.db.close()


def test_dark_default_toggle_persists_without_changing_project_data(app,store):
 snapshot={t:store.all(t) for t in ('projects','tasks','contracts','scope_items')}
 w=Window(store);assert app.property('cpcTheme')=='dark' and w.dark_mode_action.isChecked()
 assert app.palette().color(QPalette.Base).lightness()<70
 w.dark_mode_action.setChecked(False)
 assert app.property('cpcTheme')=='light' and app.palette().color(QPalette.Base).lightness()>200
 assert saved_theme(settings_for(store.path.parent))=='light'
 assert all(store.all(t)==rows for t,rows in snapshot.items());w.close()
 second=Window(store);assert app.property('cpcTheme')=='light' and second.theme_actions['light'].isChecked()
 second.theme_actions['dark'].trigger();assert app.property('cpcTheme')=='dark' and second.dark_mode_action.isChecked();second.close()


def test_dark_forms_and_overdue_highlights_switch_readably(app,store):
 w=Window(store);form=Form(w,'Task',['title','notes','status'],choices={'status':['Not Started','Completed']})
 assert form.inputs['title'].palette().color(QPalette.Base).lightness()<70
 overdue=next(i for i,row in enumerate(w.data['Tasks']) if row['title']=='Request revised accessibility plans')
 item=w.tables['Tasks'].item(overdue,0);assert item.background().color()==QColor(THEMES['dark']['error_bg']) and item.foreground().color()==QColor(THEMES['dark']['error_text'])
 w.choose_theme('light');assert form.inputs['title'].palette().color(QPalette.Base).lightness()>200
 assert w.tables['Tasks'].item(overdue,0).background().color()==QColor(THEMES['light']['error_bg'])
 form.reject();w.close()


def test_invalid_saved_theme_falls_back_to_dark_without_database_migration(app,store):
 settings=settings_for(store.path.parent);settings.setValue('appearance/theme','unsupported');settings.sync()
 version=store.db.execute('PRAGMA user_version').fetchone()[0];w=Window(store)
 assert app.property('cpcTheme')=='dark' and store.db.execute('PRAGMA user_version').fetchone()[0]==version;w.close()


def test_theme_text_and_alert_contrast_meets_wcag_aa():
 def luminance(hexcolor):
  c=QColor(hexcolor);rgb=[c.redF(),c.greenF(),c.blueF()];rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb];return sum(v*w for v,w in zip(rgb,(.2126,.7152,.0722)))
 def ratio(a,b):
  x,y=sorted((luminance(a),luminance(b)));return (y+.05)/(x+.05)
 for t in THEMES.values():
  for foreground,background in [('text','base'),('text','alternate'),('muted','panel'),('error_text','error_bg'),('warning_text','warning_bg'),('success','base'),('pending','base'),('selection_text','selected')]:
   assert ratio(t[foreground],t[background])>=4.5,(foreground,background)
