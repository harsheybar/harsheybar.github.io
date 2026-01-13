"""
Basic Usage Examples for Tumor Surgery Data Agent

This file demonstrates common usage patterns.
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from agents.data_query_agent import DataQueryAgent
from agents.trinetx_agent import TriNetXMockAgent
from agents.mapper_agent import MapperAgent
from visualization.heatmap_generator import HeatmapGenerator


def example_1_simple_query():
    """Example 1: Simple data query with mock data."""
    print("\n" + "="*60)
    print("Example 1: Simple Data Query")
    print("="*60)

    # Load configuration
    config = get_config()

    # Create data query agent
    agent = DataQueryAgent(config)

    # Query CMS data (will use mock/cached data if API unavailable)
    print("\nQuerying CMS provider data...")
    cms_data = agent.query_cms_provider_data(limit=100)

    print(f"Retrieved {len(cms_data)} records")
    if not cms_data.empty:
        print("\nSample data:")
        print(cms_data.head())


def example_2_trinetx_mock():
    """Example 2: Using TriNetX mock agent."""
    print("\n" + "="*60)
    print("Example 2: TriNetX Mock Data")
    print("="*60)

    config = get_config()

    # Create mock TriNetX agent
    agent = TriNetXMockAgent(config)

    # Build cohort definition
    cohort = agent.build_cohort_definition()
    print("\nCohort definition:")
    print(f"Name: {cohort['name']}")
    print(f"Criteria: {len(cohort['criteria']['inclusionCriteria'])} inclusion criteria")

    # Query cohort
    print("\nQuerying cohort data...")
    data = agent.query_cohort(cohort)

    print(f"\nRetrieved {len(data)} geographic locations")
    print("\nSample data:")
    print(data.head())


def example_3_census_integration():
    """Example 3: Census data integration and mapping."""
    print("\n" + "="*60)
    print("Example 3: Census Integration and Mapping")
    print("="*60)

    config = get_config()

    # Create mapper agent
    mapper = MapperAgent(config, census_api_key=None)  # Will use mock if no key

    # Load geographic crosswalk
    print("\nLoading ZIP to MSA crosswalk...")
    crosswalk = mapper.load_geographic_crosswalk()
    print(f"Loaded {len(crosswalk)} ZIP code mappings")

    # Query census population data
    print("\nQuerying Census Bureau for MSA population...")
    population = mapper.query_census_msa_population()
    print(f"Retrieved population data for {len(population)} MSAs")

    print("\nSample population data:")
    print(population.head())


def example_4_coldspot_analysis():
    """Example 4: Complete coldspot analysis."""
    print("\n" + "="*60)
    print("Example 4: Complete Coldspot Analysis")
    print("="*60)

    config = get_config()

    # Step 1: Get surgery data
    print("\n[1/5] Collecting surgery data...")
    trinetx_agent = TriNetXMockAgent(config)
    cohort = trinetx_agent.build_cohort_definition()
    surgery_data = trinetx_agent.query_cohort(cohort)

    # Add mock zipcodes if needed
    if 'zipcode' not in surgery_data.columns:
        surgery_data['zipcode'] = surgery_data.index.astype(str)

    # Rename procedure_count column if needed
    if 'procedure_count' in surgery_data.columns:
        surgery_data['total_procedures'] = surgery_data['procedure_count']

    print(f"Collected {len(surgery_data)} records")

    # Step 2: Setup mapper
    print("\n[2/5] Setting up geographic mapper...")
    mapper = MapperAgent(config)
    mapper.load_geographic_crosswalk()

    # Step 3: Map to MSAs
    print("\n[3/5] Mapping surgeries to MSAs...")
    msa_surgeries = mapper.map_surgeries_to_msa(surgery_data)
    print(f"Mapped to {len(msa_surgeries)} MSAs")

    # Step 4: Calculate rates
    print("\n[4/5] Calculating surgery rates...")
    population = mapper.query_census_msa_population()
    rate_data = mapper.calculate_surgery_rates(msa_surgeries, population)
    print(f"Calculated rates for {len(rate_data)} MSAs")

    # Step 5: Identify coldspots
    print("\n[5/5] Identifying coldspots...")
    coldspot_data = mapper.identify_coldspots(rate_data, threshold_multiplier=1.5)

    coldspots = coldspot_data[coldspot_data['is_coldspot']]
    print(f"\nIdentified {len(coldspots)} coldspots ({len(coldspots)/len(coldspot_data)*100:.1f}%)")

    print("\nTop 5 coldspots:")
    top_coldspots = coldspots.nlargest(5, 'severity_score')
    for idx, row in top_coldspots.iterrows():
        print(f"  - {row['msa_name']}: {row['population_per_surgery']:.0f} people/surgery")


def example_5_visualization():
    """Example 5: Creating visualizations."""
    print("\n" + "="*60)
    print("Example 5: Creating Visualizations")
    print("="*60)

    # Create sample data
    import pandas as pd
    import numpy as np

    np.random.seed(42)

    sample_data = pd.DataFrame({
        'msa_name': [f'MSA_{i}' for i in range(20)],
        'population': np.random.randint(100000, 5000000, 20),
        'total_surgeries': np.random.randint(10, 500, 20),
        'surgeries_per_100k': np.random.uniform(2, 15, 20),
        'population_per_surgery': np.random.uniform(5000, 30000, 20),
        'is_coldspot': np.random.choice([True, False], 20, p=[0.3, 0.7]),
        'severity_score': np.random.uniform(-1, 3, 20)
    })

    print("\nCreating visualizations...")
    generator = HeatmapGenerator()

    # Create static heatmap
    print("  - Creating static heatmap...")
    generator.create_static_heatmap(
        sample_data,
        output_file="example_heatmap.png"
    )

    # Create comparison chart
    print("  - Creating comparison chart...")
    generator.create_comparison_chart(
        sample_data,
        output_file="example_comparison.png"
    )

    # Create summary table
    print("  - Creating summary table...")
    generator.generate_summary_table(
        sample_data,
        output_file="example_summary.html"
    )

    print("\nVisualizations created successfully!")
    print("  - example_heatmap.png")
    print("  - example_comparison.png")
    print("  - example_summary.html")


def example_6_custom_analysis():
    """Example 6: Custom analysis with filtering."""
    print("\n" + "="*60)
    print("Example 6: Custom Analysis with Filtering")
    print("="*60)

    import pandas as pd

    # Create sample coldspot data
    sample_data = pd.DataFrame({
        'msa_name': ['New York', 'Los Angeles', 'Rural Area 1', 'Rural Area 2', 'Rural Area 3'],
        'population': [19000000, 13000000, 500000, 300000, 200000],
        'total_surgeries': [1500, 1100, 25, 10, 5],
        'population_per_surgery': [12666, 11818, 20000, 30000, 40000],
        'is_coldspot': [False, False, True, True, True],
        'severity_score': [0.1, 0.0, 1.5, 2.3, 3.0]
    })

    # Filter for high-severity coldspots
    print("\nFiltering for high-severity coldspots (score > 2.0)...")
    high_severity = sample_data[
        (sample_data['is_coldspot']) &
        (sample_data['severity_score'] > 2.0)
    ]

    print(f"\nFound {len(high_severity)} high-severity coldspots:")
    for idx, row in high_severity.iterrows():
        print(f"  - {row['msa_name']}")
        print(f"    Population: {row['population']:,}")
        print(f"    Surgeries: {row['total_surgeries']}")
        print(f"    Ratio: {row['population_per_surgery']:,.0f} people/surgery")
        print(f"    Severity: {row['severity_score']:.2f}\n")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("TUMOR SURGERY DATA AGENT - USAGE EXAMPLES")
    print("="*70)

    examples = [
        ("Simple Data Query", example_1_simple_query),
        ("TriNetX Mock Data", example_2_trinetx_mock),
        ("Census Integration", example_3_census_integration),
        ("Coldspot Analysis", example_4_coldspot_analysis),
        ("Visualizations", example_5_visualization),
        ("Custom Analysis", example_6_custom_analysis),
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning all examples...\n")

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("Examples complete!")
    print("="*70)


if __name__ == "__main__":
    main()
