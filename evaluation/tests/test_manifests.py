from pathlib import Path
import pytest
from evaluation.manifests import hash_files, record_command, safe_artifact


def test_source_mutation_changes_manifest(tmp_path):
    source=tmp_path/'input.py';source.write_text('a=1')
    before=hash_files(tmp_path,[Path('input.py')]);source.write_text('a=2')
    assert before!=hash_files(tmp_path,[Path('input.py')])


def test_command_failure_recorded_and_timeout_bounded(tmp_path):
    import sys
    result=record_command([sys.executable,'-c','import sys; print("failure"); sys.exit(7)'],tmp_path,tmp_path/'failed.txt',2)
    assert result['exitCode']==7 and 'failure' in (tmp_path/'failed.txt').read_text()
    result=record_command([sys.executable,'-c','import time; time.sleep(2)'],tmp_path,tmp_path/'timeout.txt',0.01)
    assert result['exitCode']==124 and result['timedOut']


def test_evidence_paths_cannot_escape_run(tmp_path):
    for path in ('../outside','/etc/passwd'):
        with pytest.raises(ValueError):safe_artifact(tmp_path,path)
    outside=tmp_path.parent/'target.txt';outside.write_text('external')
    (tmp_path/'link').symlink_to(outside)
    with pytest.raises(ValueError):safe_artifact(tmp_path,'link')
