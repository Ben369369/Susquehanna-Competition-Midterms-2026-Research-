# Forecast specification and validation plan

Version 0.2.0, evidence cutoff September 29, 2026.

## Event identity comes first

Deduplicate repeated titles, not separate party contracts. Preserve YES and NO prices. A Republican NO contract includes Democratic, independent and any other qualifying victory. It is not automatically equivalent to Democratic YES. “Independent Party” must be interpreted from the platform's actual settlement language, not inferred from colloquial party labels. State Senate in these market titles is provisionally interpreted as U.S. Senate; each Market Info page still needs verification.

## Poll model

Let m be D minus R vote margin in percentage points. For polled Senate and governor races in `data/fundamentals.json`, begin with a partisan-lean prior: m ~ Normal(lean₂₀₂₄ + environment − national₂₀₂₄ ± incumbency, sd²), with environment D+7 (generic ballot, shaded down), a 3-point bonus toward a running incumbent's party (10 for Collins, documented), sd 7 for Senate and 10 for governor. Other races keep the weak neutral Normal(0, 15²). These are analyst-set assumptions, not a fitted fundamentals model; sparse polling now updates an informed baseline instead of a 50/50 one.

For raw poll j use sampling variance 10000/n_j, a conservative near-even approximation for a margin. Add 2² points² as a poll-level error allowance. Weight its precision by 2^(-age/21). Within each pollster, average margins by these weights but cap effective precision at that firm's strongest observation. This prevents repetitions from driving uncertainty toward zero. It is not a full house-effects or overlapping-sample model.

Published polling averages replace underlying polls. The six Silver averages receive assumed SE 2.5 points; the publisher did not supply those SEs. A newly imported raw poll ending after an average replaces the stale average in this prototype. This conservative rule avoids unknown overlap but discards information and should eventually become a documented constituent-level overlap model.

Posterior precision = 1/225 + sum(effective firm precision). Posterior mean = weighted margins / posterior precision. Add a scenario shift, if requested.

Predictive variance adds posterior variance, national error 2.5², state error 1.5², local election error 2², and 0.035 × days remaining. A user uncertainty multiplier scales all standard deviations. These are exposed **research assumptions**, not empirical estimates of 2026 error.

P(D wins) = Phi(mean / predictive SD), conditional on the D/R winner approximation. R uses the complement. Other-party wins are not modeled; races explicitly containing independent contracts are withheld. Alaska/Maine estimates do not simulate ranked-choice transfers. The 80% interval is mean ± 1.28155 SD and describes margins.

## Rating baselines

Inside Elections' public JSON supplies categorical ratings. Our mapping assigns the favored party .99 / .90 / .75 / .60 for Solid / Likely / Lean / Tilt, and .50 for Toss-up. These values are not attributed to Inside Elections and have not been fitted. A synthetic margin = 6 × Phi^-1(p_D), with SD 6, permits consistent scenario shifts. It is not an estimated vote margin from actual polling.

Where polls exist, use the polling model and show the rating for comparison; do not combine two sources as independent when ratings may already incorporate the polls. When a newly verified qualitative source conflicts sharply with an old rating, suppress the rating-derived number pending review (currently Vermont governor).

## Joint scenarios

For each of 10,000 seeded draws, generate one national shock, one shock per state and one race-specific shock. All races share the national shock; races in the same state share their state shock. Local variance fills the remaining predictive variance. This induces a positive semidefinite covariance structure by construction.

The displayed count mixes Senate, House and governor races that have estimates. It is explicitly not a chamber forecast. Chamber simulation needs a validated complete seat universe, non-election seats, independent caucus outcomes, special-election identifiers, ties, vacancies and platform resolution semantics. A database containing all seats is necessary but not sufficient.

## Scoring and portfolio interpretation

The contest uses final simulated wealth, not Brier score. Use Brier/log loss to evaluate probabilities independently of trading. With a one-unit terminal payout, expected gross YES profit per share is p - executable ask; for NO it is (1-p) - its own executable ask. Subtract actual fees and account for depth. A displayed percentage with unknown timestamp is not an execution price.

The same race's Republican NO and Democratic YES can create duplicate exposure. Several Senate bets plus a chamber bet can all lose in the same polling-error scenario. Position sizing should be evaluated on joint terminal wealth, not by summing independent Kelly recommendations. Tournament rank incentives differ from maximizing expected or log wealth; do not optimize without knowing risk preference and current portfolio.

## Required out-of-sample validation

1. Build frozen as-of datasets for 2014, 2016, 2018, 2020, 2022 and 2024. Fit only on earlier election cycles; never randomly split races across years and call it independent validation.
2. Harmonize district maps and candidate identities. Match contemporaneous boundaries and distinguish primary from general-election polls. Preserve withdrawals and uncontested races.
3. Fit fundamentals from prior returns, national environment, incumbency, office and election cycle. Add aggregate campaign-finance variables only if they improve held-out scores.
4. Estimate polling error by firm, mode, office, state and cycle. Learn variance floors and national/state covariance rather than choosing convenient numbers.
5. Calibrate expert-rating mappings from historical ratings available at the relevant forecast horizon. Final ratings cannot stand in for September ratings.
6. Report Brier score, log loss, calibration bins, sharpness and interval coverage at 90/60/30/7 days, with cycle-level uncertainty. Benchmark against 50/50, prior partisan lean, expert-only and contemporaneous market models.
7. Evaluate full universes and report results separately for competitive races; safe-seat accuracy can conceal poor probability calibration.

The repository includes scoring primitives and behavioral tests, **not completed historical validation**. Research references: [AAPOR](https://aapor.org/polling-accuracy/), [FLIPR methodology](https://www.natesilver.net/p/flipr-midterms-model-methodology), [MIT returns](https://electionlab.mit.edu/articles/inside-2024-precinct-project), [FEC data](https://www.fec.gov/data/browse-data/).
