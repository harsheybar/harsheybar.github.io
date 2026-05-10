# Neurosurgery Offer Comparison Tool

A local-first, single-page web app that lets a candidate compare multiple
physician (originally neurosurgery) job offers across nominal, after-tax, and
cost-of-living-adjusted dimensions over the contract horizon.

**Privacy:** runs 100% in the browser. No analytics, no network calls beyond
loading static JSON data files. Offers persist via `localStorage`. Optional
JSON export/import or URL-hash share (URL contains your data — treat as
sensitive).

## Open it

```
# from the repo root
python3 -m http.server 8000
# then visit http://localhost:8000/tools/offer-compare/
```

Or just open `tools/offer-compare/index.html` in a modern browser; if your
browser blocks `fetch()` on `file://` URLs, use the `python3 -m http.server`
approach above.

## What it models

**Cash compensation:** base salary (with optional year-by-year overrides),
wRVU productivity bonus (rate × volume above threshold), sign-on bonus,
relocation allowance, retention bonuses (per-year schedule), student-loan
repayment (with optional total cap and taxable flag), call pay (per-shift +
annual stipend), medical directorship stipend, expected quality bonus, CME
allowance.

**Benefits valuation:** 401(k)/403(b) employer match (capped by `match% × salary`),
cash-balance / DB plan annual credit, profit-sharing, employer share of health
premium, life insurance face-value proxy, disability coverage proxy,
malpractice differential (occurrence is "free"; claims-made amortizes the
tail-coverage cost over the contract), PTO valued as `base / 52 × weeks`.

**Pre-tax deductions:** 401(k)/403(b), 457(b) (governmental/non-profit), HSA.
401k/403b/457b reduce federal + state income tax; HSA also reduces FICA wages.

**Taxes (2026):**
- Federal: progressive brackets + standard deduction by filing status.
- State: all 50 + DC. Flat-tax states use a single rate; no-tax states return 0.
  Most states' starting point is approximated as federal AGI − state std deduction.
- Local: NYC (progressive), Yonkers (NY surcharge), Philadelphia, Pittsburgh,
  major OH/MI/MD/MO/KY/IN cities (gross-wage flat rates), and Maryland counties.
  Localities not listed default to 0.
- FICA: 6.2% Social Security up to wage base + 1.45% Medicare on all wages +
  0.9% Additional Medicare above filing-status threshold.

**Cost of living:** BEA Regional Price Parities (RPP). Defaults to the metro
or state RPP. Optional housing override replaces the housing component of the
basket with the candidate's actual annual housing cost — useful when planning
to live well above or below the local median.

**Output metrics:**
- Year-by-year nominal, after-tax, and COL-adjusted cash.
- Contract-total nominal, after-tax, total economic value (cash + benefits),
  COL-adjusted total.
- NPV of after-tax cash and of total COL-adjusted economic value.
- Effective $/hour after-tax, given clinical + call hours.
- Effective composite RPP (after housing override, if any).

**PSLF / loans:** When a federal-loan balance is set in global settings, the
tool projects each offer's lifetime loan trajectory:
- For PSLF-eligible offers (501(c)(3) non-profit / government employer flag):
  auto-selects PAYE / new-IBR (the canonical PSLF plans — 10% of discretionary
  income, capped at the standard-10yr payment); reports total out-of-pocket
  paid before forgiveness + the forgiven balance.
- For non-eligible offers: models standard 10-year payoff, reporting total
  paid (including interest).
- Year-by-year loan payments are folded into the cash-flow comparison so the
  "after-tax after loan" line shows real take-home.

**PSLF caveats:**
- The std-10yr cap in real-world PAYE/IBR is fixed at the amount calculated
  when you first entered the plan. The tool conservatively recomputes the cap
  against the *current* balance, which slightly underestimates forgiveness
  benefit for borrowers who entered PAYE during residency at low income.
- ICR is intentionally excluded from the auto-pick. While ICR's 12-yr fixed
  amortization can be nominally lower than the std-10yr cap, ICR has interest-
  capitalization gotchas and is not the recommended PSLF route.
- PSLF forgiveness is federal-tax-free. Some states tax it. Not modeled here.
- The post-2024 SAVE plan injunction and OBBBA RAP rollout are not modeled.
  PAYE/new-IBR are assumed available; verify your eligibility.
- Family size for IDR is set globally and defaults to 2 (MFJ).
- Federal poverty guidelines used are 2026 estimates (continental US).

## Data sources

All data lives in `data/*.json` and can be hand-edited:

| File | Source | Notes |
|---|---|---|
| `federal-2026.json` | IRS Rev. Proc. inflation-adjusted figures | Verify at irs.gov before relying. |
| `state-tax-2026.json` | State Departments of Revenue | Top brackets only at physician-level income. |
| `local-tax-2026.json` | Municipal/county tax authorities | NYC, Yonkers, Philly, MD counties, OH/MI/MO/KY/IN cities. |
| `bea-rpp.json` | BEA Regional Price Parities | ~2023 release. Re-fetch annually. |

These values are **approximations** for planning. Year-end variation
(legislative changes, indexed brackets) means the JSON files should be
re-verified each tax year before the tool drives a real decision.

## Out of scope (v1)

- Partnership / ASC / imaging-center buy-in modeling for private-practice offers.
- 1099 / S-corp / locum tax structures (self-employment tax, QBI deduction).
- Itemized federal deductions (SALT cap, mortgage interest, charitable).
- AMT.
- Inflation forecasting across the contract horizon.
- Quality-of-life weighting (call frequency, schools, commute, family proximity)
  — purely financial in v1.
- Private student loans (PSLF/IDR don't apply); refinancing scenarios.
- State taxation of PSLF-forgiven balances (most states follow federal exclusion;
  a handful do not — verify your state).
- 25-yr taxable-forgiveness IDR scenario for non-PSLF borrowers (modeled as
  standard 10-yr payoff, which is cheapest for high earners).

## Disclaimer

Not financial, tax, or legal advice. This tool is a comparison aid only.
Verify every number against your actual contracts, IRS publications, your
state's department of revenue, and licensed advisors (CPA, financial planner,
attorney) before making decisions.
