# The five signals

[<- back to README](../README.md)

Nothing here is trained. Each threshold is a stated number with a stated reason, so a reader
can disagree with a specific choice rather than with a model.

## 1. `backdated_commits`

**Fires when** the median gap between author time and committer time exceeds **one day**.

**Why that threshold:** a gap of minutes or hours is normal - rebases, applied patches and
cherry-picks all produce one. A gap of more than a day *in the median* means the entire
history was written at one sitting and dated backwards.

**What defeats it:** setting `GIT_COMMITTER_DATE` as well as the author date. The common
tools do not, but it is one environment variable.

## 2. `single_file_every_commit`

**Fires when** every commit touched exactly one file, and there are at least 10 commits.

**Why the count gate:** a three-commit repository touching one file each is a normal new
project, not a forgery. Without the gate this is a false positive on every young repo.

**What defeats it:** committing varied files. This is the signal that catches the
committer-date-faked forgery, because generators edit one log file by design.

## 3. `templated_messages`

**Fires when** more than 98% of commit subjects are unique, there are at least 30 commits,
**and** every commit touches one file.

**Why the conjunction:** unique messages alone are normal - most real commits have distinct
subjects. Unique messages *combined with* single-file commits is the signature of a
timestamp template like `Contribution: 2024-03-15 20:00`.

## 4. `implausible_cadence`

**Fires when** there are more than 8 commits per active day, every one a single-file edit.

**What defeats it:** committing less per day. Generators default to many commits per day to
darken the graph.

## 5. `saturated_calendar`

**Fires when** commits appear on more than 70% of days across a span longer than 60 days.

**Why the span gate:** a week of daily commits is a sprint. Ten months of near-unbroken
daily commits is not how humans work - there are holidays, illnesses and other projects.

**What defeats it:** leaving gaps, or keeping the fabricated history short. This is one of
the two signals a short forgery escapes.

## The verdict

| Signals fired | Verdict |
|---:|---|
| 3 or more | `FABRICATED` |
| 2 | `SUSPICIOUS` |
| 1 | `ONE FLAG` |
| 0 | `CLEAN` |

A blended score was deliberately avoided: a single number tells you *that* a repository
looked odd but not *why*, and the signals fail differently enough that the distinction
matters.
