import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import csv
from pathlib import Path
import zipfile
import pytest
from cpc.store import Store
from cpc.exports import department_rows,write_docx

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');s.seed();yield s;s.db.close()

@pytest.fixture
def app():
 from PySide6.QtWidgets import QApplication
 return QApplication.instance() or QApplication([])


def test_department_csv_contains_related_records_costs_and_project_scope(store,tmp_path):
 rows=department_rows(store,['Electrical'])
 kinds={row['record_type'] for row in rows}
 assert kinds>={'Coordination','Development register','Bid package','Bid estimate','Cost item','Contact'}
 assert any(row['material']=='Example LED fixtures' and row['labor_rate']=='65' for row in rows)
 other=store.save('projects',{'name':'Unrelated project'})
 assert department_rows(store,['Electrical'],other)==[]
 path=tmp_path/'electrical.csv';store.export(path,rows)
 with path.open(encoding='utf-8-sig',newline='') as stream: exported=list(csv.DictReader(stream))
 assert len(exported)==len(rows) and all(row['discipline']=='Electrical' for row in exported)
 assert any(row['record_type']=='Cost item' and row['material_cost'] for row in exported)

@pytest.mark.parametrize('disciplines',[['Architecture'],['Structural Engineering','Geotechnical Engineering'],['Electrical','Fire Protection'],['Plumbing'],['Mechanical / HVAC'],['Civil Engineering','Site Work','Landscape','Utilities'],['General','Interiors','Roofing','Concrete','Masonry','Steel','Demolition']])
def test_each_department_exports_valid_word_document(store,tmp_path,disciplines):
 from docx import Document
 rows=department_rows(store,disciplines);path=tmp_path/'report.docx';write_docx(path,'Department report',rows,'Example project')
 with zipfile.ZipFile(path) as archive: assert archive.testzip() is None and 'word/document.xml' in archive.namelist()
 doc=Document(path);assert doc.paragraphs[0].text=='Department report'
 if rows: assert doc.tables
 else: assert any('No matching' in p.text for p in doc.paragraphs)


def test_department_export_filters_and_permit_checklist_inclusion(store):
 p=store.all('projects')[0]['id'];permit=next(r for r in store.all('registers') if r['record_type']=='Permit');store.save('registers',{'discipline':'Electrical'},permit['id'])
 rows=department_rows(store,['Electrical'],p)
 assert any(row['record_type']=='Permit requirement' for row in rows)
 filtered=department_rows(store,['Electrical'],p,'LED fixtures')
 assert filtered and all('LED fixtures' in ' '.join(map(str,row.values())) for row in filtered)


def test_word_text_escaping_and_empty_report(tmp_path):
 from docx import Document
 path=tmp_path/'safe.docx';write_docx(path,'Architecture & Engineering',[dict(title='A < B & C',notes='Line 1\nLine 2',completed=1)])
 doc=Document(path);texts=' '.join(p.text for p in doc.paragraphs)+' '.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
 assert 'A < B & C' in texts and 'Yes' in texts and 'Line 2' in texts


def test_section_export_buttons_write_csv_and_docx_with_filters(store,app,tmp_path,monkeypatch):
 from PySide6.QtWidgets import QFileDialog,QMessageBox
 from cpc.ui import Window
 def fail(*args):raise AssertionError(str(args[-1]))
 monkeypatch.setattr(QMessageBox,'warning',fail)
 w=Window(store)
 try:
  csv_path=tmp_path/'electrical.csv';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(csv_path),'CSV'));w.export_section('Electrical','csv')
  assert 'Cost item' in csv_path.read_text('utf-8-sig')
  doc_path=tmp_path/'electrical.docx';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(doc_path),'DOCX'));w.export_section('Electrical','docx')
  assert zipfile.is_zipfile(doc_path)
  w.filter_Tasks.setText('Request revised');rows=w.rows_for_export('Tasks');assert len(rows)==1 and 'Request revised' in rows[0]['title']
 finally:w.close()
