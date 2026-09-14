# Future work

[<- back to README](../README.md)

## 1. A larger, more varied genuine corpus

The most valuable next step by a distance. 25 repositories with roughly five commits each,
all by one author, cannot establish a false-positive rate. Mining a few hundred real public
repositories - across languages, team sizes and ages - would make the claim mean something,
and would probably surface false positives worth fixing.

## 2. Multi-author signals

Every repository tested has a single author. Real projects have contributor distributions,
review latency, merge commits and co-authored trailers. A generator reproduces none of
them, which makes this a rich and currently unused signal family.

## 3. Diff-content signals

Current signals are purely structural: how many files, how often, when. Whether commits
change **meaningful code** - or rewrite the same line forever - is unused, and is what would
catch a forgery sophisticated enough to vary its file count.

## 4. Calibrated scoring

Replace the 3-of-5 rule with a likelihood ratio per signal, producing a probability rather
than a label. That needs the larger corpus from (1) to calibrate against.

## 5. Harden against the documented evasion

A short, committer-date-faked history with varied files currently reaches only
`SUSPICIOUS`. Closing that gap probably requires (3).

## 6. Ship as a GitHub Action

Report on a pull request, or on a repository when it is first opened. The detector has no
dependencies beyond the standard library, which makes this unusually easy.

## 7. Test against other generators

Two fabricated samples from one synthesiser is not a validated detector. Running against
the several public contribution-graph tools would show whether the signals generalise or
are specific to one implementation.
