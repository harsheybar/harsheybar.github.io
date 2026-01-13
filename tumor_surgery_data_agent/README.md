# Tumor Surgery Data Agent System

A comprehensive multi-agent system for querying public health data sources to identify geographic coldspots in cranial tumor surgery access across the United States.

## Overview

This system consists of two primary agents:

1. **Data Query Agent**: Queries multiple public health data sources (NCI, CMS, TriNetX, etc.) for craniotomy tumor surgery data, focusing on 2023-2025 data with geographic granularity.

2. **Mapper Agent**: Integrates Census Bureau data for all US Metropolitan Statistical Areas (MSAs), calculates population-adjusted surgery rates, and identifies "coldspots" where access to cranial tumor surgery is inadequate.

## Features

- ✅ **Multi-Source Data Collection**: Integrates data from CMS, NCI/SEER, TriNetX, HCUP, and CDC WONDER
- ✅ **CPT & DRG Code Filtering**: Focuses specifically on craniotomy procedures for tumor resections
- ✅ **Geographic Mapping**: Automatically maps ZIP codes to MSAs using HUD crosswalk files
- ✅ **Census Integration**: Queries Census Bureau API for real-time population data
- ✅ **Coldspot Identification**: Statistical analysis to identify underserved areas
- ✅ **Rich Visualizations**: Interactive maps, heatmaps, and dashboards
- ✅ **Mock Data Support**: Built-in mock data for testing without API access

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                         │
│                     (main.py)                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────┐          ┌──────────────────┐
│  Data Query      │          │  Mapper Agent    │
│  Agent           │          │                  │
│                  │          │  - Census API    │
│  - CMS API       │          │  - ZIP→MSA Map   │
│  - TriNetX API   │───Data──▶│  - Rate Calc     │
│  - SEER/NCI      │          │  - Coldspots     │
│  - HCUP          │          │                  │
└──────────────────┘          └────────┬─────────┘
                                       │
                                       ▼
                              ┌────────────────┐
                              │ Visualization  │
                              │ Generator      │
                              │                │
                              │ - Heatmaps     │
                              │ - Dashboards   │
                              │ - Reports      │
                              └────────────────┘
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) Census Bureau API key
- (Optional) TriNetX institutional access

### Setup

1. Clone the repository:
```bash
cd tumor_surgery_data_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Set up API keys:
```bash
export CENSUS_API_KEY="your_census_api_key"
export CMS_API_KEY="your_cms_api_key"  # Optional
export TRINETX_TOKEN="your_trinetx_token"  # If using real TriNetX
```

## Usage

### Quick Start (Mock Data)

Run the complete analysis pipeline with mock data:

```bash
python main.py
```

This will:
- Use mock TriNetX data
- Query Census Bureau for population data (or use mock if no API key)
- Perform coldspot analysis
- Generate visualizations in the `output/` directory

### Production Usage

With real API keys:

```bash
python main.py \
  --census-key YOUR_CENSUS_KEY \
  --cms-key YOUR_CMS_KEY \
  --output-dir results
```

With real TriNetX access:

```bash
python main.py \
  --census-key YOUR_CENSUS_KEY \
  --trinetx-token YOUR_TRINETX_TOKEN \
  --use-real-trinetx \
  --output-dir results
```

### Command-Line Options

```
--census-key        Census Bureau API key (free registration)
--cms-key          CMS API key (optional, increases rate limits)
--trinetx-token    TriNetX OAuth access token
--output-dir       Output directory (default: output)
--no-trinetx       Skip TriNetX data collection
--no-cms           Skip CMS data collection
--use-real-trinetx Use real TriNetX API instead of mock data
```

## Medical Codes

### CPT Codes for Craniotomy Tumor Resections

- **61510**: Craniectomy for brain tumor, supratentorial (except meningioma)
- **61512**: Craniectomy for meningioma, supratentorial
- **61518**: Craniectomy for brain tumor, infratentorial/posterior fossa
- **61519**: Craniectomy for meningioma, infratentorial
- **61520**: Craniectomy for cerebellopontine angle tumor
- **61521**: Craniectomy for midline tumor at base of skull
- **61524**: Craniectomy, transtemporal for cerebellopontine angle tumor
- **61545**: Excision of craniopharyngioma

### DRG Codes

- **023**: Craniotomy with major device implant or acute complex CNS diagnosis with MCC
- **024**: Craniotomy with major device implant or acute complex CNS diagnosis without MCC
- **025**: Craniotomy and endovascular intracranial procedures with MCC
- **026**: Craniotomy and endovascular intracranial procedures with CC
- **027**: Craniotomy and endovascular intracranial procedures without CC/MCC

## Data Sources

### Public Data Sources (No Authentication Required)

1. **CMS (Centers for Medicare & Medicaid Services)**
   - Medicare Provider Utilization files
   - Inpatient Prospective Payment System
   - Physician Compare data
   - URL: https://data.cms.gov

2. **Census Bureau**
   - American Community Survey (ACS)
   - Population Estimates Program
   - Free API key: https://api.census.gov/data/key_signup.html

3. **HUD USPS Crosswalk**
   - ZIP to MSA mappings
   - Updated quarterly
   - URL: https://www.huduser.gov/portal/datasets/usps_crosswalk.html

### Restricted Data Sources (Require Special Access)

1. **TriNetX**
   - Requires institutional subscription
   - Real-time clinical research network
   - OAuth 2.0 authentication

2. **NCI SEER**
   - Requires data use agreement
   - Cancer registry data
   - Request access: https://seer.cancer.gov

3. **HCUP (AHRQ)**
   - Requires purchase and data use agreement
   - Comprehensive hospital discharge data
   - URL: https://www.hcup-us.ahrq.gov

4. **ACS NSQIP**
   - Restricted to participating hospitals
   - Surgical quality data

## Output Files

The pipeline generates several output files:

```
output/
├── surgery_data_raw.csv          # Raw surgery data from all sources
├── msa_population.csv            # MSA population estimates
├── coldspot_analysis.csv         # Complete analysis with rates
├── coldspot_report.csv           # Coldspots only with rankings
├── coldspot_heatmap.png          # Static visualization
├── msa_comparison.png            # Top/bottom MSA comparison
├── summary_table.html            # Interactive summary table
└── dashboard.html                # Interactive dashboard (if Plotly available)
```

## Coldspot Definition

**Coldspots** are Metropolitan Statistical Areas where access to cranial tumor surgery is inadequate, defined as:

- Population-to-surgery ratio > 1.5× national median
- Statistical severity score (z-score) calculated for ranking
- Considers both absolute volume and population-adjusted rates

Example:
- National median: 10,000 people per surgery
- Coldspot threshold: 15,000+ people per surgery
- High severity coldspot: 25,000+ people per surgery

## API Rate Limits

- **Census Bureau**: 500 requests/day (unlimited with API key)
- **CMS**: ~100 requests/minute (Socrata API)
- **TriNetX**: Varies by institution

## Example Analysis Output

```
COLDSPOT ANALYSIS SUMMARY
============================================================
Total MSAs Analyzed: 384
Coldspots Identified: 96 (25.0%)
Population in Coldspots: 45,000,000

National Median (Pop/Surgery): 12,500
Coldspot Median (Pop/Surgery): 23,750

Top 10 Coldspots:
  1. Rapid City, SD
  2. Bismarck, ND
  3. Great Falls, MT
  4. Casper, WY
  5. Billings, MT
  6. Missoula, MT
  7. Fargo, ND-MN
  8. Sioux Falls, SD
  9. Boise City, ID
  10. Spokane-Spokane Valley, WA
============================================================
```

## Extending the System

### Adding New Data Sources

Create a new agent in `agents/`:

```python
from config import get_config

class NewDataSourceAgent:
    def __init__(self, config):
        self.config = config

    def query_data(self) -> pd.DataFrame:
        # Implement data collection
        pass
```

### Custom Visualizations

Extend the `HeatmapGenerator` class:

```python
from visualization.heatmap_generator import HeatmapGenerator

class CustomVisualization(HeatmapGenerator):
    def create_custom_viz(self, data):
        # Your custom visualization logic
        pass
```

## Privacy & Compliance

- All data sources use de-identified, aggregate data
- HIPAA-compliant data handling
- No PHI (Protected Health Information) stored
- Minimum case thresholds applied (typically n≥11)

## Troubleshooting

### Common Issues

1. **Census API errors**: Get a free API key at https://api.census.gov/data/key_signup.html

2. **Missing geographic mappings**: The system automatically downloads HUD crosswalk files. If offline, place `ZIP_CBSA_092023.xlsx` in the project directory.

3. **TriNetX authentication**: Ensure your institution has active TriNetX subscription. Contact TriNetX support for API credentials.

4. **Visualization errors**: Install optional dependencies:
   ```bash
   pip install plotly geopandas
   ```

## Contributing

Contributions welcome! Areas for improvement:

- Additional data source integrations
- Enhanced geographic granularity (county-level)
- Temporal trend analysis
- Clinical outcomes integration
- Cost analysis integration

## License

MIT License - See LICENSE file for details

## Citation

If using this system for research, please cite:

```
Tumor Surgery Data Agent System
Healthcare Analytics
https://github.com/yourusername/tumor-surgery-data-agent
```

## Contact

For questions or issues:
- Open an issue on GitHub
- Contact: [your-email@domain.com]

## Acknowledgments

- Census Bureau for population data
- CMS for Medicare utilization data
- HUD for geographic crosswalk files
- TriNetX network participants
- SEER program of the National Cancer Institute

---

**Disclaimer**: This system is for research and analysis purposes only. Clinical decisions should not be made based solely on this analysis. Always consult with qualified healthcare professionals.
