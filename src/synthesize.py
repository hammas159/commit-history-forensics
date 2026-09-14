"""Generate fabricated commit histories, to have ground truth to detect.

This reproduces what contribution-graph generators do - `git commit --date=<past>`
against a single text file - so the detector is evaluated on the real artefact rather
than on a guess about what one looks like.

Everything is written to a temporary directory and never pushed anywhere. The point
is to *detect* these, not to make them: see README for why using one is a bad idea.
"""

from __future__ import annotations

import random
import subprocess
import time
from pathlib import Path

ENV_BASE = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def _run(args: list[str], cwd: Path, env: dict | None = None) -> None:
    import os

    full = {**os.environ, **ENV_BASE, **(env or {})}
    # check=False: the error is raised below with the git stderr attached, which is
    # far more useful than CalledProcessError's exit code alone.
    out = subprocess.run(args, cwd=cwd, env=full, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {out.stderr.strip()[:200]}")


def generate(
    target: Path,
    days: int = 365,
    max_per_day: int = 10,
    frequency: int = 80,
    seed: int = 0,
    hide_skew: bool = False,
) -> Path:
    """Build a repo whose history is entirely fabricated.

    `hide_skew=False` reproduces the naive tool: it sets only the author date, so the
    committer date stays at 'now'. `hide_skew=True` is the harder adversary that also
    sets GIT_COMMITTER_DATE - included so the detector is not evaluated only against
    the easiest possible forgery.
    """
    rng = random.Random(seed)
    target.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], target)

    log = target / "README.md"
    now = int(time.time())

    for day in range(days, 0, -1):
        if rng.randint(0, 100) > frequency:
            continue
        for i in range(rng.randint(1, max_per_day)):
            stamp = now - day * 86400 + i * 60
            iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stamp))
            message = f"Contribution: {time.strftime('%Y-%m-%d %H:%M', time.localtime(stamp))}"
            log.write_text(log.read_text() + message + "\n\n" if log.exists() else message + "\n")
            _run(["git", "add", "README.md"], target)
            env = {"GIT_COMMITTER_DATE": iso} if hide_skew else {}
            _run(["git", "commit", "-q", "-m", message, "--date", iso], target, env)

    return target


def generate_realistic(target: Path, commits: int = 40, seed: int = 0) -> Path:
    """A control: a *genuine-looking* small repo, committed normally.

    Without this the detector could be separating 'many commits' from 'few commits'
    rather than fabricated from real.
    """
    rng = random.Random(seed)
    target.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], target)

    verbs = ["Add", "Fix", "Refactor", "Remove", "Document", "Test", "Rename", "Handle"]
    nouns = [
        "parser",
        "cache",
        "config",
        "client",
        "retry logic",
        "error path",
        "schema",
        "loader",
        "timeout",
        "index",
        "validation",
        "CLI flag",
    ]

    for _ in range(commits):
        # Real commits touch a varying number of files.
        for f in range(rng.randint(1, 6)):
            path = target / f"mod_{rng.randint(0, 12)}.py"
            path.write_text(
                path.read_text() + f"# {rng.random()}\n" if path.exists() else f"# {rng.random()}\n"
            )
        _run(["git", "add", "-A"], target)
        message = f"{rng.choice(verbs)} {rng.choice(nouns)}"
        _run(["git", "commit", "-q", "-m", message], target)

    return target


if __name__ == "__main__":
    import sys
    import tempfile

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    print("generating into", out)
    naive = generate(out / "fake_naive", days=90, max_per_day=5, seed=1)
    print("  fake (naive, author-date only) ->", naive)
    sneaky = generate(out / "fake_hidden", days=90, max_per_day=5, seed=2, hide_skew=True)
    print("  fake (committer date hidden)  ->", sneaky)
    real = generate_realistic(out / "control_real", commits=40, seed=3)
    print("  control (normal commits)      ->", real)
