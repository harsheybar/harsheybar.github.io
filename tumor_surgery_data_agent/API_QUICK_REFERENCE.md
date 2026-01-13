# API Quick Reference Card

Quick reference for using your API credentials with the Tumor Surgery Data Agent.

## ✅ Your Current API Keys

### Census Bureau API Key
```
Key: 0c7b04265914894c6cdb919dbaf22085761f8561
Status: ✅ Ready to use
Cost: FREE
Rate Limit: Unlimited with key
```

### CMS Data API
```
Endpoint: https://data.cms.gov/data-api/v1/dataset/164fc736-4179-4100-9f79-592b69e41975/data
Status: ✅ Configured in code
Cost: FREE
Authentication: None required (public data)
```

### TriNetX OAuth
```
Status: ⏳ Pending OAuth credentials
Action Required: Obtain from TriNetX support
See: TRINETX_SETUP.md for detailed setup
```

## 🚀 Quick Start Commands

### 1. Test API Connections
```bash
cd tumor_surgery_data_agent
python production_config.py --test-only
```

This tests:
- Census Bureau API (with your key)
- CMS Data API (real endpoint)

### 2. Run Production Analysis (Current Setup)
```bash
python production_config.py --full-run
```

This runs with:
- ✅ Real Census data (your API key)
- ✅ Real CMS data (public endpoint)
- ⚠️  Mock TriNetX data (until OAuth available)

### 3. Command-Line Alternative
```bash
python main.py \
  --census-key 0c7b04265914894c6cdb919dbaf22085761f8561 \
  --output-dir my_results
```

## 📊 What Each API Provides

| API | Data Type | Geographic Detail | Time Period |
|-----|-----------|-------------------|-------------|
| **Census** | Population by MSA | MSA/County/ZIP | 2023 estimates |
| **CMS** | Medicare procedures | ZIP code | 2023-2025 |
| **TriNetX** | Clinical procedures | Configurable | Real-time |

## 🔧 Environment Variable Setup

### Set for Current Session
```bash
export CENSUS_API_KEY="0c7b04265914894c6cdb919dbaf22085761f8561"
```

### Set Permanently (Linux/Mac)
```bash
echo 'export CENSUS_API_KEY="0c7b04265914894c6cdb919dbaf22085761f8561"' >> ~/.bashrc
source ~/.bashrc
```

### Set Permanently (Windows PowerShell)
```powershell
setx CENSUS_API_KEY "0c7b04265914894c6cdb919dbaf22085761f8561"
```

## 📝 Expected Output Files

After running analysis, you'll find in `production_results/`:

```
production_results/
├── surgery_data_raw.csv          # All collected data
├── msa_population.csv            # Census MSA populations
├── coldspot_analysis.csv         # Complete analysis
├── coldspot_report.csv           # Ranked coldspots
├── coldspot_heatmap.png          # Visualization
├── msa_comparison.png            # Best vs worst
├── summary_table.html            # Interactive table
└── dashboard.html                # Interactive dashboard
```

## 🎯 Typical Workflow

```
1. Test APIs
   └─> python production_config.py --test-only

2. Run Analysis
   └─> python production_config.py --full-run

3. Review Results
   └─> cd production_results/
   └─> open dashboard.html

4. [Later] Add TriNetX
   └─> Get OAuth credentials
   └─> Update production_config.py
   └─> Re-run analysis
```

## 🔍 Checking Results Quality

### Quick Python Check
```python
import pandas as pd

# Load results
analysis = pd.read_csv('production_results/coldspot_analysis.csv')

print(f"Total MSAs analyzed: {len(analysis)}")
print(f"Coldspots identified: {analysis['is_coldspot'].sum()}")
print(f"Population coverage: {analysis['population'].sum():,}")

# Top 5 coldspots
top_coldspots = analysis[analysis['is_coldspot']].nlargest(5, 'severity_score')
print("\nTop 5 Coldspots:")
print(top_coldspots[['msa_name', 'population_per_surgery', 'severity_score']])
```

### Verify Census Data
```python
# Check if Census data looks reasonable
pop_data = pd.read_csv('production_results/msa_population.csv')
print(f"MSAs with population data: {len(pop_data)}")
print(f"Total US population covered: {pop_data['population'].sum():,}")
print(f"Largest MSA: {pop_data.nlargest(1, 'population')['msa_name'].values[0]}")
```

## 🐛 Troubleshooting

### Census API Returns Error
```bash
# Test the key directly
curl "https://api.census.gov/data/2023/pep/population?get=POP_2023,NAME&for=state:*&key=0c7b04265914894c6cdb919dbaf22085761f8561"
```

If this fails:
- Check internet connection
- Verify key wasn't revoked
- Try re-registering at https://api.census.gov/data/key_signup.html

### CMS API Returns No Data
```bash
# Test CMS endpoint directly
curl "https://data.cms.gov/data-api/v1/dataset/164fc736-4179-4100-9f79-592b69e41975/data?size=1"
```

If this fails:
- CMS API may be temporarily down
- Check CMS status page
- Dataset may have been updated (check data.cms.gov)

### Python Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install minimal set
pip install pandas numpy requests pyyaml matplotlib seaborn
```

## 📞 Getting Help

### Census Bureau API
- Support: https://www.census.gov/data/developers/guidance.html
- Status: https://status.census.gov/
- Re-register: https://api.census.gov/data/key_signup.html

### CMS Data API
- Portal: https://data.cms.gov
- Documentation: https://data.cms.gov/provider-data/api-docs
- Support: Via data.cms.gov contact form

### TriNetX
- Support: support@trinetx.com
- Setup Guide: See TRINETX_SETUP.md
- Status: Check with your institutional admin

### This Agent System
- README: See README.md
- Setup Guide: See SETUP_GUIDE.md
- Examples: See examples/basic_usage.py

## 🔐 Security Reminders

✅ **DO:**
- Use environment variables for keys
- Keep credentials out of git
- Store keys securely
- Rotate keys periodically

❌ **DON'T:**
- Commit keys to repositories
- Share keys publicly
- Hardcode in files (except for testing)
- Exceed rate limits

## 📈 Next Steps

1. **Now**: Test your current setup
   ```bash
   python production_config.py --test-only
   ```

2. **Today**: Run first analysis
   ```bash
   python production_config.py --full-run
   ```

3. **When TriNetX Ready**: Update credentials
   - See TRINETX_SETUP.md
   - Update production_config.py
   - Re-run analysis with real data

4. **Ongoing**: Monitor and improve
   - Check output quality
   - Validate coldspot findings
   - Refine analysis parameters
   - Add additional data sources

---

**Ready?** Start with: `python production_config.py --test-only`
