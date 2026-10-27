from hashlib import sha256
import pytest
from ases.ui import source_window


@pytest.mark.parametrize('ending',['\n','\r\n','\r'])
def test_large_source_preview_retains_only_window_and_verifies_full_hash(tmp_path,ending):
    data=ending.join('# '+str(i)+' café' for i in range(110000)).encode('utf-8')
    assert len(data)>1024*1024
    path=tmp_path/'large.py';path.write_bytes(data)
    view=source_window(path,100000,sha256(data).hexdigest())
    assert view['total_lines']==110000
    assert len(view['lines'])==33 and view['start']==99992
    assert view['lines'][8]=='# 99999 café'
    assert view['verified_bytes']==len(data)
    with pytest.raises(ValueError,match='changed'):source_window(path,1,'0'*64)


@pytest.mark.parametrize('data,total',[(b'',0),(b'a',1),(b'a\n',1),(b'\n\n',2),(b'a\r\nb',2)])
def test_source_line_boundaries(tmp_path,data,total):
    path=tmp_path/'source.py';path.write_bytes(data)
    assert source_window(path,1,sha256(data).hexdigest())['total_lines']==total


def test_long_line_and_stream_budget_are_bounded(tmp_path,monkeypatch):
    path=tmp_path/'source.py';data=b'x'*1500000+b'\nend';path.write_bytes(data)
    view=source_window(path,1,sha256(data).hexdigest())
    assert view['lines']==['x'*2000,'end'] and view['lines_truncated']
    monkeypatch.setattr('ases.ui.SOURCE_LIMIT',65536)
    with pytest.raises(ValueError,match='verification budget'):source_window(path,1,sha256(data).hexdigest())
