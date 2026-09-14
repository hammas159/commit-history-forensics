# Problems hit while building this

[<- back to README](../README.md)

## 1. An empty repository crashed the scanner

`git log` exits non-zero on a repository that has a branch but no commits. The scanner
raised `RuntimeError` - reporting a failure to *read* the history rather than an empty one.

**Fix:** detect that specific stderr message and return an empty list. The caller decides
what emptiness means; `fingerprint()` raises a clear `ValueError`.

**Test:** `test_empty_repo_raises_clearly`

## 2. A test fixture silently hid a real weakness

Shrinking the `hidden_fake` fixture to 40 days made the test fail: the verdict dropped to
`SUSPICIOUS`. Two of the five signals are gated on a span longer than 60 days, so a shorter
fake defeats them.

The easy move was to lengthen the fixture back to 90 days and say nothing.

**What was done instead:** kept **both**. A 90-day fixture asserts `FABRICATED`, and a
separate 40-day one asserts the weaker verdict. The limitation is now documented in
[LIMITATIONS.md](LIMITATIONS.md) and asserted in
`test_short_hidden_fake_is_only_suspicious`, so it cannot quietly regress.

This is the most useful thing in the repository's history: a failing test revealed a real
limitation, and the limitation was published rather than tuned away.

## 3. CI could not create the test fixtures

The tests build real git repositories with real commits. GitHub's runner has no git
identity configured, so `git commit` refused and every fixture failed.

**Fix:** configure `user.name`, `user.email` and `init.defaultBranch` in the workflow before
running pytest.

## 4. `subprocess.run` lint failure

`ruff` flagged `PLW1510` - missing an explicit `check=` argument - on calls that
deliberately inspect the return code themselves.

**Fix:** passed `check=False` explicitly, with a comment explaining that an empty repository
is a legitimate outcome handled below, not an exception.

## 5. CI cache misconfigured

`setup-uv` errors outright when its default `**/uv.lock` glob matches nothing - a hard job
failure, not a cache miss. No lock file is committed here.

**Fix:** keyed the cache on `pyproject.toml`.
