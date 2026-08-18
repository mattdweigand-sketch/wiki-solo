#!/usr/bin/env python3
"""Adversarial evals for durable single-file replacement and stable locks."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import _durable_files as durable
from eval_lib import Results


REPO_ROOT = Path(__file__).resolve().parents[1]
results = Results()


with tempfile.TemporaryDirectory(prefix="wiki-durable-eval-") as td:
    root = Path(td)
    target = root / "target"
    target.write_bytes(b"old")
    digest = durable.atomic_replace_bytes(target, b"new")
    results.record("complete-replacement-passes", target.read_bytes() == b"new" and digest == durable.sha256_bytes(b"new"), "replacement mismatch")

    original_write = durable._write_once
    calls = 0

    def short_write(fd, content):
        nonlocal_calls[0] += 1
        return original_write(fd, content[:1])

    nonlocal_calls = [0]
    durable._write_once = short_write
    try:
        durable.atomic_replace_bytes(target, b"abcdef")
        ok = target.read_bytes() == b"abcdef" and nonlocal_calls[0] >= 6
    finally:
        durable._write_once = original_write
    results.record("short-writes-loop-to-completion", ok, f"calls={nonlocal_calls[0]}")

    durable._write_once = lambda _fd, _content: 0
    before = target.read_bytes()
    try:
        durable.atomic_replace_bytes(target, b"zero")
    except durable.DurableFileError as exc:
        ok = "zero-progress" in str(exc) and target.read_bytes() == before
        detail = str(exc)
    else:
        ok = False
        detail = "zero-progress write passed"
    finally:
        durable._write_once = original_write
    results.record("zero-progress-write-fails-old-intact", ok, detail)

    stages = (
        "before_write", "after_write", "after_file_fsync", "before_replace",
        "after_replace", "after_dir_fsync", "before_reopen", "after_reopen", "after_verify",
    )
    for stage in stages:
        path = root / f"fault-{stage}"
        path.write_bytes(b"old")
        try:
            durable.atomic_replace_bytes(
                path,
                b"new",
                fault=lambda current, wanted=stage: (_ for _ in ()).throw(RuntimeError(wanted)) if current == wanted else None,
            )
        except RuntimeError:
            ok = path.read_bytes() in {b"old", b"new"}
            detail = f"bytes={path.read_bytes()!r}"
        else:
            ok = False
            detail = "fault did not fire"
        results.record(f"fault-{stage}-leaves-complete-file", ok, detail)

    changed = root / "concurrent"
    changed.write_bytes(b"planned")
    expected = durable.sha256_bytes(b"planned")
    changed.write_bytes(b"third-party")
    try:
        durable.atomic_replace_bytes(changed, b"output", expected_sha256=expected)
    except durable.DurableFileError as exc:
        ok = "changed after planning" in str(exc) and changed.read_bytes() == b"third-party"
        detail = str(exc)
    else:
        ok = False
        detail = "concurrent edit was overwritten"
    results.record("preimage-recheck-preserves-third-party-bytes", ok, detail)

    absent = root / "absent"
    durable.atomic_replace_bytes(absent, b"created", expected_sha256=None)
    results.record("missing-target-can-be-created", absent.read_bytes() == b"created", "create failed")

    for kind in ("symlink", "hardlink", "directory", "fifo", "socket"):
        victim = root / f"unsafe-{kind}"
        anchor = root / f"anchor-{kind}"
        anchor.write_bytes(b"anchor")
        sock = None
        if kind == "symlink":
            victim.symlink_to(anchor)
        elif kind == "hardlink":
            os.link(anchor, victim)
        elif kind == "directory":
            victim.mkdir()
        elif kind == "fifo":
            os.mkfifo(victim)
        else:
            sock = socket.socket(socket.AF_UNIX)
            sock.bind(str(victim))
        try:
            try:
                durable.atomic_replace_bytes(victim, b"new")
            except durable.DurableFileError:
                ok = True
            else:
                ok = False
        finally:
            if sock is not None:
                sock.close()
        results.record(f"unsafe-{kind}-target-fails", ok, f"accepted {kind}")

    real_parent = root / "real-parent"
    real_parent.mkdir()
    link_parent = root / "link-parent"
    link_parent.symlink_to(real_parent, target_is_directory=True)
    try:
        durable.atomic_replace_bytes(link_parent / "file", b"x")
    except durable.DurableFileError as exc:
        ok = "parent is a symlink" in str(exc)
        detail = str(exc)
    else:
        ok = False
        detail = "symlink parent accepted"
    results.record("symlinked-parent-fails", ok, detail)

    lock = root / ".stable.lock"
    child_code = """
import sys
from pathlib import Path
from _durable_files import stable_lock
print('READY', flush=True)
with stable_lock(Path(sys.argv[1])):
    print('ACQUIRED', flush=True)
"""
    with durable.stable_lock(lock):
        inode_before = lock.stat().st_ino
        protected = root / "protected"
        protected.write_bytes(b"old")
        durable.atomic_replace_bytes(protected, b"new")
        proc = subprocess.Popen(
            [sys.executable, "-c", child_code, str(lock)],
            cwd=REPO_ROOT / "scripts", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        assert proc.stdout is not None
        ready = proc.stdout.readline().strip()
        try:
            proc.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            blocked = True
        else:
            blocked = False
    stdout, stderr = proc.communicate(timeout=5)
    results.record(
        "stable-lock-excludes-across-target-replacement",
        ready == "READY" and blocked and "ACQUIRED" in stdout and lock.stat().st_ino == inode_before,
        f"ready={ready!r} blocked={blocked} stdout={stdout!r} stderr={stderr!r}",
    )

sys.exit(results.finish())
