import pytest

from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_episode_persists_and_redacts_credentials(tmp_path):
    db_path = tmp_path / "data" / "test.db"
    with MemoryStore(db_path, workspace=tmp_path) as store:
        record_id = store.add_episode(
            'Called endpoint with password="secret-value"',
            source_ref="test",
            metadata={"auth": "Bearer abcdefgh"},
        )
        records = store.list_episodes()
    assert records[0]["id"] == record_id
    assert "secret-value" not in records[0]["summary"]
    assert "abcdefgh" not in str(records[0]["metadata"])


def test_database_must_stay_inside_workspace(tmp_path):
    outside = tmp_path.parent / "outside.db"
    with pytest.raises(ValueError):
        MemoryStore(outside, workspace=tmp_path)


def test_empty_episode_is_rejected():
    with MemoryStore(":memory:") as store:
        with pytest.raises(ValueError):
            store.add_episode("  ")


def test_unicode_episode_summary_roundtrip():
    with MemoryStore(":memory:") as store:
        record_id = store.add_episode("Kiểm tra bộ nhớ tiếng Việt có dấu", source_ref="manual-test")
        records = store.list_episodes()
        assert records[0]["id"] == record_id
        assert records[0]["summary"] == "Kiểm tra bộ nhớ tiếng Việt có dấu"

