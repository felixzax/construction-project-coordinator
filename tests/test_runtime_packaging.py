import importlib.util
import json
from pathlib import Path
import pytest
from cpc.runtime import WINDOWS_RUNTIME_FILES,missing_runtime_files,check_frozen_runtime,report_startup_failure
from scripts.portable_build import stage_release,check_manifest,isolated_environment,run_isolated


def test_reported_shiboken_error_matches_missing_package_folder(tmp_path):
 import PySide6
 package=tmp_path/'_internal'/'PySide6';package.mkdir(parents=True)
 with pytest.raises(ImportError,match='libshiboken.*does not exist'):
  PySide6._additional_dll_directories(package)
 shiboken=tmp_path/'_internal'/'shiboken6';shiboken.mkdir()
 assert PySide6._additional_dll_directories(package)==[shiboken]


def test_runtime_guard_lists_missing_dlls_and_accepts_complete_layout(tmp_path):
 assert set(missing_runtime_files(tmp_path))==set(WINDOWS_RUNTIME_FILES)
 for name in WINDOWS_RUNTIME_FILES:
  path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'bundled-file')
 assert missing_runtime_files(tmp_path)==[]
 (tmp_path/'shiboken6'/'Shiboken.pyd').unlink()
 assert missing_runtime_files(tmp_path)==['shiboken6/Shiboken.pyd']


def test_runtime_guard_only_applies_to_frozen_windows(tmp_path,monkeypatch):
 import cpc.runtime as runtime
 monkeypatch.setattr(runtime.sys,'frozen',True,raising=False);monkeypatch.setattr(runtime.sys,'_MEIPASS',str(tmp_path),raising=False);monkeypatch.setattr(runtime.sys,'platform','win32')
 assert 'shiboken6/Shiboken.pyd' in check_frozen_runtime()
 monkeypatch.setattr(runtime.sys,'frozen',False)
 assert check_frozen_runtime()==[]


def test_startup_error_records_message_without_creating_project_database(tmp_path,monkeypatch):
 monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
 report_startup_failure('Missing shiboken runtime',quiet=True)
 assert (tmp_path/'Construction Project Coordinator'/'startup-error.txt').read_text('utf-8')=='Missing shiboken runtime'
 assert not list(tmp_path.rglob('*.sqlite3'))


def test_main_reports_missing_runtime_before_importing_qt(monkeypatch):
 import main
 import cpc.runtime as runtime
 reports=[];monkeypatch.setattr(runtime,'check_frozen_runtime',lambda:['shiboken6/Shiboken.pyd']);monkeypatch.setattr(runtime,'report_startup_failure',lambda message,quiet=False:reports.append(message))
 assert main.launch()==2
 assert reports and 'incomplete' in reports[0] and '_internal' in reports[0]


def test_standalone_manifest_covers_executable_and_docs(tmp_path):
 dist=tmp_path/'dist';dist.mkdir();(dist/'ConstructionProjectCoordinator.exe').write_bytes(b'MZ-test-binary')
 output=tmp_path/'release';stage_release(dist,output)
 assert check_manifest(output).name=='ConstructionProjectCoordinator.exe'
 assert sorted(p.name for p in output.iterdir())==['CHANGELOG.md','ConstructionProjectCoordinator.exe','README.md','SHA256SUMS.json']
 (output/'ConstructionProjectCoordinator.exe').write_bytes(b'changed')
 with pytest.raises(ValueError,match='changed release file'):check_manifest(output)


def test_release_has_no_external_runtime_directories(tmp_path):
 dist=tmp_path/'dist';dist.mkdir();(dist/'ConstructionProjectCoordinator.exe').write_bytes(b'MZ')
 output=tmp_path/'release';stage_release(dist,output);(output/'_internal').mkdir()
 with pytest.raises(ValueError,match='companion directories'):check_manifest(output)


def test_clean_launch_environment_removes_build_dependencies(monkeypatch):
 monkeypatch.setenv('PYTHONPATH','build-python-site-packages');monkeypatch.setenv('PYTHONHOME','build-python');monkeypatch.setenv('QT_PLUGIN_PATH','build-qt');monkeypatch.setenv('VIRTUAL_ENV','build-venv');monkeypatch.setenv('PATH','build-machine-dlls')
 env=isolated_environment('windows')
 assert not any(k in env for k in ('PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH','VIRTUAL_ENV'))
 assert env['QT_QPA_PLATFORM']=='windows' and 'build-machine-dlls' not in env['PATH']


def test_clean_launch_uses_external_cwd_and_verified_executable(tmp_path,monkeypatch):
 import scripts.portable_build as portable
 dist=tmp_path/'dist';dist.mkdir();(dist/'ConstructionProjectCoordinator.exe').write_bytes(b'MZ')
 output=tmp_path/'release';stage_release(dist,output);calls=[]
 monkeypatch.setattr(portable.subprocess,'run',lambda *args,**kwargs:calls.append((args,kwargs)))
 run_isolated(output)
 args,options=calls[0]
 assert Path(args[0][0])==output/'ConstructionProjectCoordinator.exe'
 assert options['cwd']!=str(output) and options['check'] is True
 assert options['env']['QT_QPA_PLATFORM']=='offscreen'
 assert args[0][1]=='--smoke-test'
