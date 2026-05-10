// PSLF / income-driven repayment modeling.
//
// Scope: federal Direct Loans (incl. consolidated). PSLF forgives the
// remaining balance after 120 qualifying monthly payments while working
// full-time at a qualifying employer (501(c)(3) non-profit or government).
// Forgiven balance is excluded from federal taxable income.
//
// Plans modeled:
//   PAYE  — 10% of discretionary income, capped at standard-10-yr payment
//           (cap is fixed at the amount when entering PAYE; we approximate
//           with std-10yr on the current balance).
//   IBR   — 10% of discretionary (post-2014 borrowers), 15% (pre-2014),
//           also capped at std-10yr.
//   ICR   — lower of 20% of discretionary income or a 12-yr fixed amortization.
//           No std-10yr cap.
//
// For PSLF optimization at attending-physician income, the std-10yr cap is
// what matters: PAYE / new-IBR pin the monthly payment to std-10yr, while
// ICR (and the now-enjoined SAVE) typically charge much more.

const MONTHS_PER_YEAR = 12;

// 2026 federal poverty guidelines (continental US, est.). Family size = 1
// adds POVERTY_INCREMENT per additional person.
const POVERTY_BASE_1 = 15650;
const POVERTY_INCREMENT = 5500;

export function povertyLine(familySize) {
  return POVERTY_BASE_1 + (Math.max(1, familySize) - 1) * POVERTY_INCREMENT;
}

export function discretionaryIncome(agi, familySize) {
  return Math.max(0, agi - 1.5 * povertyLine(familySize));
}

export function standard10yrMonthly(balance, annualRate) {
  if (balance <= 0) return 0;
  const r = annualRate / MONTHS_PER_YEAR;
  const n = 120;
  if (r === 0) return balance / n;
  return balance * r / (1 - Math.pow(1 + r, -n));
}

function fixedAmortMonthly(balance, annualRate, termMonths) {
  if (balance <= 0) return 0;
  const r = annualRate / MONTHS_PER_YEAR;
  if (r === 0) return balance / termMonths;
  return balance * r / (1 - Math.pow(1 + r, -termMonths));
}

function paye_ibrNew(args) {
  const idr = discretionaryIncome(args.agi, args.familySize) * 0.10 / MONTHS_PER_YEAR;
  const cap = standard10yrMonthly(args.balance, args.annualRate);
  return Math.min(idr, cap);
}

function ibrOld(args) {
  const idr = discretionaryIncome(args.agi, args.familySize) * 0.15 / MONTHS_PER_YEAR;
  const cap = standard10yrMonthly(args.balance, args.annualRate);
  return Math.min(idr, cap);
}

function icr(args) {
  const disc = discretionaryIncome(args.agi, args.familySize) * 0.20 / MONTHS_PER_YEAR;
  const fixed = fixedAmortMonthly(args.balance, args.annualRate, 144);
  return Math.min(disc, fixed);
}

const PLANS = {
  PAYE:   { name: "PAYE",                payment: paye_ibrNew, capped: true  },
  IBR:    { name: "IBR (new, post-2014)", payment: paye_ibrNew, capped: true },
  IBROld: { name: "IBR (old, pre-2014)",  payment: ibrOld,      capped: true },
  ICR:    { name: "ICR",                 payment: icr,         capped: false }
};

// For PSLF, prefer a capped plan (PAYE / new IBR) — these match the canonical
// strategist recommendation: 10% of discretionary, capped at the std-10yr
// payment. We pick the lower monthly between PAYE and IBR (they tie at
// attending income). ICR is intentionally excluded from the auto-pick: while
// its 12-yr fixed amortization can produce a nominally lower monthly than
// the std-10yr cap, ICR has interest-capitalization gotchas, more aggressive
// recertification rules, and is not the recommended PSLF route in practice.
export function selectOptimalPlanForPSLF(args) {
  const candidates = ["PAYE", "IBR"]
    .map(k => ({ key: k, plan: PLANS[k], monthly: PLANS[k].payment(args) }));
  candidates.sort((a, b) => a.monthly - b.monthly);
  return candidates[0];
}

// Simulate monthly cash flows. Stops at one of:
//   - balance reaches ~0 (full payoff)
//   - forgiveAtMonth reached (PSLF: forgive the remaining balance)
//   - hardCapMonths reached (safety)
export function simulate({
  balance, annualRate, monthlyPayment,
  forgiveAtMonth = null,
  hardCapMonths = 600
}) {
  const r = annualRate / MONTHS_PER_YEAR;
  let bal = balance;
  let totalPaid = 0;
  let forgiven = 0;
  let m = 0;
  const yearlyPayments = []; // sum of payments per year (1-indexed)

  while (bal > 0.005 && m < hardCapMonths) {
    m++;
    const interest = bal * r;
    bal += interest;
    const payment = Math.min(monthlyPayment, bal);
    bal -= payment;
    totalPaid += payment;
    const yearIdx = Math.ceil(m / MONTHS_PER_YEAR) - 1;
    yearlyPayments[yearIdx] = (yearlyPayments[yearIdx] || 0) + payment;
    if (forgiveAtMonth != null && m === forgiveAtMonth) {
      forgiven = bal;
      bal = 0;
      break;
    }
  }
  return { totalPaid, forgiven, monthsToCompletion: m, finalBalance: bal, yearlyPayments };
}

// One-shot projection for an offer.
//   loanSettings: { balance, paymentsMade, annualRate, familySize }
//   offer.pslfEligible: boolean
// agi: scalar steady-state AGI (use Y2 base salary or comparable proxy).
export function projectForOffer({ offer, agi, loanSettings }) {
  const { balance, paymentsMade, annualRate, familySize } = loanSettings;
  if (!balance || balance <= 0) {
    return {
      eligible: !!offer.pslfEligible,
      planName: "—",
      monthlyPayment: 0,
      totalPaid: 0,
      forgiven: 0,
      monthsToCompletion: 0,
      yearlyPayments: []
    };
  }
  const remaining = Math.max(0, 120 - (paymentsMade || 0));

  if (offer.pslfEligible) {
    const opt = selectOptimalPlanForPSLF({ agi, familySize, balance, annualRate });
    const sim = simulate({
      balance, annualRate,
      monthlyPayment: opt.monthly,
      forgiveAtMonth: remaining
    });
    return {
      eligible: true,
      planName: opt.plan.name,
      monthlyPayment: opt.monthly,
      totalPaid: sim.totalPaid,
      forgiven: sim.forgiven,
      monthsToCompletion: sim.monthsToCompletion,
      yearlyPayments: sim.yearlyPayments
    };
  }

  // Non-PSLF: standard 10-year payoff is the cheapest path for high earners
  // (lower lifetime interest than IDR forgiveness at 20-25 yrs which would
  // also be taxable and accrue more interest at attending income).
  const monthly = standard10yrMonthly(balance, annualRate);
  const sim = simulate({ balance, annualRate, monthlyPayment: monthly });
  return {
    eligible: false,
    planName: "Standard 10-yr",
    monthlyPayment: monthly,
    totalPaid: sim.totalPaid,
    forgiven: 0,
    monthsToCompletion: sim.monthsToCompletion,
    yearlyPayments: sim.yearlyPayments
  };
}
