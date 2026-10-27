from pathlib import Path

import pytest

from ases.pipeline import scan_project
from ases.scanners import filesystem


def assert_gap(result):
    assert any(row['reason']=='source_unavailable_during_scan' for row in result['graph']['unknowns'])
    assert result['validation']['status']=='PASS'


def test_source_removed_between_discovery_and_scope_limit_check(tmp_path, monkeypatch):
    root=tmp_path/'app';root.mkdir()
    path=root/'temporary.py';path.write_text('def read(): return 1\n')
    original=filesystem._walk_project_files
    def discovery(root, **kwargs):
        paths=list(original(root,**kwargs))
        path.unlink()
        yield from paths
    monkeypatch.setattr(filesystem,'_walk_project_files',discovery)
    result=scan_project(root,tmp_path/'out',limits={'files':10,'bytes':10000,'file_bytes':10000})
    assert_gap(result)
    assert result['inventory']['source_scope']['unavailable_files']


def test_source_removed_while_inventory_hash_is_read(tmp_path, monkeypatch):
    root=tmp_path/'app';root.mkdir()
    path=root/'temporary.py';path.write_text('def read(): return 1\n')
    def vanished(candidate):
        candidate.unlink()
        raise FileNotFoundError('source removed')
    monkeypatch.setattr(filesystem,'sha256_file',vanished)
    result=scan_project(root,tmp_path/'out')
    assert_gap(result)
    assert not result['inventory']['source_manifest']


@pytest.mark.parametrize('suffix,stage,reader', [('.py','python','read_text'),('.java','java','read_text'),('.js','javascript','read_bytes'),('.html','frontend','read_bytes')])
def test_source_removed_during_parser_read_is_unknown(tmp_path,monkeypatch,suffix,stage,reader):
    root=tmp_path/'app';root.mkdir()
    path=root/('temporary'+suffix);path.write_text('placeholder')
    active=None
    def progress(value):
        nonlocal active
        active=value
    original=getattr(Path,reader)
    def disappearing(candidate,*args,**kwargs):
        if candidate==path and active==stage:
            candidate.unlink()
            raise FileNotFoundError('source removed')
        return original(candidate,*args,**kwargs)
    monkeypatch.setattr(Path,reader,disappearing)
    result=scan_project(root,tmp_path/'out',progress=progress)
    assert_gap(result)
    assert result['graph']['coverage'][path.name]['status']=='UNKNOWN'
