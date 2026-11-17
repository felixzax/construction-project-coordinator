import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import pytest
from cpc.file_editor import EditableFile

@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])


def test_text_edit_save_word_pdf_and_original_preserved(tmp_path,app):
 from docx import Document
 source=tmp_path/'scope.txt';source.write_text('Original terms',encoding='utf-8');model=EditableFile(source);model.text='Revised terms\nSecond line'
 word=tmp_path/'scope.docx';model.save(word);assert [p.text for p in Document(word).paragraphs]==['Revised terms','Second line']
 text=tmp_path/'new.txt';model.save(text);assert text.read_text()=='Revised terms\nSecond line'
 pdf=tmp_path/'scope.pdf';model.save(pdf);assert pdf.read_bytes().startswith(b'%PDF')
 assert source.read_text()=='Original terms'


def test_csv_edit_roundtrip_excel_preserves_leading_zeros_and_literal_formulas(tmp_path):
 from openpyxl import load_workbook
 source=tmp_path/'budget.csv';source.write_text('code,cost\n0012,10\n=literal,20',encoding='utf-8');model=EditableFile(source);model.set_cell(1,1,'25')
 out=tmp_path/'budget.xlsx';model.save(out);book=load_workbook(out)
 assert book.active['A2'].value=='0012' and book.active['B2'].value=='25'
 assert book.active['A3'].value=='=literal' and book.active['A3'].data_type=='s'


def test_workbook_edit_preserves_sheets_styles_and_formula_with_safe_conversion_gate(tmp_path):
 from openpyxl import Workbook,load_workbook
 from openpyxl.styles import Font
 source=tmp_path/'budget.xlsx';book=Workbook();sheet=book.active;sheet.title='Electrical';sheet['A1']='Cost';sheet['B1']=10;sheet['B1'].font=Font(bold=True);sheet['C1']='=B1*2';book.create_sheet('Plumbing')['A1']='Keep other sheet';book.save(source)
 model=EditableFile(source);model.set_cell(0,1,'12.50');assert model.formats()==['.xlsx']
 with pytest.raises(ValueError):model.save(tmp_path/'bad.csv')
 target=tmp_path/'edited.xlsx';model.save(target);saved=load_workbook(target)
 assert saved['Electrical']['B1'].value==12.5 and saved['Electrical']['B1'].font.bold
 assert saved['Electrical']['C1'].value=='=B1*2' and saved['Plumbing']['A1'].value=='Keep other sheet'
 model.set_cell(0,2,'25');assert '.csv' in model.formats()


def test_basic_word_edit_preserves_uniform_style_and_converts_simple_text(tmp_path,app):
 from docx import Document
 source=tmp_path/'contract.docx';doc=Document();p=doc.add_paragraph();p.add_run('Original clause').bold=True;doc.save(source)
 model=EditableFile(source);model.set_cell(0,1,'Updated clause');target=tmp_path/'updated.docx';model.save(target);saved=Document(target)
 assert saved.paragraphs[0].text=='Updated clause' and saved.paragraphs[0].runs[0].bold
 model.save(tmp_path/'plain.txt');assert (tmp_path/'plain.txt').read_text()=='Updated clause'


def test_complex_word_and_legacy_formats_require_external_editor(tmp_path):
 from docx import Document
 source=tmp_path/'complex.docx';doc=Document();p=doc.add_paragraph();p.add_run('Bold').bold=True;p.add_run(' normal');doc.save(source)
 with pytest.raises(ValueError,match='Mixed'):EditableFile(source)
 for extension in ('.pdf','.doc','.xls','.dwg'):
  path=tmp_path/('source'+extension);path.write_bytes(b'original')
  with pytest.raises(ValueError,match='In-app editing'):EditableFile(path)


def test_word_table_allows_native_edits_but_not_flat_conversion(tmp_path):
 from docx import Document
 source=tmp_path/'contract.docx';doc=Document();table=doc.add_table(rows=1,cols=1);table.cell(0,0).text='Scope';doc.save(source)
 model=EditableFile(source);assert model.formats()==['.docx'];model.set_cell(0,1,'New scope');out=tmp_path/'edit.docx';model.save(out);assert Document(out).tables[0].cell(0,0).text=='New scope'


def test_file_editor_saved_version_autosave_and_export_keep_original(tmp_path,app,monkeypatch):
 from cpc.store import Store
 from cpc.ui import Window
 from cpc.file_editor import FileEditor
 from PySide6.QtWidgets import QMessageBox,QFileDialog
 from PySide6.QtTest import QTest
 s=Store(tmp_path/'data.sqlite3');p=s.save('projects',{'name':'Project'});b=s.save('budgets',dict(project_id=p,title='Budget'));source=tmp_path/'notes.txt';source.write_text('Original');fid=s.import_finance_files('budgets',b,[source])[0]
 w=Window(s);editor=FileEditor(w,s,fid);editor.autosave_timer.setInterval(30);editor.editor.setPlainText('Edited in tool');QTest.qWait(150)
 files=s.finance_files('budgets',b);assert len(files)==2 and Path(files[0]['file_path']).read_text()=='Edited in tool'
 original,_=s.checked_finance_file(fid);assert Path(original['file_path']).read_text()=='Original'
 out=tmp_path/'converted.docx';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(out),'Word content document (*.docx)'));monkeypatch.setattr(QMessageBox,'information',lambda *args:None);editor.save_as()
 from docx import Document
 assert Document(out).paragraphs[0].text=='Edited in tool' and len(s.finance_files('budgets',b))==3
 editor.close();w.close();s.db.close()


def test_empty_word_can_be_edited_and_excel_date_type_preserved(tmp_path):
 from docx import Document
 from openpyxl import Workbook,load_workbook
 from datetime import datetime
 empty=tmp_path/'empty.docx';Document().save(empty);model=EditableFile(empty);model.set_cell(0,1,'Added clause');out=tmp_path/'filled.docx';model.save(out);assert Document(out).paragraphs[0].text=='Added clause'
 source=tmp_path/'dates.xlsx';book=Workbook();book.active['A1']=datetime(2026,1,1);book.save(source)
 model=EditableFile(source);model.set_cell(0,0,'2026-12-01');out=tmp_path/'newdates.xlsx';model.save(out)
 assert load_workbook(out).active['A1'].value==datetime(2026,12,1)


def test_editor_close_cancel_does_not_discard_unsaved_work(tmp_path,app,monkeypatch):
 from cpc.store import Store
 from cpc.ui import Window
 from cpc.file_editor import FileEditor
 from PySide6.QtWidgets import QMessageBox
 s=Store(tmp_path/'data.sqlite3');p=s.save('projects',{'name':'Project'});b=s.save('budgets',dict(project_id=p,title='Budget'));source=tmp_path/'notes.txt';source.write_text('Original');fid=s.import_finance_files('budgets',b,[source])[0];w=Window(s);editor=FileEditor(w,s,fid);editor.editor.setPlainText('Unsaved')
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Cancel);editor.reject();assert editor.dirty and editor.autosave_timer.isActive()
 monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Discard);editor.reject();assert not editor.dirty and not editor.autosave_timer.isActive();w.close();s.db.close()
