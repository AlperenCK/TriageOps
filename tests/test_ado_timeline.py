"""Timeline -> basarisiz task tespitinin dogrulanmasi."""

from devops_agent.ado.builds import BuildReader


class _FakeClient:
    def __init__(self, timeline):
        self._timeline = timeline

    def get(self, path, *, params=None, collection_scope=False, as_text=False):
        if path.endswith("/timeline"):
            return self._timeline
        raise AssertionError(f"beklenmeyen cagri: {path}")


def test_failed_timeline_records_prefers_task(load_fixture):
    reader = BuildReader(_FakeClient(load_fixture("timeline_failed.json")))

    records = reader.get_failed_timeline_records(12345)

    # Job da 'failed' ama Task varken yalnizca Task dondurulmeli.
    assert len(records) == 1
    rec = records[0]
    assert rec.name == "Compile"
    assert rec.record_type == "Task"
    assert rec.log_id == 12
    # Yalnizca 'error' tipindeki issue'lar; 'warning' haric.
    assert rec.issues == ["error CS0103: 'Foo' adi gecerli degil"]


def test_failed_timeline_records_falls_back_when_no_task():
    timeline = {
        "records": [
            {"id": "j1", "type": "Job", "name": "J", "result": "failed",
             "issues": [{"type": "error", "message": "timeout"}], "log": {"id": 3}},
            {"id": "t1", "type": "Task", "name": "T", "result": "succeeded",
             "issues": [], "log": {"id": 4}},
        ]
    }
    reader = BuildReader(_FakeClient(timeline))

    records = reader.get_failed_timeline_records(1)

    assert len(records) == 1
    assert records[0].record_type == "Job"
    assert records[0].issues == ["timeout"]


def test_task_log_tail():
    class _LogClient:
        def get(self, path, *, params=None, collection_scope=False, as_text=False):
            return "l1\nl2\nl3\nl4\nl5"

    reader = BuildReader(_LogClient())
    out = reader.get_task_log(1, 12, tail=2)
    assert out == "l4\nl5"
