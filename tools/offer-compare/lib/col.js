// Cost-of-living adjustment via BEA Regional Price Parities.
// rpp = 100 means equal to US average. afterTaxCash / (rpp/100) → real $US-avg.

export function lookupRpp(beaData, locationKey) {
  if (!locationKey) return { rpp: 100, rentsRpp: 100, name: "US average", source: "default" };
  const m = beaData.metros?.[locationKey];
  if (m) return { rpp: m.rpp, rentsRpp: m.rentsRpp, name: m.name, source: "metro" };
  const s = beaData.states?.[locationKey];
  if (s) return { rpp: s.rpp, rentsRpp: s.rentsRpp, name: s.name, source: "state" };
  return { rpp: 100, rentsRpp: 100, name: "US average", source: "default" };
}

// Apply housing override: replace the housing component of the basket with the
// candidate's actual annual housing cost, keeping non-housing portion at the
// regional rate. Returns an effective composite RPP.
//
// Math: composite_RPP = (1 - w) * nonHousingRpp + w * housingRpp_effective
//   nonHousingRpp = (rpp - w * rentsRpp) / (1 - w)
//   housingRpp_effective = (userAnnualHousing / usAvgAnnualHousing) * 100
//
// usAvgAnnualHousing is approximated from total US-avg PCE * housing weight;
// we use a calibrated baseline so housingRpp_effective for a region matches
// rentsRpp when the user enters that region's typical cost.
const US_AVG_ANNUAL_HOUSING = 18000; // BEA-implied US-avg housing PCE per consumer unit (approx).

export function compositeRpp(rpp, rentsRpp, housingWeight, monthlyHousingOverride) {
  const w = housingWeight;
  const nonHousingRpp = (rpp - w * rentsRpp) / (1 - w);
  if (monthlyHousingOverride == null || monthlyHousingOverride <= 0) {
    return rpp; // no override
  }
  const annualUserHousing = monthlyHousingOverride * 12;
  const housingRppEff = (annualUserHousing / US_AVG_ANNUAL_HOUSING) * 100;
  return (1 - w) * nonHousingRpp + w * housingRppEff;
}

export function colAdjust(amount, effectiveRpp) {
  if (!effectiveRpp || effectiveRpp <= 0) return amount;
  return amount / (effectiveRpp / 100);
}
