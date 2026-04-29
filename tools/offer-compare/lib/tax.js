// Pure tax math. All inputs are USD; "filingStatus" ∈ {"single","mfj","hoh"}.

export function applyBrackets(taxableIncome, brackets) {
  if (taxableIncome <= 0) return 0;
  let owed = 0;
  let prev = 0;
  for (const b of brackets) {
    const cap = b.upTo == null ? Infinity : b.upTo;
    const slice = Math.min(taxableIncome, cap) - prev;
    if (slice > 0) owed += slice * b.rate;
    if (taxableIncome <= cap) break;
    prev = cap;
  }
  return owed;
}

export function federalIncomeTax(taxableIncome, filingStatus, federalData) {
  const brackets = federalData.brackets[filingStatus] || federalData.brackets.single;
  return applyBrackets(taxableIncome, brackets);
}

export function stateIncomeTax(stateTaxableIncome, filingStatus, stateData) {
  if (!stateData || stateData.type === "none") return 0;
  if (stateData.type === "flat") {
    return Math.max(0, stateTaxableIncome) * stateData.rate;
  }
  const brackets = stateData.brackets[filingStatus] || stateData.brackets.single;
  return applyBrackets(Math.max(0, stateTaxableIncome), brackets);
}

export function localTax({ locality, gross, stateTaxableIncome, stateTaxOwed, filingStatus }) {
  if (!locality) return 0;
  const base = locality.appliesTo === "gross" ? gross
             : locality.appliesTo === "stateTaxableIncome" ? stateTaxableIncome
             : locality.appliesTo === "nyStateTaxLiability" ? stateTaxOwed
             : 0;
  if (locality.type === "flat") return Math.max(0, base) * locality.rate;
  if (locality.type === "surcharge") return Math.max(0, base) * locality.rate;
  if (locality.type === "progressive") {
    const brackets = locality.brackets[filingStatus] || locality.brackets.single;
    return applyBrackets(Math.max(0, base), brackets);
  }
  return 0;
}

export function fica(wagesSubjectToFica, filingStatus, federalData) {
  const f = federalData.fica;
  const ss = Math.min(wagesSubjectToFica, f.ssWageBase) * f.ssRate;
  const medicare = wagesSubjectToFica * f.medicareRate;
  const addlThresh = f.addlMedicareThreshold[filingStatus] ?? f.addlMedicareThreshold.single;
  const addl = Math.max(0, wagesSubjectToFica - addlThresh) * f.addlMedicareRate;
  return { ss, medicare, addl, total: ss + medicare + addl };
}

// Compute taxable wages given gross + pre-tax deductions.
// Conventions:
//   401k/403b: reduces federal & state taxable; FICA still applied to gross.
//   457b:      reduces federal & state taxable; FICA still applied to gross.
//   HSA (cafeteria): reduces federal, state, and FICA wages.
export function computeTaxableIncomes({ gross, preTax, stdDed }) {
  const k401 = preTax.contribution401k || 0;
  const k457 = preTax.contribution457b || 0;
  const hsa  = preTax.contributionHSA  || 0;

  const ficaWages    = Math.max(0, gross - hsa);
  const fedAGI       = Math.max(0, gross - k401 - k457 - hsa);
  const fedTaxable   = Math.max(0, fedAGI - (stdDed.federal || 0));
  // Most states start from federal AGI and apply state-specific std deduction;
  // this is a reasonable approximation for high-income wage earners.
  const stateTaxable = Math.max(0, fedAGI - (stdDed.state || 0));

  return { ficaWages, fedAGI, fedTaxable, stateTaxable };
}

export function computeAllTaxes({
  gross, preTax, filingStatus, federalData, stateData, locality
}) {
  const stdDed = {
    federal: federalData.standardDeduction[filingStatus] ?? federalData.standardDeduction.single,
    state:   stateData?.stdDed?.[filingStatus] ?? 0
  };
  const inc = computeTaxableIncomes({ gross, preTax, stdDed });

  const fed   = federalIncomeTax(inc.fedTaxable, filingStatus, federalData);
  const state = stateIncomeTax(inc.stateTaxable, filingStatus, stateData);
  const ficaParts = fica(inc.ficaWages, filingStatus, federalData);
  const local = localTax({
    locality,
    gross,
    stateTaxableIncome: inc.stateTaxable,
    stateTaxOwed: state,
    filingStatus
  });

  const totalTax = fed + state + local + ficaParts.total;

  return {
    inputs: inc,
    federal: fed,
    state,
    local,
    fica: ficaParts,
    totalTax,
    afterTax: gross - totalTax,
    effectiveRate: gross > 0 ? totalTax / gross : 0
  };
}
