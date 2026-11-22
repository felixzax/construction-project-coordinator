"""Manual R-factor arithmetic. No rainfall model, network calls or EPA scraping."""
import calendar
from datetime import date,timedelta
from decimal import Decimal,localcontext,ROUND_HALF_UP,InvalidOperation
import hashlib,json

def decimal_value(text,label='Value',blank=False):
 if text in ('',None):
  if blank:return None
  raise ValueError(label+' is required')
 raw=str(text)
 if len(raw)>250:raise ValueError(label+' is too long')
 try:value=Decimal(raw)
 except InvalidOperation:raise ValueError(label+' must be a non-negative decimal') from None
 if not value.is_finite() or value<0 or abs(value.as_tuple().exponent)>1000:raise ValueError(label+' must be a finite non-negative decimal')
 return value

def period_flags(start,end):
 a=date.fromisoformat(start);b=date.fromisoformat(end);flags=[]
 if (a.month,a.day)==(2,29) or (b.month,b.day)==(2,29):flags.append('Feb 29 boundary: verify in the EPA calculator')
 if (b-a).days+1>365:flags.append('Window exceeds 365 days: verify in the EPA calculator')
 if calendar.isleap(b.year) and (b.month,b.day)==(12,31):flags.append('Leap-year Dec 31 end: guide suggests Dec 30; verify in EPA; dates were not changed')
 return flags

def generate_periods(start,end):
 a=date.fromisoformat(start);last=date.fromisoformat(end)
 if last<a:raise ValueError('Construction end cannot precede start')
 rows=[]
 while a<=last:
  if a==last:b=last
  else:
   if (a.month,a.day)==(2,29):raise ValueError('Feb 29 start has an ambiguous anniversary. Enter periods manually and verify in EPA; no dates were guessed.')
   if a.year==9999:b=last
   else:b=min(date(a.year+1,a.month,a.day)-timedelta(days=1),last)
  rows.append(dict(start_date=a.isoformat(),end_date=b.isoformat(),verification_flags=period_flags(a.isoformat(),b.isoformat())))
  if b==last:break
  a=b+timedelta(days=1)
 return rows

def fingerprint(site):
 values={k:site.get(k,'') for k in ('location_address','latitude','longitude','construction_start','final_stabilization')}
 return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()

def evaluate(site,periods):
 result=dict(state='Incomplete',total='',arithmetic='',warnings=[],erosion_estimate='',waiver_hint=False)
 for row in periods:
  value=decimal_value(row.get('r_value_text',''),'R value',True)
  if value is not None and (row.get('needs_recalculation') or row.get('inputs_fingerprint')!=fingerprint(site)):
   result['state']='Outdated';result['warnings']=['Site dates/location changed or a period needs recalculation'];return result
 if not site.get('construction_start') or not site.get('final_stabilization'):return result
 first=date.fromisoformat(site['construction_start']);last=date.fromisoformat(site['final_stabilization']);expected=first;values=[];raw=[];outdated=False;incomplete=not periods
 if last<first:raise ValueError('Construction end cannot precede start')
 for row in periods:
  a=date.fromisoformat(row['start_date']);b=date.fromisoformat(row['end_date'])
  if a!=expected or b<a or b>last:result['state']='Invalid';result['warnings'].append('Periods must be contiguous, ordered, non-overlapping and within construction dates');return result
  expected=b+timedelta(days=1) if b<date.max else b
  result['warnings']+=period_flags(row['start_date'],row['end_date'])
  value=decimal_value(row.get('r_value_text',''),'R value',True)
  if value is None:incomplete=True
  else:
   values.append(value);raw.append(str(row['r_value_text']))
   if row.get('needs_recalculation') or row.get('inputs_fingerprint')!=fingerprint(site):outdated=True
 if periods and (periods[0]['start_date']!=first.isoformat() or periods[-1]['end_date']!=last.isoformat()):result['state']='Invalid';result['warnings'].append('First start and last end must match construction dates');return result
 if outdated:result['state']='Outdated';return result
 if incomplete:return result
 with localcontext() as ctx:
  ctx.prec=max(50,sum(len(v.as_tuple().digits)+abs(v.as_tuple().exponent) for v in values)+10)
  total=sum(values,Decimal(0)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
  result.update(state='Complete',total=str(total),arithmetic=' + '.join(raw)+' = '+str(total))
  if site.get('erosion_enabled'):
   k=decimal_value(site.get('k_text',''),'K',True);ls=decimal_value(site.get('ls_text',''),'LS',True)
   if k is not None and ls is not None:
    ctx.prec+=len(k.as_tuple().digits)+abs(k.as_tuple().exponent)+len(ls.as_tuple().digits)+abs(ls.as_tuple().exponent)+10
    result['erosion_estimate']=str((total*k*ls).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
  acres=decimal_value(site.get('disturbed_acres',''),'Disturbed acres',True)
  result['waiver_hint']=total<5 and acres is not None and acres<5
 return result
