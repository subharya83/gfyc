import argparse
import logging
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("db_management.log"), logging.StreamHandler()]
)
logger = logging.getLogger("db_manager")

def load_config(config_file):
    """Load configuration from a JSON file."""
    with open(config_file, 'r') as f:
        return json.load(f)

def is_data_outdated(filename, max_age_days=30):
    """Check if data file is outdated based on modification time."""
    file_path = Path(filename)
    
    if not file_path.exists():
        return True
    
    file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    current_time = datetime.now()
    
    return (current_time - file_mod_time).days > max_age_days

def create_tables(conn):
    """Create tables in the database."""
    with conn.cursor() as cur:
        cur.execute("""
        CREATE SCHEMA IF NOT EXISTS county_data;
        
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
        
        CREATE TABLE IF NOT EXISTS county_data.housing (
            fips CHAR(5) NOT NULL,
            date DATE NOT NULL,
            year INT NOT NULL,
            month INT NOT NULL,
            home_value_index NUMERIC,
            region_name VARCHAR(255),
            PRIMARY KEY (fips, date)
        );
        
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
        
        CREATE TABLE IF NOT EXISTS county_data.counties (
            fips CHAR(5) PRIMARY KEY,
            state_fips CHAR(2) NOT NULL,
            county_fips CHAR(3) NOT NULL,
            state_name VARCHAR(100),
            county_name VARCHAR(100)
        );
        """)
        conn.commit()
    logger.info("Tables created successfully.")

def load_data(conn, data_dir):
    """Load data from CSV files into the database."""
    with conn.cursor() as cur:
        cur.execute(f"""
        COPY county_data.census FROM '{data_dir}/census_data.csv' DELIMITER ',' CSV HEADER;
        COPY county_data.employment FROM '{data_dir}/bls_employment_data.csv' DELIMITER ',' CSV HEADER;
        COPY county_data.housing FROM '{data_dir}/zillow_housing_data.csv' DELIMITER ',' CSV HEADER;
        COPY county_data.climate FROM '{data_dir}/noaa_climate_data.csv' DELIMITER ',' CSV HEADER;
        COPY county_data.economic FROM '{data_dir}/fred_economic_data.csv' DELIMITER ',' CSV HEADER;
        """)
        conn.commit()
    logger.info("Data loaded successfully.")

def main():
    parser = argparse.ArgumentParser(description="Manage database for county data.")
    parser.add_argument("--config", required=True, help="Path to config file")
    parser.add_argument("--data_dir", required=True, help="Directory containing data files")
    parser.add_argument("--update", action="store_true", help="Update data if outdated")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    data_dir = Path(args.data_dir)
    
    # Connect to the database
    conn = psycopg2.connect(
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
        host=config["host"],
        port=config["port"]
    )
    
    # Create tables if they don't exist
    create_tables(conn)
    
    # Check if data is outdated and update if necessary
    if args.update:
        if is_data_outdated(data_dir / "census_data.csv"):
            logger.info("Data is outdated. Updating...")
            # Call the data collection script here or trigger an update process
        else:
            logger.info("Data is up to date.")
    
    # Load data into the database
    load_data(conn, data_dir)
    
    conn.close()

if __name__ == "__main__":
    main()

