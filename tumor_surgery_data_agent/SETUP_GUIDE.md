# Setup Guide - Tumor Surgery Data Agent

Detailed step-by-step guide for setting up and using the Tumor Surgery Data Agent system.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [API Key Setup](#api-key-setup)
4. [Quick Start](#quick-start)
5. [Advanced Configuration](#advanced-configuration)
6. [Data Source Setup](#data-source-setup)
7. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for application + data
- **Internet**: Required for API queries

### Recommended Setup

- **Python**: 3.10+
- **RAM**: 16GB for large datasets
- **Storage**: 2GB+ for historical data
- **OS**: Linux, macOS, or Windows 10+

## Installation

### Step 1: Python Environment Setup

We recommend using a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For minimal installation (no visualizations):
pip install pandas numpy requests pyyaml matplotlib seaborn
```

### Step 3: Verify Installation

```bash
# Test imports
python -c "import pandas, numpy, requests, yaml; print('Success!')"
```

## API Key Setup

### Census Bureau API Key (Recommended)

The Census API key is free and significantly increases rate limits.

1. **Register for API key**:
   - Visit: https://api.census.gov/data/key_signup.html
   - Fill in your information
   - Receive key via email (instant)

2. **Configure the key**:

   **Option A: Environment Variable (Recommended)**
   ```bash
   # On macOS/Linux:
   export CENSUS_API_KEY="your_key_here"

   # Make permanent by adding to ~/.bashrc or ~/.zshrc:
   echo 'export CENSUS_API_KEY="your_key_here"' >> ~/.bashrc

   # On Windows (PowerShell):
   $env:CENSUS_API_KEY="your_key_here"

   # Make permanent (Windows):
   setx CENSUS_API_KEY "your_key_here"
   ```

   **Option B: Pass as argument**
   ```bash
   python main.py --census-key YOUR_KEY_HERE
   ```

### CMS API Access (Optional)

CMS provides public data without authentication, but having an API key may help with rate limits.

1. Visit: https://data.cms.gov/
2. Sign up for an account
3. Generate API key in your profile

### TriNetX Access (Institutional)

TriNetX requires institutional subscription:

1. **Check institutional access**:
   - Contact your hospital/university IT
   - TriNetX is common in academic medical centers

2. **Get credentials**:
   - Request OAuth credentials from TriNetX support
   - Your institution's TriNetX administrator can help

3. **Authenticate**:
   ```python
   from agents.trinetx_agent import TriNetXAgent
   from config import get_config

   config = get_config()
   agent = TriNetXAgent(config)

   token = agent.authenticate(
       client_id="your_client_id",
       client_secret="your_client_secret",
       organization="your_org_id"
   )
   ```

## Quick Start

### Example 1: Basic Analysis (Mock Data)

```bash
# Run with default settings (uses mock data)
python main.py
```

This will:
- Use synthetic TriNetX data
- Query Census Bureau (with fallback to mock if no key)
- Generate analysis and visualizations
- Output to `output/` directory

### Example 2: With Census API Key

```bash
python main.py --census-key YOUR_CENSUS_KEY
```

### Example 3: Custom Output Directory

```bash
python main.py \
  --census-key YOUR_KEY \
  --output-dir results/2025_analysis
```

### Example 4: Production Run (All Real Data)

```bash
python main.py \
  --census-key YOUR_CENSUS_KEY \
  --cms-key YOUR_CMS_KEY \
  --trinetx-token YOUR_TRINETX_TOKEN \
  --use-real-trinetx \
  --output-dir production_results
```

## Advanced Configuration

### Modifying Medical Codes

Edit `config/medical_codes.yaml` to add/remove CPT or DRG codes:

```yaml
cpt_codes:
  craniotomy_tumor_resection:
    - code: "61510"
      description: "Your description"
      category: "supratentorial_tumor"
    # Add more codes...
```

### Adjusting Coldspot Threshold

In `main.py` or when calling the mapper agent:

```python
# Default: 1.5x median
coldspot_data = mapper_agent.identify_coldspots(
    rate_data,
    threshold_multiplier=2.0  # More conservative threshold
)
```

### Custom Date Ranges

Edit `config/medical_codes.yaml`:

```yaml
date_range:
  start: "2024-01-01"
  end: "2024-12-31"
```

## Data Source Setup

### Working with HCUP Data

HCUP requires purchase and data use agreement:

1. **Purchase data**:
   - Visit: https://www.hcup-us.ahrq.gov/tech_assist/centdist.jsp
   - Select State Inpatient Database (SID) for geographic detail
   - Complete data use agreement

2. **Load HCUP data**:
   ```python
   from agents.data_query_agent import DataQueryAgent
   from config import get_config

   config = get_config()
   agent = DataQueryAgent(config)

   # Load your HCUP file
   hcup_data = agent.load_hcup_file("path/to/hcup_data.csv")
   ```

### Working with SEER Data

SEER provides cancer surveillance data:

1. **Request access**:
   - Visit: https://seer.cancer.gov/data-software/
   - Sign data use agreement
   - Download SEER*Stat software

2. **Export data**:
   - Use SEER*Stat to query brain tumor cases
   - Filter by CPT codes and geography
   - Export to CSV

3. **Load SEER data**:
   ```python
   import pandas as pd
   seer_data = pd.read_csv("seer_export.csv")
   # Process and add to pipeline
   ```

### Offline Mode

For environments without internet access:

1. **Pre-download data files**:
   ```bash
   # Download ZIP-MSA crosswalk
   wget https://www.huduser.gov/portal/datasets/usps/ZIP_CBSA_092023.xlsx

   # Download Census data
   # (use Census API to export large files)
   ```

2. **Load offline**:
   ```python
   mapper = MapperAgent(config)
   mapper.load_geographic_crosswalk("ZIP_CBSA_092023.xlsx")

   # Load pre-downloaded population data
   pop_data = pd.read_csv("census_population.csv")
   ```

## Example Workflows

### Workflow 1: State-Level Analysis

Focus analysis on a specific state:

```python
from agents.data_query_agent import DataQueryAgent
from agents.mapper_agent import MapperAgent
from config import get_config

config = get_config()
data_agent = DataQueryAgent(config)
mapper = MapperAgent(config, census_api_key="YOUR_KEY")

# Collect data
surgery_data = data_agent.aggregate_all_sources()

# Filter to specific state (e.g., California)
ca_data = surgery_data[surgery_data['zipcode'].str.startswith('9')]

# Continue with analysis
mapper.load_geographic_crosswalk()
msa_surgeries = mapper.map_surgeries_to_msa(ca_data)
# ... rest of pipeline
```

### Workflow 2: Temporal Comparison

Compare multiple time periods:

```bash
# Analyze 2023
python main.py --output-dir results/2023_analysis
# (Modify config date range to 2023)

# Analyze 2024
python main.py --output-dir results/2024_analysis
# (Modify config date range to 2024)

# Compare results
python compare_years.py results/2023_analysis results/2024_analysis
```

### Workflow 3: Custom Export

Export data in specific format:

```python
from main import TumorSurgeryAnalysisPipeline

pipeline = TumorSurgeryAnalysisPipeline(census_api_key="YOUR_KEY")
results = pipeline.run_full_analysis()

# Custom export
import json
with open('results.json', 'w') as f:
    json.dump(results['summary'], f, indent=2)
```

## Troubleshooting

### Issue: Import Error for yaml

```bash
pip install pyyaml
```

### Issue: Census API Returns 403

You've exceeded rate limit. Solutions:
1. Get API key (increases limit to unlimited)
2. Wait and retry
3. Use mock data for testing

### Issue: Visualizations Not Generating

Install optional dependencies:
```bash
pip install plotly kaleido
```

### Issue: Memory Error with Large Datasets

```python
# Process data in chunks
chunk_size = 10000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    process_chunk(chunk)
```

### Issue: TriNetX Authentication Failed

1. Verify credentials with TriNetX support
2. Check institutional subscription status
3. Ensure network allows TriNetX API access
4. Use mock data for testing: omit `--use-real-trinetx` flag

### Issue: Geographic Crosswalk Download Fails

Manual download:
```bash
# Download manually from:
# https://www.huduser.gov/portal/datasets/usps_crosswalk.html

# Place in project directory
python main.py  # Will auto-detect file
```

## Performance Optimization

### Speed Up Large Analyses

```python
# Use fewer data sources for testing
python main.py --no-cms --no-trinetx

# Process subset of MSAs
# (Modify mapper_agent.py to filter MSAs)

# Reduce visualization complexity
# (Edit heatmap_generator.py)
```

### Reduce Memory Usage

```python
# In config, reduce data collection period
date_range:
  start: "2024-01-01"
  end: "2024-12-31"  # Single year instead of 3

# Process data in smaller batches
# Enable garbage collection
import gc
gc.collect()
```

## Next Steps

After setup:

1. **Run initial analysis**: `python main.py`
2. **Review outputs**: Check `output/` directory
3. **Customize**: Modify configs for your needs
4. **Scale up**: Add real data sources
5. **Integrate**: Connect to your data pipeline

## Support

- **Documentation**: See README.md
- **Issues**: Open GitHub issue
- **Community**: Join discussions

## Appendix: Full Example Script

```python
#!/usr/bin/env python
"""
Complete example workflow
"""

from main import TumorSurgeryAnalysisPipeline
import logging

logging.basicConfig(level=logging.INFO)

# Initialize with your API keys
pipeline = TumorSurgeryAnalysisPipeline(
    census_api_key="your_census_key",
    cms_api_key="your_cms_key",  # Optional
    use_mock_trinetx=True  # Set False if you have TriNetX
)

# Run full analysis
results = pipeline.run_full_analysis(
    output_dir="my_analysis",
    include_trinetx=True,
    include_cms=True
)

# Print summary
print("\n" + "="*60)
print("Analysis Complete!")
print(f"Total MSAs: {results['summary']['total_msas_analyzed']}")
print(f"Coldspots: {results['summary']['coldspots_identified']}")
print("="*60)

# Results are saved to my_analysis/
```

Save as `run_analysis.py` and execute:
```bash
python run_analysis.py
```

---

**Ready to start?** Run `python main.py` to begin your first analysis!
