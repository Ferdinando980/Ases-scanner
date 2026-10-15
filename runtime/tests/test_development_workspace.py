"""The engineering kit and generated scanner output must safely coexist."""
from pathlib import Path
import pytest

from ases.cli import main
from ases.pipeline import scan_project, clean_output


def engineering_kit(root):
    kit = root / '.ases'
    kit.mkdir(parents=True)
    (kit / 'STANDARD.md').write_text('Engineering method: preserve this file.', encoding='utf-8')
    (root / 'app.py').write_text('def read(): return 1', encoding='utf-8')
    return kit


def test_default_scan_preserves_installed_engineering_method(tmp_path):
    kit = engineering_kit(tmp_path)
    result = scan_project(tmp_path)
    assert (kit / 'STANDARD.md').read_text() == 'Engineering method: preserve this file.'
    assert Path(result['output']) == tmp_path / 'ases-scan.ases'
    assert (tmp_path / 'ases-scan.ases/consumer-context.v2.json').is_file()


@pytest.mark.parametrize('operation', ['scan', 'clean'])
def test_explicit_engineering_directory_is_never_generated_output(tmp_path, operation):
    kit = engineering_kit(tmp_path)
    with pytest.raises(ValueError):
        scan_project(tmp_path, kit) if operation == 'scan' else clean_output(kit)
    assert (kit / 'STANDARD.md').is_file()


@pytest.mark.parametrize('name', ['ordinary', '.ases', 'notes.ases'])
def test_nonempty_unmarked_output_is_preserved(tmp_path, name):
    source, output = tmp_path / 'source', tmp_path / name
    source.mkdir()
    output.mkdir()
    keep = output / 'keep.txt'
    keep.write_text('user material')
    with pytest.raises(ValueError):
        scan_project(source, output)
    with pytest.raises(ValueError):
        clean_output(output)
    assert keep.read_text() == 'user material'


def test_clean_all_skips_method_and_other_unmarked_directories(tmp_path, monkeypatch, capsys):
    kit = engineering_kit(tmp_path)
    generated = tmp_path / 'results.ases'
    scan_project(tmp_path, generated)
    notes = tmp_path / 'notes.ases'
    notes.mkdir()
    (notes / 'keep.txt').write_text('notes')
    monkeypatch.chdir(tmp_path)
    assert main(['clean', '--all']) == 0
    capsys.readouterr()
    assert not generated.exists()
    assert (kit / 'STANDARD.md').is_file()
    assert (notes / 'keep.txt').is_file()


def test_cli_default_scan_and_audit_find_the_safe_output(tmp_path, capsys):
    kit = engineering_kit(tmp_path)
    assert main(['scan', str(tmp_path), '--json']) == 0
    capsys.readouterr()
    assert (kit / 'STANDARD.md').exists()
    assert main(['audit', str(tmp_path), '--json']) == 0
    assert '"baseline_present": true' in capsys.readouterr().out


def test_marker_never_authorizes_removing_an_engineering_kit(tmp_path):
    kit = engineering_kit(tmp_path)
    (kit / '.ases-output').write_text('ASES generated output. Safe to remove.\n')
    with pytest.raises(ValueError):
        clean_output(kit)
    assert (kit / 'STANDARD.md').is_file()


def test_output_links_cannot_redirect_cleanup_or_scanning(tmp_path):
    source, target, link = tmp_path / 'app', tmp_path / 'target.ases', tmp_path / 'link.ases'
    source.mkdir()
    target.mkdir()
    (target / '.ases-output').write_text('ASES generated output. Safe to remove.\n')
    (target / 'keep.txt').write_text('preserve')
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('Creating symlinks is not permitted by this Windows account.')
    with pytest.raises(ValueError):
        clean_output(link)
    with pytest.raises(ValueError):
        scan_project(source, link)
    assert (target / 'keep.txt').is_file()


@pytest.mark.parametrize('name', ['artifact-snapshot.json', 'bundle.js'])
def test_artifact_output_cannot_overwrite_its_supplied_input(tmp_path, name):
    from ases.artifacts import write_artifact
    (tmp_path / '.ases-output').write_text('ASES generated output. Safe to remove.\n')
    source = tmp_path / name
    source.write_text('{}' if name.endswith('.json') else "fetch('/users');")
    before = source.read_bytes()
    with pytest.raises(ValueError):
        write_artifact(source, tmp_path)
    assert source.read_bytes() == before
