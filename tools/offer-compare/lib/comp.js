import { computeAllTaxes } from "./tax.js";
import { lookupRpp, compositeRpp, colAdjust } from "./col.js";

// Defaults for an offer; merge with user data when computing.
export const DEFAULT_OFFER = () => ({
  id: cryptoRandomId(),
  meta: { name: "New offer", state: "TX", locationKey: "Houston", localityKey: "", startDate: "", contractYears: 5 },
  cash: {
    base: 600000,
    baseYearly: [], // optional override array
    wRVU: { ratePerRVU: 80, threshold: 8000, expectedVolume: 8000 },
    signOn: { amount: 0, clawbackYears: 3 },
    relocation: 0,
    retention: [], // [{ year, amount, vestingYears }]
    loanRepayment: { annual: 0, totalCap: 0, taxable: true },
    call: { perShift: 0, shiftsPerYear: 0, annualStipend: 0 },
    directorship: { annual: 0 },
    qualityBonus: { maxAnnual: 0, expectedAnnual: 0 },
    cmeAllowance: 0
  },
  benefits: {
    retirement: {
      plan401kMatchPct: 0,        // % of salary match (e.g. 0.04)
      plan401kMatchCapPct: 1,     // up to % of salary contributed
      has457b: false,
      cashBalanceAnnual: 0,
      profitShareAnnual: 0
    },
    healthPremiumEmployerAnnual: 0,
    lifeInsuranceFace: 0,
    disability: { shortTermCovered: false, longTermCovered: false },
    malpractice: { type: "occurrence", tailCoverageCostIfClaimsMade: 0 },
    pto: { weeksPTO: 4, cmeDays: 5 }
  },
  preTax: { contribution401k: 0, contribution457b: 0, contributionHSA: 0 },
  filingStatus: "mfj",
  housingOverride: null, // { monthlyHousingCost: number }
  workHours: { clinicalHoursPerWeek: 50, weeksWorked: 48, callHoursPerYear: 0 }
});

function cryptoRandomId() {
  if (window.crypto && crypto.getRandomValues) {
    const a = new Uint32Array(2);
    crypto.getRandomValues(a);
    return `o_${a[0].toString(36)}${a[1].toString(36)}`;
  }
  return `o_${Math.random().toString(36).slice(2)}`;
}

function baseForYear(cash, year) {
  if (cash.baseYearly && cash.baseYearly.length >= year && cash.baseYearly[year - 1] != null) {
    return Number(cash.baseYearly[year - 1]) || 0;
  }
  return Number(cash.base) || 0;
}

function productivityBonus(wRVU) {
  const above = Math.max(0, (wRVU.expectedVolume || 0) - (wRVU.threshold || 0));
  return above * (wRVU.ratePerRVU || 0);
}

function callPay(call) {
  return (call.perShift || 0) * (call.shiftsPerYear || 0) + (call.annualStipend || 0);
}

// Annualized value of malpractice coverage: occurrence is "free" (employer pays
// in full and there's no tail liability). Claims-made carries an effective cost
// that lands on the physician at separation; we amortize it over the contract.
function malpracticeValueAnnual(malp, contractYears) {
  if (malp.type === "occurrence") return 0;
  const tail = Number(malp.tailCoverageCostIfClaimsMade) || 0;
  return -tail / Math.max(1, contractYears); // negative = liability vs occurrence
}

function ptoValue(base, weeksPTO) {
  return (base / 52) * (weeksPTO || 0);
}

function retirementMatchValue(base, retire, contribution401k) {
  const cap = (retire.plan401kMatchCapPct || 0) * base;
  const matched = Math.min(contribution401k || 0, cap);
  return matched * (retire.plan401kMatchPct || 0);
}

// Build a year-by-year stream for one offer.
export function buildSchedule(offer, federalData, stateTaxData, localTaxData, beaData) {
  const years = Math.max(1, Number(offer.meta.contractYears) || 1);
  const stateData = stateTaxData.states[offer.meta.state];
  const locality  = offer.meta.localityKey ? localTaxData.localities[offer.meta.localityKey] : null;
  const rppRow    = lookupRpp(beaData, offer.meta.locationKey || offer.meta.state);
  const effRpp    = compositeRpp(
    rppRow.rpp, rppRow.rentsRpp, beaData.housingWeight,
    offer.housingOverride?.monthlyHousingCost
  );

  const schedule = [];
  for (let y = 1; y <= years; y++) {
    const base = baseForYear(offer.cash, y);
    const productivity = productivityBonus(offer.cash.wRVU);
    const signOn = y === 1 ? (offer.cash.signOn?.amount || 0) : 0;
    const reloc  = y === 1 ? (offer.cash.relocation || 0) : 0;
    const retention = (offer.cash.retention || [])
      .filter(r => r.year === y)
      .reduce((s, r) => s + (Number(r.amount) || 0), 0);
    const loanCap = Number(offer.cash.loanRepayment?.totalCap) || 0;
    const loanAnnual = Number(offer.cash.loanRepayment?.annual) || 0;
    const loanPaidSoFar = (y - 1) * loanAnnual;
    const loanThisYear = loanCap > 0
      ? Math.max(0, Math.min(loanAnnual, loanCap - loanPaidSoFar))
      : loanAnnual;
    const loanTaxable = offer.cash.loanRepayment?.taxable !== false ? loanThisYear : 0;
    const callAmt = callPay(offer.cash.call);
    const director = offer.cash.directorship?.annual || 0;
    const quality = offer.cash.qualityBonus?.expectedAnnual || 0;
    const cme = offer.cash.cmeAllowance || 0;

    // Cash compensation is wages reportable as W-2 income (incl. taxable loan repay).
    // CME / relocation are often reimbursed (taxable to employee) — treated taxable here.
    const grossW2 =
      base + productivity + signOn + reloc + retention + loanTaxable +
      callAmt + director + quality + cme;

    // Benefits valuation (not all taxable — separated for clarity).
    const ret = offer.benefits.retirement;
    const matchVal = retirementMatchValue(base, ret, offer.preTax.contribution401k);
    const cashBal  = ret.cashBalanceAnnual || 0;
    const profit   = ret.profitShareAnnual || 0;
    const health   = offer.benefits.healthPremiumEmployerAnnual || 0;
    const lifeVal  = (offer.benefits.lifeInsuranceFace || 0) * 0.001; // proxy: ~$1/$1000 face
    const disab    = (offer.benefits.disability?.shortTermCovered ? 1500 : 0) +
                     (offer.benefits.disability?.longTermCovered  ? 3500 : 0);
    const malp     = malpracticeValueAnnual(offer.benefits.malpractice, years);
    const pto      = ptoValue(base, offer.benefits.pto?.weeksPTO);
    const benefitsValue = matchVal + cashBal + profit + health + lifeVal + disab + malp + pto;

    // Tax pre-tax salary deferrals are limited to actual wage exposure
    const tax = computeAllTaxes({
      gross: grossW2,
      preTax: offer.preTax,
      filingStatus: offer.filingStatus,
      federalData,
      stateData,
      locality
    });

    const afterTaxCash = grossW2 - tax.totalTax;
    const colAdjustedCash = colAdjust(afterTaxCash, effRpp);

    schedule.push({
      year: y,
      base, productivity, signOn, reloc, retention, loanTaxable,
      callPay: callAmt, directorship: director, quality, cme,
      grossW2,
      benefitsBreakdown: { matchVal, cashBal, profit, health, lifeVal, disab, malp, pto },
      benefitsValue,
      tax,
      afterTaxCash,
      colAdjustedCash,
      totalEconomicValue: afterTaxCash + benefitsValue,
      colAdjustedTotal: colAdjust(afterTaxCash + benefitsValue, effRpp)
    });
  }

  return { schedule, effRpp, rppRow, locality };
}

export function summarize(offer, federalData, stateTaxData, localTaxData, beaData, opts = {}) {
  const { discountRate = 0.05 } = opts;
  const { schedule, effRpp, rppRow, locality } = buildSchedule(
    offer, federalData, stateTaxData, localTaxData, beaData
  );

  const sumKey = (k) => schedule.reduce((s, r) => s + (r[k] || 0), 0);
  const npv = (key) =>
    schedule.reduce((s, r) => s + (r[key] || 0) / Math.pow(1 + discountRate, r.year - 1), 0);

  const wh = offer.workHours || {};
  const annualHours = (wh.clinicalHoursPerWeek || 0) * (wh.weeksWorked || 0) + (wh.callHoursPerYear || 0);
  const yrs = schedule.length;
  const avgAfterTax = sumKey("afterTaxCash") / yrs;
  const effectiveHourly = annualHours > 0 ? avgAfterTax / annualHours : null;

  return {
    schedule,
    effRpp,
    rppRow,
    locality,
    totals: {
      grossW2: sumKey("grossW2"),
      benefitsValue: sumKey("benefitsValue"),
      totalEconomicValue: sumKey("totalEconomicValue"),
      afterTaxCash: sumKey("afterTaxCash"),
      colAdjustedCash: sumKey("colAdjustedCash"),
      colAdjustedTotal: sumKey("colAdjustedTotal"),
      tax: sumKey("grossW2") - sumKey("afterTaxCash")
    },
    npv: {
      afterTaxCash: npv("afterTaxCash"),
      totalEconomicValue: npv("totalEconomicValue"),
      colAdjustedTotal: npv("colAdjustedTotal")
    },
    effectiveHourly,
    annualHours
  };
}
