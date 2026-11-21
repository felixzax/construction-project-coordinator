import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import csv
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QPushButton,QToolBar,QMessageBox,QFileDialog,QDialog
from PySide6.QtTest import QTest
from cpc.store import Store
from cpc.ui import Window
from cpc.sidebar import HIDDEN,eye_rect

@pytest.fixture
def app():return QApplication.instance() or QApplication([])
@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');s.seed();yield s;s.db.close()
@pytest.fixture
def window(store,app,monkeypatch):
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail);w=Window(store);w.show();app.processEvents();yield w;w.close()


def test_eye_click_hides_without_navigating_and_hidden_eye_restores(window,store,app):
 w=window;before=len(store.all('work_packages'));item=w.nav.item(w.navigation.index('Electrical'));w.nav.scrollToItem(item);app.processEvents();position=eye_rect(w.nav.visualItemRect(item)).center()
 QTest.mouseClick(w.nav.viewport(),Qt.LeftButton,pos=position);app.processEvents()
 assert item.isHidden() and w.current=='Dashboard'
 assert any(w.hidden_sections_list.item(i).data(Qt.UserRole)=='Electrical' for i in range(w.hidden_sections_list.count()))
 w.nav.setCurrentRow(w.navigation.index(HIDDEN));target=next(w.hidden_sections_list.item(i) for i in range(w.hidden_sections_list.count()) if w.hidden_sections_list.item(i).data(Qt.UserRole)=='Electrical');w.hidden_sections_list.scrollToItem(target);app.processEvents()
 QTest.mouseClick(w.hidden_sections_list.viewport(),Qt.LeftButton,pos=eye_rect(w.hidden_sections_list.visualItemRect(target)).center());app.processEvents()
 assert not item.isHidden() and 'Electrical' not in w.navigation_hidden() and len(store.all('work_packages'))==before


def test_sidebar_profile_persistence_and_separate_all_projects_preferences(window,store,app):
 w=window;pid=store.all('projects')[0]['id'];other=store.save('projects',{'name':'Another project'});w.refresh();w.hide_sidebar_section('Meetings')
 w.project_filter.setCurrentIndex(w.project_filter.findData(pid));assert 'Meetings' not in w.navigation_hidden();w.hide_sidebar_section('Electrical')
 w.project_filter.setCurrentIndex(w.project_filter.findData(other));assert w.navigation_hidden()=={'Regulatory & Permits'}
 w.project_filter.setCurrentIndex(0);assert w.navigation_hidden()=={'Meetings','Regulatory & Permits'}
 w.close();second=Window(store);assert second.navigation_hidden()=={'Meetings','Regulatory & Permits'}
 second.project_filter.setCurrentIndex(second.project_filter.findData(pid));assert second.navigation_hidden()=={'Electrical','Regulatory & Permits'};second.close()


def test_every_category_can_be_hidden_except_single_hidden_drawer(window,store):
 w=window;pid=store.all('projects')[0]['id'];w.project_filter.setCurrentIndex(w.project_filter.findData(pid))
 targets=set(w.navigation)-{HIDDEN};w.save_navigation_hidden(targets);w.apply_section_visibility()
 assert [w.navigation[i] for i in range(w.nav.count()) if not w.nav.item(i).isHidden()]==[HIDDEN]
 assert w.current==HIDDEN and w.hidden_sections_list.count()==len(targets)
 w.hide_sidebar_section(HIDDEN);assert not w.nav.item(w.navigation.index(HIDDEN)).isHidden()
 w.show_all_sections();assert w.hidden_sections_list.count()==0 and all(not w.nav.item(i).isHidden() for i in range(w.nav.count()))
 assert store.all('projects') and store.all('documents')


def test_keyboard_hide_restore_and_sidebar_scroll(window,app):
 w=window;w.nav.setCurrentRow(w.navigation.index('Tasks'));w.nav.setFocus();QTest.keyClick(w.nav,Qt.Key_H,Qt.ControlModifier);app.processEvents()
 assert 'Tasks' in w.navigation_hidden() and w.current=='Dashboard'
 w.nav.setCurrentRow(w.navigation.index(HIDDEN));w.hidden_sections_list.setCurrentRow(0);w.hidden_sections_list.setFocus();QTest.keyClick(w.hidden_sections_list,Qt.Key_H,Qt.ControlModifier);app.processEvents()
 assert 'Tasks' not in w.navigation_hidden();assert w.nav.verticalScrollBar().maximum()>0


def test_theme_switch_text_tracks_both_toolbar_click_directions(window,app):
 w=window;assert w.theme_button.text()=='Switch to Light mode'
 QTest.mouseClick(w.theme_button,Qt.LeftButton);app.processEvents();assert app.property('cpcTheme')=='light' and w.theme_button.text()=='Switch to Dark mode'
 QTest.mouseClick(w.theme_button,Qt.LeftButton);app.processEvents();assert app.property('cpcTheme')=='dark' and w.theme_button.text()=='Switch to Light mode'
 w.refresh();assert w.theme_button.text()=='Switch to Light mode'


def test_compact_primary_commands_and_export_menu_execute_filtered_csv(window,tmp_path,monkeypatch):
 w=window;w.nav.setCurrentRow(w.navigation.index('Tasks'));page=w.stack.currentWidget()
 assert all(bar.isHidden() for bar in w.findChildren(QToolBar))
 visible=[b for b in page.findChildren(QPushButton) if not b.isHidden()]
 assert [b.text() for b in visible]==['New','Edit','Files']
 w.filter_Tasks.setText('Request revised');out=tmp_path/'filtered.csv';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(out),'CSV'))
 menu=w.command_menus['Tasks']['Export'];next(a for a in menu.actions() if a.text()=='Listed records — CSV').trigger()
 with out.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
 assert len(rows)==1 and rows[0]['title']=='Request revised accessibility plans'


def test_delete_menu_preserves_confirmation_and_recovery_snapshot(window,store,monkeypatch):
 w=window;w.tables['Tasks'].selectRow(0);count=len(store.all('tasks'));menu=w.command_menus['Tasks']['More'];remove=next(a.menu() for a in menu.actions() if a.menu() is not None);action=next(a for a in remove.actions() if a.text()=='Delete selected records')
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.No);action.trigger();assert len(store.all('tasks'))==count
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes);action.trigger();assert len(store.all('tasks'))==count-1 and store.recovery_snapshots()


def test_file_dialog_keeps_primary_download_and_moves_secondary_commands(window,store,tmp_path,monkeypatch):
 w=window;w.tables['Contracts'].selectRow(0);source=tmp_path/'agreement.pdf';source.write_bytes(b'original agreement');out=tmp_path/'saved.pdf'
 monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *args:([str(source)],''));monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(out),''))
 def run(dialog):
  visible=[b for b in dialog.findChildren(QPushButton) if not b.isHidden()]
  assert [b.text() for b in visible]==['Add files…','Edit / convert…','Save a copy…','Close']
  next(b for b in visible if b.text()=='Add files…').click()
  from cpc.table import DataTable
  dialog.findChild(DataTable).selectRow(0);next(b for b in visible if b.text()=='Save a copy…').click()
  assert any(a.text()=='Save all as ZIP…' for a in dialog.compact_commands['More'].actions());dialog.accept();return dialog.result()
 monkeypatch.setattr(QDialog,'exec',run);w.finance_file_manager('Contracts');assert out.read_bytes()==source.read_bytes()


def test_hidden_section_search_and_reports_preserve_files_and_deadlines(window,store,tmp_path):
 w=window;pid=store.all('projects')[0]['id'];sid=store.save('scope_items',dict(project_id=pid,title='Stair review',deadline='2020-01-01'));source=tmp_path/'stairs.txt';source.write_text('original stair specifications');fid=store.import_finance_files('scope_items',sid,[source])[0]
 w.hide_sidebar_section('Scope & Systems');w.refresh()
 assert any(r.get('_source_table')=='scope_items' and r['_source_id']==sid for r in w.data['Dashboard'])
 assert any(r['type']=='scope_items' for r in store.search('Stair review')) and 'Stair review' in store.report(pid)
 assert store.checked_finance_file(fid)[1].read_text()=='original stair specifications'
