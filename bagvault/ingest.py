from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(path: Path) -> list[tuple[str, str]]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        checksum, member = line.split(maxsplit=1)
        member = member.strip()
        if member.startswith("*"):
            member = member[1:]
        entries.append((checksum.strip().lower(), member.strip()))
    return entries


def _read_fetch(path: Path) -> dict[str, tuple[str, int]]:
    """Map payload path -> (url, declared length) from fetch.txt."""
    fetched = {}
    if not path.is_file():
        return fetched
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        url, length, member = line.split(maxsplit=2)
        fetched[member.strip()] = (url.strip(), int(length))
    return fetched


def _is_safe_payload_path(member: str) -> bool:
    if not member.startswith("data/") or member == "data/":
        return False
    if member.startswith("/") or "\\" in member or "\x00" in member:
        return False
    parts = member.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    return True


def _check_tagmanifest(bag_dir: Path) -> list[str]:
    tagmanifest = bag_dir / "tagmanifest-sha256.txt"
    mismatched = []
    if not tagmanifest.is_file():
        return mismatched
    for expected, member in _read_manifest(tagmanifest):
        tag_path = (bag_dir / member).resolve()
        if not tag_path.is_relative_to(bag_dir.resolve()) or not tag_path.is_file():
            mismatched.append(member)
            continue
        if _sha256_file(tag_path) != expected:
            mismatched.append(member)
    return mismatched


def _cache_lookup(cache_dir: Path, index: dict, url: str) -> Path | None:
    name = index.get(url)
    if not isinstance(name, str) or not name:
        return None
    candidate = (cache_dir / name).resolve()
    if not candidate.is_relative_to(cache_dir.resolve()) or not candidate.is_file():
        return None
    return candidate


def run_ingest(args) -> int:
    bag_dir = Path(args.bag).resolve()
    cache_dir = Path(args.cache).resolve()
    out_dir = Path(args.out).resolve()
    payload_out = out_dir / "payload"

    quarantine = []

    for tag_member in _check_tagmanifest(bag_dir):
        quarantine.append({"path": tag_member, "reason": "tag_mismatch"})

    manifest = _read_manifest(bag_dir / "manifest-sha256.txt")
    fetched = _read_fetch(bag_dir / "fetch.txt")

    index_path = cache_dir / "index.json"
    cache_index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {}

    if payload_out.is_symlink():
        payload_out.unlink()
    elif payload_out.exists():
        shutil.rmtree(payload_out)
    payload_out.mkdir(parents=True, exist_ok=True)

    payload_count = 0
    for expected_hash, member in manifest:
        if not _is_safe_payload_path(member):
            quarantine.append({"path": member, "reason": "path_escape"})
            continue

        relative = member[len("data/"):]
        target = (payload_out / relative).resolve()
        if not target.is_relative_to(payload_out.resolve()):
            quarantine.append({"path": member, "reason": "path_escape"})
            continue

        if member in fetched:
            url, _declared_length = fetched[member]
            cached = _cache_lookup(cache_dir, cache_index, url)
            if cached is None:
                quarantine.append({"path": member, "reason": "missing_cache"})
                continue
            source = cached
        else:
            source = bag_dir / member
            if not source.resolve().is_relative_to(bag_dir) or not source.is_file():
                quarantine.append({"path": member, "reason": "checksum_mismatch"})
                continue

        actual_hash = _sha256_file(source)
        if actual_hash != expected_hash:
            quarantine.append({"path": member, "reason": "checksum_mismatch"})
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        payload_count += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    quarantine_path = out_dir / "quarantine.jsonl"
    with quarantine_path.open("w", encoding="utf-8") as handle:
        for record in quarantine:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    report = {
        "payload_count": payload_count,
        "quarantine_count": len(quarantine),
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"ingest done: {payload_count} payload, {len(quarantine)} quarantined -> {out_dir}"
    )
    return 0
