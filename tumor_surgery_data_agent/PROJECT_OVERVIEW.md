# Project Overview: Tumor Surgery Data Agent System

## Executive Summary

The Tumor Surgery Data Agent System is a sophisticated multi-agent platform designed to identify geographic disparities in access to cranial tumor surgery across the United States. By integrating data from multiple public health sources and Census Bureau population data, the system identifies "coldspots" - areas where the ratio of population to surgical volume indicates inadequate access to neurosurgical care.

## Problem Statement

Access to specialized neurosurgical care for brain tumors is not evenly distributed across the United States. Rural and underserved areas may have significantly lower access to craniotomy procedures for tumor resections, leading to delayed treatment and worse outcomes. Identifying these geographic disparities is crucial for:

- Healthcare policy development
- Resource allocation decisions
- Identifying areas needing telemedicine expansion
- Guiding hospital network planning
- Supporting health equity research

## Solution Architecture

### Multi-Agent System

The system employs a modular multi-agent architecture:

**Agent 1: Data Query Agent**
- Queries CMS Medicare data for craniotomy procedures
- Integrates TriNetX clinical research network data
- Supports HCUP and SEER data integration
- Filters by specific CPT codes and DRG codes
- Focuses on 2023-2025 time period

**Agent 2: Mapper Agent**
- Queries Census Bureau for MSA population data
- Maps ZIP codes to Metropolitan Statistical Areas
- Calculates population-adjusted surgery rates
- Identifies coldspots using statistical methods
- Generates comprehensive reports

**Supporting Components:**
- Configuration management for medical codes
- Visualization engine for heatmaps and dashboards
- Data validation and quality checks

### Medical Focus

**Procedures Included:**
- Craniotomy for supratentorial brain tumors
- Craniotomy for meningiomas
- Craniotomy for posterior fossa tumors
- Craniotomy for skull base tumors
- Related tumor resection procedures

**Exclusions:**
- Non-tumor craniotomies (trauma, vascular, etc.)
- Stereotactic procedures (different access pattern)
- Pediatric-only procedures (different considerations)

## Data Sources

### Primary Sources (Public Access)

1. **CMS (Centers for Medicare & Medicaid Services)**
   - Medicare Provider Utilization files
   - Inpatient hospital data by DRG
   - Geographic granularity: ZIP code level
   - No cost, public access

2. **Census Bureau**
   - American Community Survey (ACS)
   - Population Estimates Program
   - Free API with key registration
   - MSA-level demographic data

3. **HUD USPS Crosswalk**
   - ZIP to MSA mapping files
   - Updated quarterly
   - Free download

### Secondary Sources (Restricted Access)

1. **TriNetX**
   - Requires institutional subscription
   - Real-time clinical data network
   - 100+ million patients across networks
   - System includes mock data generator for testing

2. **HCUP (AHRQ)**
   - Requires purchase and data use agreement
   - Most comprehensive hospital discharge data
   - State-specific geographic detail

3. **SEER (NCI)**
   - Requires data use agreement
   - Cancer surveillance data
   - Can validate surgical volume estimates

## Methodology

### 1. Data Collection

```
For each data source:
  - Query procedures matching CPT codes: 61510, 61512, 61518, 61519, 61520, 61521, etc.
  - Query admissions matching DRGs: 023, 024, 025, 026, 027
  - Filter date range: 2023-01-01 to 2025-12-31
  - Extract geographic identifier (ZIP code)
  - Aggregate by geography
```

### 2. Geographic Mapping

```
For each ZIP code:
  - Map to Metropolitan Statistical Area (MSA) using HUD crosswalk
  - Handle unmapped ZIPs (rural areas, new developments)
  - Aggregate surgical volumes by MSA
```

### 3. Population Integration

```
For each MSA:
  - Query Census Bureau for 2023 population estimate
  - Calculate: surgeries per 100,000 population
  - Calculate: population per surgery
```

### 4. Coldspot Identification

**Statistical Approach:**

```
National_Median = median(population_per_surgery)
Coldspot_Threshold = National_Median × 1.5

For each MSA:
  If population_per_surgery > Coldspot_Threshold:
    Mark as coldspot
    Calculate severity_score = (value - mean) / std_dev
```

**Interpretation:**
- Coldspot: MSA with >1.5× national median ratio
- High-severity: Coldspot with z-score > 2.0
- Critical: Coldspot with z-score > 3.0

### 5. Validation

- Compare against known neurosurgery center locations
- Cross-reference with hospital network data
- Validate against prior geographic health access studies

## Key Features

### 1. Comprehensive Medical Code Coverage
- 8 CPT codes for craniotomy tumor resections
- 5 DRG codes for cranial surgery admissions
- ICD-10 code filtering for tumor diagnoses

### 2. Multi-Source Data Integration
- Handles data from 6+ different sources
- Automatic format standardization
- Deduplication and quality checks

### 3. Geographic Precision
- ZIP code to MSA mapping
- Coverage of all 384 US MSAs
- Separate analysis for micropolitan areas

### 4. Rich Visualizations
- Static heatmaps (PNG)
- Interactive dashboards (HTML)
- Comparison charts (best vs worst coverage)
- Geographic distribution maps

### 5. Flexible Configuration
- YAML-based configuration files
- Easy to modify CPT/DRG codes
- Adjustable coldspot thresholds
- Customizable date ranges

### 6. Production-Ready
- Comprehensive error handling
- API rate limiting
- Mock data for testing
- Extensive documentation

## Use Cases

### 1. Healthcare Policy
**Scenario:** State health department wants to identify underserved areas

**Workflow:**
```bash
python main.py --census-key STATE_KEY --output-dir state_analysis
# Review coldspot_report.csv
# Identify rural areas needing intervention
# Plan mobile neurosurgery clinics or telemedicine expansion
```

### 2. Hospital Network Planning
**Scenario:** Hospital system evaluating service line expansion

**Workflow:**
```bash
python main.py --output-dir network_analysis
# Identify coldspots in service area
# Assess population-adjusted demand
# Plan facility locations or partnerships
```

### 3. Academic Research
**Scenario:** Researcher studying health equity in neurosurgery access

**Workflow:**
```bash
python main.py --census-key RESEARCH_KEY
# Analyze coldspot demographics using ACS data
# Correlate with outcomes data
# Publish findings on geographic disparities
```

### 4. Quality Improvement
**Scenario:** National neurosurgery organization analyzing access patterns

**Workflow:**
```bash
# Run analysis annually
python main.py --output-dir analysis_2023
python main.py --output-dir analysis_2024
python main.py --output-dir analysis_2025

# Compare trends over time
# Monitor impact of interventions
```

## Technical Specifications

### System Requirements
- Python 3.8+
- 4GB RAM (8GB recommended)
- Internet access for API queries
- 500MB disk space

### Dependencies
- Core: pandas, numpy, requests, pyyaml
- Visualization: matplotlib, seaborn, plotly
- Optional: geopandas, scipy, sklearn

### Performance
- Typical runtime: 2-5 minutes (with API access)
- Processes ~400 MSAs
- Generates 5-10 output files
- Memory usage: ~500MB for standard analysis

### Scalability
- Handles datasets with 100K+ records
- Supports state-level or national analysis
- Can be extended to county-level analysis
- Compatible with distributed computing frameworks

## Output Deliverables

### 1. Data Files (CSV)
- `surgery_data_raw.csv`: All collected surgical procedures
- `coldspot_analysis.csv`: Complete analysis with all metrics
- `coldspot_report.csv`: Filtered to coldspots only, ranked by severity

### 2. Visualizations
- `coldspot_heatmap.png`: Top 30 MSAs by population-per-surgery ratio
- `msa_comparison.png`: Side-by-side best vs worst access
- `dashboard.html`: Interactive multi-panel dashboard

### 3. Summary Reports
- `summary_table.html`: Sortable/filterable table of all MSAs
- Console output with key statistics and top 10 coldspots

## Future Enhancements

### Planned Features
1. **Temporal Analysis**: Track coldspot changes over time
2. **Outcome Integration**: Correlate access with survival/morbidity data
3. **Cost Analysis**: Estimate economic impact of access disparities
4. **Telemedicine Integration**: Factor in virtual neurosurgery consultations
5. **County-Level Detail**: More granular geographic analysis
6. **Real-Time Dashboard**: Web-based monitoring system
7. **Predictive Modeling**: Forecast future access needs

### Technical Improvements
1. **Database Backend**: PostgreSQL/MongoDB for large-scale data
2. **API Server**: REST API for programmatic access
3. **Containerization**: Docker deployment for reproducibility
4. **Cloud Integration**: AWS/Azure deployment options
5. **Automated Updates**: Scheduled data refresh pipeline

## Impact Metrics

### Expected Outcomes

**For Healthcare Systems:**
- Identify 20-30% of MSAs as coldspots
- Prioritize expansion investments
- Improve network adequacy metrics

**For Policy Makers:**
- Evidence-based resource allocation
- Target rural health initiatives
- Monitor health equity goals

**For Researchers:**
- Quantify geographic disparities
- Study social determinants of surgical access
- Evaluate intervention effectiveness

## Ethical Considerations

### Privacy
- All data is de-identified and aggregated
- No patient-level information stored
- Compliant with HIPAA regulations

### Equity
- Identifies disparities to promote equity
- Supports underserved communities
- Transparent methodology

### Clinical Validity
- Not a substitute for clinical judgment
- Requires expert interpretation
- Supplementary to other analyses

## Documentation

### Available Resources
1. **README.md**: Quick start and overview
2. **SETUP_GUIDE.md**: Detailed installation and configuration
3. **PROJECT_OVERVIEW.md**: This document (architecture and methodology)
4. **examples/basic_usage.py**: Code examples for common tasks
5. **Inline Documentation**: Comprehensive docstrings in all modules

### Support Channels
- GitHub Issues: Bug reports and feature requests
- Documentation: Comprehensive guides and examples
- Code Comments: Detailed inline documentation

## Conclusion

The Tumor Surgery Data Agent System provides a comprehensive, automated solution for identifying geographic disparities in neurosurgical access. By integrating multiple data sources and employing sophisticated statistical methods, it delivers actionable insights for healthcare policy, hospital planning, and equity research.

The system's modular architecture, extensive documentation, and production-ready design make it suitable for both academic research and operational healthcare analytics.

---

**Version:** 1.0.0
**Last Updated:** 2025-01-13
**License:** MIT
**Contact:** [GitHub Issues](https://github.com/yourusername/tumor-surgery-data-agent)
