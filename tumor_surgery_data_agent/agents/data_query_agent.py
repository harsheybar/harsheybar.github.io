"""
Data Query Agent

Queries NCI, CMS, and other public sources for tumor surgery data.
Focuses on craniotomy procedures for tumor resections with geographic granularity.
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataQueryAgent:
    """
    Agent for querying public health data sources for craniotomy tumor surgery data.
    """

    def __init__(self, config):
        """
        Initialize the data query agent.

        Args:
            config: Configuration object with data source details
        """
        self.config = config
        self.cpt_codes = config.get_cpt_codes()
        self.drg_codes = config.get_drg_codes()
        self.date_range = config.get_date_range()
        self.cache = {}

    def query_cms_provider_data(
        self,
        api_key: Optional[str] = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """
        Query CMS Provider Charge Data for craniotomy procedures.

        Args:
            api_key: Optional API key for higher rate limits
            limit: Maximum number of records to retrieve

        Returns:
            DataFrame with provider charge data by geography
        """
        logger.info("Querying CMS Provider Charge Data...")

        cms_config = self.config.get_data_source_config('cms')
        base_url = cms_config['base_url']

        # CMS Socrata API endpoint for Medicare Provider Utilization
        # Note: This is an example - actual dataset IDs need to be verified
        dataset_id = "nrth-mfg3"  # Example: Medicare Physician & Other Practitioners
        url = f"https://data.cms.gov/resource/{dataset_id}.json"

        params = {
            '$limit': limit,
            '$where': self._build_cpt_filter(),
            '$order': 'nppes_provider_zip_code',
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = pd.DataFrame(data)

            logger.info(f"Retrieved {len(df)} records from CMS")
            return self._process_cms_data(df)

        except requests.RequestException as e:
            logger.error(f"Error querying CMS data: {e}")
            return pd.DataFrame()

    def query_cms_inpatient_data(
        self,
        api_key: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query CMS Inpatient data for DRG-based craniotomy procedures.

        Args:
            api_key: Optional API key for higher rate limits

        Returns:
            DataFrame with inpatient data by geography
        """
        logger.info("Querying CMS Inpatient Data...")

        # CMS Inpatient Charge Data
        # Dataset: Medicare Inpatient Hospitals by Provider and Service
        dataset_id = "tcsp-6e99"
        url = f"https://data.cms.gov/resource/{dataset_id}.json"

        params = {
            '$limit': 10000,
            '$where': self._build_drg_filter(),
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = pd.DataFrame(data)

            logger.info(f"Retrieved {len(df)} inpatient records from CMS")
            return self._process_inpatient_data(df)

        except requests.RequestException as e:
            logger.error(f"Error querying CMS inpatient data: {e}")
            return pd.DataFrame()

    def query_hcup_data(self, state: Optional[str] = None) -> pd.DataFrame:
        """
        Query HCUP (Healthcare Cost and Utilization Project) data.

        Note: HCUP requires data use agreement and purchase.
        This is a placeholder for data that would be pre-downloaded.

        Args:
            state: Optional state filter

        Returns:
            DataFrame with HCUP data (or empty if not available)
        """
        logger.info("HCUP data requires special access and pre-download")
        logger.info("Please download HCUP data separately and load via load_hcup_file()")

        return pd.DataFrame()

    def load_hcup_file(self, filepath: str) -> pd.DataFrame:
        """
        Load pre-downloaded HCUP data file.

        Args:
            filepath: Path to HCUP data file (CSV or SAS)

        Returns:
            DataFrame with processed HCUP data
        """
        logger.info(f"Loading HCUP data from {filepath}")

        # HCUP data is typically in SAS format, but CSV exports are common
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            # Would need pyreadstat or similar for SAS files
            logger.error("SAS file support requires pyreadstat package")
            return pd.DataFrame()

        # Filter for relevant CPT/DRG codes
        return self._filter_by_codes(df)

    def query_seer_data(self) -> pd.DataFrame:
        """
        Query SEER (Surveillance, Epidemiology, and End Results) data.

        Note: SEER data requires data use agreement and is typically
        accessed via SEER*Stat software or pre-downloaded files.

        Returns:
            DataFrame with SEER data (or empty if not available)
        """
        logger.info("SEER data requires data use agreement and SEER*Stat software")
        logger.info("Alternative: Use SEER API if available or load pre-downloaded data")

        # SEER provides a limited REST API for some datasets
        # For full data, users need to download via SEER*Stat

        return pd.DataFrame()

    def query_cdc_wonder(self) -> pd.DataFrame:
        """
        Query CDC WONDER for cancer statistics by geography.

        Returns:
            DataFrame with CDC WONDER data
        """
        logger.info("Querying CDC WONDER...")

        # CDC WONDER API is available but complex
        # Example: Query United States Cancer Statistics (USCS)
        base_url = "https://wonder.cdc.gov/controller/datarequest"

        # This would require complex XML-based requests
        # Placeholder for now
        logger.info("CDC WONDER requires XML-based API requests")
        logger.info("Consider using CDC WONDER web interface for data download")

        return pd.DataFrame()

    def aggregate_all_sources(
        self,
        cms_key: Optional[str] = None,
        trinetx_data: Optional[pd.DataFrame] = None,
        hcup_data: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Aggregate data from all available sources.

        Args:
            cms_key: Optional CMS API key
            trinetx_data: Pre-queried TriNetX data (if available)
            hcup_data: Pre-loaded HCUP data (if available)

        Returns:
            Aggregated DataFrame with all surgery data by geography
        """
        logger.info("Aggregating data from all sources...")

        dfs = []

        # Query CMS data
        cms_provider = self.query_cms_provider_data(api_key=cms_key)
        if not cms_provider.empty:
            dfs.append(cms_provider)

        cms_inpatient = self.query_cms_inpatient_data(api_key=cms_key)
        if not cms_inpatient.empty:
            dfs.append(cms_inpatient)

        # Add TriNetX data if provided
        if trinetx_data is not None and not trinetx_data.empty:
            dfs.append(self._standardize_trinetx_data(trinetx_data))

        # Add HCUP data if provided
        if hcup_data is not None and not hcup_data.empty:
            dfs.append(self._standardize_hcup_data(hcup_data))

        if not dfs:
            logger.warning("No data retrieved from any source")
            return pd.DataFrame()

        # Combine all dataframes
        combined = pd.concat(dfs, ignore_index=True)

        # Standardize and aggregate by geography
        aggregated = self._aggregate_by_geography(combined)

        logger.info(f"Aggregated {len(aggregated)} geographic areas")
        return aggregated

    def _build_cpt_filter(self) -> str:
        """Build SQL WHERE clause for CPT codes."""
        cpt_list = "','".join(self.cpt_codes)
        return f"hcpcs_code IN ('{cpt_list}')"

    def _build_drg_filter(self) -> str:
        """Build SQL WHERE clause for DRG codes."""
        drg_list = "','".join(self.drg_codes)
        return f"drg_definition LIKE '%{drg_list[0]}%'"  # Simplified

    def _filter_by_codes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter dataframe by relevant CPT/DRG codes."""
        if 'cpt_code' in df.columns:
            return df[df['cpt_code'].isin(self.cpt_codes)]
        elif 'drg_code' in df.columns:
            return df[df['drg_code'].isin(self.drg_codes)]
        return df

    def _process_cms_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and standardize CMS provider data."""
        if df.empty:
            return df

        # Standardize column names
        rename_map = {
            'nppes_provider_zip_code': 'zipcode',
            'line_srvc_cnt': 'procedure_count',
            'hcpcs_code': 'cpt_code',
        }

        df = df.rename(columns=rename_map)

        # Keep only relevant columns
        keep_cols = ['zipcode', 'cpt_code', 'procedure_count']
        df = df[[col for col in keep_cols if col in df.columns]]

        # Convert procedure count to numeric
        if 'procedure_count' in df.columns:
            df['procedure_count'] = pd.to_numeric(
                df['procedure_count'],
                errors='coerce'
            )

        df['data_source'] = 'CMS_Provider'

        return df

    def _process_inpatient_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and standardize CMS inpatient data."""
        if df.empty:
            return df

        rename_map = {
            'provider_zip_code': 'zipcode',
            'total_discharges': 'procedure_count',
            'drg_definition': 'drg_code',
        }

        df = df.rename(columns=rename_map)
        df['data_source'] = 'CMS_Inpatient'

        return df

    def _standardize_trinetx_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize TriNetX data format."""
        # Assuming TriNetX data comes in with patient_count and geography
        df['data_source'] = 'TriNetX'
        return df

    def _standardize_hcup_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize HCUP data format."""
        df['data_source'] = 'HCUP'
        return df

    def _aggregate_by_geography(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate surgery counts by geography."""
        if 'zipcode' not in df.columns:
            logger.warning("No geography column found in data")
            return df

        # Aggregate by zipcode
        agg_df = df.groupby('zipcode').agg({
            'procedure_count': 'sum',
            'data_source': lambda x: ','.join(set(x))
        }).reset_index()

        agg_df.columns = ['zipcode', 'total_procedures', 'data_sources']

        return agg_df

    def save_data(self, df: pd.DataFrame, filepath: str):
        """
        Save aggregated data to file.

        Args:
            df: DataFrame to save
            filepath: Output file path (CSV)
        """
        df.to_csv(filepath, index=False)
        logger.info(f"Data saved to {filepath}")


if __name__ == "__main__":
    # Example usage
    from config import get_config

    config = get_config()
    agent = DataQueryAgent(config)

    # Query CMS data
    data = agent.aggregate_all_sources()

    if not data.empty:
        agent.save_data(data, "tumor_surgery_data.csv")
