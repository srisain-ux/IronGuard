"""Run API tools before or after member A supplies the editable ML package."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
if sys.version_info < (3, 11):
    os.execv(uv, [uv, "run", "--no-project", "--python", "3.11", "python", __file__, *sys.argv[1:]])
import tomllib  # noqa: E402

project = tomllib.loads((ROOT / "api/pyproject.toml").read_text())
command = [uv, "run", "--python", "3.11"]
if (ROOT / "api/.env").is_file():  # NVIDIA_API_KEY etc. live here (gitignored)
    command += ["--env-file", str(ROOT / "api/.env")]
if not (ROOT / "ml/pyproject.toml").is_file():
    print("ML package pending: installing API dependencies only; stub uses contract fixtures.", flush=True)
    command += ["--no-project"]
    dependencies = project["project"]["dependencies"] + project["dependency-groups"]["dev"]
    for dependency in dependencies:
        if dependency != "ironguard-ml":
            command += ["--with", dependency]
command += sys.argv[1:]
os.chdir(ROOT / "api")
raise SystemExit(subprocess.call(command))
