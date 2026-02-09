"""
Database Management Module

This module handles database operations for county migration data including
table creation, data loading, and maintenance tasks.
"""

import argparse
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List

import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


class DatabaseManager:
    """Manages database operations for county data."""
    
    def __init__(self, config: Dict):
        """
        Initialize database manager.
        
        Args:
            config: Configuration dictionary containing database settings
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.conn = None
    
    def connect(self):
        """
        Establish database connection using configuration.
        
        Returns:
            Database connection object
        
        Raises:
            psycopg2.Error: If connection fails
        """
        load_dotenv()
        
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', self.config.get('dbname')),
                user=os.getenv('DB_USER', self.config.get('user')),
                password=os.getenv('DB_PASSWORD', self.config.get('password')),
                host=os.getenv('DB_HOST', self.config.get('host', 'localhost')),
                port=os.getenv('DB_PORT', self.config.get('port', 5432))
            )
            self.logger.info("Database connection established successfully")
            return self.conn
        except psycopg2.Error as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            if self.conn:
                self.conn.rollback()
                self.logger.error("Transaction rolled back due to error")
        self.close()
    
    def create_schema(self):
        """Create database schema if it doesn't exist."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS county_data;")
            self.conn.commit()
            self.logger.info("Schema 'county_data' created/verified")
        except psycopg2.Error as e:
            self.conn.rollback()
            self.logger.error(f"Error creating schema: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables with proper constraints and indexes."""
        try:
            with self.conn.cursor() as cur:
                # Counties table (reference table)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS county_data.counties (
                    fips CHAR(5) PRIMARY KEY,
                    state_fips CHAR(2) NOT NULL,
                    county_fips CHAR(3) NOT NULL,
                    state_name VARCHAR(100) NOT NULL,
                    county_name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT valid_fips CHECK (fips ~ '^[0-9]{5}$'),
                    CONSTRAINT valid_state_fips CHECK (state_fips ~ '^[0-9]{2}$'),
                    CONSTRAINT valid_county_fips CHECK (county_fips ~ '^[0-9]{3}$')
                );
                """)
                
                # Census data table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS county_data.census (
                    id SERIAL PRIMARY KEY,
                    fips CHAR(5) NOT NULL,
                    date DATE NOT NULL,
                    year INT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
                    population INT CHECK (population >= 0),
                    median_household_income NUMERIC(12, 2) CHECK (median_household_income >= 0),
                    median_home_value NUMERIC(12, 2) CHECK (median_home_value >= 0),
                    bachelors_degree INT CHECK (bachelors_degree >= 0),
                    masters_degree INT CHECK (masters_degree >= 0),
                    professional_degree INT CHECK (professional_degree >= 0),
                    doctorate_degree INT CHECK (doctorate_degree >= 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_census_entry UNIQUE(fips, date),
                    CONSTRAINT fk_census_county FOREIGN KEY (fips) 
                        REFERENCES county_data.counties(fips) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_census_fips ON county_data.census(fips);
                CREATE INDEX IF NOT EXISTS idx_census_date ON county_data.census(date);
                CREATE INDEX IF NOT EXISTS idx_census_year ON county_data.census(year);
                """)
                
                # Employment data table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS county_data.employment (
                    id SERIAL PRIMARY KEY,
                    fips CHAR(5) NOT NULL,
                    date DATE NOT NULL,
                    year INT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
                    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
                    unemployment_rate NUMERIC(5, 2) CHECK (unemployment_rate >= 0 AND unemployment_rate <= 100),
                    unemployment_count INT CHECK (unemployment_count >= 0),
                    employment_count INT CHECK (employment_count >= 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_employment_entry UNIQUE(fips, date),
                    CONSTRAINT fk_employment_county FOREIGN KEY (fips) 
                        REFERENCES county_data.counties(fips) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_employment_fips ON county_data.employment(fips);
                CREATE INDEX IF NOT EXISTS idx_employment_date ON county_data.employment(date);
                """)
                
                # Housing data table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS county_data.housing (
                    id SERIAL PRIMARY KEY,
                    fips CHAR(5) NOT NULL,
                    date DATE NOT NULL,
                    year INT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
                    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
                    home_value_index NUMERIC(12, 2) CHECK (home_value_index >= 0),
                    region_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_housing_entry UNIQUE(fips, date),
                    CONSTRAINT fk_housing_county FOREIGN KEY (fips) 
                        REFERENCES county_data.counties(fips) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_housing_fips ON county_data.housing(fips);
                CREATE INDEX IF NOT EXISTS idx_housing_date ON county_data.housing(date);
                """)
                
                # Climate data table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS county_data.climate (
                    id SERIAL PRIMARY KEY,
                    fips CHAR(5) NOT NULL,
                    date DATE NOT NULL,
                    year INT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
                    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
                    avg_temperature NUMERIC(6, 2),
                    min_temperature NUMERIC(6, 2),
                    max_temperature NUMERIC(6, 2),
                    precipitation NUMERIC(8, 2) CHECK (precipitation >= 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_climate_entry UNIQUE(fips, date),
                    CONSTRAINT fk_climate_county FOREIGN KEY (fips) 
                        REFERENCES county_data.counties(fips) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_climate_fips ON county_data.climate(fips);
                CREATE INDEX IF NOT EXISTS idx_climate_date ON county_data.climate(date);
                """)
                
                # Economic data table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS county_data.economic (
                    id SERIAL PRIMARY KEY,
                    fips CHAR(5) NOT NULL,
                    date DATE NOT NULL,
                    year INT NOT NULL CHECK (year BETWEEN 1900 AND 2100),
                    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
                    median_days_on_market NUMERIC(6, 2) CHECK (median_days_on_market >= 0),
                    median_listing_price NUMERIC(12, 2) CHECK (median_listing_price >= 0),
                    active_listings_count INT CHECK (active_listings_count >= 0),
                    rental_vacancy_rate NUMERIC(5, 2) CHECK (rental_vacancy_rate >= 0 AND rental_vacancy_rate <= 100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_economic_entry UNIQUE(fips, date),
                    CONSTRAINT fk_economic_county FOREIGN KEY (fips) 
                        REFERENCES county_data.counties(fips) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_economic_fips ON county_data.economic(fips);
                CREATE INDEX IF NOT EXISTS idx_economic_date ON county_data.economic(date);
                """)
            
            self.conn.commit()
            self.logger.info("All tables created successfully with constraints and indexes")
            
        except psycopg2.Error as e:
            self.conn.rollback()
            self.logger.error(f"Error creating tables: {e}")
            raise
    
    def validate_csv_file(self, file_path: Path, data_dir: Path) -> bool:
        """
        Validate CSV file exists and is within the data directory.
        
        Args:
            file_path: Path to CSV file
            data_dir: Base data directory
        
        Returns:
            True if valid, False otherwise
        """
        if not file_path.exists():
            self.logger.warning(f"File not found: {file_path}")
            return False
        
        # Prevent directory traversal attacks
        try:
            file_path.resolve().relative_to(data_dir.resolve())
        except ValueError:
            self.logger.error(f"File path outside data directory: {file_path}")
            return False
        
        return True
    
    def load_data_from_csv(self, table_name: str, csv_file: Path, data_dir: Path):
        """
        Load data from CSV file into database table.
        
        Args:
            table_name: Name of the table (without schema)
            csv_file: Path to CSV file
            data_dir: Base data directory for validation
        
        Raises:
            psycopg2.Error: If database operation fails
        """
        if not self.validate_csv_file(csv_file, data_dir):
            return
        
        try:
            # Read CSV with pandas for better error handling
            df = pd.read_csv(csv_file)
            
            if df.empty:
                self.logger.warning(f"Empty CSV file: {csv_file}")
                return
            
            # Get column names
            columns = df.columns.tolist()
            
            # Create INSERT statement with ON CONFLICT
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            
            # Simple insert (can be modified to upsert if needed)
            insert_query = f"""
                INSERT INTO county_data.{table_name} ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            with self.conn.cursor() as cur:
                # Use execute_batch for better performance
                psycopg2.extras.execute_batch(
                    cur,
                    insert_query,
                    df.values.tolist(),
                    page_size=1000
                )
            
            self.conn.commit()
            self.logger.info(
                f"Loaded {len(df)} records from {csv_file.name} into {table_name}"
            )
            
        except pd.errors.EmptyDataError:
            self.logger.warning(f"Empty or invalid CSV file: {csv_file}")
        except psycopg2.Error as e:
            self.conn.rollback()
            self.logger.error(f"Database error loading {csv_file.name}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading {csv_file.name}: {e}")
            raise
    
    def load_all_data(self, data_dir: Path):
        """
        Load data from all CSV files in the data directory.
        
        Args:
            data_dir: Directory containing CSV files
        """
        # Mapping of CSV files to table names
        file_table_mapping = {
            'census_data.csv': 'census',
            'bls_employment_data.csv': 'employment',
            'zillow_housing_data.csv': 'housing',
            'noaa_climate_data.csv': 'climate',
            'fred_economic_data.csv': 'economic'
        }
        
        for filename, table in file_table_mapping.items():
            csv_file = data_dir / filename
            self.logger.info(f"Loading {filename} into {table} table...")
            self.load_data_from_csv(table, csv_file, data_dir)
    
    def is_data_outdated(self, filepath: Path, max_age_days: int = 30) -> bool:
        """
        Check if data file is outdated based on modification time.
        
        Args:
            filepath: Path to file to check
            max_age_days: Maximum age in days before considered outdated
        
        Returns:
            True if file is outdated or doesn't exist
        """
        if not filepath.exists():
            return True
        
        file_mod_time = datetime.fromtimestamp(filepath.stat().st_mtime)
        current_time = datetime.now()
        age_days = (current_time - file_mod_time).days
        
        is_outdated = age_days > max_age_days
        
        if is_outdated:
            self.logger.info(
                f"File {filepath.name} is {age_days} days old (threshold: {max_age_days})"
            )
        
        return is_outdated


def load_config(config_file: str) -> Dict:
    """
    Load configuration from JSON file.
    
    Args:
        config_file: Path to JSON configuration file
    
    Returns:
        Configuration dictionary
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_path, 'r') as f:
        return json.load(f)


def setup_logging(log_level: int = logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('db_management.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point for database management script."""
    parser = argparse.ArgumentParser(
        description="Manage database for county migration data"
    )
    parser.add_argument(
        '--config',
        required=True,
        help='Path to JSON configuration file'
    )
    parser.add_argument(
        '--data-dir',
        required=True,
        help='Directory containing CSV data files'
    )
    parser.add_argument(
        '--create-tables',
        action='store_true',
        help='Create database tables'
    )
    parser.add_argument(
        '--load-data',
        action='store_true',
        help='Load data from CSV files'
    )
    parser.add_argument(
        '--check-outdated',
        action='store_true',
        help='Check if data files are outdated'
    )
    parser.add_argument(
        '--max-age',
        type=int,
        default=30,
        help='Maximum age in days before data is considered outdated (default: 30)'
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
        # Load configuration
        config = load_config(args.config)
        data_dir = Path(args.data_dir)
        
        if not data_dir.exists():
            logger.error(f"Data directory does not exist: {data_dir}")
            return 1
        
        # Use context manager for database operations
        with DatabaseManager(config) as db_manager:
            # Create schema
            db_manager.create_schema()
            
            # Create tables if requested
            if args.create_tables:
                logger.info("Creating database tables...")
                db_manager.create_tables()
            
            # Check if data is outdated
            if args.check_outdated:
                logger.info("Checking data freshness...")
                for csv_file in data_dir.glob('*.csv'):
                    is_outdated = db_manager.is_data_outdated(csv_file, args.max_age)
                    status = "OUTDATED" if is_outdated else "CURRENT"
                    logger.info(f"{csv_file.name}: {status}")
            
            # Load data if requested
            if args.load_data:
                logger.info("Loading data from CSV files...")
                db_manager.load_all_data(data_dir)
        
        logger.info("Database management operations completed successfully")
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return 1
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())