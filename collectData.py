import requests
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import time
import logging
from pathlib import Path
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("county_data.log"), logging.StreamHandler()]
)
logger = logging.getLogger("county_data_collector")

# Create data directory if it doesn't exist
DATA_DIR = Path("county_data")
DATA_DIR.mkdir(exist_ok=True)

# Census API key - replace with your own
CENSUS_API_KEY = "YOUR_CENSUS_API_KEY"  # Get from https://api.census.gov/data/key_signup.html

# Define data sources with their configurations
DATA_SOURCES = {
    "census": {
        "url": "https://api.census.gov/data/{year}/acs/acs5",
        "params": {
            "get": "NAME,B01001_001E,B19013_001E,B25077_001E,B15003_022E,B15003_023E,B15003_024E,B15003_025E",
            "for": "county:{county}",
            "in": "state:{state}",
            "key": CENSUS_API_KEY
        },
        "columns": {
            "B01001_001E": "population",
            "B19013_001E": "median_household_income",
            "B25077_001E": "median_home_value",
            "B15003_022E": "bachelors_degree",
            "B15003_023E": "masters_degree",
            "B15003_024E": "professional_degree",
            "B15003_025E": "doctorate_degree"
        },
        "frequency": "annual",
        "filename": "census_data.csv"
    },
    "bls": {
        "url": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        "params": {
            "registrationkey": "",  # Optional, higher rate limits with registration
            "seriesid": [],  # Will be populated dynamically with county codes
            "startyear": "{start_year}",
            "endyear": "{end_year}"
        },
        "series_template": "LAUCN{fips}00000000{data_type}",  # data_type: 03=unemployment_rate, 04=unemployment, 05=employment
        "frequency": "monthly",
        "filename": "bls_employment_data.csv"
    },
    "zillow": {
        "url": "https://www.zillow.com/research/data/",
        "direct_download": "https://files.zillowstatic.com/research/public_csvs/zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        "frequency": "monthly",
        "filename": "zillow_housing_data.csv"
    },
    "noaa": {
        "url": "https://www.ncdc.noaa.gov/cdo-web/api/v2/data",
        "params": {
            "datasetid": "GHCND",
            "locationid": "FIPS:{fips}",
            "startdate": "{start_date}",
            "enddate": "{end_date}",
            "limit": 1000,
            "datatypeid": "TAVG,TMIN,TMAX,PRCP",
            "units": "standard"
        },
        "headers": {
            "token": "YOUR_NOAA_TOKEN"  # Get from https://www.ncdc.noaa.gov/cdo-web/token
        },
        "frequency": "monthly",
        "filename": "noaa_climate_data.csv"
    },
    "fred": {
        "url": "https://api.stlouisfed.org/fred/county/data",
        "params": {
            "county_fips": "{fips}",
            "api_key": "YOUR_FRED_API_KEY",  # Get from https://fred.stlouisfed.org/docs/api/api_key.html
            "file_type": "json",
            "frequency": "m",  # monthly
            "series_group": "income,housing,employment"
        },
        "frequency": "monthly",
        "filename": "fred_economic_data.csv"
    }
}

def split_fips(fips):
    """Split FIPS code into state and county components."""
    if len(fips) == 5:
        return fips[:2], fips[2:]
    else:
        logger.error(f"Invalid FIPS code: {fips}. Must be 5 digits.")
        return None, None

def fetch_census_data(counties, year):
    """Fetch data from Census API for specified counties."""
    logger.info(f"Fetching Census data for {len(counties)} counties for year {year}")
    
    results = []
    source_config = DATA_SOURCES["census"]
    
    for fips in counties:
        state_code, county_code = split_fips(fips)
        if state_code is None:
            continue
            
        params = source_config["params"].copy()
        params["for"] = params["for"].format(county=county_code)
        params["in"] = params["in"].format(state=state_code)
        
        url = source_config["url"].format(year=year)
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            headers = data[0]
            values = data[1]
            
            row = {headers[i]: values[i] for i in range(len(headers))}
            row["fips"] = fips
            row["year"] = year
            row["date"] = f"{year}-12-31"  # Last day of the year for annual data
            
            # Rename columns according to the mapping
            for census_col, readable_name in source_config["columns"].items():
                if census_col in row:
                    row[readable_name] = row.pop(census_col)
            
            results.append(row)
            logger.debug(f"Successfully fetched Census data for county {fips}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Census data for county {fips}: {e}")
            
        time.sleep(0.5)  # Rate limiting to be nice to the API
    
    if results:
        df = pd.DataFrame(results)
        return df
    return None

def fetch_bls_data(counties, start_date, end_date):
    """Fetch employment data from BLS API."""
    logger.info(f"Fetching BLS data for {len(counties)} counties from {start_date} to {end_date}")
    
    start_year = start_date.year
    end_year = end_date.year
    source_config = DATA_SOURCES["bls"]
    
    # Create series IDs for unemployment rate for each county
    series_ids = []
    for fips in counties:
        # Unemployment rate (03), unemployment count (04), employment count (05)
        for data_type in ["03", "04", "05"]:
            series_id = source_config["series_template"].format(fips=fips, data_type=data_type)
            series_ids.append(series_id)
    
    # Split into chunks of 50 to comply with API limits
    series_chunks = [series_ids[i:i+50] for i in range(0, len(series_ids), 50)]
    
    all_results = []
    
    for chunk in series_chunks:
        params = source_config["params"].copy()
        params["seriesid"] = chunk
        params["startyear"] = str(start_year)
        params["endyear"] = str(end_year)
        
        try:
            response = requests.post(source_config["url"], json=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data["status"] == "REQUEST_SUCCEEDED":
                for series in data["Results"]["series"]:
                    series_id = series["seriesID"]
                    fips = series_id[5:10]  # Extract FIPS from series ID
                    data_type = series_id[-2:]  # Extract data type from series ID
                    
                    for item in series["data"]:
                        value = item["value"]
                        year = item["year"]
                        period = item["period"]
                        
                        if period != "M13":  # Skip annual averages
                            month = int(period[1:])  # Convert M01 to 1, etc.
                            date_str = f"{year}-{month:02d}-01"
                            
                            result = {
                                "fips": fips,
                                "date": date_str,
                                "year": year,
                                "month": month
                            }
                            
                            # Set the appropriate field based on the data type
                            if data_type == "03":
                                result["unemployment_rate"] = value
                            elif data_type == "04":
                                result["unemployment_count"] = value
                            elif data_type == "05":
                                result["employment_count"] = value
                            
                            all_results.append(result)
            else:
                logger.error(f"BLS API error: {data['message']}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching BLS data: {e}")
            
        time.sleep(0.5)  # Rate limiting to be nice to the API
    
    if all_results:
        # Create a DataFrame and aggregate by county and date to combine the different metrics
        df = pd.DataFrame(all_results)
        df = df.groupby(["fips", "date", "year", "month"], as_index=False).first()
        return df
    return None

def fetch_zillow_data(counties, start_date, end_date):
    """Fetch housing data from Zillow."""
    logger.info(f"Fetching Zillow data for {len(counties)} counties from {start_date} to {end_date}")
    
    source_config = DATA_SOURCES["zillow"]
    
    try:
        # For Zillow, we download the entire dataset and filter by county
        df = pd.read_csv(source_config["direct_download"])
        
        # Extract state and county codes
        df["StateFIPS"] = df["RegionID"].astype(str).str[:2].astype(str).str.zfill(2)
        df["CountyFIPS"] = df["RegionID"].astype(str).str[2:5].astype(str).str.zfill(3)
        df["FIPS"] = df["StateFIPS"] + df["CountyFIPS"]
        
        # Filter to our counties of interest
        df = df[df["FIPS"].isin(counties)]
        
        # Convert to long format (unpivot the date columns)
        id_vars = ["FIPS", "RegionID", "SizeRank", "RegionName", "RegionType", "StateName", "State", "Metro", "StateCodeFIPS", "MunicipalCodeFIPS"]
        date_cols = [col for col in df.columns if col not in id_vars and col not in ["StateFIPS", "CountyFIPS"]]
        
        df_long = pd.melt(
            df, 
            id_vars=["FIPS"] + id_vars, 
            value_vars=date_cols,
            var_name="date", 
            value_name="home_value_index"
        )
        
        # Convert date format
        df_long["date"] = pd.to_datetime(df_long["date"])
        
        # Filter by our date range
        df_long = df_long[(df_long["date"] >= start_date) & (df_long["date"] <= end_date)]
        
        # Keep only the essential columns
        result_df = df_long[["FIPS", "date", "home_value_index", "RegionName"]]
        result_df.rename(columns={"FIPS": "fips"}, inplace=True)
        
        # Add year and month columns
        result_df["year"] = result_df["date"].dt.year
        result_df["month"] = result_df["date"].dt.month
        result_df["date"] = result_df["date"].dt.strftime("%Y-%m-%d")
        
        return result_df
        
    except Exception as e:
        logger.error(f"Error fetching Zillow data: {e}")
        return None

def fetch_noaa_data(counties, start_date, end_date):
    """Fetch climate data from NOAA."""
    logger.info(f"Fetching NOAA data for {len(counties)} counties from {start_date} to {end_date}")
    
    source_config = DATA_SOURCES["noaa"]
    results = []
    
    for fips in counties:
        params = source_config["params"].copy()
        params["locationid"] = params["locationid"].format(fips=fips)
        params["startdate"] = start_date.strftime("%Y-%m-%d")
        params["enddate"] = end_date.strftime("%Y-%m-%d")
        
        try:
            response = requests.get(
                source_config["url"], 
                params=params, 
                headers=source_config["headers"]
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "results" in data:
                for item in data["results"]:
                    date_obj = datetime.strptime(item["date"], "%Y-%m-%dT%H:%M:%S")
                    
                    result = {
                        "fips": fips,
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "year": date_obj.year,
                        "month": date_obj.month,
                        "datatype": item["datatype"],
                        "value": item["value"]
                    }
                    
                    results.append(result)
                    
            logger.debug(f"Successfully fetched NOAA data for county {fips}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching NOAA data for county {fips}: {e}")
            
        time.sleep(0.5)  # Rate limiting to be nice to the API
    
    if results:
        # Create a DataFrame and reshape to have one row per county-date with columns for each metric
        df = pd.DataFrame(results)
        
        # Pivot to wide format with datatypes as columns
        df_wide = df.pivot_table(
            index=["fips", "date", "year", "month"],
            columns="datatype",
            values="value",
            aggfunc="mean"
        ).reset_index()
        
        # Rename columns for clarity
        if isinstance(df_wide.columns, pd.MultiIndex):
            df_wide.columns = [col[1] if col[1] else col[0] for col in df_wide.columns]
        
        # Rename specific data type columns
        rename_map = {
            "TAVG": "avg_temperature",
            "TMIN": "min_temperature",
            "TMAX": "max_temperature",
            "PRCP": "precipitation"
        }
        df_wide.rename(columns=rename_map, inplace=True)
        
        return df_wide
    return None

def fetch_fred_data(counties, start_date, end_date):
    """Fetch economic data from FRED API."""
    logger.info(f"Fetching FRED data for {len(counties)} counties from {start_date} to {end_date}")
    
    source_config = DATA_SOURCES["fred"]
    results = []
    
    for fips in counties:
        params = source_config["params"].copy()
        params["county_fips"] = fips
        params["observation_start"] = start_date.strftime("%Y-%m-%d")
        params["observation_end"] = end_date.strftime("%Y-%m-%d")
        
        try:
            response = requests.get(source_config["url"], params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "observations" in data:
                for obs in data["observations"]:
                    date_obj = datetime.strptime(obs["date"], "%Y-%m-%d")
                    
                    result = {
                        "fips": fips,
                        "date": obs["date"],
                        "year": date_obj.year,
                        "month": date_obj.month,
                        "series_id": obs["series_id"],
                        "value": obs["value"]
                    }
                    
                    results.append(result)
                    
            logger.debug(f"Successfully fetched FRED data for county {fips}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching FRED data for county {fips}: {e}")
            
        time.sleep(0.5)  # Rate limiting to be nice to the API
    
    if results:
        # Create a DataFrame
        df = pd.DataFrame(results)
        
        # Map series IDs to readable names
        # This would need to be updated with actual FRED series mappings
        series_name_map = {
            # Example mappings - would need to be populated with actual FRED series IDs
            "MEDDAYONMAR": "median_days_on_market",
            "MEDLISPRI": "median_listing_price",
            "ACTLISCOU": "active_listings_count",
            "RRVRUSFOR": "rental_vacancy_rate"
        }
        
        # Add a column with the readable name based on the series_id
        df["metric_name"] = df["series_id"].map(lambda x: series_name_map.get(x, x))
        
        # Pivot to get one row per county-date with columns for each metric
        df_wide = df.pivot_table(
            index=["fips", "date", "year", "month"],
            columns="metric_name",
            values="value",
            aggfunc="first"
        ).reset_index()
        
        # Handle MultiIndex columns if present
        if isinstance(df_wide.columns, pd.MultiIndex):
            df_wide.columns = [col[1] if col[1] else col[0] for col in df_wide.columns]
        
        return df_wide
    return None

def is_data_outdated(filename, max_age_days=30):
    """Check if data file is outdated based on modification time."""
    file_path = DATA_DIR / filename
    
    if not file_path.exists():
        return True
    
    file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    current_time = datetime.now()
    
    return (current_time - file_mod_time).days > max_age_days

def save_to_csv(df, filename, mode="w"):
    """Save DataFrame to CSV file."""
    if df is None or df.empty:
        logger.warning(f"No data to save to {filename}")
        return False
    
    file_path = DATA_DIR / filename
    
    try:
        # Determine if we need to write headers (only in write mode or if file doesn't exist)
        write_header = mode == "w" or not file_path.exists()
        
        # Make sure the directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to CSV
        df.to_csv(file_path, mode=mode, index=False, header=write_header)
        logger.info(f"Successfully saved data to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {filename}: {e}")
        return False

def check_and_update_data(counties, start_date, end_date):
    """Check if data files need updating and fetch new data if needed."""
    update_results = {}
    
    for source_name, source_config in DATA_SOURCES.items():
        filename = source_config["filename"]
        
        if is_data_outdated(filename):
            logger.info(f"Data for {source_name} is outdated or missing. Updating...")
            
            if source_name == "census":
                # For annual data, we get the latest year
                current_year = datetime.now().year
                # Census data typically has a 1-2 year lag
                latest_year = current_year - 2
                
                df = fetch_census_data(counties, latest_year)
                update_results[source_name] = save_to_csv(df, filename)
                
            elif source_name == "bls":
                df = fetch_bls_data(counties, start_date, end_date)
                update_results[source_name] = save_to_csv(df, filename)
                
            elif source_name == "zillow":
                df = fetch_zillow_data(counties, start_date, end_date)
                update_results[source_name] = save_to_csv(df, filename)
                
            elif source_name == "noaa":
                df = fetch_noaa_data(counties, start_date, end_date)
                update_results[source_name] = save_to_csv(df, filename)
                
            elif source_name == "fred":
                df = fetch_fred_data(counties, start_date, end_date)
                update_results[source_name] = save_to_csv(df, filename)
        else:
            logger.info(f"Data for {source_name} is up to date.")
            update_results[source_name] = True
    
    return update_results

def fetch_all_data(counties, start_date, end_date):
    """Fetch data from all sources for the specified counties and date range."""
    results = {}
    
    # Census data (annual)
    years = list(range(start_date.year, end_date.year + 1))
    census_dfs = []
    
    for year in years:
        df = fetch_census_data(counties, year)
        if df is not None:
            census_dfs.append(df)
    
    if census_dfs:
        census_df = pd.concat(census_dfs)
        save_to_csv(census_df, DATA_SOURCES["census"]["filename"])
        results["census"] = True
    else:
        results["census"] = False
    
    # BLS employment data (monthly)
    bls_df = fetch_bls_data(counties, start_date, end_date)
    save_to_csv(bls_df, DATA_SOURCES["bls"]["filename"])
    results["bls"] = bls_df is not None
    
    # Zillow housing data (monthly)
    zillow_df = fetch_zillow_data(counties, start_date, end_date)
    save_to_csv(zillow_df, DATA_SOURCES["zillow"]["filename"])
    results["zillow"] = zillow_df is not None
    
    # NOAA climate data (monthly/daily)
    noaa_df = fetch_noaa_data(counties, start_date, end_date)
    save_to_csv(noaa_df, DATA_SOURCES["noaa"]["filename"])
    results["noaa"] = noaa_df is not None
    
    # FRED economic data (monthly)
    fred_df = fetch_fred_data(counties, start_date, end_date)
    save_to_csv(fred_df, DATA_SOURCES["fred"]["filename"])
    results["fred"] = fred_df is not None
    
    return results

def create_postgres_scripts():
    """Create SQL scripts for loading data into PostgreSQL."""
    # Create a directory for SQL scripts
    sql_dir = Path("sql_scripts")
    sql_dir.mkdir(exist_ok=True)
    
    # Create table creation script
    create_tables_sql = """
    -- Create schema for county data
    CREATE SCHEMA IF NOT EXISTS county_data;
    
    -- Census demographics table
    CREATE TABLE IF NOT EXISTS county_data.census (
        fips CHAR(5) NOT NULL,
        date DATE NOT NULL,
        year INT NOT NULL,
        population INT,
        median_household_income NUMERIC,
        median_home_value NUMERIC,
        bachelors_degree INT,
        masters_degree INT,
        professional_degree INT,
        doctorate_degree INT,
        PRIMARY KEY (fips, date)
    );
    
    -- BLS employment data
    CREATE TABLE IF NOT EXISTS county_data.employment (
        fips CHAR(5) NOT NULL,
        date DATE NOT NULL,
        year INT NOT NULL,
        month INT NOT NULL,
        unemployment_rate NUMERIC,
        unemployment_count INT,
        employment_count INT,
        PRIMARY KEY (fips, date)
    );
    
    -- Zillow housing data
    CREATE TABLE IF NOT EXISTS county_data.housing (
        fips CHAR(5) NOT NULL,
        date DATE NOT NULL,
        year INT NOT NULL,
        month INT NOT NULL,
        home_value_index NUMERIC,
        region_name VARCHAR(255),
        PRIMARY KEY (fips, date)
    );
    
    -- NOAA climate data
    CREATE TABLE IF NOT EXISTS county_data.climate (
        fips CHAR(5) NOT NULL,
        date DATE NOT NULL,
        year INT NOT NULL,
        month INT NOT NULL,
        avg_temperature NUMERIC,
        min_temperature NUMERIC,
        max_temperature NUMERIC,
        precipitation NUMERIC,
        PRIMARY KEY (fips, date)
    );
    
    -- FRED economic data
    CREATE TABLE IF NOT EXISTS county_data.economic (
        fips CHAR(5) NOT NULL,
        date DATE NOT NULL,
        year INT NOT NULL,
        month INT NOT NULL,
        median_days_on_market NUMERIC,
        median_listing_price NUMERIC,
        active_listings_count INT,
        rental_vacancy_rate NUMERIC,
        PRIMARY KEY (fips, date)
    );
    
    -- Counties reference table
    CREATE TABLE IF NOT EXISTS county_data.counties (
        fips CHAR(5) PRIMARY KEY,
        state_fips CHAR(2) NOT NULL,
        county_fips CHAR(3) NOT NULL,
        state_name VARCHAR(100),
        county_name VARCHAR(100)
    );
    """
    
    with open(sql_dir / "create_tables.sql", "w") as f:
        f.write(create_tables_sql)
    
    # Create data loading script
    load_data_sql = """
    -- Load census data
    COPY county_data.census FROM '/path/to/county_data/census_data.csv' 
    DELIMITER ',' CSV HEADER;
    
    -- Load BLS employment data
    COPY county_data.employment FROM '/path/to/county_data/bls_employment_data.csv' 
    DELIMITER ',' CSV HEADER;
    
    -- Load Zillow housing data
    COPY county_data.housing FROM '/path/to/county_data/zillow_housing_data.csv' 
    DELIMITER ',' CSV HEADER;
    
    -- Load NOAA climate data
    COPY county_data.climate FROM '/path/to/county_data/noaa_climate_data.csv' 
    DELIMITER ',' CSV HEADER;
    
    -- Load FRED economic data
    COPY county_data.economic FROM '/path/to/county_data/fred_economic_data.csv' 
    DELIMITER ',' CSV HEADER;
    """
    
    with open(sql_dir / "load_data.sql", "w") as f:
        f.write(load_data_sql)
    
    # Create sample queries script
    sample_queries_sql = """
    -- Sample query 1: Counties with highest population growth
    SELECT 
        c1.fips,
        c1.county_name,
        c1.state_name,
        c2.population as pop_start,
        c1.population as pop_end,
        round(((c1.population - c2.population) / c2.population::numeric * 100), 2) as growth_pct
    FROM 
        county_data.census c1
    JOIN 
        county_data.census c2 ON c1.fips = c2.fips AND c1.year = c2.year + 1
    JOIN 
        county_data.counties co ON c1.fips = co.fips
    ORDER BY 
        growth_pct DESC
    LIMIT 10;
    
    -- Sample query 2: Counties with lowest unemployment rates
    SELECT 
        e.fips,
        co.county_name,
        co.state_name,
        e.date,
        e.unemployment_rate
    FROM 
        county_data.employment e
    JOIN 
        county_data.counties co ON e.fips = co.fips
    WHERE 
        e.date = (SELECT MAX(date) FROM county_data.employment)
    ORDER BY 
        e.unemployment_rate ASC
    LIMIT 10;
    
    -- Sample query 3: Counties with highest home values and their climate data
    SELECT 
        h.fips,
        co.county_name,
        co.state_name,
        h.date,
        h.home_value_index,
        c.avg_temperature,
        c.precipitation
    FROM 
        county_data.housing h
    JOIN 
        county_data.climate c ON h.fips = c.fips AND h.date = c.date
    JOIN 
        county_data.counties co ON h.fips = co.fips
    WHERE 
        h.date = (SELECT MAX(date) FROM county_data.housing)
    ORDER BY 
        h.home_value_index DESC
    LIMIT 10;
    
    -- Sample query 4: Correlation between education level and income
    SELECT 
        corr(
            (c.bachelors_degree + c.masters_degree + c.professional_degree + c.doctorate_degree)::numeric / c.population * 100, 
            c.median_household_income
        ) as education_income_correlation
    FROM 
        county_data.census c
    WHERE 
        c.year = (SELECT MAX(year) FROM county_data.census);
    
    -- Sample query 5: Counties with most extreme temperature variations
    SELECT 
        c.fips,
        co.county_name,
        co.state_name,
        AVG(c.max_temperature - c.min_temperature) as avg_daily_temp_range,
        AVG(c.avg_temperature) as avg_temp
    FROM 
        county_data.climate c
    JOIN 
        county_data.counties co ON c.fips = co.fips
    GROUP BY 
        c.fips, co.county_name, co.state_name
    ORDER BY 
        avg_daily_temp_range DESC
    LIMIT 10;
    """
    
    with open(sql_dir / "sample_queries.sql", "w") as f:
        f.write(sample_queries_sql)
    
    logger.info("Created PostgreSQL scripts in the sql_scripts directory")

def main():
    """Main function to run the data collection."""
    # Example usage:
    counties = [
        "06037",  # Los Angeles County, CA
        "36061",  # New York County, NY
        "17031",  # Cook County, IL
        "48201",  # Harris County, TX
        "04013"   # Maricopa County, AZ
    ]
    
    # Date range for data collection
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 3)  # 3 years of data
    
    print(f"Fetching data for counties: {counties}")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Fetch data from all sources
    results = fetch_all_data(counties, start_date, end_date)

    # Check which data sources were successfully fetched
    for source, success in results.items():
        if success:
            logger.info(f"Successfully fetched data from {source}")
        else:
            logger.error(f"Failed to fetch data from {source}")

    # Create PostgreSQL scripts for loading and querying the data
    create_postgres_scripts()

    logger.info("Data collection and script generation complete.")

if __name__ == "__main__":
    main()
