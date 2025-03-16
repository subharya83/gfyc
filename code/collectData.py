import requests
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import time
import logging
from pathlib import Path
import argparse

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

def load_config(config_file):
    """Load configuration from a JSON file."""
    with open(config_file, 'r') as f:
        return json.load(f)

def split_fips(fips):
    """Split FIPS code into state and county components."""
    if len(fips) == 5:
        return fips[:2], fips[2:]
    else:
        logger.error(f"Invalid FIPS code: {fips}. Must be 5 digits.")
        return None, None

def fetch_census_data(counties, year, config):
    """Fetch data from Census API for specified counties."""
    logger.info(f"Fetching Census data for {len(counties)} counties for year {year}")
    
    results = []
    source_config = config["census"]
    
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

def fetch_all_data(counties, start_date, end_date, config):
    """Fetch data from all sources and save results to CSV files."""
    results = {}
    
    # Fetch Census data
    census_df = fetch_census_data(counties, start_date.year, config)
    if census_df is not None:
        save_to_csv(census_df, "census_data.csv", mode="w")
        results["Census"] = True
    else:
        results["Census"] = False
    
    # Fetch BLS data
    bls_df = fetch_bls_data(counties, start_date, end_date)
    if bls_df is not None:
        save_to_csv(bls_df, "bls_data.csv", mode="w")
        results["BLS"] = True
    else:
        results["BLS"] = False
    
    # Fetch Zillow data
    zillow_df = fetch_zillow_data(counties, start_date, end_date)
    if zillow_df is not None:
        save_to_csv(zillow_df, "zillow_data.csv", mode="w")
        results["Zillow"] = True
    else:
        results["Zillow"] = False
    
    # Fetch NOAA data
    noaa_df = fetch_noaa_data(counties, start_date, end_date)
    if noaa_df is not None:
        save_to_csv(noaa_df, "noaa_data.csv", mode="w")
        results["NOAA"] = True
    else:
        results["NOAA"] = False
    
    # Fetch FRED data
    fred_df = fetch_fred_data(counties, start_date, end_date)
    if fred_df is not None:
        save_to_csv(fred_df, "fred_data.csv", mode="w")
        results["FRED"] = True
    else:
        results["FRED"] = False
    
    return results

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

def main():
    parser = argparse.ArgumentParser(description="Fetch data for specified counties and date range.")
    parser.add_argument("--counties", nargs="+", required=True, help="List of county FIPS codes")
    parser.add_argument("--start_date", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--config", required=True, help="Path to config file")
    
    args = parser.parse_args()
    
    counties = args.counties
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    config = load_config(args.config)
    
    # Fetch data from all sources
    results = fetch_all_data(counties, start_date, end_date, config)

    # Check which data sources were successfully fetched
    for source, success in results.items():
        if success:
            logger.info(f"Successfully fetched data from {source}")
        else:
            logger.error(f"Failed to fetch data from {source}")

if __name__ == "__main__":
    main()
