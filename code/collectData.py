"""
County Data Collection Module

This module fetches county-level data from various public APIs including
Census, BLS, Zillow, NOAA, and FRED.
"""

import argparse
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv


# Data source configurations
def get_data_sources():
    """Get data source configurations with API keys from environment."""
    load_dotenv()
    
    return {
        "census": {
            "url": "https://api.census.gov/data/{year}/acs/acs5",
            "params": {
                "get": "B01003_001E,B19013_001E,B25077_001E,B15003_022E,B15003_023E,B15003_024E,B15003_025E",
                "for": "county:{county}",
                "in": "state:{state}",
                "key": os.getenv('CENSUS_API_KEY', '')
            },
            "columns": {
                "B01003_001E": "population",
                "B19013_001E": "median_household_income",
                "B25077_001E": "median_home_value",
                "B15003_022E": "bachelors_degree",
                "B15003_023E": "masters_degree",
                "B15003_024E": "professional_degree",
                "B15003_025E": "doctorate_degree"
            }
        },
        "bls": {
            "url": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            "series_template": "LAUCN{fips}0000000{data_type}",
            "params": {
                "registrationkey": os.getenv('BLS_API_KEY', '')
            }
        },
        "zillow": {
            "direct_download": "https://files.zillowstatic.com/research/public_csvs/zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
        },
        "noaa": {
            "url": "https://www.ncdc.noaa.gov/cdo-web/api/v2/data",
            "params": {
                "datasetid": "GHCND",
                "units": "metric"
            },
            "headers": {
                "token": os.getenv('NOAA_TOKEN', '')
            },
            "datatypes": ["TAVG", "TMIN", "TMAX", "PRCP"]
        },
        "fred": {
            "url": "https://api.stlouisfed.org/fred/series/observations",
            "params": {
                "api_key": os.getenv('FRED_API_KEY', ''),
                "file_type": "json"
            },
            "series_map": {
                "MEDDAYONMAR": "median_days_on_market",
                "MEDLISPRI": "median_listing_price",
                "ACTLISCOU": "active_listings_count",
                "RRVRUSFOR": "rental_vacancy_rate"
            }
        }
    }


class DataCollectionError(Exception):
    """Custom exception for data collection errors."""
    pass


def create_session_with_retries(
    total_retries: int = 3,
    backoff_factor: float = 1.0
) -> requests.Session:
    """
    Create a requests session with retry logic.
    
    Args:
        total_retries: Number of retries for failed requests
        backoff_factor: Backoff factor for exponential backoff
    
    Returns:
        Configured requests Session
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def validate_fips(fips: str) -> bool:
    """
    Validate FIPS code format.
    
    Args:
        fips: FIPS code to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(fips, str):
        return False
    if len(fips) != 5:
        return False
    if not fips.isdigit():
        return False
    return True


def validate_date_range(start_date: datetime, end_date: datetime):
    """
    Validate date range.
    
    Args:
        start_date: Start date
        end_date: End date
    
    Raises:
        ValueError: If date range is invalid
    """
    if start_date > end_date:
        raise ValueError("Start date must be before end date")
    
    if end_date > datetime.now():
        raise ValueError("End date cannot be in the future")
    
    # Limit to reasonable range (10 years)
    if (end_date - start_date).days > 3650:
        raise ValueError("Date range cannot exceed 10 years")


def split_fips(fips: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Split FIPS code into state and county components.
    
    Args:
        fips: 5-digit FIPS code
    
    Returns:
        Tuple of (state_code, county_code)
    """
    if not validate_fips(fips):
        return None, None
    return fips[:2], fips[2:]


class DataFetcher(ABC):
    """Base class for data fetchers."""
    
    def __init__(self, config: Dict):
        """
        Initialize data fetcher.
        
        Args:
            config: Configuration dictionary for this data source
        """
        self.config = config
        self.session = create_session_with_retries()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def fetch(
        self,
        counties: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data for specified counties and date range.
        
        Args:
            counties: List of 5-digit FIPS codes
            start_date: Start date for data collection
            end_date: End date for data collection
        
        Returns:
            DataFrame with collected data, or None if no data
        """
        pass
    
    def validate_response(self, response: requests.Response) -> bool:
        """
        Validate API response.
        
        Args:
            response: Response object from requests
        
        Returns:
            True if response is valid
        """
        if not response.ok:
            self.logger.error(
                f"API returned status {response.status_code}: {response.text}"
            )
            return False
        return True


class CensusFetcher(DataFetcher):
    """Fetch Census data."""
    
    def fetch(
        self,
        counties: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Fetch Census data for the given year."""
        year = start_date.year
        self.logger.info(f"Fetching Census data for {len(counties)} counties for year {year}")
        
        results = []
        
        for fips in counties:
            if not validate_fips(fips):
                self.logger.warning(f"Invalid FIPS code: {fips}")
                continue
            
            state_code, county_code = split_fips(fips)
            if state_code is None:
                continue
            
            params = self.config["params"].copy()
            params["for"] = params["for"].format(county=county_code)
            params["in"] = params["in"].format(state=state_code)
            
            url = self.config["url"].format(year=year)
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if not self.validate_response(response):
                    continue
                
                data = response.json()
                
                if len(data) < 2:
                    self.logger.warning(f"Insufficient data for county {fips}")
                    continue
                
                headers = data[0]
                values = data[1]
                
                row = {headers[i]: values[i] for i in range(len(headers))}
                row["fips"] = fips
                row["year"] = year
                row["date"] = f"{year}-12-31"
                
                # Rename columns
                for census_col, readable_name in self.config["columns"].items():
                    if census_col in row:
                        row[readable_name] = row.pop(census_col)
                
                results.append(row)
                self.logger.debug(f"Successfully fetched Census data for county {fips}")
                
            except requests.exceptions.Timeout:
                self.logger.error(f"Timeout fetching Census data for county {fips}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching Census data for county {fips}: {e}")
            except (KeyError, IndexError, ValueError) as e:
                self.logger.error(f"Error parsing Census data for county {fips}: {e}")
            
            time.sleep(0.5)  # Rate limiting
        
        if results:
            return pd.DataFrame(results)
        return None


class BLSFetcher(DataFetcher):
    """Fetch BLS employment data."""
    
    def fetch(
        self,
        counties: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Fetch BLS employment data."""
        self.logger.info(
            f"Fetching BLS data for {len(counties)} counties "
            f"from {start_date.date()} to {end_date.date()}"
        )
        
        start_year = start_date.year
        end_year = end_date.year
        
        # Create series IDs for each county and data type
        series_ids = []
        for fips in counties:
            if not validate_fips(fips):
                continue
            # 03=unemployment rate, 04=unemployment count, 05=employment count
            for data_type in ["03", "04", "05"]:
                series_id = self.config["series_template"].format(
                    fips=fips,
                    data_type=data_type
                )
                series_ids.append(series_id)
        
        # Split into chunks of 50 (API limit)
        series_chunks = [series_ids[i:i+50] for i in range(0, len(series_ids), 50)]
        
        all_results = []
        
        for chunk in series_chunks:
            params = self.config["params"].copy()
            params["seriesid"] = chunk
            params["startyear"] = str(start_year)
            params["endyear"] = str(end_year)
            
            try:
                response = self.session.post(
                    self.config["url"],
                    json=params,
                    timeout=60
                )
                
                if not self.validate_response(response):
                    continue
                
                data = response.json()
                
                if data.get("status") != "REQUEST_SUCCEEDED":
                    self.logger.error(f"BLS API error: {data.get('message')}")
                    continue
                
                for series in data.get("Results", {}).get("series", []):
                    series_id = series["seriesID"]
                    fips = series_id[5:10]
                    data_type = series_id[-2:]
                    
                    for item in series.get("data", []):
                        period = item.get("period", "")
                        if period == "M13":  # Skip annual averages
                            continue
                        
                        year = item.get("year")
                        month = int(period[1:]) if period.startswith("M") else 0
                        value = item.get("value")
                        
                        if not all([year, month, value]):
                            continue
                        
                        date_str = f"{year}-{month:02d}-01"
                        
                        result = {
                            "fips": fips,
                            "date": date_str,
                            "year": int(year),
                            "month": month
                        }
                        
                        if data_type == "03":
                            result["unemployment_rate"] = value
                        elif data_type == "04":
                            result["unemployment_count"] = value
                        elif data_type == "05":
                            result["employment_count"] = value
                        
                        all_results.append(result)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching BLS data: {e}")
            except (KeyError, ValueError) as e:
                self.logger.error(f"Error parsing BLS data: {e}")
            
            time.sleep(0.5)
        
        if all_results:
            df = pd.DataFrame(all_results)
            # Aggregate by county and date
            df = df.groupby(["fips", "date", "year", "month"], as_index=False).first()
            return df
        return None


class ZillowFetcher(DataFetcher):
    """Fetch Zillow housing data."""
    
    def fetch(
        self,
        counties: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Fetch Zillow housing data."""
        self.logger.info(
            f"Fetching Zillow data for {len(counties)} counties "
            f"from {start_date.date()} to {end_date.date()}"
        )
        
        try:
            # Download the entire dataset
            df = pd.read_csv(self.config["direct_download"])
            
            # Parse FIPS from RegionID
            df["StateFIPS"] = df["RegionID"].astype(str).str[:2].str.zfill(2)
            df["CountyFIPS"] = df["RegionID"].astype(str).str[2:5].str.zfill(3)
            df["FIPS"] = df["StateFIPS"] + df["CountyFIPS"]
            
            # Filter to our counties
            df = df[df["FIPS"].isin(counties)]
            
            if df.empty:
                self.logger.warning("No Zillow data found for specified counties")
                return None
            
            # Identify date columns
            id_vars = ["FIPS", "RegionID", "RegionName"]
            date_cols = [col for col in df.columns 
                        if col not in id_vars + ["StateFIPS", "CountyFIPS"] 
                        and not col.startswith("Size") 
                        and not col.startswith("Region")
                        and not col.startswith("State")
                        and not col.startswith("Metro")
                        and not col.startswith("Municipal")]
            
            # Convert to long format
            df_long = pd.melt(
                df,
                id_vars=id_vars,
                value_vars=date_cols,
                var_name="date",
                value_name="home_value_index"
            )
            
            # Convert date format
            df_long["date"] = pd.to_datetime(df_long["date"])
            
            # Filter by date range
            df_long = df_long[
                (df_long["date"] >= start_date) & 
                (df_long["date"] <= end_date)
            ]
            
            # Add year and month
            df_long["year"] = df_long["date"].dt.year
            df_long["month"] = df_long["date"].dt.month
            df_long["date"] = df_long["date"].dt.strftime("%Y-%m-%d")
            
            # Rename columns
            result_df = df_long.rename(columns={
                "FIPS": "fips",
                "RegionName": "region_name"
            })
            
            # Select final columns
            result_df = result_df[["fips", "date", "year", "month", 
                                   "home_value_index", "region_name"]]
            
            return result_df
            
        except Exception as e:
            self.logger.error(f"Error fetching Zillow data: {e}", exc_info=True)
            return None


class NOAAFetcher(DataFetcher):
    """Fetch NOAA climate data."""
    
    def fetch(
        self,
        counties: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Fetch NOAA climate data."""
        self.logger.info(
            f"Fetching NOAA data for {len(counties)} counties "
            f"from {start_date.date()} to {end_date.date()}"
        )
        
        results = []
        
        for fips in counties:
            if not validate_fips(fips):
                continue
            
            params = self.config["params"].copy()
            params["locationid"] = f"FIPS:{fips}"
            params["startdate"] = start_date.strftime("%Y-%m-%d")
            params["enddate"] = end_date.strftime("%Y-%m-%d")
            params["datatypeid"] = ",".join(self.config["datatypes"])
            params["limit"] = 1000
            
            headers = self.config.get("headers", {})
            
            try:
                response = self.session.get(
                    self.config["url"],
                    params=params,
                    headers=headers,
                    timeout=30
                )
                
                if not self.validate_response(response):
                    continue
                
                data = response.json()
                
                for item in data.get("results", []):
                    date_str = item.get("date", "")[:10]  # Extract date part
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    result = {
                        "fips": fips,
                        "date": date_str,
                        "year": date_obj.year,
                        "month": date_obj.month,
                        "datatype": item.get("datatype"),
                        "value": item.get("value")
                    }
                    
                    results.append(result)
                
                self.logger.debug(f"Successfully fetched NOAA data for county {fips}")
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching NOAA data for county {fips}: {e}")
            except (KeyError, ValueError) as e:
                self.logger.error(f"Error parsing NOAA data for county {fips}: {e}")
            
            time.sleep(0.5)
        
        if results:
            df = pd.DataFrame(results)
            
            # Pivot to wide format
            df_wide = df.pivot_table(
                index=["fips", "date", "year", "month"],
                columns="datatype",
                values="value",
                aggfunc="mean"
            ).reset_index()
            
            # Rename columns
            rename_map = {
                "TAVG": "avg_temperature",
                "TMIN": "min_temperature",
                "TMAX": "max_temperature",
                "PRCP": "precipitation"
            }
            df_wide.rename(columns=rename_map, inplace=True)
            
            return df_wide
        return None


class FREDFetcher(DataFetcher):
    """Fetch FRED economic data."""
    
    def fetch(
        self,
        counties: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Fetch FRED economic data."""
        self.logger.info(
            f"Fetching FRED data for {len(counties)} counties "
            f"from {start_date.date()} to {end_date.date()}"
        )
        
        # Note: FRED data access patterns may vary
        # This is a simplified implementation
        self.logger.warning(
            "FRED fetcher is simplified. Update with actual series IDs for your data."
        )
        
        return None


class DataCollector:
    """Orchestrate data collection from multiple sources."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize data collector.
        
        Args:
            data_dir: Directory to save collected data
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize fetchers
        sources = get_data_sources()
        self.fetchers = {
            'census': CensusFetcher(sources['census']),
            'bls': BLSFetcher(sources['bls']),
            'zillow': ZillowFetcher(sources['zillow']),
            'noaa': NOAAFetcher(sources['noaa']),
            'fred': FREDFetcher(sources['fred'])
        }
    
    def save_to_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """
        Save DataFrame to CSV file.
        
        Args:
            df: DataFrame to save
            filename: Output filename
        
        Returns:
            True if successful, False otherwise
        """
        if df is None or df.empty:
            self.logger.warning(f"No data to save to {filename}")
            return False
        
        filepath = self.data_dir / filename
        
        try:
            df.to_csv(filepath, index=False)
            self.logger.info(f"Saved {len(df)} records to {filename}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving to {filename}: {e}")
            return False
    
    def collect_all(
        self,
        counties: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, bool]:
        """
        Collect data from all sources.
        
        Args:
            counties: List of FIPS codes
            start_date: Start date
            end_date: End date
        
        Returns:
            Dictionary mapping source names to success status
        """
        # Validate inputs
        validate_date_range(start_date, end_date)
        
        valid_counties = [c for c in counties if validate_fips(c)]
        if not valid_counties:
            raise ValueError("No valid FIPS codes provided")
        
        self.logger.info(
            f"Collecting data for {len(valid_counties)} counties "
            f"from {start_date.date()} to {end_date.date()}"
        )
        
        results = {}
        
        # Mapping of fetchers to output files
        output_files = {
            'census': 'census_data.csv',
            'bls': 'bls_employment_data.csv',
            'zillow': 'zillow_housing_data.csv',
            'noaa': 'noaa_climate_data.csv',
            'fred': 'fred_economic_data.csv'
        }
        
        for name, fetcher in self.fetchers.items():
            try:
                self.logger.info(f"Fetching {name} data...")
                df = fetcher.fetch(valid_counties, start_date, end_date)
                
                if df is not None and not df.empty:
                    success = self.save_to_csv(df, output_files[name])
                    results[name] = success
                else:
                    self.logger.warning(f"No data collected from {name}")
                    results[name] = False
                    
            except Exception as e:
                self.logger.error(f"Error collecting {name} data: {e}", exc_info=True)
                results[name] = False
        
        return results


def setup_logging(log_level: int = logging.INFO):
    """Configure logging for the application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'county_data.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point for data collection script."""
    parser = argparse.ArgumentParser(
        description="Fetch county data from various public APIs"
    )
    parser.add_argument(
        '--counties',
        nargs='+',
        required=True,
        help='List of 5-digit county FIPS codes'
    )
    parser.add_argument(
        '--start-date',
        required=True,
        help='Start date in YYYY-MM-DD format'
    )
    parser.add_argument(
        '--end-date',
        required=True,
        help='End date in YYYY-MM-DD format'
    )
    parser.add_argument(
        '--data-dir',
        default='county_data',
        help='Directory to save collected data (default: county_data)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Parse dates
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        
        # Create collector
        collector = DataCollector(Path(args.data_dir))
        
        # Collect data
        results = collector.collect_all(args.counties, start_date, end_date)
        
        # Report results
        logger.info("=" * 60)
        logger.info("Data Collection Summary")
        logger.info("=" * 60)
        
        for source, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"{source:15s}: {status}")
        
        successful = sum(1 for s in results.values() if s)
        logger.info(f"\nTotal: {successful}/{len(results)} sources successful")
        
        return 0 if successful > 0 else 1
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())