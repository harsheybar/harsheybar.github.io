# TriNetX OAuth Setup Guide

This guide will help you integrate your TriNetX OAuth credentials once you receive them.

## Prerequisites

- Institutional TriNetX subscription
- OAuth client credentials from TriNetX support
- Python environment with agent system installed

## What You'll Receive

TriNetX will provide you with:
- **Client ID**: Unique identifier for your application
- **Client Secret**: Secret key for authentication
- **Organization ID**: Your institution's identifier
- **API Endpoint**: Usually `https://api.trinetx.com` or institution-specific

## Step 1: Store Credentials Securely

### Option A: Environment Variables (Recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc
export TRINETX_CLIENT_ID="your_client_id_here"
export TRINETX_CLIENT_SECRET="your_client_secret_here"
export TRINETX_ORG_ID="your_org_id_here"

# Reload shell
source ~/.bashrc
```

### Option B: Configuration File (Not Recommended for Production)

Create `.env` file (DO NOT commit to git):

```
TRINETX_CLIENT_ID=your_client_id_here
TRINETX_CLIENT_SECRET=your_client_secret_here
TRINETX_ORG_ID=your_org_id_here
```

Load with python-dotenv:
```bash
pip install python-dotenv
```

## Step 2: Test Authentication

Create a test script `test_trinetx_auth.py`:

```python
#!/usr/bin/env python
"""
Test TriNetX authentication.
"""

import os
from config import get_config
from agents.trinetx_agent import TriNetXAgent

def test_trinetx_authentication():
    """Test TriNetX OAuth authentication."""

    # Get credentials from environment
    client_id = os.getenv('TRINETX_CLIENT_ID')
    client_secret = os.getenv('TRINETX_CLIENT_SECRET')
    org_id = os.getenv('TRINETX_ORG_ID')

    if not all([client_id, client_secret, org_id]):
        print("❌ Missing credentials!")
        print("Required environment variables:")
        print("  - TRINETX_CLIENT_ID")
        print("  - TRINETX_CLIENT_SECRET")
        print("  - TRINETX_ORG_ID")
        return False

    print("Testing TriNetX authentication...")
    print(f"Client ID: {client_id[:10]}...")
    print(f"Organization: {org_id}")

    try:
        config = get_config()
        agent = TriNetXAgent(config)

        # Authenticate
        token = agent.authenticate(
            client_id=client_id,
            client_secret=client_secret,
            organization=org_id
        )

        print("✅ Authentication successful!")
        print(f"Token: {token[:20]}...")

        # Test basic query
        print("\nTesting cohort creation...")
        cohort_def = agent.build_cohort_definition()
        print(f"Cohort: {cohort_def['name']}")

        # Try querying (may take time)
        print("\nQuerying cohort data...")
        data = agent.query_cohort(cohort_def)

        if not data.empty:
            print(f"✅ Retrieved {len(data)} geographic locations")
            print("\nSample data:")
            print(data.head())
        else:
            print("⚠️  No data returned (may be expected if no matches)")

        return True

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify credentials with TriNetX support")
        print("  2. Check network access to TriNetX API")
        print("  3. Confirm institutional subscription is active")
        return False


if __name__ == "__main__":
    test_trinetx_authentication()
```

Run the test:
```bash
python test_trinetx_auth.py
```

## Step 3: Update Production Configuration

Edit `production_config.py`:

```python
import os

# Option 1: From environment variables (recommended)
TRINETX_TOKEN = None  # Will authenticate on demand
TRINETX_CLIENT_ID = os.getenv('TRINETX_CLIENT_ID')
TRINETX_CLIENT_SECRET = os.getenv('TRINETX_CLIENT_SECRET')
TRINETX_ORG_ID = os.getenv('TRINETX_ORG_ID')

# Option 2: Authenticate and get token
from agents.trinetx_agent import TriNetXAgent
from config import get_config

config = get_config()
agent = TriNetXAgent(config)

TRINETX_TOKEN = agent.authenticate(
    client_id=TRINETX_CLIENT_ID,
    client_secret=TRINETX_CLIENT_SECRET,
    organization=TRINETX_ORG_ID
)

# Now run with real TriNetX data
pipeline = TumorSurgeryAnalysisPipeline(
    census_api_key=CENSUS_API_KEY,
    trinetx_token=TRINETX_TOKEN,
    use_mock_trinetx=False  # Use real data!
)
```

## Step 4: Run Production Analysis

```bash
# Full production run with real TriNetX data
python production_config.py --full-run
```

Or use environment variables directly:

```bash
export TRINETX_CLIENT_ID="your_id"
export TRINETX_CLIENT_SECRET="your_secret"
export TRINETX_ORG_ID="your_org"

python main.py \
  --census-key 0c7b04265914894c6cdb919dbaf22085761f8561 \
  --use-real-trinetx \
  --output-dir production_results
```

## Step 5: Verify Data Quality

After running, check:

```python
import pandas as pd

# Load results
data = pd.read_csv('production_results/surgery_data_raw.csv')

# Check TriNetX data
trinetx_data = data[data['data_source'].str.contains('TriNetX')]

print(f"TriNetX records: {len(trinetx_data)}")
print(f"Geographic locations: {trinetx_data['zipcode'].nunique()}")
print(f"Total procedures: {trinetx_data['total_procedures'].sum()}")
```

## Common Issues

### Issue 1: Authentication Fails

**Error**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:
1. Verify credentials are correct
2. Check that institutional subscription is active
3. Confirm your IP address/network has access
4. Contact TriNetX support to verify account setup

### Issue 2: No Data Returned

**Error**: Empty DataFrame from query

**Possible causes**:
1. No patients match cohort criteria (rare procedures)
2. Date range too restrictive
3. Geographic filters excluding data
4. Institutional data may not include procedure codes

**Solutions**:
1. Broaden cohort criteria
2. Extend date range
3. Check with TriNetX what data your institution has access to

### Issue 3: Timeout Errors

**Error**: `Request timeout`

**Solutions**:
1. Increase timeout in agent code
2. Large cohorts may take time - be patient
3. Consider breaking query into smaller geographic regions
4. Use TriNetX's asynchronous query API if available

### Issue 4: Token Expiration

**Error**: `401 Unauthorized` after some time

**Solution**: Tokens expire! Re-authenticate:

```python
# Tokens typically expire after 1 hour
# Re-authenticate as needed
token = agent.authenticate(
    client_id=client_id,
    client_secret=client_secret,
    organization=org_id
)
```

## Advanced: Custom TriNetX Queries

### Query Specific Date Range

```python
cohort_def = {
    "name": "Craniotomy 2024 Only",
    "criteria": {
        "inclusionCriteria": [
            {
                "type": "procedure",
                "codes": [{"system": "CPT", "code": "61510"}],
                "dateRange": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                }
            }
        ]
    }
}

data = agent.query_cohort(cohort_def)
```

### Query Specific Geographic Region

```python
# Add geographic filter (if supported by your TriNetX instance)
cohort_def = agent.build_cohort_definition()
cohort_def['geographicFilters'] = {
    'states': ['CA', 'NY', 'TX']  # Focus on specific states
}

data = agent.query_cohort(cohort_def)
```

### Export Large Cohorts

```python
# For very large cohorts, use export function
cohort_id = "your_cohort_id_from_previous_query"
filename = agent.export_cohort_data(cohort_id, output_format='csv')
print(f"Data exported to: {filename}")
```

## Security Best Practices

1. **Never commit credentials to git**
   - Use environment variables
   - Add credentials files to `.gitignore`

2. **Rotate credentials regularly**
   - Request new OAuth credentials periodically
   - Update environment variables

3. **Use read-only access**
   - Request minimal necessary permissions
   - Don't request write access unless needed

4. **Monitor usage**
   - Track API calls
   - Watch for unusual patterns
   - Stay within institutional limits

5. **Secure token storage**
   - Don't log tokens
   - Don't share tokens
   - Store encrypted if persisting

## TriNetX Support

If you encounter issues:

1. **Technical Support**: support@trinetx.com
2. **Documentation**: https://trinetx.com/documentation
3. **Your Institution's Admin**: Check who manages TriNetX at your organization

## Data Use Agreement

Remember:
- TriNetX data is de-identified but still sensitive
- Follow your institution's data use policies
- Comply with TriNetX terms of service
- Results should be reviewed for potential re-identification risks
- Aggregate data appropriately before publication

## Example: Complete Production Run

```python
#!/usr/bin/env python
"""
Complete production run with TriNetX.
"""

import os
from main import TumorSurgeryAnalysisPipeline
from agents.trinetx_agent import TriNetXAgent
from config import get_config

# Get credentials
CENSUS_KEY = "0c7b04265914894c6cdb919dbaf22085761f8561"
TRINETX_CLIENT_ID = os.getenv('TRINETX_CLIENT_ID')
TRINETX_CLIENT_SECRET = os.getenv('TRINETX_CLIENT_SECRET')
TRINETX_ORG_ID = os.getenv('TRINETX_ORG_ID')

# Authenticate
config = get_config()
trinetx = TriNetXAgent(config)

print("Authenticating with TriNetX...")
token = trinetx.authenticate(
    client_id=TRINETX_CLIENT_ID,
    client_secret=TRINETX_CLIENT_SECRET,
    organization=TRINETX_ORG_ID
)
print("✓ Authenticated")

# Run pipeline
pipeline = TumorSurgeryAnalysisPipeline(
    census_api_key=CENSUS_KEY,
    trinetx_token=token,
    use_mock_trinetx=False
)

print("\nRunning production analysis...")
results = pipeline.run_full_analysis(
    output_dir="production_results",
    include_trinetx=True,
    include_cms=True
)

print("\n✓ Analysis complete!")
print(f"Results in: production_results/")
```

---

**Questions?** Contact your TriNetX administrator or check the main README.md for general support options.
