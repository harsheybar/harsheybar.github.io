"""
Main Orchestrator for Tumor Surgery Data Agent System

Coordinates data collection, mapping, and coldspot analysis.
"""

import argparse
import logging
from pathlib import Path
import pandas as pd

from config import get_config
from agents.data_query_agent import DataQueryAgent
from agents.trinetx_agent import TriNetXAgent, TriNetXMockAgent
from agents.mapper_agent import MapperAgent
from visualization.heatmap_generator import HeatmapGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TumorSurgeryAnalysisPipeline:
    """
    Main pipeline for tumor surgery data analysis and coldspot identification.
    """

    def __init__(
        self,
        census_api_key: str = None,
        cms_api_key: str = None,
        trinetx_token: str = None,
        use_mock_trinetx: bool = True
    ):
        """
        Initialize the analysis pipeline.

        Args:
            census_api_key: Census Bureau API key
            cms_api_key: CMS API key (optional)
            trinetx_token: TriNetX access token
            use_mock_trinetx: Use mock TriNetX data (default True)
        """
        self.config = get_config()
        self.census_api_key = census_api_key
        self.cms_api_key = cms_api_key

        # Initialize agents
        self.data_agent = DataQueryAgent(self.config)
        self.mapper_agent = MapperAgent(self.config, census_api_key)
        self.viz_generator = HeatmapGenerator()

        # Initialize TriNetX agent
        if use_mock_trinetx:
            self.trinetx_agent = TriNetXMockAgent(self.config)
        else:
            self.trinetx_agent = TriNetXAgent(self.config, trinetx_token)

        logger.info("Pipeline initialized successfully")

    def run_full_analysis(
        self,
        output_dir: str = "output",
        include_trinetx: bool = True,
        include_cms: bool = True
    ) -> dict:
        """
        Run the complete analysis pipeline.

        Args:
            output_dir: Directory for output files
            include_trinetx: Whether to query TriNetX data
            include_cms: Whether to query CMS data

        Returns:
            Dictionary with analysis results and file paths
        """
        logger.info("=" * 60)
        logger.info("Starting Tumor Surgery Coldspot Analysis Pipeline")
        logger.info("=" * 60)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        results = {}

        # Step 1: Collect surgery data
        logger.info("\nStep 1: Collecting surgery data from public sources...")
        surgery_data = self._collect_surgery_data(include_trinetx, include_cms)

        if surgery_data.empty:
            logger.error("No surgery data collected. Aborting analysis.")
            return results

        # Save raw surgery data
        surgery_file = output_path / "surgery_data_raw.csv"
        surgery_data.to_csv(surgery_file, index=False)
        results['surgery_data_file'] = str(surgery_file)
        logger.info(f"Raw surgery data saved: {surgery_file}")

        # Step 2: Load geographic crosswalk
        logger.info("\nStep 2: Loading geographic crosswalk (ZIP to MSA)...")
        self.mapper_agent.load_geographic_crosswalk()

        # Step 3: Query census data
        logger.info("\nStep 3: Querying Census Bureau for MSA population data...")
        population_data = self.mapper_agent.query_census_msa_population()

        population_file = output_path / "msa_population.csv"
        population_data.to_csv(population_file, index=False)
        results['population_data_file'] = str(population_file)

        # Step 4: Map surgeries to MSAs
        logger.info("\nStep 4: Mapping surgeries to MSAs...")
        msa_surgeries = self.mapper_agent.map_surgeries_to_msa(surgery_data)

        # Step 5: Calculate surgery rates
        logger.info("\nStep 5: Calculating surgery rates per population...")
        rate_data = self.mapper_agent.calculate_surgery_rates(
            msa_surgeries,
            population_data
        )

        # Step 6: Identify coldspots
        logger.info("\nStep 6: Identifying healthcare coldspots...")
        coldspot_data = self.mapper_agent.identify_coldspots(rate_data)

        # Save coldspot analysis
        analysis_file = output_path / "coldspot_analysis.csv"
        coldspot_data.to_csv(analysis_file, index=False)
        results['coldspot_analysis_file'] = str(analysis_file)

        # Generate summary report
        summary = self.mapper_agent.generate_coldspot_report(
            coldspot_data,
            output_file=str(output_path / "coldspot_report.csv")
        )
        results['summary'] = summary

        # Step 7: Generate visualizations
        logger.info("\nStep 7: Generating visualizations...")
        self._generate_visualizations(coldspot_data, output_path)

        results['visualization_dir'] = str(output_path)

        # Print summary
        self._print_summary(summary)

        logger.info("\n" + "=" * 60)
        logger.info("Analysis complete!")
        logger.info(f"All results saved to: {output_dir}")
        logger.info("=" * 60)

        return results

    def _collect_surgery_data(
        self,
        include_trinetx: bool,
        include_cms: bool
    ) -> pd.DataFrame:
        """Collect surgery data from all sources."""

        trinetx_data = None
        if include_trinetx:
            logger.info("Querying TriNetX...")
            cohort_def = self.trinetx_agent.build_cohort_definition()
            trinetx_data = self.trinetx_agent.query_cohort(cohort_def)

            if not trinetx_data.empty:
                logger.info(f"Retrieved {len(trinetx_data)} records from TriNetX")

        # Aggregate all sources
        surgery_data = self.data_agent.aggregate_all_sources(
            cms_key=self.cms_api_key,
            trinetx_data=trinetx_data if include_trinetx else None
        )

        logger.info(f"Total records collected: {len(surgery_data)}")

        return surgery_data

    def _generate_visualizations(self, data: pd.DataFrame, output_dir: Path):
        """Generate all visualizations."""

        try:
            # Static heatmap
            self.viz_generator.create_static_heatmap(
                data,
                output_file=str(output_dir / "coldspot_heatmap.png")
            )

            # Comparison chart
            self.viz_generator.create_comparison_chart(
                data,
                output_file=str(output_dir / "msa_comparison.png")
            )

            # Summary table
            self.viz_generator.generate_summary_table(
                data,
                output_file=str(output_dir / "summary_table.html")
            )

            # Interactive dashboard (if Plotly available)
            try:
                self.viz_generator.create_dashboard(
                    data,
                    output_file=str(output_dir / "dashboard.html")
                )
            except Exception as e:
                logger.warning(f"Could not create dashboard: {e}")

        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")

    def _print_summary(self, summary: dict):
        """Print analysis summary."""

        print("\n" + "=" * 60)
        print("COLDSPOT ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total MSAs Analyzed: {summary['total_msas_analyzed']}")
        print(f"Coldspots Identified: {summary['coldspots_identified']} "
              f"({summary['coldspot_percentage']:.1f}%)")
        print(f"Population in Coldspots: {summary['total_population_in_coldspots']:,.0f}")
        print(f"\nNational Median (Pop/Surgery): "
              f"{summary['median_population_per_surgery_national']:.0f}")
        print(f"Coldspot Median (Pop/Surgery): "
              f"{summary['median_population_per_surgery_coldspots']:.0f}")
        print("\nTop 10 Coldspots:")
        for i, msa in enumerate(summary['top_10_coldspots'], 1):
            print(f"  {i}. {msa}")
        print("=" * 60)


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description='Tumor Surgery Data Agent - Coldspot Analysis Pipeline'
    )

    parser.add_argument(
        '--census-key',
        type=str,
        help='Census Bureau API key'
    )

    parser.add_argument(
        '--cms-key',
        type=str,
        help='CMS API key (optional)'
    )

    parser.add_argument(
        '--trinetx-token',
        type=str,
        help='TriNetX access token'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Output directory for results (default: output)'
    )

    parser.add_argument(
        '--no-trinetx',
        action='store_true',
        help='Skip TriNetX data collection'
    )

    parser.add_argument(
        '--no-cms',
        action='store_true',
        help='Skip CMS data collection'
    )

    parser.add_argument(
        '--use-real-trinetx',
        action='store_true',
        help='Use real TriNetX API instead of mock data'
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = TumorSurgeryAnalysisPipeline(
        census_api_key=args.census_key,
        cms_api_key=args.cms_key,
        trinetx_token=args.trinetx_token,
        use_mock_trinetx=not args.use_real_trinetx
    )

    # Run analysis
    results = pipeline.run_full_analysis(
        output_dir=args.output_dir,
        include_trinetx=not args.no_trinetx,
        include_cms=not args.no_cms
    )

    return results


if __name__ == "__main__":
    main()
