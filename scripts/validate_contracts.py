"""Validate every contract schema and example, plus taxonomy consistency.

Usage:  uv run --with jsonschema python scripts/validate_contracts.py [extra.jsonl ...]
Example files are named <schema>.<anything>.json and are checked against contracts/schemas/<schema>.schema.json.
Extra .jsonl paths (e.g. data/generated/v1/train.jsonl) are validated line by line as Conversations.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "contracts" / "schemas"
EXAMPLES = ROOT / "contracts" / "examples"
taxonomy = json.loads((ROOT / "contracts" / "taxonomy.json").read_text())
FAMILIES = {f["id"] for f in taxonomy["families"]}
ZD = taxonomy["zero_day_prefix"]

errors = []
validators = {}
for path in sorted(SCHEMAS.glob("*.schema.json")):
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    validators[path.name.removesuffix(".schema.json")] = Draft202012Validator(schema)


def check(name, obj, where):
    for err in validators[name].iter_errors(obj):
        errors.append(f"{where}: {'/'.join(map(str, err.path)) or '<root>'}: {err.message}")
    fam = obj.get("family")
    fam_id = fam.get("id") if isinstance(fam, dict) else fam
    if fam_id and fam_id not in FAMILIES and not str(fam_id).startswith(ZD):
        errors.append(f"{where}: unknown family '{fam_id}' (not in taxonomy.json)")
    for key in obj.get("family_probs", {}):
        if key not in FAMILIES and not key.startswith(ZD):
            errors.append(f"{where}: family_probs key '{key}' not in taxonomy.json")
    if name == "conversation":
        turns, strike = obj.get("turns", []), obj.get("strike_turn")
        if obj.get("family") == "benign" and strike is not None:
            errors.append(f"{where}: benign conversation must have strike_turn null")
        if strike is not None and (strike >= len(turns) or turns[strike]["stage"] != "strike"):
            errors.append(f"{where}: strike_turn must index the first 'strike' turn")
        firsts = [i for i, t in enumerate(turns) if t["stage"] == "strike"]
        if firsts and strike != firsts[0]:
            errors.append(f"{where}: strike_turn={strike} but first strike stage is at {firsts[0]}")


for path in sorted(EXAMPLES.glob("*.json")):
    name = path.name.split(".")[0]
    if name not in validators:
        errors.append(f"{path.name}: no schema named {name}.schema.json")
        continue
    check(name, json.loads(path.read_text()), path.name)

for extra in sys.argv[1:]:
    for i, line in enumerate(Path(extra).read_text().splitlines(), 1):
        if line.strip():
            check("conversation", json.loads(line), f"{extra}:{i}")

if errors:
    print("CONTRACTS INVALID:\n  " + "\n  ".join(errors[:200]))
    sys.exit(1)
print(f"contracts OK: {len(validators)} schemas, {len(list(EXAMPLES.glob('*.json')))} examples"
      + (f", {len(sys.argv) - 1} dataset file(s)" if len(sys.argv) > 1 else ""))
