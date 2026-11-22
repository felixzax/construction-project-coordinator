import json
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor,QImage,QPainter
from PySide6.QtWidgets import QApplication,QMenu,QColorDialog,QStyleOptionViewItem
from cpc.store import Store
from cpc.ui import Window
from cpc.section_colors import COLOR_ROLE,KEY,PALETTE

@pytest.fixture
def window(tmp_path):
 app=QApplication.instance() or QApplication([]);store=Store(tmp_path/'data.sqlite3');store.seed();w=Window(store);w.show();app.processEvents();yield w;w.close();store.db.close()

def test_color_survives_hide_restore_reorder_theme_refresh_and_restart(window):
 from cpc import __version__
 w=window;assert w.windowTitle().endswith(__version__);before=w.store.all('tasks');pid=w.store.all('projects')[0]['id'];w.set_section_color('Electrical','#aBc123');assert w.nav_item('Electrical').data(COLOR_ROLE)=='#abc123'
 w.hide_sidebar_section('Electrical');hidden=next(w.hidden_sections_list.item(i) for i in range(w.hidden_sections_list.count()) if w.hidden_sections_list.item(i).data(Qt.UserRole)=='Electrical');assert hidden.data(COLOR_ROLE)=='#abc123'
 w.restore_sidebar_section('Electrical');order=w.nav.visible_sections();order.remove('Electrical');order.insert(0,'Electrical');assert w.reorder_sections('sidebar',order)
 w.choose_theme('light');w.choose_theme('dark');w.refresh_from_disk();assert w.nav_item('Electrical').data(COLOR_ROLE)=='#abc123'
 w.project_filter.setCurrentIndex(w.project_filter.findData(pid));assert w.nav_item('Electrical').data(COLOR_ROLE)=='#abc123'
 assert w.store.all('tasks')==before
 w.close();other=Window(w.store);assert other.nav_item('Electrical').data(COLOR_ROLE)=='#abc123';other.close()


def test_presets_custom_cancel_reset_and_menu_actions(window,monkeypatch):
 w=window;menu=QMenu(w);w.add_section_color_menu(menu,'Tasks');sub=menu._section_color_menu
 next(a for a in sub.actions() if a.text()=='Purple').trigger();assert w.section_colors()['Tasks']==PALETTE['Purple']
 monkeypatch.setattr(QColorDialog,'getColor',lambda *a:QColor());w.choose_section_color('Tasks');assert w.section_colors()['Tasks']==PALETTE['Purple']
 monkeypatch.setattr(QColorDialog,'getColor',lambda *a:QColor('#123456'));w.choose_section_color('Tasks');assert w.section_colors()['Tasks']=='#123456'
 next(a for a in sub.actions() if a.text()=='No color').trigger();assert 'Tasks' not in w.section_colors()
 w.use_suggested_section_colors();assert len(w.section_colors())==len(w.navigation)
 w.save_section_colors({});assert not w.section_colors() and w.nav_item('Tasks').data(COLOR_ROLE) is None


def test_invalid_saved_settings_and_values_do_not_change_records(window):
 w=window
 for saved in ('bad JSON','[]',json.dumps({'Tasks':'red','Missing':'#abcdef','Documents':'#abcdef'})):
  w.appearance_settings.setValue(KEY,saved);assert w.section_colors() in ({},{'Documents':'#abcdef'})
 prior=w.appearance_settings.value(KEY)
 for title,value in [('Missing','#123456'),('Tasks','red'),('Tasks','#12345678')]:
  with pytest.raises(ValueError):w.set_section_color(title,value)
 assert w.appearance_settings.value(KEY)==prior


def test_delegate_renders_marker_in_both_views_and_themes(window):
 w=window;w.set_section_color('Tasks','#f87171')
 for theme in ('light','dark'):
  w.choose_theme(theme);item=w.nav_item('Tasks');index=w.nav.indexFromItem(item);option=QStyleOptionViewItem();option.rect.setRect(0,0,250,36)
  image=QImage(250,36,QImage.Format_ARGB32);image.fill(QColor('#000000'));painter=QPainter(image);w.nav.itemDelegate().paint(painter,option,index);painter.end();assert image.pixelColor(5,18).name()=='#f87171'
 w.hide_sidebar_section('Tasks');item=next(w.hidden_sections_list.item(i) for i in range(w.hidden_sections_list.count()) if w.hidden_sections_list.item(i).data(Qt.UserRole)=='Tasks');assert item.data(COLOR_ROLE)=='#f87171'
