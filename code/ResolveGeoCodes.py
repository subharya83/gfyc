import argparse
import csv
import googlemaps as gm
import logging
import os


class AddressResolver:
    def __init__(self):
        API_KEY = "AIzaSyCUfXqvurEH_EMMahJUoajN1tkR4HCdUDk"
        self.loc = gm.Client(key=API_KEY)

    def getinfo(self, input_file=None, output_file=None):
        _output_file = open(output_file, mode='w')
        _row_writer = csv.writer(_output_file, delimiter=',', quotechar='"')

        with open(input_file, 'r') as _input_file:
            _row_reader = csv.reader(_input_file, delimiter='|')
            _row_count = 1
            for row in _row_reader:
                address_str = row[2]
                if address_str:
                    try:
                        gcres = self.loc.geocode(address_str)
                        lt = gcres[0]['geometry']['location']['lat']
                        lg = gcres[0]['geometry']['location']['lng']
                        tp = gcres[0]['types']
                        # Parse state and county
                        for _item in gcres[0]['address_components']:
                            _res = [s for s in _item['types'] if "administrative_area_level_2" in s]
                            if any(_res):
                                county = _item['long_name']
                            _res = [s for s in _item['types'] if "administrative_area_level_1" in s]
                            if any(_res):
                                state = _item['long_name']
                        refined_address = gcres[0]['formatted_address']
                        # Attraction Name, Attraction Address, Latitude, Longitude, Type of Address, County, State, Link
                        _row_str = [row[1], refined_address, lt, lg, tp, county, state, row[0]]
                        logging.info('Writing: %s' % _row_str)
                        _row_writer.writerow(_row_str)
                    except:
                        logging.info('Could not find details for %s' % address_str)
                else:
                    logging.info('Invalid address for row %d in file %s' %(_row_count, input_file))
                _row_count += 1
        _output_file.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Address to GPS coordinates, county info')
    parser.add_argument('-i', type=str, required=True, help='csv file containing addresses (one per line)')
    parser.add_argument('-o', type=str, required=True, help='Path to output csv file')

    args = parser.parse_args()
    ar = AddressResolver()
    if os.path.isfile(args.i):
        ar.getinfo(input_file=args.i, output_file=args.o)
    else:
        logging.error('Invalid input file path %s ' % args.i)
