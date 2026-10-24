# September 29 research brief

## What the competition actually rewards

This is a simulated trading contest, not a survey asking for point predictions. Final SUSQies wealth determines rank. Build forecasts first, then compare them with executable prices and evaluate the joint exposure of any positions. The supplied percentages have no capture timestamp and may represent indicative prices rather than fillable orders. Settlement is defined in each market's Info tab. [Official competition rules](https://predictionscup.com/rules/)

The paste contains 237 party contracts across 117 contests. Repeated display titles were removed; distinct Democratic, Republican and Independent contracts were retained. Many listed party YES prices sum above or below 100%. This is a data-quality and contract-comparison flag, not proof of an executable arbitrage. The paste does not contain Ohio Senate; the independent ratings universe does.

## Current evidence and its implications

**Senate uncertainty is shared.** Silver Bulletin's public September 29 article reports D-positive polling averages in six potentially consequential Senate states: Texas +3.6, Maine +2.7, Ohio +5.3, Iowa +2.1, Michigan +3.4 and Alaska +2.5. These are margins, not win probabilities. Small leads remain vulnerable to a common polling error. The model imports those averages as a single observation per state and does not also count older constituent polls. [Published averages](https://www.natesilver.net/p/nate-silver-2026-midterm-election-polls-model)

**Kansas is a high-priority disagreement.** Emerson's September 15–16 poll reports Hamilton ahead of Marshall 45–43. The supplied market snapshot places Democratic YES at 30%; the imported outside rating is more Republican-favorable than this poll. That is a reason to gather independent polls and assess candidate effects, not to assume the first poll proves an edge. In the same survey, Masterson leads Holscher 51–44 for governor, so treating Kansas as one uniform partisan event loses information. [Primary release](https://emersoncollegepolling.com/kansas-2026/)

**Texas has different Senate and governor contests.** Emerson's September 12–14 results show Talarico 47–46 over Paxton and Abbott 49–46 over Hinojosa. Preserve office-specific evidence rather than extrapolating one race to the other. The later published Senate average supersedes this raw Senate poll in the prototype; the governor poll remains in use. [Primary release](https://emersoncollegepolling.com/texas-2026-poll-talarico-and-paxton-in-dead-heat-abbott-maintains-edge/)

**Michigan also shows a split between offices.** Emerson reports El-Sayed 48–46 over Rogers for Senate, while Benson leads James 49–42 for governor. These lead sizes justify different estimates even with shared state uncertainty. Again, the newer Senate average replaces the raw Senate poll to avoid double counting. [Primary release](https://emersoncollegepolling.com/michigan-2026-poll-el-sayed-and-rogers-locked-in-close-election/)

**Iowa illustrates recency risk.** Emerson's August 31–September 1 poll had Hinson ahead of Turek 50–45, while Sand led Lahn 49–46. The later Senate average is more favorable to Democrats. The portal retains the older observation for audit but excludes it when using the newer average. A single old governor poll remains a weak foundation for a confident number. [Primary release](https://emersoncollegepolling.com/iowa-2026-poll-hinson-leads-turek/)

**Nevada governor remains sensitive to undecideds.** Emerson's September 5–8 poll has Ford 44 and Lombardo 42, with 11% undecided. A two-point lead cannot be translated directly into a high-confidence election call. The prototype widens uncertainty as evidence ages, but it does not yet model differential undecided allocation. [Primary release](https://emersoncollegepolling.com/nevada-2026-poll-ford-and-lombardo/)

**New Hampshire requires price-confidence review.** UNH's September 24 abstract describes a narrow Democratic Senate lead and statistical ties in NH-01 and the governor race. The pasted governor market assigns Republican YES 93%, while NH-01 Democratic YES is 93%. Those apparently decisive prices deserve investigation against the release. The report's numerical PDF returned HTTP 403, so the abstract is recorded as qualitative evidence and no numbers were guessed. [UNH release](https://scholars.unh.edu/survey_center_polls/1005/)

**Vermont is a direct source conflict.** UNH's September 24 abstract describes a statistical tie between Janoo and Scott. The outside ratings feed still labels the contest Solid Republican. A rating-only model would hide that disagreement behind a precise-looking probability, so this race is withheld until numerical evidence can be reviewed. [UNH release](https://scholars.unh.edu/survey_center_polls/1006/)

## Breadth of coverage

The Inside Elections public feeds contain the full 435-seat House, 100-seat Senate and 50-governor universe, including seats not up this cycle. The portal maps 2026 active ratings onto the challenge races. These are categorical expert assessments; the project's numerical rating conversion is an explicit analyst assumption. A rating's last-change date is not its last review date or the date of a new poll. [House](https://insideelections.com/ratings/house/), [Senate](https://insideelections.com/ratings/senate/), [Governors](https://insideelections.com/ratings/governor/)

Coverage must not be confused with deep independent research. Currently 11 challenge races have numerical polling estimates, 100 have only a rating-derived baseline, and six have no numeric estimate. All 117 have a reviewable record. The three explicit independent-candidate contests need multi-party models and exact settlement interpretation. Chamber-control calculations require validated caucus and seat mappings before use.

## Data architecture and refresh discipline

The original paste remains immutable. Downloaded public sources are archived with SHA-256 hashes; failures are logged. Verified numeric observations carry race ID, source ID, fieldwork end, publication date and sample size or declared assumed SE. Polls published after the model's as-of date are excluded.

The platform's public OpenAPI schema has been downloaded and inspected. Live market endpoints require bearer authentication and explicit tournament context. A read-only paginated archive client is included, but no authenticated connection can be claimed without a configured user key. A quoted price from a different tournament currency is not interchangeable with a SUSQies price. [Official API reference](https://sig.thesuper.market/api/v1/docs)

Historical election returns and aggregate finance databases have been identified but not ingested into a fitted forecast. MIT's data is suitable for historical returns after boundary harmonization; FEC supplies federal candidate and campaign-finance data. Fundraising should enter only after holdout testing, and governors need separate state finance sources. [MIT](https://electionlab.mit.edu/articles/inside-2024-precinct-project), [FEC](https://www.fec.gov/data/browse-data/)

## Next research gates

1. Review each platform contract's settlement, IDs and live orderbook. Confirm election year, regular versus special seat and party versus caucus definitions.
2. Replace rating-only baselines with verified local polls or a fitted fundamentals model. Prioritize large discrepancies and source conflicts rather than spending equal effort on every safe seat.
3. Confirm House district correspondence in the 2026 map. Do not join old election results by district number alone.
4. Build cycle-held-out calibration and jointly estimate polling-error covariance. The current error scales and rating probabilities are assumptions, not fitted findings.
5. Extend independent and ranked-choice races with candidate-level vote/transfer models, then validate complete chamber simulation.
6. Connect current executable quotes and a user-reviewed portfolio to scenario losses. No trade should be described as actionable from an undated display price alone.

AAPOR's polling guidance motivates retaining shared error even after averaging; large sample sizes do not eliminate all sources of polling bias. [AAPOR](https://aapor.org/polling-accuracy/)
