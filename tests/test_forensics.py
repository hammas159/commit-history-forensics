"""Tests that build real git repositories in tmp_path.

No network, no fixtures checked into the repo: each test constructs the history it
needs with actual git commands, so what is asserted is the behaviour of the detector
against real git objects rather than against a mock of them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from features import Commit, find_repos, fingerprint, shannon_entropy
from score import evaluate, verdict
from synthesize import generate, generate_realistic

# --- pure functions ------------------------------------------------------------------


def test_entropy_of_identical_strings_is_zero():
    assert shannon_entropy(["same"] * 10) == 0.0


def test_entropy_of_distinct_strings_is_log2_n():
    assert shannon_entropy(["a", "b", "c", "d"]) == pytest.approx(2.0)


def test_entropy_of_empty_is_zero():
    assert shannon_entropy([]) == 0.0


def test_date_skew_is_committer_minus_author():
    assert Commit("h", 1000, 4000, "s", 1).date_skew == 3000
    assert Commit("h", 1000, 1000, "s", 1).date_skew == 0


# --- against real generated histories -------------------------------------------------


@pytest.fixture(scope="module")
def naive_fake(tmp_path_factory) -> Path:
    return generate(tmp_path_factory.mktemp("nf") / "fake", days=40, max_per_day=4, seed=7)


@pytest.fixture(scope="module")
def hidden_fake(tmp_path_factory) -> Path:
    # 90 days on purpose: two of the five signals are gated on a history spanning more
    # than 60 days, so a shorter fake is genuinely harder to call. See
    # test_short_hidden_fake_is_only_suspicious for that limitation, stated explicitly.
    return generate(
        tmp_path_factory.mktemp("hf") / "fake", days=90, max_per_day=6, seed=8, hide_skew=True
    )


@pytest.fixture(scope="module")
def short_hidden_fake(tmp_path_factory) -> Path:
    return generate(
        tmp_path_factory.mktemp("sh") / "fake", days=40, max_per_day=4, seed=8, hide_skew=True
    )


@pytest.fixture(scope="module")
def genuine(tmp_path_factory) -> Path:
    return generate_realistic(tmp_path_factory.mktemp("gr") / "real", commits=40, seed=9)


def test_naive_fake_is_flagged(naive_fake):
    label, fired = verdict(evaluate(fingerprint(naive_fake)))
    assert label == "FABRICATED", f"only {fired} flags fired"


def test_hidden_fake_is_still_flagged(hidden_fake):
    """The harder adversary sets GIT_COMMITTER_DATE too, defeating the skew signal.

    It must still be caught - otherwise the detector only works on the laziest forgery.
    """
    f = fingerprint(hidden_fake)
    assert f.skew_median == 0, "fixture should have concealed the skew"
    label, _ = verdict(evaluate(f))
    assert label == "FABRICATED"


def test_short_hidden_fake_is_only_suspicious(short_hidden_fake):
    """A documented limitation, asserted so it cannot regress silently.

    An adversary who conceals the committer date AND keeps the fabricated history
    short (under ~60 days, few commits per day) defeats three of the five signals.
    Only uniformity still fires, so the verdict lands on SUSPICIOUS rather than
    FABRICATED. The detector should say so rather than overclaim.
    """
    label, fired = verdict(evaluate(fingerprint(short_hidden_fake)))
    assert label in {"SUSPICIOUS", "FABRICATED"}, f"missed entirely ({fired} flags)"
    assert fired >= 1


def test_genuine_repo_is_clean(genuine):
    label, fired = verdict(evaluate(fingerprint(genuine)))
    assert label == "CLEAN", f"false positive: {fired} flags on a genuine history"


def test_skew_signal_only_fires_on_the_naive_fake(naive_fake, hidden_fake, genuine):
    def skew_fired(repo):
        return next(s.fired for s in evaluate(fingerprint(repo)) if s.name == "backdated_commits")

    assert skew_fired(naive_fake)
    assert not skew_fired(hidden_fake)
    assert not skew_fired(genuine)


def test_single_file_signal_catches_both_fakes(naive_fake, hidden_fake, genuine):
    def uniform_fired(repo):
        return next(
            s.fired for s in evaluate(fingerprint(repo)) if s.name == "single_file_every_commit"
        )

    assert uniform_fired(naive_fake)
    assert uniform_fired(hidden_fake)
    assert not uniform_fired(genuine)


# --- guard rails ----------------------------------------------------------------------


def test_short_history_does_not_trip_count_gated_signals(tmp_path):
    """A 3-commit repo touching one file each is normal, not fabricated.

    Without the `commits >= 10` gate this would be a false positive on every new repo.
    """
    repo = tmp_path / "tiny"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    import os

    for i in range(3):
        (repo / "only.py").write_text(f"x = {i}\n")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", f"change {i}"],
            cwd=repo,
            check=True,
            env={**os.environ, **env},
        )
    assert verdict(evaluate(fingerprint(repo)))[0] == "CLEAN"


def test_empty_repo_raises_clearly(tmp_path):
    repo = tmp_path / "empty"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    with pytest.raises(ValueError, match="no commits"):
        fingerprint(repo)


def test_find_repos_skips_plain_directories(tmp_path, genuine):
    (tmp_path / "not-a-repo").mkdir()
    import shutil

    shutil.copytree(genuine, tmp_path / "is-a-repo")
    found = {p.name for p in find_repos(tmp_path)}
    assert "is-a-repo" in found
    assert "not-a-repo" not in found
