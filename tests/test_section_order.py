import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from contextlib import closing
import sqlite3
import pytest
from PySide6.QtCore import Qt,QPoint,QPointF,QEvent
from PySide6.QtGui import QDragEnterEvent,QDragMoveEvent,QDropEvent,QDragLeaveEvent,QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from cpc.store import Store
from cpc.ui import Window
from cpc.sidebar import HIDDEN,eye_rect
from cpc.section_list import DROP_COLORS

@pytest.fixture
def app():return QApplication.instance() or QApplication([])
@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');s.seed();yield s;s.db.close()
@pytest.fixture
def window(store,app):
 w=Window(store);w.show();app.processEvents();yield w;w.close()

def send_preview(view,title,point):
 mime=view.drag_mime(title);enter=QDragEnterEvent(point,Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier);QApplication.sendEvent(view.viewport(),enter);assert enter.isAccepted()
 move=QDragMoveEvent(point,Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier);QApplication.sendEvent(view.viewport(),move);assert move.isAccepted();return mime

def drop(view,title,point):
 mime=send_preview(view,title,point);event=QDropEvent(QPointF(point),Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier);QApplication.sendEvent(view.viewport(),event);assert event.isAccepted();return view.visible_sections()


def test_sidebar_drop_both_directions_preserves_page_and_identity(window,app):
 w=window;w.navigate('Contracts');initial=w.current;w.nav.verticalScrollBar().setValue(0);app.processEvents()
 order=drop(w.nav,'Tasks',QPoint(10,2));assert order[0]=='Tasks' and w.current==initial and w.stack.currentIndex()==w.navigation.index(initial)
 w.navigate('Tasks');assert w.current=='Tasks' and w.stack.currentIndex()==w.navigation.index('Tasks')
 w.nav.scrollToItem(w.nav_item('Projects'));app.processEvents();target=w.nav.visualItemRect(w.nav_item('Projects'));order=drop(w.nav,'Tasks',QPoint(10,target.bottom()-1))
 assert order.index('Tasks')==order.index('Projects')+1
 for section in ('Documents','Recovery & Data','Projects','Tasks'):
  w.navigate(section);assert w.stack.currentIndex()==w.navigation.index(section) and w.current==section


def test_hidden_order_is_independent_and_restoration_keeps_sidebar_position(window):
 w=window;drop(w.nav,'Electrical',QPoint(10,2));normal=w.saved_section_order('sidebar')
 for section in ('Architecture','Electrical','Plumbing'):w.hide_sidebar_section(section)
 w.navigate(HIDDEN);drop(w.hidden_sections_list,'Plumbing',QPoint(10,2))
 assert w.hidden_sections_list.visible_sections()[0]=='Plumbing' and w.saved_section_order('sidebar')==normal
 w.restore_sidebar_section('Electrical');assert w.nav.visible_sections()[0]=='Electrical'
 w.hide_sidebar_section('Electrical');assert w.hidden_sections_list.visible_sections()[0]=='Plumbing'


def test_orders_persist_separately_for_projects_and_all_projects(window,store):
 w=window;pid=store.all('projects')[0]['id'];other=store.save('projects',{'name':'Other project'});w.refresh();drop(w.nav,'Tasks',QPoint(10,2))
 w.project_filter.setCurrentIndex(w.project_filter.findData(pid));drop(w.nav,'Contracts',QPoint(10,2));w.hide_sidebar_section('Electrical');w.hide_sidebar_section('Plumbing');w.navigate(HIDDEN);drop(w.hidden_sections_list,'Plumbing',QPoint(10,2))
 w.project_filter.setCurrentIndex(w.project_filter.findData(other));assert w.nav.visible_sections()[0]=='Dashboard'
 w.project_filter.setCurrentIndex(0);assert w.nav.visible_sections()[0]=='Tasks';w.close()
 second=Window(store)
 assert second.nav.visible_sections()[0]=='Tasks'
 second.project_filter.setCurrentIndex(second.project_filter.findData(pid));assert second.nav.visible_sections()[0]=='Contracts' and second.hidden_sections_list.visible_sections()[0]=='Plumbing';second.close()


def test_cancelled_foreign_and_stale_drags_do_not_save(window,store,app):
 w=window;before=w.saved_section_order('sidebar');mime=send_preview(w.nav,'Tasks',QPoint(12,2));assert w.nav._drop_boundary==0
 leave=QDragLeaveEvent();QApplication.sendEvent(w.nav.viewport(),leave);assert w.nav._drop_boundary is None and w.saved_section_order('sidebar')==before
 foreign=w.hidden_sections_list.drag_mime('Tasks');enter=QDragEnterEvent(QPoint(12,2),Qt.MoveAction,foreign,Qt.LeftButton,Qt.NoModifier);QApplication.sendEvent(w.nav.viewport(),enter);assert not enter.isAccepted()
 pid=store.all('projects')[0]['id'];w.project_filter.setCurrentIndex(w.project_filter.findData(pid));enter=QDragEnterEvent(QPoint(12,2),Qt.MoveAction,mime,Qt.LeftButton,Qt.NoModifier);QApplication.sendEvent(w.nav.viewport(),enter);assert not enter.isAccepted() and store.section_order(pid,'sidebar')==list(w.navigation)


@pytest.mark.parametrize('theme',['dark','light'])
def test_drop_indicator_has_theme_color_and_clears_on_leave(window,app,theme,tmp_path):
 w=window;w.choose_theme(theme);send_preview(w.nav,'Tasks',QPoint(15,2));app.processEvents();image=w.nav.viewport().grab().toImage();edge=QColor(DROP_COLORS[theme][0]);y=2
 assert any(image.pixelColor(x,y).name()==edge.name() for x in range(10,min(image.width()-10,150)))
 assert w.nav._drop_boundary==0
 QApplication.sendEvent(w.nav.viewport(),QDragLeaveEvent());assert w.nav._drop_boundary is None


def test_drag_auto_scroll_and_alt_keyboard_move(window,app):
 w=window;bar=w.nav.verticalScrollBar();assert bar.maximum()>0
 point=QPoint(15,w.nav.viewport().height()-3);send_preview(w.nav,'Tasks',point);before=bar.value();QTest.qWait(130);assert bar.value()>before
 QApplication.sendEvent(w.nav.viewport(),QDragLeaveEvent());w.navigate('Tasks');order=w.nav.visible_sections();old=order.index('Tasks');w.nav.setFocus();QTest.keyClick(w.nav,Qt.Key_Up,Qt.AltModifier);assert w.nav.visible_sections().index('Tasks')==old-1 and w.current=='Tasks'


def test_eye_controls_and_shortcuts_work_after_reordering(window,app):
 w=window;pid=w.store.all('projects')[0]['id'];w.project_filter.setCurrentIndex(w.project_filter.findData(pid));drop(w.nav,'Projects',QPoint(10,2));w.navigate('Projects');w.tables['Projects'].selectRow(0)
 w.show_project_issues('Violations')
 assert w.current=='Violations'
 item=w.nav_item('Projects');w.nav.scrollToItem(item);app.processEvents();QTest.mouseClick(w.nav.viewport(),Qt.LeftButton,pos=eye_rect(w.nav.visualItemRect(item)).center());assert item.isHidden() and 'Projects' in w.navigation_hidden()
 w.restore_sidebar_section('Projects');assert not w.nav_item('Projects').isHidden()


def test_reset_order_preserves_hidden_flags_and_records(window,store):
 w=window;pid=store.all('projects')[0]['id'];w.project_filter.setCurrentIndex(w.project_filter.findData(pid));before=store.all('tasks');drop(w.nav,'Tasks',QPoint(10,2));w.hide_sidebar_section('Electrical');w.reset_section_order()
 assert w.saved_section_order('sidebar')==list(w.navigation) and w.navigation_hidden()=={'Electrical','Regulatory & Permits'} and store.all('tasks')==before


def test_backup_restore_keeps_project_orders_and_delete_cleans_preferences(store,tmp_path):
 from cpc.development_ui import NAVIGATION
 pid=store.all('projects')[0]['id'];order=['Tasks']+[s for s in NAVIGATION if s!='Tasks'];store.set_section_order(pid,'sidebar',order);store.set_section_order(pid,'hidden',list(reversed(NAVIGATION)));store.set_hidden_sections(pid,['Electrical']);backup=tmp_path/'backup.sqlite3';store.backup(backup)
 store.delete_records([('projects',pid)]);assert store.rows('SELECT * FROM project_section_order')==[]
 store.restore(backup);assert store.section_order(pid,'sidebar')==order and store.section_order(pid,'hidden')==list(reversed(NAVIGATION)) and store.hidden_sections(pid)=={'Electrical'}


def test_v8_upgrade_preserves_data_and_visibility_and_old_backup_restore(store,tmp_path):
 old=tmp_path/'v8.sqlite3'
 with closing(sqlite3.connect(old)) as db:db.executescript((Path(__file__).parent/'fixtures/v8_database.sql').read_text())
 upgraded=Store(old)
 try:
  assert upgraded.db.execute('PRAGMA user_version').fetchone()[0]==12 and len(upgraded.all('contracts'))==1
  pid=upgraded.all('projects')[0]['id'];assert upgraded.hidden_sections(pid)=={'Electrical','Plumbing'} and upgraded.rows('SELECT * FROM project_section_order')==[]
 finally:upgraded.db.close()
 safety=str(old)+'.before-v1.11.0.sqlite3'
 with closing(sqlite3.connect(safety)) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==8
 store.restore(safety);assert len(store.all('scope_items'))==1 and store.rows('SELECT * FROM project_section_order')==[]


def test_invalid_order_is_rejected_without_changes_and_new_sections_merge(store):
 from cpc.development_ui import NAVIGATION
 pid=store.all('projects')[0]['id'];store.set_section_order(pid,'sidebar',['Tasks']);order=store.section_order(pid,'sidebar');assert order[0]=='Tasks' and set(order)==set(NAVIGATION)
 for invalid in (['Tasks','Tasks'],['Made up section'],[None]):
  with pytest.raises(ValueError):store.set_section_order(pid,'sidebar',invalid)
  assert store.section_order(pid,'sidebar')==order


def test_invalid_backup_order_does_not_replace_live_data(store,tmp_path):
 pid=store.all('projects')[0]['id'];store.set_section_order(pid,'sidebar',['Tasks']);bad=tmp_path/'bad.sqlite3';store.backup(bad)
 with closing(sqlite3.connect(bad)) as db:db.execute("UPDATE project_section_order SET section='Invalid category' WHERE position=0");db.commit()
 with pytest.raises(ValueError,match='ordering'):store.restore(bad)
 assert store.section_order(pid,'sidebar')[0]=='Tasks'
