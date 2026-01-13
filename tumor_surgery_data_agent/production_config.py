"""
Production Configuration Script

This script demonstrates how to run the analysis with real API credentials.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import TumorSurgeryAnalysisPipeline


def run_with_real_credentials():
    """
    Run analysis with real API credentials.

    Configuration:
    - Census API Key: Provided
    - CMS Data API: Using real endpoint
    - TriNetX: Mock data (update when OAuth token available)
    """

    # Real Census Bureau API Key
    CENSUS_API_KEY = "0c7b04265914894c6cdb919dbaf22085761f8561"

    # CMS dataset is configured in data_query_agent.py
    # Endpoint: https://data.cms.gov/data-api/v1/dataset/164fc736-4179-4100-9f79-592b69e41975/data

    # TriNetX OAuth token (update when available)
    TRINETX_TOKEN = None  # Set this when you receive OAuth credentials

    print("="*70)
    print("TUMOR SURGERY DATA AGENT - PRODUCTION RUN")
    print("="*70)
    print("\nConfiguration:")
    print(f"  Census API Key: {'*' * 20}{CENSUS_API_KEY[-10:]}")
    print(f"  CMS Data API: Real endpoint configured")
    print(f"  TriNetX: {'Mock data (OAuth token pending)' if not TRINETX_TOKEN else 'Real data'}")
    print("\n" + "="*70 + "\n")

    # Initialize pipeline
    pipeline = TumorSurgeryAnalysisPipeline(
        census_api_key=CENSUS_API_KEY,
        cms_api_key=None,  # CMS Data API v1 doesn't require auth
        trinetx_token=TRINETX_TOKEN,
        use_mock_trinetx=(TRINETX_TOKEN is None)
    )

    # Run full analysis
    results = pipeline.run_full_analysis(
        output_dir="production_results",
        include_trinetx=True,
        include_cms=True
    )

    print("\n" + "="*70)
    print("PRODUCTION RUN COMPLETE")
    print("="*70)
    print(f"\nResults saved to: production_results/")
    print("\nKey outputs:")
    print("  - coldspot_analysis.csv: Complete analysis data")
    print("  - coldspot_heatmap.png: Visual representation")
    print("  - dashboard.html: Interactive dashboard")
    print("\nNext steps:")
    print("  1. Review output files in production_results/")
    print("  2. Update TRINETX_TOKEN when OAuth credentials available")
    print("  3. Re-run for analysis with real TriNetX data")

    return results


def test_cms_api():
    """
    Test CMS API connection with a small query.
    """
    import requests

    print("\n" + "="*70)
    print("TESTING CMS DATA API CONNECTION")
    print("="*70 + "\n")

    url = "https://data.cms.gov/data-api/v1/dataset/164fc736-4179-4100-9f79-592b69e41975/data"

    params = {
        'size': 10,  # Just get 10 records to test
        'offset': 0
    }

    print(f"Querying: {url}")
    print(f"Parameters: {params}\n")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        print("✓ CMS API connection successful!")
        print(f"✓ Retrieved {len(data) if isinstance(data, list) else 'unknown'} records")

        # Show sample record structure
        if isinstance(data, list) and len(data) > 0:
            print("\nSample record structure:")
            sample = data[0]
            print(f"  Columns: {list(sample.keys())[:10]}...")
        elif isinstance(data, dict):
            print(f"\nResponse type: dict with keys: {list(data.keys())}")

        return True

    except requests.RequestException as e:
        print(f"✗ CMS API connection failed: {e}")
        return False


def test_census_api():
    """
    Test Census Bureau API connection.
    """
    import requests

    print("\n" + "="*70)
    print("TESTING CENSUS BUREAU API CONNECTION")
    print("="*70 + "\n")

    CENSUS_API_KEY = "0c7b04265914894c6cdb919dbaf22085761f8561"

    # Test query for population data
    url = "https://api.census.gov/data/2023/pep/population"

    params = {
        'get': 'POP_2023,NAME',
        'for': 'metropolitan statistical area/micropolitan statistical area:*',
        'key': CENSUS_API_KEY
    }

    print(f"Querying: {url}")
    print(f"Using API key: {'*' * 20}{CENSUS_API_KEY[-10:]}\n")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        print("✓ Census API connection successful!")
        print(f"✓ Retrieved {len(data) - 1} MSAs (excluding header)")
        print("\nSample MSAs:")
        for row in data[1:6]:  # Show first 5 MSAs
            print(f"  - {row[1]}: Population {row[0]}")

        return True

    except requests.RequestException as e:
        print(f"✗ Census API connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify API key is correct")
        print("  2. Check internet connection")
        print("  3. Try: https://api.census.gov/data/key_signup.html")
        return False


def main():
    """
    Main entry point.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='Production configuration for Tumor Surgery Data Agent'
    )

    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Only test API connections, do not run full analysis'
    )

    parser.add_argument(
        '--full-run',
        action='store_true',
        help='Run full production analysis'
    )

    args = parser.parse_args()

    if args.test_only:
        print("\n" + "="*70)
        print("RUNNING API CONNECTION TESTS")
        print("="*70)

        census_ok = test_census_api()
        cms_ok = test_cms_api()

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Census API: {'✓ PASS' if census_ok else '✗ FAIL'}")
        print(f"CMS API: {'✓ PASS' if cms_ok else '✗ FAIL'}")

        if census_ok and cms_ok:
            print("\n✓ All tests passed! Ready for production run.")
            print("Run with --full-run to execute analysis.")
        else:
            print("\n✗ Some tests failed. Fix issues before running analysis.")

    elif args.full_run:
        run_with_real_credentials()

    else:
        # Default: run tests first, then ask about full run
        census_ok = test_census_api()
        cms_ok = test_cms_api()

        print("\n" + "="*70)

        if census_ok and cms_ok:
            print("✓ API tests passed!")
            print("\nReady to run full analysis.")
            print("\nOptions:")
            print("  1. Run full analysis: python production_config.py --full-run")
            print("  2. Test again: python production_config.py --test-only")
        else:
            print("✗ Some API tests failed.")
            print("Fix connection issues before running full analysis.")


if __name__ == "__main__":
    main()
