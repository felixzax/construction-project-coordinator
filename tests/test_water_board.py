"""Independent calculator and local Water Board workflow acceptance tests."""
from datetime import date,timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import csv,json,random
import pytest
from cpc.store import Store
from cpc.rfactor import generate_periods,evaluate,fingerprint,period_flags
from cpc.water_board import annual_dates,water_catalog

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data.sqlite3');yield s;s.db.close()
@pytest.fixture
def pid(store):return store.save('projects',dict(name='Fictional stormwater project',address='100 Example Lane'))
def site(store,pid,**values):
 store.set_regulatory_settings(pid,cgp_subject='Yes')
 return store.save('reg_wb_sites',dict(project_id=pid,location_address='100 Example Lane',construction_start='2020-11-01',final_stabilization='2022-12-28',**values))
def filled(store,pid):
 sid=site(store,pid);store.generate_water_periods(sid)
 for r,v in zip(store.water_periods(sid),['45.49','45.49','14.16']):store.save_r_period(dict(r_value_text=v,calculated_on='2026-11-20'),r['id'])
 return sid

def test_requested_golden_three_periods_and_fraction_total(store,pid):
 sid=filled(store,pid);rows=store.water_periods(sid)
 assert [(r['start_date'],r['end_date']) for r in rows]==[('2020-11-01','2021-10-31'),('2021-11-01','2022-10-31'),('2022-11-01','2022-12-28')]
 total=store.water_r_summary(sid);assert total['total']=='105.14' and total['arithmetic']=='45.49 + 45.49 + 14.16 = 105.14'
 assert Fraction(total['total'])==sum(Fraction(r['r_value_text']) for r in rows)

def test_single_year_golden_and_current_guide_example():
 for start,end,raw,expected in [('2020-11-01','2021-10-31',['45.49'],'45.49'),('2025-11-01','2028-08-15',['45.49','45.49','42.13'],'133.11')]:
  s=dict(construction_start=start,final_stabilization=end);periods=generate_periods(start,end)
  for p,r in zip(periods,raw):p.update(r_value_text=r,inputs_fingerprint=fingerprint(s))
  assert evaluate(s,periods)['total']==expected

@pytest.mark.parametrize('start,end,count',[('2021-01-01','2021-01-01',1),('2021-01-01','2021-12-31',1),('2020-01-01','2020-12-31',1),('2020-02-29','2020-02-29',1)])
def test_period_edge_dates_never_silently_changed(start,end,count):
 rows=generate_periods(start,end);assert len(rows)==count and rows[0]['start_date']==start and rows[-1]['end_date']==end
 if '02-29' in start or end=='2020-12-31':assert rows[0]['verification_flags']

def test_feb29_ambiguous_start_requires_manual_dates():
 with pytest.raises(ValueError,match='no dates were guessed'):generate_periods('2020-02-29','2022-03-01')
 assert any('Feb 29' in s for s in period_flags('2020-02-29','2021-02-28'))
 assert any('365' in s for s in period_flags('2019-03-01','2020-02-29'))
 assert any('Dec 30' in s for s in period_flags('2020-01-01','2020-12-31'))


def test_property_windows_cover_every_day_exactly_once():
 rng=random.Random(1729)
 for _ in range(180):
  first=date(1990,1,1)+timedelta(days=rng.randrange(15000));last=first+timedelta(days=rng.randrange(2000))
  if (first.month,first.day)==(2,29):continue
  rows=generate_periods(first.isoformat(),last.isoformat());days=[]
  for row in rows:
   a=date.fromisoformat(row['start_date']);b=date.fromisoformat(row['end_date']);days.extend(a+timedelta(days=d) for d in range((b-a).days+1))
  assert days==[first+timedelta(days=d) for d in range((last-first).days+1)] and len(set(days))==len(days)

@pytest.mark.parametrize('raw,expected',[('1.005','1.01'),('0.0049','0.00'),('0','0.00'),(' 45.4900 ','45.49'),('999999999999999999999999999999.995','1000000000000000000000000000000.00')])
def test_decimal_raw_precision_half_up_and_fraction_independence(raw,expected):
 s=dict(construction_start='2021-01-01',final_stabilization='2021-01-01');p=dict(start_date='2021-01-01',end_date='2021-01-01',r_value_text=raw,inputs_fingerprint=fingerprint(s));assert evaluate(s,[p])['total']==expected
 # Independent Fraction rounding for non-negative numbers.
 q=Fraction(raw.strip())*100;rounded=(q.numerator*2+q.denominator)//(2*q.denominator)
 assert Fraction(expected)==Fraction(rounded,100)

@pytest.mark.parametrize('raw',['-1','NaN','Infinity','not a number'])
def test_r_rejects_negative_nonfinite_and_invalid(store,pid,raw):
 sid=site(store,pid);store.generate_water_periods(sid);r=store.water_periods(sid)[0]
 with pytest.raises(ValueError):store.save_r_period(dict(r_value_text=raw),r['id'])
 assert store.water_periods(sid)[0]['r_value_text']==''


def test_incomplete_gaps_overlaps_order_and_mismatched_end(store,pid):
 sid=site(store,pid);store.generate_water_periods(sid);assert store.water_r_summary(sid)['state']=='Incomplete'
 for r in store.water_periods(sid):store.save_r_period(dict(r_value_text='1'),r['id'])
 rows=store.water_periods(sid);store.save_r_period(dict(start_date='2021-11-02'),rows[1]['id'],True);assert store.water_r_summary(sid)['state']=='Invalid'
 store.save_r_period(dict(start_date='2021-10-31'),rows[1]['id'],True);assert store.water_r_summary(sid)['state']=='Invalid'
 store.save_r_period(dict(start_date='2021-11-01'),rows[1]['id'],True);store.save_r_period(dict(end_date='2022-12-27'),rows[-1]['id'],True);assert store.water_r_summary(sid)['state']=='Invalid'

@pytest.mark.parametrize('field,value',[('location_address','Other location'),('latitude','38.5790'),('longitude','-121.4735'),('construction_start','2020-11-02'),('final_stabilization','2022-12-29')])
def test_site_changes_mark_rows_and_total_outdated(store,pid,field,value):
 sid=filled(store,pid);store.save('reg_wb_sites',{field:value},sid)
 assert store.water_r_summary(sid)['state']=='Outdated' and all(r['needs_recalculation'] for r in store.water_periods(sid))
 first=store.water_periods(sid)[0];store.save_r_period(dict(notes='Just a note'),first['id']);assert store.water_r_summary(sid)['state']=='Outdated'


def test_recalculation_is_explicit_and_preserves_raw_text(store,pid):
 sid=filled(store,pid);store.save('reg_wb_sites',dict(latitude='38.5790'),sid)
 for r in store.water_periods(sid):store.save_r_period(dict(r_value_text=r['r_value_text']),r['id'],True)
 assert store.water_r_summary(sid)['state']=='Complete'
 r=store.water_periods(sid)[0];store.save_r_period(dict(r_value_text=' 45.4900 '),r['id']);assert store.water_periods(sid)[0]['r_value_text']==' 45.4900 '


def test_optional_erosion_and_waiver_hint_are_not_eligibility_decisions(store,pid):
 sid=site(store,pid,disturbed_acres='4.5',erosion_enabled=1,k_text='0.2',ls_text='3');store.generate_water_periods(sid)
 for r in store.water_periods(sid):store.save_r_period(dict(r_value_text='1'),r['id'])
 summary=store.water_r_summary(sid);assert summary['total']=='3.00' and summary['erosion_estimate']=='1.80' and summary['waiver_hint']
 store.save('reg_wb_sites',dict(erosion_enabled=0),sid);assert store.water_r_summary(sid)['erosion_estimate']==''


def coi(store,pid,sid,**values):return store.save('reg_filings',dict(project_id=pid,wb_site_id=sid,filing_type='COI (Site)',**values))
def certifier(store,pid,role='LRP',auth='Yes'):
 c=store.save('contacts',dict(name='Fictional certifier'));return store.save('reg_project_roles',dict(project_id=pid,contact_id=c,role=role,eauthorization_status=auth,eauthorization_date='2026-11-20'))

@pytest.mark.parametrize('role,auth,reason',[('DEP','Yes','Update'),('LRP','No','Update'),('DAR','Unknown','Update'),('LRP','Yes','')])
def test_coi_hard_blockers_cannot_be_overridden(store,pid,role,auth,reason):
 sid=filled(store,pid);r=certifier(store,pid,role,auth)
 for state in ('Ready','Submitted'):
  with pytest.raises(ValueError,match='cannot be overridden'):coi(store,pid,sid,reason_for_change=reason,certifier_role_id=r,readiness_flag='Ready' if state=='Ready' else 'Not Ready',status='Submitted' if state=='Submitted' else 'Draft',details_json=json.dumps({'override_reason':'Office exception'}))
 assert not store.all('reg_filings')


def test_coi_valid_certifier_snapshots_and_draft_copy_never_submit(store,pid):
 sid=filled(store,pid);role=certifier(store,pid);fid=coi(store,pid,sid,reason_for_change='Risk input update',certifier_role_id=role)
 assert store.use_r_in_coi(sid,fid)=='105.14';row=store.all('reg_filings')[0];assert row['status']=='Draft' and row['readiness_flag']=='Not Ready'
 assert store.all('reg_filing_changes')[0]['revised_value']=='105.14'
 store.save('reg_filings',dict(readiness_flag='Ready'),fid);assert store.all('reg_filings')[0]['certifier_name_snapshot']=='Fictional certifier'
 with pytest.raises(ValueError):store.use_r_in_coi(sid,fid)
 store.save('reg_filings',dict(status='Submitted',submitted_date='2026-11-20'),fid)
 assert store.all('reg_filings')[0]['status']=='Submitted'


def test_filing_warnings_typed_override_logged_and_files_preserved(store,pid,tmp_path):
 sid=filled(store,pid);role=certifier(store,pid);fid=coi(store,pid,sid,reason_for_change='Revised site',certifier_role_id=role)
 path=tmp_path/'very long unusual attachment name $.txt';path.write_text('Ordinary reference')
 store.import_finance_files('reg_filings',fid,[path])
 with pytest.raises(ValueError,match='override reason'):store.save('reg_filings',dict(readiness_flag='Ready'),fid)
 store.save('reg_filings',dict(readiness_flag='Ready',details_json=json.dumps({'override_reason':'Intake requested this local reference name; verify portal copy'})),fid)
 assert store.all('reg_rule_overrides')[0]['reason'].startswith('Intake requested') and store.finance_files('reg_filings',fid)
 assert store.water_attachment_warnings('safe.pdf',100000001)


def test_annual_dates_next_period_idempotence_and_ceqa_separation(store,pid):
 sid=site(store,pid);start,end,due=annual_dates(2025);fid=store.save('reg_filings',dict(project_id=pid,wb_site_id=sid,filing_type='Annual Report',report_period_start=start,report_period_end=end))
 assert store.all('reg_filings')[0]['deadline']=='2026-09-01'
 store.save('reg_filings',dict(status='Submitted'),fid);store.save('reg_filings',dict(notes='Repeat update'),fid)
 rows=store.all('reg_filings');assert len(rows)==2 and any(r['report_period_start']=='2026-07-01' and r['deadline']=='2027-09-01' for r in rows)
 ceqa=store.save('reg_filings',dict(project_id=pid,filing_type='CEQA Notice of Determination'));assert next(r for r in store.all('reg_filings') if r['id']==ceqa)['regulatory_lane']=='County CEQA'


def test_weekly_inspection_uses_performed_date_not_future_or_cancelled(store,pid):
 sid=site(store,pid,status='Active');assert store.water_weekly_progress(pid,date(2026,11,20))['overdue']
 rid=store.save('registers',dict(project_id=pid,title='Weekly inspection',record_type='Inspection'));store.save_regulatory_inspection(rid,dict(inspection_kind='Stormwater Weekly',inspection_date='2026-11-12',result='Fail'))
 assert store.water_weekly_progress(pid,date(2026,11,20))['days_since_weekly']==8
 assert store.water_weekly_progress(pid,date(2026,11,19))['overdue'] is False
 store.save('reg_wb_sites',dict(status='Inactive'),sid);assert not store.water_weekly_progress(pid,date(2026,11,20))['overdue']


def test_standard_items_keep_edits_hidden_and_deleted_rules_global(store,pid):
 site(store,pid);assert store.add_water_standards(pid)==14 and store.add_water_standards(pid)==0
 assert store.add_water_standards(pid,'rules')==16 and store.add_water_standards(pid,'rules')==0
 step=store.all('reg_tracker_steps')[0];store.save('reg_tracker_steps',dict(notes='Keep user edit'),step['id']);store.add_water_standards(pid);assert store.all('reg_tracker_steps')[0]['notes']=='Keep user edit'
 rule=store.all('reg_rules')[0]
 with pytest.raises(ValueError,match='read-only'):store.save('reg_rules',dict(body='Overwrite'),rule['id'])
 store.delete_records([('reg_rules',rule['id']),('reg_tracker_steps',step['id'])]);store.add_water_standards(pid,'rules');store.add_water_standards(pid)
 assert next(r for r in store.all('reg_rules') if r['id']==rule['id'])['deleted']==1
 assert next(r for r in store.all('reg_tracker_steps') if r['id']==step['id'])['deleted']==1
 store.delete_records([('projects',pid)]);assert store.all('reg_rules') and store.all('reg_sources') and not store.all('reg_wb_sites')


def test_compliance_csv_docx_html_seal_name_and_department_integration(store,pid,tmp_path):
 from cpc.city_permits import CITY,metadata
 from cpc.exports import write_docx,department_rows
 from docx import Document
 contact=store.save('contacts',dict(name='Fictional Seal Engineer'))
 rid=store.configure_city_permit(dict(project_id=pid,title='Permit',jurisdiction_key=CITY,occupancy_type='Commercial',work_type='New Construction',permit_family='Building',seal_contact_id=contact,seal_discipline='Structural',seal_notes='Design coordination'))
 sid=filled(store,pid);store.add_water_standards(pid);rows=store.compliance_rows(pid)
 assert any(r['field']=='Person Responsible for Seal' and r['value']=='Fictional Seal Engineer' for r in rows)
 assert any(r['value']=='45.49 + 45.49 + 14.16 = 105.14' for r in rows)
 csvfile=tmp_path/'report.csv';store.export(csvfile,rows)
 with csvfile.open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==len(rows)
 docx=tmp_path/'report.docx';write_docx(docx,'Compliance report',rows);assert len(Document(docx).tables)==len(rows)
 assert '105.14' in store.report(pid) and 'Fictional Seal Engineer' in store.report(pid)
 assert any(r['record_type'].startswith('Regulatory') for r in department_rows(store,['Civil Engineering'],pid))
 store.delete_records([('contacts',contact)]);assert metadata(store.city_details(rid))['seal_contact_id'] is None


def test_water_ui_drafts_r_copy_reports_and_dashboard_links(store,pid):
 from PySide6.QtWidgets import QApplication
 from cpc.ui import Window
 app=QApplication.instance() or QApplication([]);sid=filled(store,pid);store.add_water_standards(pid);step=store.all('reg_tracker_steps')[0];store.save('reg_tracker_steps',dict(status='Waiting on Agency',deadline='2020-01-01'),step['id'])
 w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(pid));assert len(w.water_rows['R-factor'])==3
 w.copy_water_total();assert QApplication.clipboard().text()=='105.14'
 rows=[r for r in w.data['Dashboard'] if r.get('_source_table')=='reg_tracker_steps'];assert rows and rows[0]['_reg_no_overdue']
 assert w._compliance_rows and '105.14' in w.water_total.text();w.close()


def test_submitted_history_survives_contact_deletion_and_notes_remain_editable(store,pid):
 sid=filled(store,pid);role=certifier(store,pid);fid=coi(store,pid,sid,reason_for_change='Schedule update',certifier_role_id=role,status='Submitted')
 contact=store.all('reg_project_roles')[0]['contact_id'];store.delete_records([('contacts',contact)])
 store.save('reg_filings',dict(notes='Historic coordination note'),fid)
 row=store.all('reg_filings')[0];assert row['status']=='Submitted' and row['certifier_name_snapshot']=='Fictional certifier'


def test_changing_authorization_revokes_unsubmitted_readiness(store,pid):
 sid=filled(store,pid);role=certifier(store,pid);fid=coi(store,pid,sid,reason_for_change='Scope',certifier_role_id=role,readiness_flag='Ready')
 store.save('reg_project_roles',dict(eauthorization_status='No'),role)
 assert store.all('reg_filings')[0]['readiness_flag']=='Not Ready'


def test_per_list_export_shapes_sources_and_site_delete_global_catalog_survives(store,pid):
 from PySide6.QtWidgets import QApplication
 from cpc.ui import Window
 app=QApplication.instance() or QApplication([]);sid=filled(store,pid);store.add_water_standards(pid);store.add_water_standards(pid,'rules');w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(pid))
 assert w._water_exports['R-factor'][0]['start_date']=='11/01/2020'
 assert w._water_exports['R-factor'][0]['source_document']
 store.delete_records([('reg_wb_sites',sid)]);assert not store.all('reg_rfactor_periods') and not store.all('reg_tracker_steps')
 assert store.all('reg_rules') and store.all('reg_sources');w.close()


def test_schema_stays12_and_seal_drafts_preserve_metadata(store,pid):
 import hashlib
 expected='2d5112ff6891113c7487e8e5b1b429a56f5e77ce29a10062443e4c0e845380fd'
 assert hashlib.sha256((Path(__file__).parents[1]/'cpc/regulatory_schema.py').read_text(encoding='utf-8').encode()).hexdigest()==expected
 assert store.db.execute('PRAGMA user_version').fetchone()[0]==12


def test_ceqa_form_does_not_require_a_cgp_site(store,pid,monkeypatch):
 from PySide6.QtWidgets import QApplication
 from cpc.ui import Window,Form
 app=QApplication.instance() or QApplication([]);w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(pid))
 def accept(form):
  assert form.values()['filing_type']=='CEQA Notice of Determination';form.persist(form.values());form.clear_recovery_draft();return 1
 monkeypatch.setattr(Form,'exec',accept);w.edit_water_row('Filings');assert not store.all('reg_wb_sites') and store.all('reg_filings')[0]['regulatory_lane']=='County CEQA'
 assert w.water_rows['Filings'];w.close()


def test_ceqa_survives_deleting_water_site_and_regenerate_clears_obsolete_row_draft(store,pid):
 sid=filled(store,pid);row=store.water_periods(sid)[0];store.save_draft('old-period','reg_rfactor_periods',row['id'],dict(r_value_text='45.49'))
 store.generate_water_periods(sid,True);assert not store.drafts() and store.recovery_snapshots()
 ceqa=store.save('reg_filings',dict(project_id=pid,wb_site_id=sid,filing_type='CEQA Notice of Determination'))
 assert next(r for r in store.all('reg_filings') if r['id']==ceqa)['wb_site_id'] is None
 store.delete_records([('reg_wb_sites',sid)]);assert store.all('reg_filings')[0]['id']==ceqa


def test_new_records_have_readable_search_labels_and_weekly_dashboard_warning(store,pid):
 from PySide6.QtWidgets import QApplication
 from cpc.ui import Window
 app=QApplication.instance() or QApplication([]);sid=filled(store,pid);store.save('reg_wb_sites',dict(wdid='Fictional WDID unique',status='Active'),sid)
 fid=coi(store,pid,sid,reference='Fictional COI unique')
 assert any(r['label']=='Fictional WDID unique' for r in store.search('Fictional WDID unique'))
 assert any('COI (Site)' in r['label'] for r in store.search('Fictional COI unique'))
 assert all(r['label'] for r in store.search('45.49') if r['type']=='reg_rfactor_periods')
 w=Window(store);w.project_filter.setCurrentIndex(w.project_filter.findData(pid));assert any(r.get('_source_table')=='reg_wb_sites' and 'Weekly inspection' in r['kind'] for r in w.data['Dashboard']);w.close()
