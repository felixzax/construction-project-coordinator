"""Prospective guardrails, not encryption or a document-content security scanner."""
from pathlib import Path
import re
import json
from urllib.parse import urlsplit, parse_qsl
import zipfile

ERROR='Credentials, payment details, certificate/signature files and eAuthorization forms must not be stored. Remove sensitive content before saving.'
FORBIDDEN_EXTENSIONS={'.pfx','.p12','.pem','.key','.cer','.crt','.der','.jks','.keystore','.sig','.p7s','.p7b','.p7c'}
SECRET=re.compile(r'(?i)(?:password|passwd|(?:portal|smarts|accela)[ _-]*(?:login|username)|login|username|security[ _-]*(?:question|answer)|eauthorization[ _-]*(?:secret|token)|api[ _-]*key|access[ _-]*token|credit[ _-]*card|card[ _-]*number|bank[ _-]*account|routing[ _-]*number)\s*[:=]\s*\S+|-----BEGIN (?:RSA |EC |ENCRYPTED |OPENSSH )?PRIVATE KEY-----')
SECRET_QUERY={'password','passwd','token','access_token','api_key','secret','authorization','signature','login','username'}
def check_values(value):
 if isinstance(value,dict):
  for k,v in value.items():
   if isinstance(v,(str,int,float)) and str(v).strip() and SECRET.search(str(k)+': '+str(v)):raise ValueError(ERROR)
   check_values(v)
 elif isinstance(value,(tuple,list)):
  for v in value:check_values(v)
 elif isinstance(value,str):
  if value.lstrip().startswith(('{','[')):
   try:parsed=json.loads(value)
   except ValueError:pass
   else:check_values(parsed)
  if SECRET.search(value):raise ValueError(ERROR)
  for url in re.findall(r'https?://[^\s<>"\']+',value):
   try:parts=urlsplit(url)
   except ValueError:raise ValueError(ERROR) from None
   if parts.username or parts.password or any(k.lower() in SECRET_QUERY for k,v in parse_qsl(parts.query) if v):raise ValueError(ERROR)

def check_filename(name):
 p=Path(name)
 if p.suffix.lower() in FORBIDDEN_EXTENSIONS or re.search(r'(?i)e[ _-]*authori[sz]ation',p.name):raise ValueError(ERROR)
 check_values(p.name)

def check_attachment(path):
 """Allow ordinary signed/stamped PDFs. Inspect obvious text and ZIP content.
 Binary PDFs/CAD/images are not parsed; the user's visible warning is essential.
 """
 path=Path(path);check_filename(path.name)
 if not path.is_file():raise ValueError('File does not exist')
 if path.suffix.lower() in {'.txt','.csv','.xml','.json','.html','.htm','.md','.rtf'}:
  if path.stat().st_size>20*1024*1024:raise ValueError('Text file too large to inspect; remove sensitive content and split the file first')
  check_values(path.read_bytes().decode('utf-8',errors='replace'))
 if zipfile.is_zipfile(path):
  with zipfile.ZipFile(path) as archive:
   total=0
   for entry in archive.infolist():
    check_filename(entry.filename);total+=entry.file_size
    if entry.flag_bits&1 or total>100*1024*1024:raise ValueError('Cannot inspect encrypted or expanded archive over 100 MB')
    if Path(entry.filename).suffix.lower() in {'.txt','.csv','.xml','.json','.html','.md','.rtf'}:
     check_values(archive.read(entry).decode('utf-8',errors='replace'))
