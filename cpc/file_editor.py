"""Conservative editing and explicitly supported file conversions."""
import copy
import csv
import html
import io
from pathlib import Path
import re
import zipfile
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QTextDocument,QKeySequence
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPlainTextEdit,QTableWidgetItem,QPushButton,QFileDialog,QMessageBox,QApplication
from .table import DataTable


def decoded_text(path):
 data=Path(path).read_bytes()
 encoding='utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
 try:return data.decode(encoding)
 except UnicodeDecodeError:raise ValueError('This text encoding needs an external editor; UTF-8 and BOM-marked UTF-16 are supported') from None

class EditableFile:
 def __init__(self,path):
  self.path=Path(path);self.kind=self.path.suffix.lower();self.sheet_name=None
  if self.kind=='.txt':self.text=decoded_text(path)
  elif self.kind=='.csv':
   text=decoded_text(path)
   try:self.dialect=csv.Sniffer().sniff(text[:4096],delimiters=',;\t|')
   except csv.Error:self.dialect=csv.excel
   self.rows=list(csv.reader(io.StringIO(text),self.dialect)) or [['']]
   if len(self.rows)>5000 or max(map(len,self.rows),default=0)>100:raise ValueError('Use a spreadsheet app for files larger than 5,000 rows or 100 columns')
  elif self.kind=='.docx':self.load_word(path)
  elif self.kind=='.xlsx':
   from openpyxl import load_workbook
   with zipfile.ZipFile(path) as archive:
    if any(name.startswith(('xl/charts/','xl/drawings/','xl/pivot','xl/externalLinks/','xl/embeddings/','xl/activeX/','customXml/')) or 'vbaProject' in name or name=='xl/connections.xml' for name in archive.namelist()):raise ValueError('This workbook contains complex objects; edit it in Excel and import the revised file to preserve them')
   self.workbook=load_workbook(path,keep_links=True);self.sheet_name=self.workbook.sheetnames[0]
   for sheet in self.workbook:
    if sheet.max_row>5000 or sheet.max_column>100 or sheet.protection.sheet:raise ValueError('Large or protected worksheets require an external spreadsheet editor')
  else:raise ValueError('In-app editing supports UTF text/CSV, basic DOCX and plain XLSX workbooks. Use Open in default app and add the revised file for PDF, CAD, legacy Office or other formats.')
 def load_word(self,path):
  from docx import Document
  self.document=Document(path)
  body=self.document.element
  if body.xpath('.//w:drawing|.//w:object|.//w:fldChar|.//w:instrText|.//w:hyperlink|.//w:ins|.//w:del|.//w:sdt|.//w:bookmarkStart|.//w:gridSpan|.//w:vMerge') or len(self.document.sections)!=1:raise ValueError('This Word file has complex layout/fields/objects; use Word and import the revised file to preserve them')
  for section in self.document.sections:
   if any(p.text for story in (section.header,section.footer) for p in story.paragraphs):raise ValueError('Headers/footers require an external Word editor to preserve document layout')
  if not self.document.paragraphs and not self.document.tables:self.document.add_paragraph('')
  self.word_entries=[]
  for i,p in enumerate(self.document.paragraphs):self.word_entries.append((f'Paragraph {i+1}',p))
  for ti,table in enumerate(self.document.tables):
   for ri,row in enumerate(table.rows):
    for ci,cell in enumerate(row.cells):
     for pi,p in enumerate(cell.paragraphs):self.word_entries.append((f'Table {ti+1}, row {ri+1}, column {ci+1}, paragraph {pi+1}',p))
  for _,p in self.word_entries:
   styles={str(run._r.rPr.xml) if run._r.rPr is not None else '' for run in p.runs}
   if len(styles)>1 or p._p.xpath('.//w:br[@w:type="page"]'):raise ValueError('Mixed inline formatting/page breaks require Word; this editor preserves basic uniform paragraphs and simple tables')
 def table_data(self):
  if self.kind=='.csv':return [list(row) for row in self.rows]
  if self.kind=='.docx':return [[label,p.text] for label,p in self.word_entries]
  sheet=self.workbook[self.sheet_name]
  return [[str(c.value) if c.value is not None else '' for c in row] for row in sheet.iter_rows()]
 def set_cell(self,row,column,value):
  if self.kind=='.csv':
   while len(self.rows)<=row:self.rows.append([])
   while len(self.rows[row])<=column:self.rows[row].append('')
   self.rows[row][column]=value
  elif self.kind=='.docx':
   if column!=1:return
   p=self.word_entries[row][1];rpr=copy.deepcopy(p.runs[0]._r.rPr) if p.runs else None
   p.text=value
   if rpr is not None and p.runs:p.runs[0]._r.insert(0,rpr)
  else:
   from openpyxl.cell.cell import MergedCell
   cell=self.workbook[self.sheet_name].cell(row+1,column+1)
   if isinstance(cell,MergedCell):raise ValueError('Edit only the top-left cell of a merged range')
   from datetime import datetime,date
   if value and isinstance(cell.value,(datetime,date)):
    try:cell.value=datetime.fromisoformat(value) if isinstance(cell.value,datetime) else date.fromisoformat(value)
    except ValueError:raise ValueError('Enter an ISO date/time, for example 2026-12-01, or use Excel for date formatting') from None
   elif value=='':cell.value=None
   elif value.startswith('='):cell.value=value
   elif re.fullmatch(r'-?(?:(?:0|[1-9]\d*)(?:\.\d*)?|\.\d+)',value) and len(value.replace('.','').replace('-',''))<=15:cell.value=float(value) if '.' in value else int(value)
   elif value in ('TRUE','FALSE'):cell.value=value=='TRUE'
   else:cell.value=value
 def formats(self):
  if self.kind=='.txt':return ['.txt','.docx','.pdf']
  if self.kind=='.csv':return ['.csv','.xlsx','.docx','.pdf']
  if self.kind=='.docx':
   numbered=any(p._p.pPr is not None and p._p.pPr.numPr is not None or 'Number' in p.style.name or 'List' in p.style.name for _,p in self.word_entries)
   return ['.docx'] if self.document.tables or numbered else ['.docx','.txt','.pdf']
  sheet=self.workbook[self.sheet_name]
  if sheet.merged_cells.ranges or any(c.data_type=='f' for row in sheet for c in row):return ['.xlsx']
  return ['.xlsx','.csv','.docx','.pdf']
 def save(self,path,extension=None):
  path=Path(path);extension=extension or path.suffix.lower()
  if extension not in self.formats():raise ValueError('This conversion would lose formulas, structure or layout; save in the original format or convert using the original application')
  if extension=='.xlsx' and self.kind=='.xlsx':
   if self.workbook.calculation is None:
    from openpyxl.workbook.properties import CalcProperties
    self.workbook.calculation=CalcProperties()
   self.workbook.calculation.fullCalcOnLoad=True;self.workbook.save(path);return
  if extension=='.docx' and self.kind=='.docx':self.document.save(path);return
  text=self.text if self.kind=='.txt' else '\n'.join(p.text for _,p in self.word_entries) if self.kind=='.docx' else None
  rows=self.table_data() if self.kind in ('.csv','.xlsx') else None
  if extension=='.txt':path.write_text(text,encoding='utf-8');return
  if extension=='.csv':
   with path.open('w',encoding='utf-8-sig',newline='') as stream:csv.writer(stream,self.dialect if self.kind=='.csv' else csv.excel).writerows(rows)
   return
  if extension=='.xlsx':
   from openpyxl import Workbook
   book=Workbook();sheet=book.active
   for ri,row in enumerate(rows,1):
    for ci,value in enumerate(row,1):cell=sheet.cell(ri,ci,str(value));cell.data_type='s'
   book.save(path);return
  if extension=='.docx':
   from docx import Document
   doc=Document()
   if rows:
    table=doc.add_table(rows=0,cols=max(map(len,rows),default=1));table.style='Table Grid'
    for row in rows:
     cells=table.add_row().cells
     for ci,value in enumerate(row):cells[ci].text=str(value)
   else:
    for line in (text or '').split('\n'):doc.add_paragraph(line)
   doc.save(path);return
  if extension=='.pdf':
   doc=QTextDocument()
   if rows:doc.setHtml('<table border="1" cellspacing="0" cellpadding="4">'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</table>')
   else:doc.setPlainText(text or '')
   printer=QPrinter();printer.setOutputFormat(QPrinter.PdfFormat);printer.setOutputFileName(str(path));doc.print_(printer)

class EditingTable(DataTable):
 def keyPressEvent(self,event):
  if event.matches(QKeySequence.Paste):
   rows=list(csv.reader(io.StringIO(QApplication.clipboard().text()),delimiter='\t'));r=max(0,self.currentRow());c=max(0,self.currentColumn())
   if getattr(self,'allow_growth',True):self.setRowCount(max(self.rowCount(),r+len(rows)));self.setColumnCount(max(self.columnCount(),c+max(map(len,rows),default=0)))
   for ri,row in enumerate(rows):
    for ci,value in enumerate(row):
     if r+ri>=self.rowCount() or c+ci>=self.columnCount():continue
     old=self.item(r+ri,c+ci)
     if old is not None and not old.flags() & Qt.ItemIsEditable:continue
     self.setItem(r+ri,c+ci,QTableWidgetItem(value))
   return
  super().keyPressEvent(event)

class FileEditor(QDialog):
 def __init__(self,parent,store,file_id):
  super().__init__(parent);self.store=store;self.file_id=file_id;self.record,self.source=store.checked_finance_file(file_id);self.model=EditableFile(self.source);self.dirty=False;self.autosave_timer=QTimer(self);self.autosave_timer.setInterval(10000);self.autosave_timer.timeout.connect(self.autosave);self.autosave_timer.start();self.setWindowTitle('Edit file — '+self.record['original_name']);self.resize(1100,720)
  layout=QVBoxLayout(self);hint=QLabel('Original attachment is retained. Save edited version adds a new file; Save as also exports a copy. PDF/Word table conversions are content reports, not a reproduction of Office page layout. Formula workbooks must stay XLSX and recalculate in Excel.');hint.setWordWrap(True);layout.addWidget(hint)
  bar=QHBoxLayout();layout.addLayout(bar)
  if self.model.kind=='.xlsx':
   self.sheets=QComboBox();self.sheets.addItems(self.model.workbook.sheetnames);self.sheets.currentTextChanged.connect(self.change_sheet);bar.addWidget(self.sheets)
  if self.model.kind=='.txt':self.editor=QPlainTextEdit(self.model.text);layout.addWidget(self.editor);self.editor.textChanged.connect(self.text_changed)
  else:
   self.grid=EditingTable();self.grid.allow_growth=self.model.kind!='.docx';layout.addWidget(self.grid);self.load_grid();self.grid.itemChanged.connect(self.cell_changed)
   if self.model.kind=='.csv':
    add=QPushButton('Add row');add.clicked.connect(self.add_row);bar.addWidget(add)
    addc=QPushButton('Add column');addc.clicked.connect(self.add_column);bar.addWidget(addc)
  for label,callback in [('Save edited version',lambda:self.save_version()),('Save as / export…',self.save_as),('Close',self.close)]:
   button=QPushButton(label);button.clicked.connect(callback);bar.addWidget(button)
 def load_grid(self):
  rows=self.model.table_data();self.grid.blockSignals(True);self.grid.setRowCount(max(1,len(rows)));self.grid.setColumnCount(max(map(len,rows),default=1));self.grid.clearContents()
  for ri,row in enumerate(rows):
   for ci,value in enumerate(row):
    item=QTableWidgetItem(value)
    if self.model.kind=='.docx' and ci==0:item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    self.grid.setItem(ri,ci,item)
  self.grid.blockSignals(False);self.grid.resizeColumnsToContents()
 def cell_changed(self,item):
  try:self.model.set_cell(item.row(),item.column(),item.text());self.dirty=True
  except Exception as ex:QMessageBox.warning(self,'Cell cannot be changed',str(ex));self.load_grid()
 def text_changed(self):self.model.text=self.editor.toPlainText();self.dirty=True
 def add_row(self):self.model.rows.append(['']*max(1,self.grid.columnCount()));self.dirty=True;self.load_grid()
 def add_column(self):
  columns=self.grid.columnCount()+1
  for row in self.model.rows:row.extend(['']*(columns-len(row)))
  self.dirty=True;self.load_grid()
 def change_sheet(self,name):self.model.sheet_name=name;self.load_grid()
 def attach_result(self,path):
  table='contracts' if self.record['contract_id'] else 'budgets';parent=self.record['contract_id'] or self.record['budget_id']
  self.store.import_finance_files(table,parent,[path],notes=f'Edited/converted from attachment #{self.file_id}: {self.record["original_name"]}')
 def autosave(self):
  if self.dirty:self.save_version(automatic=True)
 def save_version(self,automatic=False):
  import tempfile
  from .finance import safe_name
  try:
   with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/safe_name(self.record['original_name']);self.model.save(path,self.model.kind);self.attach_result(path)
   self.dirty=False
   if not automatic:QMessageBox.information(self,'Version saved','A new attachment version was saved. The original is retained.')
   return True
  except Exception as ex:
   if automatic:self.setWindowTitle('File autosave failed — '+str(ex))
   else:QMessageBox.warning(self,'Unable to save edited version',str(ex))
   return False
 def confirm_close(self):
  if not self.dirty:return True
  choice=QMessageBox.question(self,'Save file edits?','Save a new attachment version before closing? Earlier autosaved versions remain available.',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Save)
  if choice==QMessageBox.Cancel:return False
  if choice==QMessageBox.Save:return self.save_version(automatic=True)
  self.dirty=False;return True
 def closeEvent(self,event):
  if not self.confirm_close():event.ignore();return
  self.autosave_timer.stop();super().closeEvent(event)
 def reject(self):
  if self.confirm_close():self.autosave_timer.stop();super().reject()
 def save_as(self):
  formats=self.model.formats();labels={'.csv':'CSV (selected sheet/data only)','.xlsx':'Excel workbook','.docx':'Word content document','.txt':'UTF-8 text','.pdf':'PDF content report'}
  filters=';;'.join(f'{labels[ext]} (*{ext})' for ext in formats)
  path,chosen=QFileDialog.getSaveFileName(self,'Save edited file as',Path(self.record['original_name']).stem,filters)
  if not path:return
  try:
   extension=next((ext for ext in formats if f'(*{ext})' in chosen),Path(path).suffix.lower())
   if extension not in formats:raise ValueError('Choose one of the supported output formats')
   output=Path(path)
   if output.suffix.lower()!=extension:output=output.with_suffix(extension)
   if (self.store.path.parent/'documents').resolve() in output.resolve().parents:raise ValueError('Choose a location outside the retained originals')
   if output!=Path(path) and output.exists() and QMessageBox.question(self,'Replace file?',f'Replace {output}?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
   import tempfile,os
   with tempfile.NamedTemporaryFile(dir=output.parent,suffix=extension,delete=False) as file:temporary=Path(file.name)
   try:
    self.model.save(temporary,extension)
    if not temporary.is_file():raise ValueError('Conversion did not produce a file')
    if extension in ('.docx','.xlsx'):
     with zipfile.ZipFile(temporary) as archive:
      expected='word/document.xml' if extension=='.docx' else 'xl/workbook.xml'
      if archive.testzip() or expected not in archive.namelist():raise ValueError('Converted document failed validation')
    if extension=='.pdf' and not temporary.read_bytes().startswith(b'%PDF'):raise ValueError('PDF conversion failed')
    os.replace(temporary,output)
   finally:temporary.unlink(missing_ok=True)
   self.attach_result(output);self.dirty=False;QMessageBox.information(self,'Saved','The exported file and a new attachment version were saved.')
  except Exception as ex:QMessageBox.warning(self,'Conversion could not be completed',str(ex))
