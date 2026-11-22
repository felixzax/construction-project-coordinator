"""Compliance exports and printable project report using existing export paths."""
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QAbstractItemView
from .table import DataTable
from .regulatory import DISCLAIMER

class ComplianceUI:
 def build_compliance_tab(self,layout):
  note=QLabel(DISCLAIMER+' Reports include source dates, Verify flags, retained hidden items and R-factor ambiguities.');note.setWordWrap(True);layout.addWidget(note)
  bar=QHBoxLayout();layout.addLayout(bar);self.compliance_section=QComboBox();self.compliance_section.addItems(['All','Permits','Tracker','Checklist','Review Cycles','Discipline Reviews','Charges','Site Coverage','Filings','Revised Fields','R-factor','R Summary','Inspections','Document Requests','Roles','Rules','Sources','Project applicability']);self.compliance_section.currentTextChanged.connect(self.refresh_compliance);bar.addWidget(self.compliance_section)
  self.button(bar,'Export CSV',lambda:self.export_compliance('csv'));self.button(bar,'Export DOCX',lambda:self.export_compliance('docx'));self.button(bar,'Printable status report',self.print_report);bar.addStretch()
  self.compliance_hint=QLabel();layout.addWidget(self.compliance_hint);self.compliance_table=DataTable();self.compliance_table.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(self.compliance_table)
 def refresh_compliance(self,*args):
  pid=self.project_filter.currentData();rows=self.store.compliance_rows(pid,self.compliance_section.currentText()) if pid else [];self._compliance_rows=rows;self.compliance_hint.setText(str(len(rows))+' field rows; select a project to export.');self.render_recovery_table(self.compliance_table,rows)
 def export_compliance(self,kind):
  def action():
   self.selected_project_id();self.export_rows_dialog('Compliance — '+self.compliance_section.currentText(),self._compliance_rows,kind)
  self.guard(action)
