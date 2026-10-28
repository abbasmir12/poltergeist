"""Audit log tests — JSONL, redacted, thread-safe enough, wipeable."""

import threading

from poltergeist.safety.audit import AuditLog


def test_record_and_tail(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record(command="rm -rf sjack-evil", verdict="blocked", approved_by="ghost-auto")
    log.record(
        command="ls", verdict="safe", approved_by="user", exit_code=0, output="daemon spook\n"
    )
    entries = log.tail(10)
    assert len(entries) == 2
    assert entries[0]["verdict"] == "blocked"
    assert entries[1]["exit_code"] == 0


def test_output_is_redacted(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record(
        command="ls",
        verdict="safe",
        approved_by="user",
        output="SECRET_KEY=ghp_SecretGhostSecretsLongEnough\n",
    )
    entry = log.tail(10)[0]
    assert "ghp_SecretGhostSecretsLongEnough" not in entry["output_preview"]


def test_disabled_log_writes_nothing(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl", enabled=False)
    assert log.record(command="ls", verdict="safe", approved_by="user") is None
    assert not (tmp_path / "audit.jsonl").exists()
    assert log.tail() == []


def test_wipe(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.record(command="echo", verdict="safe", approved_by="user")
    assert log.wipe() is True
    assert log.wipe() is False
    assert not path.exists()


def test_thread_safety_smoke(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")

    def spam(i: int) -> None:
        for _ in range(25):
            log.record(command=f"echo {i}", verdict="safe", approved_by="user")

    threads = [threading.Thread(target=spam, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(log.tail(1000)) == 100
