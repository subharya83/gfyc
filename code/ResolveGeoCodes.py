"""
Address Geocoding Module

This module provides functionality to geocode addresses using Google Maps API
and extract geographic and administrative information.
"""

import argparse
import csv
import logging
import os
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import googlemaps as gm
from dotenv import load_dotenv


@dataclass
class LocationInfo:
    """Store geocoded location information."""
    name: str
    address: str
    latitude: float
    longitude: float
    location_types: list
    county: Optional[str]
    state: Optional[str]
    link: str


class AddressResolver:
    """Resolves addresses to geographic coordinates and administrative areas."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AddressResolver with Google Maps API key.
        
        Args:
            api_key: Google Maps API key. If not provided, reads from environment.
        
        Raises:
            ValueError: If API key is not provided and not found in environment.
        """
        load_dotenv()
        
        self.api_key = api_key or os.getenv('GOOGLE_MAPS_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Google Maps API key must be provided either as argument or "
                "in GOOGLE_MAPS_API_KEY environment variable"
            )
        
        try:
            self.client = gm.Client(key=self.api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Google Maps client: {e}")
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def extract_administrative_info(
        self, 
        address_components: list
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract county and state from address components.
        
        Args:
            address_components: List of address component dictionaries from Google Maps API
        
        Returns:
            Tuple of (county, state), either of which may be None
        """
        county = None
        state = None
        
        for component in address_components:
            component_types = component.get('types', [])
            
            if "administrative_area_level_2" in component_types:
                county = component.get('long_name')
            
            if "administrative_area_level_1" in component_types:
                state = component.get('long_name')
        
        return county, state
    
    def geocode_address(self, address: str) -> Optional[LocationInfo]:
        """
        Geocode a single address.
        
        Args:
            address: Address string to geocode
        
        Returns:
            LocationInfo object if successful, None otherwise
        """
        if not address or not address.strip():
            self.logger.warning("Empty or whitespace-only address provided")
            return None
        
        try:
            results = self.client.geocode(address)
            
            if not results:
                self.logger.warning(f'No geocoding results found for: {address}')
                return None
            
            first_result = results[0]
            
            # Extract geometry information
            geometry = first_result.get('geometry', {})
            location = geometry.get('location', {})
            
            if not location:
                self.logger.error(f'No location data in geocoding result for: {address}')
                return None
            
            # Extract administrative information
            address_components = first_result.get('address_components', [])
            county, state = self.extract_administrative_info(address_components)
            
            # Create LocationInfo object
            location_info = LocationInfo(
                name="",  # Will be filled by caller
                address=first_result.get('formatted_address', address),
                latitude=location.get('lat', 0.0),
                longitude=location.get('lng', 0.0),
                location_types=first_result.get('types', []),
                county=county,
                state=state,
                link=""  # Will be filled by caller
            )
            
            return location_info
            
        except gm.exceptions.ApiError as e:
            self.logger.error(f'Google Maps API error for "{address}": {e}')
            return None
        except (KeyError, IndexError) as e:
            self.logger.error(f'Unexpected response format for "{address}": {e}')
            return None
        except Exception as e:
            self.logger.error(
                f'Unexpected error processing "{address}": {e}', 
                exc_info=True
            )
            return None
    
    def process_file(
        self, 
        input_file: str, 
        output_file: str,
        delimiter: str = '|',
        skip_header: bool = False
    ) -> int:
        """
        Process a CSV file of addresses and geocode them.
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output CSV file
            delimiter: Delimiter used in input file (default: '|')
            skip_header: Whether to skip first row of input file
        
        Returns:
            Number of successfully processed addresses
        
        Raises:
            FileNotFoundError: If input file doesn't exist
            IOError: If there are file read/write errors
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        processed_count = 0
        error_count = 0
        
        try:
            with open(output_path, mode='w', newline='', encoding='utf-8') as out_file, \
                 open(input_path, 'r', encoding='utf-8') as in_file:
                
                writer = csv.writer(out_file, delimiter=',', quotechar='"')
                reader = csv.reader(in_file, delimiter=delimiter)
                
                # Write header
                writer.writerow([
                    'Attraction Name', 
                    'Refined Address', 
                    'Latitude', 
                    'Longitude', 
                    'Location Types', 
                    'County', 
                    'State', 
                    'Link'
                ])
                
                # Skip header if requested
                if skip_header:
                    next(reader, None)
                
                for row_num, row in enumerate(reader, start=1):
                    # Validate row has enough columns
                    if len(row) < 3:
                        self.logger.warning(
                            f'Row {row_num}: Insufficient columns (expected 3+, got {len(row)})'
                        )
                        error_count += 1
                        continue
                    
                    # Extract data from row
                    link = row[0] if len(row) > 0 else ''
                    name = row[1] if len(row) > 1 else ''
                    address = row[2].strip() if len(row) > 2 else ''
                    
                    if not address:
                        self.logger.warning(f'Row {row_num}: Empty address field')
                        error_count += 1
                        continue
                    
                    # Geocode the address
                    location = self.geocode_address(address)
                    
                    if location:
                        location.name = name
                        location.link = link
                        
                        writer.writerow([
                            location.name,
                            location.address,
                            location.latitude,
                            location.longitude,
                            ', '.join(location.location_types),
                            location.county or 'Unknown',
                            location.state or 'Unknown',
                            location.link
                        ])
                        
                        processed_count += 1
                        self.logger.info(
                            f'Row {row_num}: Successfully geocoded "{address}"'
                        )
                    else:
                        error_count += 1
                        self.logger.error(
                            f'Row {row_num}: Failed to geocode "{address}"'
                        )
        
        except IOError as e:
            self.logger.error(f'File I/O error: {e}')
            raise
        except Exception as e:
            self.logger.error(f'Unexpected error during file processing: {e}', exc_info=True)
            raise
        
        self.logger.info(
            f'Processing complete. Successful: {processed_count}, '
            f'Failed: {error_count}, Total: {processed_count + error_count}'
        )
        
        return processed_count


def setup_logging(log_level: int = logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('geocoding.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Geocode addresses to GPS coordinates with county information'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='CSV file containing addresses (format: link|name|address)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Path to output CSV file'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='Google Maps API key (overrides environment variable)'
    )
    parser.add_argument(
        '--delimiter',
        type=str,
        default='|',
        help='Input file delimiter (default: |)'
    )
    parser.add_argument(
        '--skip-header',
        action='store_true',
        help='Skip first row of input file'
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
        # Validate input file
        if not os.path.isfile(args.input):
            logger.error(f'Input file does not exist: {args.input}')
            return 1
        
        # Create resolver
        resolver = AddressResolver(api_key=args.api_key)
        
        # Process file
        count = resolver.process_file(
            input_file=args.input,
            output_file=args.output,
            delimiter=args.delimiter,
            skip_header=args.skip_header
        )
        
        logger.info(f'Successfully processed {count} addresses')
        return 0
        
    except ValueError as e:
        logger.error(f'Configuration error: {e}')
        return 1
    except FileNotFoundError as e:
        logger.error(f'File error: {e}')
        return 1
    except Exception as e:
        logger.error(f'Fatal error: {e}', exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())