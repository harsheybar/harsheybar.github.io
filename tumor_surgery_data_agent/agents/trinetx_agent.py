"""
TriNetX Agent

Specialized agent for querying TriNetX global health research network.
TriNetX requires institutional subscription and OAuth authentication.
"""

import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TriNetXAgent:
    """
    Agent for querying TriNetX clinical research network for tumor surgery data.

    TriNetX provides access to de-identified patient data from healthcare organizations.
    Requires institutional subscription and proper authentication.
    """

    def __init__(self, config, access_token: Optional[str] = None):
        """
        Initialize TriNetX agent.

        Args:
            config: Configuration object
            access_token: OAuth 2.0 access token for TriNetX API
        """
        self.config = config
        self.access_token = access_token
        self.trinetx_config = config.get_data_source_config('trinetx')
        self.base_url = self.trinetx_config.get('base_url', 'https://api.trinetx.com')

        self.cpt_codes = config.get_cpt_codes()
        self.drg_codes = config.get_drg_codes()
        self.date_range = config.get_date_range()

        if not access_token:
            logger.warning(
                "No access token provided. TriNetX queries will not work without authentication."
            )

    def authenticate(self, client_id: str, client_secret: str, organization: str) -> str:
        """
        Authenticate with TriNetX API using OAuth 2.0.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            organization: Organization identifier

        Returns:
            Access token
        """
        auth_url = f"{self.base_url}/oauth/token"

        payload = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'research'
        }

        try:
            response = requests.post(auth_url, data=payload, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data['access_token']

            logger.info("Successfully authenticated with TriNetX")
            return self.access_token

        except requests.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def build_cohort_definition(self) -> Dict:
        """
        Build cohort definition for craniotomy tumor resection patients.

        Returns:
            Cohort definition dictionary for TriNetX query
        """
        cohort = {
            "name": "Craniotomy Tumor Resection Patients 2023-2025",
            "description": "Patients with craniotomy procedures for tumor resection",
            "criteria": {
                "inclusionCriteria": [
                    {
                        "type": "procedure",
                        "codes": [
                            {"system": "CPT", "code": code}
                            for code in self.cpt_codes
                        ],
                        "dateRange": {
                            "start": self.date_range['start'],
                            "end": self.date_range['end']
                        }
                    },
                    {
                        "type": "diagnosis",
                        "codes": [
                            {"system": "ICD10", "code": code}
                            for code in self._get_brain_tumor_icd10_codes()
                        ]
                    }
                ]
            },
            "demographicFilters": {
                "ageRange": {"min": 0, "max": 120}
            }
        }

        return cohort

    def query_cohort(
        self,
        cohort_definition: Dict,
        include_geography: bool = True
    ) -> pd.DataFrame:
        """
        Query TriNetX for cohort data.

        Args:
            cohort_definition: Cohort definition dictionary
            include_geography: Whether to include geographic data

        Returns:
            DataFrame with patient counts by geography
        """
        if not self.access_token:
            raise ValueError("Access token required. Call authenticate() first.")

        logger.info("Querying TriNetX cohort...")

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        # Create cohort
        cohort_url = f"{self.base_url}/api/cohorts"

        try:
            response = requests.post(
                cohort_url,
                json=cohort_definition,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()

            cohort_result = response.json()
            cohort_id = cohort_result.get('cohortId')

            logger.info(f"Cohort created: {cohort_id}")

            # Query cohort statistics
            if include_geography:
                return self._query_cohort_geography(cohort_id, headers)
            else:
                return self._query_cohort_statistics(cohort_id, headers)

        except requests.RequestException as e:
            logger.error(f"Error querying TriNetX: {e}")
            return pd.DataFrame()

    def _query_cohort_geography(
        self,
        cohort_id: str,
        headers: Dict
    ) -> pd.DataFrame:
        """
        Query geographic distribution of cohort.

        Args:
            cohort_id: Cohort identifier
            headers: Request headers with auth token

        Returns:
            DataFrame with patient counts by geography
        """
        geo_url = f"{self.base_url}/api/cohorts/{cohort_id}/geography"

        try:
            response = requests.get(geo_url, headers=headers, timeout=30)
            response.raise_for_status()

            geo_data = response.json()

            # Convert to DataFrame
            df = pd.DataFrame(geo_data.get('distribution', []))

            # Standardize columns
            df = df.rename(columns={
                'zipCode': 'zipcode',
                'patientCount': 'procedure_count'
            })

            df['data_source'] = 'TriNetX'
            df['date_queried'] = datetime.now().isoformat()

            logger.info(f"Retrieved geographic data for {len(df)} locations")

            return df

        except requests.RequestException as e:
            logger.error(f"Error querying cohort geography: {e}")
            return pd.DataFrame()

    def _query_cohort_statistics(
        self,
        cohort_id: str,
        headers: Dict
    ) -> pd.DataFrame:
        """
        Query general statistics for cohort.

        Args:
            cohort_id: Cohort identifier
            headers: Request headers with auth token

        Returns:
            DataFrame with cohort statistics
        """
        stats_url = f"{self.base_url}/api/cohorts/{cohort_id}/statistics"

        try:
            response = requests.get(stats_url, headers=headers, timeout=30)
            response.raise_for_status()

            stats_data = response.json()

            df = pd.DataFrame([stats_data])
            df['data_source'] = 'TriNetX'

            logger.info(f"Retrieved cohort statistics: {stats_data.get('totalPatients', 0)} patients")

            return df

        except requests.RequestException as e:
            logger.error(f"Error querying cohort statistics: {e}")
            return pd.DataFrame()

    def _get_brain_tumor_icd10_codes(self) -> List[str]:
        """Get brain tumor ICD-10 codes from config."""
        codes = []
        icd10_config = self.config.medical_codes.get('icd10_codes', {})

        for category in ['malignant_brain_tumors', 'benign_brain_tumors', 'meningioma']:
            codes.extend(icd10_config.get(category, []))

        return codes

    def export_cohort_data(
        self,
        cohort_id: str,
        output_format: str = 'csv'
    ) -> str:
        """
        Export cohort data for offline analysis.

        Args:
            cohort_id: Cohort identifier
            output_format: Export format (csv, json)

        Returns:
            Path to exported file
        """
        if not self.access_token:
            raise ValueError("Access token required")

        export_url = f"{self.base_url}/api/cohorts/{cohort_id}/export"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
        }

        params = {'format': output_format}

        try:
            response = requests.get(
                export_url,
                headers=headers,
                params=params,
                timeout=120
            )
            response.raise_for_status()

            # Save to file
            filename = f"trinetx_cohort_{cohort_id}.{output_format}"
            with open(filename, 'wb') as f:
                f.write(response.content)

            logger.info(f"Cohort data exported to {filename}")
            return filename

        except requests.RequestException as e:
            logger.error(f"Error exporting cohort data: {e}")
            raise


class TriNetXMockAgent(TriNetXAgent):
    """
    Mock TriNetX agent for testing without actual TriNetX access.
    Generates synthetic data that mimics TriNetX structure.
    """

    def __init__(self, config):
        """Initialize mock agent without authentication."""
        super().__init__(config, access_token="mock_token")
        logger.info("Using MOCK TriNetX agent - generating synthetic data")

    def query_cohort(
        self,
        cohort_definition: Dict,
        include_geography: bool = True
    ) -> pd.DataFrame:
        """
        Generate mock cohort data.

        Args:
            cohort_definition: Cohort definition (ignored in mock)
            include_geography: Whether to include geography

        Returns:
            DataFrame with synthetic data
        """
        logger.info("Generating mock TriNetX data...")

        # Generate synthetic data for major US cities
        mock_data = [
            {'zipcode': '10001', 'procedure_count': 45, 'city': 'New York'},
            {'zipcode': '90001', 'procedure_count': 38, 'city': 'Los Angeles'},
            {'zipcode': '60601', 'procedure_count': 42, 'city': 'Chicago'},
            {'zipcode': '77001', 'procedure_count': 35, 'city': 'Houston'},
            {'zipcode': '85001', 'procedure_count': 28, 'city': 'Phoenix'},
            {'zipcode': '19019', 'procedure_count': 32, 'city': 'Philadelphia'},
            {'zipcode': '78201', 'procedure_count': 25, 'city': 'San Antonio'},
            {'zipcode': '92101', 'procedure_count': 30, 'city': 'San Diego'},
            {'zipcode': '75201', 'procedure_count': 33, 'city': 'Dallas'},
            {'zipcode': '95101', 'procedure_count': 27, 'city': 'San Jose'},
        ]

        df = pd.DataFrame(mock_data)
        df['data_source'] = 'TriNetX_Mock'
        df['date_queried'] = datetime.now().isoformat()

        logger.info(f"Generated mock data for {len(df)} locations")

        return df


if __name__ == "__main__":
    # Example usage with mock agent
    from config import get_config

    config = get_config()

    # Use mock agent for testing
    agent = TriNetXMockAgent(config)

    cohort_def = agent.build_cohort_definition()
    data = agent.query_cohort(cohort_def)

    print(data)
