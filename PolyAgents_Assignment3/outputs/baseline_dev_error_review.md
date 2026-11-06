# Provisional error review: checkpoint baseline (Llama-3-8B stand-in, zero-shot CoT), dev split

All 10 errors out of 103 dev problems. Single-reviewer, PROVISIONAL categories (drafted with Claude Code, to be
re-labelled independently by two team members with the final scheme).

| ID | Heur. distractor | Gold | Pred | Category | Note |
|---|---|---|---|---|---|
| chal-30 | yes | 2 | 2.5 | extraction | uses "$5", which is not in the problem |
| chal-76 | no | 2173 | 2153 | arithmetic | correct setup 53 x 41, wrong product |
| chal-932 | yes | 3021 | 3011 | arithmetic | correct setup 57 x 53, wrong product; ignored distractor correctly |
| chal-191 | yes | 76 | 11 | filtering / inconsistency | computes 154 - 78 = 76 in step 3 but final line says "Answer: 11" |
| chal-917 | yes | 123 | 42 | filtering | question asks what was *made*; model uses *sold* quantities |
| chal-566 | yes | 2 | 14 | filtering | answers with the given bag count instead of 28 / 14 |
| chal-377 | yes | 6 | -137 | extraction | replaces 145 cakes sold with 2 |
| chal-601 | no | 2 | 6 | operation | adds instead of subtracting after algebra confusion |
| chal-498 | yes | 1 | -293 | ill-posed item | "bought 99 candy bars for $3 each" with $4; gold 4 - 3 = 1 treats 99 as distractor |
| chal-641 | yes | 2 | 0 | ill-posed item | gold 6 / 3 = 2 ignores "Dan has $2" |

Counts: extraction 2, filtering 3, operation 1, arithmetic 2, ill-posed item 2, format 0.
