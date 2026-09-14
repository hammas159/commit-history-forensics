# Results

[<- back to README](../README.md)

## Evaluation set

**25 genuine histories** - 24 real repositories with real development history, plus one
control repository committed normally by `generate_realistic()`.

**2 fabricated histories** built by `src/synthesize.py`:

- `fake_naive` - reproduces what contribution-graph generators do: `git commit --date`
  against a single log file, author date only
- `fake_hidden` - the harder adversary, which also sets `GIT_COMMITTER_DATE`

## Verdicts

| Repository class | n | Verdict | Signals fired |
|---|---:|---|---:|
| Genuine (24 real + 1 control) | 25 | **CLEAN** | 0 |
| `fake_naive` | 1 | **FABRICATED** | 4 / 5 |
| `fake_hidden` | 1 | **FABRICATED** | 3 / 5 |

**Zero false positives, zero false negatives** on this set.

## The two discriminating features

| Repository | commits | median author&rarr;committer gap | files per commit |
|---|---:|---:|---:|
| `fake_naive` | 224 | **3,196,575 s (37 days)** | **1.00** |
| `fake_hidden` | 233 | 0 s | **1.00** |
| control (genuine) | 40 | 0 s | 3.2 |
| 24 real repositories | 2 - 12 each | 0 s | 1.0 - 95.6 |

### Why `fake_hidden` is the interesting row

`git commit --date` sets **only the author date**. The committer date stays at "now", which
is why the naive fake shows a 37-day median gap - the loudest signal there is, and the one
common tools do not hide.

Setting `GIT_COMMITTER_DATE` closes that gap entirely. The forgery is still caught, because
**it edits exactly one file in every commit** and real work varies: the genuine
repositories span 1.0 to 95.6 files per commit.

## Real repository fingerprints

All 24 genuine repositories showed `skew_median = 0` - author and committer dates identical,
as expected for normal committing. Files-per-commit varied widely (1.0 to 95.6), and
subject entropy ranged 1.00 to 3.58 bits.

None tripped a single signal.

## Reproducing

```bash
python src/synthesize.py /tmp/fakes    # builds fake_naive, fake_hidden, control_real
python src/score.py /path/to/real/repos /tmp/fakes
```

The synthesiser is seeded, so the fabricated repositories are reproducible.
