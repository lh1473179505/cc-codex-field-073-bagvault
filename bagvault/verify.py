from __future__ import annotations
import hashlib, json
from pathlib import Path

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rows(path):
    p=Path(path)
    if not p.is_file():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def run_verify(args) -> int:
    out=Path(args.out)
    exp=json.loads(Path(args.expect).read_text())
    errors=[]
    payload=out/"payload"
    got={}
    if payload.is_dir():
        for p in payload.rglob("*"):
            if p.is_file():
                rel=str(p.relative_to(payload)).replace("\\","/")
                got[rel]=sha(p)
    if set(got)!=set(exp["payload"]):
        errors.append(f"payload extra={sorted(set(got)-set(exp['payload']))} missing={sorted(set(exp['payload'])-set(got))}")
    for name,h in exp["payload"].items():
        if got.get(name)!=h:
            errors.append(f"{name} sha {got.get(name)} != {h}")
    late=rows(out/"quarantine.jsonl")
    have={(r.get("path"), r.get("reason")) for r in late}
    for q in exp["quarantine"]:
        if (q["path"], q["reason"]) not in have:
            errors.append(f"quarantine missing {q} (have {late})")
    # escape must not appear in payload or out root
    for p in out.rglob("*"):
        if p.is_file() and p.name=="pwned.txt":
            errors.append(f"escaped file was written: {p}")
    if errors:
        print("verify failed:")
        for e in errors:
            print(" -", e)
        return 1
    print("verify ok")
    return 0
