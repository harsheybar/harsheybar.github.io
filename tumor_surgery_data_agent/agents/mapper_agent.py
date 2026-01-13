"""
Mapper Agent

Queries census data for MSAs, maps surgical volume to population,
and identifies healthcare coldspots.
"""

import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MapperAgent:
    """
    Agent for mapping surgical volumes to census data and identifying coldspots.

    Coldspots are defined as areas where the ratio of population to surgeries
    is significantly higher than the national average.
    """

    def __init__(self, config, census_api_key: Optional[str] = None):
        """
        Initialize mapper agent.

        Args:
            config: Configuration object
            census_api_key: Census Bureau API key (optional but recommended)
        """
        self.config = config
        self.census_api_key = census_api_key
        self.census_config = config.get_data_source_config('census')

        self.zip_to_msa_map = {}
        self.msa_data = pd.DataFrame()

    def load_geographic_crosswalk(self, filepath: Optional[str] = None) -> pd.DataFrame:
        """
        Load ZIP to MSA crosswalk file.

        Args:
            filepath: Path to crosswalk file. If None, downloads from HUD.

        Returns:
            DataFrame with ZIP to MSA mappings
        """
        logger.info("Loading ZIP to MSA crosswalk...")

        if filepath and Path(filepath).exists():
            df = pd.read_csv(filepath)
            logger.info(f"Loaded crosswalk from {filepath}")
        else:
            # Download from HUD USPS Crosswalk
            url = "https://www.huduser.gov/portal/datasets/usps/ZIP_CBSA_092023.xlsx"

            try:
                df = pd.read_excel(url)
                logger.info("Downloaded crosswalk from HUD")

                # Save for future use
                df.to_csv("zip_to_msa_crosswalk.csv", index=False)

            except Exception as e:
                logger.error(f"Error downloading crosswalk: {e}")
                logger.info("Using backup: generating synthetic crosswalk")
                return self._generate_synthetic_crosswalk()

        # Standardize column names
        df = df.rename(columns={
            'ZIP': 'zipcode',
            'CBSA': 'msa_code',
            'CBSA_NAME': 'msa_name'
        })

        # Create lookup dictionary
        self.zip_to_msa_map = dict(zip(df['zipcode'], df['msa_code']))

        logger.info(f"Loaded {len(df)} ZIP to MSA mappings")
        return df

    def query_census_msa_population(self) -> pd.DataFrame:
        """
        Query Census Bureau for MSA population data.

        Returns:
            DataFrame with MSA population estimates
        """
        logger.info("Querying Census Bureau for MSA population data...")

        base_url = "https://api.census.gov/data/2023/pep/population"

        params = {
            'get': 'POP_2023,NAME',
            'for': 'metropolitan statistical area/micropolitan statistical area:*',
        }

        if self.census_api_key:
            params['key'] = self.census_api_key

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Convert to DataFrame
            df = pd.DataFrame(data[1:], columns=data[0])

            df = df.rename(columns={
                'POP_2023': 'population',
                'NAME': 'msa_name',
                'metropolitan statistical area/micropolitan statistical area': 'msa_code'
            })

            df['population'] = pd.to_numeric(df['population'], errors='coerce')

            logger.info(f"Retrieved population data for {len(df)} MSAs")

            self.msa_data = df
            return df

        except requests.RequestException as e:
            logger.error(f"Error querying Census API: {e}")
            logger.info("Using backup: generating synthetic MSA data")
            return self._generate_synthetic_msa_data()

    def query_census_acs_data(self, variables: List[str] = None) -> pd.DataFrame:
        """
        Query American Community Survey 5-Year Estimates for additional demographics.

        Args:
            variables: List of ACS variables to query (e.g., median income, education)

        Returns:
            DataFrame with ACS data by MSA
        """
        if variables is None:
            variables = [
                'B01003_001E',  # Total population
                'B19013_001E',  # Median household income
                'B25077_001E',  # Median home value
            ]

        logger.info("Querying ACS data for MSAs...")

        base_url = "https://api.census.gov/data/2023/acs/acs5"

        var_string = ','.join(variables + ['NAME'])

        params = {
            'get': var_string,
            'for': 'metropolitan statistical area/micropolitan statistical area:*',
        }

        if self.census_api_key:
            params['key'] = self.census_api_key

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = pd.DataFrame(data[1:], columns=data[0])

            logger.info(f"Retrieved ACS data for {len(df)} MSAs")
            return df

        except requests.RequestException as e:
            logger.error(f"Error querying ACS data: {e}")
            return pd.DataFrame()

    def map_surgeries_to_msa(self, surgery_data: pd.DataFrame) -> pd.DataFrame:
        """
        Map surgical volume data to MSAs.

        Args:
            surgery_data: DataFrame with surgery counts by zipcode

        Returns:
            DataFrame with surgeries aggregated by MSA
        """
        logger.info("Mapping surgeries to MSAs...")

        if self.zip_to_msa_map is None or len(self.zip_to_msa_map) == 0:
            self.load_geographic_crosswalk()

        # Ensure zipcode is string for matching
        surgery_data['zipcode'] = surgery_data['zipcode'].astype(str)

        # Map zipcodes to MSAs
        surgery_data['msa_code'] = surgery_data['zipcode'].map(self.zip_to_msa_map)

        # Filter out unmapped zipcodes
        mapped = surgery_data.dropna(subset=['msa_code'])

        logger.info(
            f"Mapped {len(mapped)} of {len(surgery_data)} records to MSAs "
            f"({len(mapped)/len(surgery_data)*100:.1f}%)"
        )

        # Aggregate by MSA
        msa_surgeries = mapped.groupby('msa_code').agg({
            'total_procedures': 'sum',
            'zipcode': 'count'  # Number of zipcodes per MSA
        }).reset_index()

        msa_surgeries.columns = ['msa_code', 'total_surgeries', 'zipcode_count']

        return msa_surgeries

    def calculate_surgery_rates(
        self,
        msa_surgeries: pd.DataFrame,
        msa_population: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Calculate surgery rates per population.

        Args:
            msa_surgeries: DataFrame with surgery counts by MSA
            msa_population: DataFrame with MSA population. If None, queries Census.

        Returns:
            DataFrame with surgery rates per 100k population
        """
        logger.info("Calculating surgery rates...")

        if msa_population is None:
            msa_population = self.query_census_msa_population()

        # Merge surgery and population data
        merged = pd.merge(
            msa_surgeries,
            msa_population,
            on='msa_code',
            how='inner'
        )

        # Calculate rates per 100,000 population
        merged['surgeries_per_100k'] = (
            merged['total_surgeries'] / merged['population'] * 100000
        )

        # Calculate population to surgery ratio
        merged['population_per_surgery'] = (
            merged['population'] / merged['total_surgeries']
        )

        logger.info(f"Calculated rates for {len(merged)} MSAs")

        return merged

    def identify_coldspots(
        self,
        rate_data: pd.DataFrame,
        threshold_multiplier: float = 1.5
    ) -> pd.DataFrame:
        """
        Identify healthcare coldspots.

        Coldspots are defined as MSAs where the population-per-surgery ratio
        is significantly higher than the national median.

        Args:
            rate_data: DataFrame with surgery rates by MSA
            threshold_multiplier: Multiplier for median to define coldspot threshold

        Returns:
            DataFrame with coldspot analysis
        """
        logger.info("Identifying coldspots...")

        # Calculate national statistics
        median_pop_per_surgery = rate_data['population_per_surgery'].median()
        mean_pop_per_surgery = rate_data['population_per_surgery'].mean()
        std_pop_per_surgery = rate_data['population_per_surgery'].std()

        # Define coldspot threshold
        coldspot_threshold = median_pop_per_surgery * threshold_multiplier

        # Identify coldspots
        rate_data['is_coldspot'] = (
            rate_data['population_per_surgery'] > coldspot_threshold
        )

        # Calculate severity score (z-score based)
        rate_data['severity_score'] = (
            (rate_data['population_per_surgery'] - mean_pop_per_surgery) /
            std_pop_per_surgery
        )

        # Rank coldspots by severity
        coldspots = rate_data[rate_data['is_coldspot']].copy()
        coldspots = coldspots.sort_values('severity_score', ascending=False)

        logger.info(
            f"Identified {len(coldspots)} coldspots "
            f"({len(coldspots)/len(rate_data)*100:.1f}% of MSAs)"
        )

        logger.info(f"National median: {median_pop_per_surgery:.0f} people per surgery")
        logger.info(f"Coldspot threshold: {coldspot_threshold:.0f} people per surgery")

        # Add national statistics to dataframe
        rate_data['national_median'] = median_pop_per_surgery
        rate_data['coldspot_threshold'] = coldspot_threshold

        return rate_data

    def generate_coldspot_report(
        self,
        coldspot_data: pd.DataFrame,
        output_file: str = "coldspot_report.csv"
    ) -> Dict:
        """
        Generate comprehensive coldspot report.

        Args:
            coldspot_data: DataFrame with coldspot analysis
            output_file: Path for output CSV

        Returns:
            Dictionary with summary statistics
        """
        logger.info("Generating coldspot report...")

        # Filter to coldspots only
        coldspots = coldspot_data[coldspot_data['is_coldspot']].copy()

        # Sort by severity
        coldspots = coldspots.sort_values('severity_score', ascending=False)

        # Save to CSV
        coldspots.to_csv(output_file, index=False)
        logger.info(f"Report saved to {output_file}")

        # Generate summary
        summary = {
            'total_msas_analyzed': len(coldspot_data),
            'coldspots_identified': len(coldspots),
            'coldspot_percentage': len(coldspots) / len(coldspot_data) * 100,
            'total_population_in_coldspots': coldspots['population'].sum(),
            'median_population_per_surgery_national': coldspot_data['population_per_surgery'].median(),
            'median_population_per_surgery_coldspots': coldspots['population_per_surgery'].median(),
            'top_10_coldspots': coldspots.head(10)['msa_name'].tolist()
        }

        return summary

    def _generate_synthetic_crosswalk(self) -> pd.DataFrame:
        """Generate synthetic ZIP to MSA crosswalk for testing."""
        logger.info("Generating synthetic crosswalk data...")

        # Sample MSAs with major cities
        msas = [
            ('10001', '35620', 'New York-Newark-Jersey City, NY-NJ-PA'),
            ('90001', '31080', 'Los Angeles-Long Beach-Anaheim, CA'),
            ('60601', '16980', 'Chicago-Naperville-Elgin, IL-IN-WI'),
            ('77001', '26420', 'Houston-The Woodlands-Sugar Land, TX'),
            ('85001', '38060', 'Phoenix-Mesa-Scottsdale, AZ'),
        ]

        df = pd.DataFrame(msas, columns=['zipcode', 'msa_code', 'msa_name'])
        self.zip_to_msa_map = dict(zip(df['zipcode'], df['msa_code']))

        return df

    def _generate_synthetic_msa_data(self) -> pd.DataFrame:
        """Generate synthetic MSA population data for testing."""
        logger.info("Generating synthetic MSA population data...")

        msas = [
            {'msa_code': '35620', 'msa_name': 'New York-Newark-Jersey City, NY-NJ-PA', 'population': 19500000},
            {'msa_code': '31080', 'msa_name': 'Los Angeles-Long Beach-Anaheim, CA', 'population': 13200000},
            {'msa_code': '16980', 'msa_name': 'Chicago-Naperville-Elgin, IL-IN-WI', 'population': 9400000},
            {'msa_code': '26420', 'msa_name': 'Houston-The Woodlands-Sugar Land, TX', 'population': 7100000},
            {'msa_code': '38060', 'msa_name': 'Phoenix-Mesa-Scottsdale, AZ', 'population': 4900000},
        ]

        df = pd.DataFrame(msas)
        self.msa_data = df

        return df


if __name__ == "__main__":
    # Example usage
    from config import get_config

    config = get_config()
    mapper = MapperAgent(config)

    # Load crosswalk
    crosswalk = mapper.load_geographic_crosswalk()

    # Query population data
    population = mapper.query_census_msa_population()

    print(population.head())
