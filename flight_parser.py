
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


class FlightParser:
    """Main flight parser class that handles CSV parsing, validation, and querying."""
    
    DATE_FORMAT = "%Y-%m-%d %H:%M"
    
    def __init__(self):
        self.valid_flights = []
        self.errors = []
        
    def validate_flight_id(self, flight_id):
        """Validate flight_id: 2-8 alphanumeric characters"""
        return bool(re.match(r'^[A-Za-z0-9]{2,8}$', flight_id))
    
    def validate_airport_code(self, code):
        """Validate airport code: 3 uppercase letters"""
        return bool(re.match(r'^[A-Z]{3}$', code))
    
    def validate_datetime(self, datetime_str):
        """Validate datetime format: YYYY-MM-DD HH:MM"""
        try:
            datetime.strptime(datetime_str, self.DATE_FORMAT)
            return True
        except ValueError:
            return False
    
    def validate_price(self, price_str):
        """Validate price: positive float number"""
        try:
            price = float(price_str)
            return price > 0
        except ValueError:
            return False
    
    def validate_times(self, departure_str, arrival_str):
        """Validate that arrival is after departure"""
        try:
            departure = datetime.strptime(departure_str, self.DATE_FORMAT)
            arrival = datetime.strptime(arrival_str, self.DATE_FORMAT)
            return arrival > departure
        except ValueError:
            return False
    
    def parse_flight_record(self, record, line_number, filename):
        """
        Parse and validate a single flight record
        Returns: (is_valid, flight_data, error_messages)
        """
        errors = []
        
        # Check for correct number of fields
        if len(record) != 6:
            if len(record) < 6:
                errors.append("missing required fields")
            else:
                errors.append("extra fields")
            return False, None, errors
        
        flight_id, origin, destination, departure_dt, arrival_dt, price = record
        
        # Strip whitespace from all fields
        flight_id = flight_id.strip()
        origin = origin.strip()
        destination = destination.strip()
        departure_dt = departure_dt.strip()
        arrival_dt = arrival_dt.strip()
        price = price.strip()
        
        # Validate individual fields
        if not flight_id:
            errors.append("missing flight_id")
        elif not self.validate_flight_id(flight_id):
            if len(flight_id) < 2:
                errors.append("flight_id too short (less than 2 characters)")
            elif len(flight_id) > 8:
                errors.append("flight_id too long (more than 8 characters)")
            else:
                errors.append("flight_id must be alphanumeric")
        
        if not origin:
            errors.append("missing origin")
        elif not self.validate_airport_code(origin):
            errors.append("invalid origin code")
        
        if not destination:
            errors.append("missing destination")
        elif not self.validate_airport_code(destination):
            errors.append("invalid destination code")
        
        if not departure_dt:
            errors.append("missing departure_datetime")
        elif not self.validate_datetime(departure_dt):
            errors.append("invalid departure datetime")
        
        if not arrival_dt:
            errors.append("missing arrival_datetime")
        elif not self.validate_datetime(arrival_dt):
            errors.append("invalid arrival datetime")
        elif (self.validate_datetime(departure_dt) and 
              self.validate_datetime(arrival_dt) and 
              not self.validate_times(departure_dt, arrival_dt)):
            errors.append("arrival before departure")
        
        if not price:
            errors.append("missing price")
        elif not self.validate_price(price):
            try:
                price_val = float(price)
                if price_val <= 0:
                    errors.append("price must be positive")
                else:
                    errors.append("invalid price format")
            except ValueError:
                errors.append("invalid price format")
        
        # If any errors, return invalid
        if errors:
            return False, None, errors
        
        # Create valid flight data
        flight_data = {
            'flight_id': flight_id,
            'origin': origin,
            'destination': destination,
            'departure_datetime': departure_dt,
            'arrival_datetime': arrival_dt,
            'price': round(float(price), 2)
        }
        
        return True, flight_data, []
    
    def parse_csv_file(self, file_path):
        """Parse a single CSV file and separate valid/invalid records"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                line_number = 0
                
                for row in reader:
                    line_number += 1
                    
                    # Skip empty lines
                    if not row:
                        continue
                    
                    # Skip comment lines (lines starting with #)
                    if row[0].strip().startswith('#'):
                        self.errors.append({
                            'file': file_path,
                            'line_number': line_number,
                            'raw_line': ','.join(row),
                            'error': 'comment line, ignored for data parsing'
                        })
                        continue
                    
                    # Skip header row if it matches expected fields
                    if (line_number == 1 and 
                        len(row) >= 6 and 
                        row[0].lower() == 'flight_id' and 
                        row[1].lower() == 'origin'):
                        continue
                    
                    # Validate the record
                    is_valid, flight_data, errors = self.parse_flight_record(
                        row, line_number, file_path
                    )
                    
                    if is_valid:
                        self.valid_flights.append(flight_data)
                    else:
                        self.errors.append({
                            'file': file_path,
                            'line_number': line_number,
                            'raw_line': ','.join(row),
                            'error': '; '.join(errors)
                        })
                        
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            sys.exit(1)
    
    def parse_csv_folder(self, folder_path):
        """Parse all CSV files in a folder"""
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"Error: Folder {folder_path} does not exist")
            sys.exit(1)
            
        csv_files = list(folder.glob("*.csv"))
        
        if not csv_files:
            print(f"No CSV files found in {folder_path}")
            return
        
        for csv_file in sorted(csv_files):
            print(f"Parsing {csv_file}...")
            self.parse_csv_file(csv_file)
    
    def export_valid_flights(self, output_path):
        """Export valid flights to JSON file"""
        if not self.valid_flights:
            print("No valid flights to export")
            return
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.valid_flights, f, indent=2)
        print(f"Exported {len(self.valid_flights)} valid flights to {output_path}")
    
    def export_errors(self, output_path="errors.txt"):
        """Export error information to text file"""
        if not self.errors:
            print("No errors to export")
            return
            
        with open(output_path, 'w', encoding='utf-8') as f:
            for error in self.errors:
                line_content = error['raw_line']
                # Handle comment lines specially
                if 'comment line' in error['error']:
                    f.write(f"Line {error['line_number']}: {line_content} → comment line, ignored for data parsing\n")
                else:
                    f.write(f"Line {error['line_number']}: {line_content} → {error['error']}\n")
        print(f"Exported {len(self.errors)} errors to {output_path}")
    
    def load_json_database(self, json_path):
        """Load existing JSON database"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise ValueError("JSON database should be an array of flight objects")
            
            # Basic validation of loaded data
            validated_flights = []
            for i, flight in enumerate(data):
                try:
                    # Check required fields
                    required_fields = ['flight_id', 'origin', 'destination', 
                                     'departure_datetime', 'arrival_datetime', 'price']
                    for field in required_fields:
                        if field not in flight:
                            raise ValueError(f"Missing field: {field}")
                    
                    # Validate field formats
                    if not self.validate_flight_id(str(flight['flight_id'])):
                        raise ValueError("Invalid flight_id")
                    
                    if not self.validate_airport_code(str(flight['origin'])):
                        raise ValueError("Invalid origin code")
                    
                    if not self.validate_airport_code(str(flight['destination'])):
                        raise ValueError("Invalid destination code")
                    
                    if not self.validate_datetime(str(flight['departure_datetime'])):
                        raise ValueError("Invalid departure datetime")
                    
                    if not self.validate_datetime(str(flight['arrival_datetime'])):
                        raise ValueError("Invalid arrival datetime")
                    
                    if not self.validate_times(str(flight['departure_datetime']), str(flight['arrival_datetime'])):
                        raise ValueError("Arrival before departure")
                    
                    price = float(flight['price'])
                    if price <= 0:
                        raise ValueError("Price must be positive")
                    
                    # Add to valid flights
                    validated_flights.append({
                        'flight_id': str(flight['flight_id']),
                        'origin': str(flight['origin']),
                        'destination': str(flight['destination']),
                        'departure_datetime': str(flight['departure_datetime']),
                        'arrival_datetime': str(flight['arrival_datetime']),
                        'price': round(price, 2)
                    })
                    
                except Exception as e:
                    print(f"Warning: Skipping invalid flight at index {i}: {e}")
            
            self.valid_flights = validated_flights
            print(f"Loaded {len(self.valid_flights)} valid flights from {json_path}")
            
        except Exception as e:
            print(f"Error loading JSON database: {e}")
            sys.exit(1)
    
    def execute_query(self, query):
        """Execute a single query on flights"""
        matches = []
        
        for flight in self.valid_flights:
            match = True
            
            for field, value in query.items():
                if field == 'flight_id':
                    if flight.get('flight_id') != value:
                        match = False
                        break
                
                elif field == 'origin':
                    if flight.get('origin') != value:
                        match = False
                        break
                
                elif field == 'destination':
                    if flight.get('destination') != value:
                        match = False
                        break
                
                elif field == 'departure_datetime':
                    flight_dt = datetime.strptime(flight['departure_datetime'], self.DATE_FORMAT)
                    query_dt = datetime.strptime(value, self.DATE_FORMAT)
                    if flight_dt < query_dt:
                        match = False
                        break
                
                elif field == 'arrival_datetime':
                    flight_dt = datetime.strptime(flight['arrival_datetime'], self.DATE_FORMAT)
                    query_dt = datetime.strptime(value, self.DATE_FORMAT)
                    if flight_dt > query_dt:
                        match = False
                        break
                
                elif field == 'price':
                    try:
                        query_price = float(value)
                        if flight.get('price') > query_price:
                            match = False
                            break
                    except ValueError:
                        match = False
                        break
            
            if match:
                matches.append(flight)
        
        return matches
    
    def execute_queries_from_file(self, query_file_path):
        """Execute queries from JSON file"""
        try:
            with open(query_file_path, 'r', encoding='utf-8') as f:
                queries_data = json.load(f)
            
            # Handle both single query object and array of queries
            if isinstance(queries_data, dict):
                queries = [queries_data]
            elif isinstance(queries_data, list):
                queries = queries_data
            else:
                raise ValueError("Query file should contain an object or array of objects")
            
            results = []
            for query in queries:
                matches = self.execute_query(query)
                results.append({
                    "query": query,
                    "matches": matches
                })
            
            return results
            
        except Exception as e:
            print(f"Error executing queries: {e}")
            sys.exit(1)
    
    def save_query_results(self, results, student_id, first_name, last_name):
        """Save query results with timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"response_{student_id}_{first_name}_{last_name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"Query results saved to {filename}")
        return filename


def main():
    """Main function to handle command-line arguments and coordinate parsing"""
    parser = argparse.ArgumentParser(
        description='Parse flight schedule CSV files, validate records, and execute queries'
    )
    
    # Input source arguments (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        '-i', '--input',
        help='Parse a single CSV file'
    )
    input_group.add_argument(
        '-d', '--directory',
        help='Parse all .csv files in a folder and combine results'
    )
    input_group.add_argument(
        '-j', '--json',
        help='Load existing JSON database instead of parsing CSVs'
    )
    
    # Output and query arguments
    parser.add_argument(
        '-o', '--output',
        default='db.json',
        help='Optional custom output path for valid flights JSON (default: db.json)'
    )
    parser.add_argument(
        '-q', '--query',
        help='Execute queries defined in a JSON file on the loaded database'
    )
    
    # Student information for output filename
    parser.add_argument(
        '--student-id',
        default='241ADB029',
        help='Student ID for output filename'
    )
    parser.add_argument(
        '--first-name',
        default='Nandana',
        help='First name for output filename'
    )
    parser.add_argument(
        '--last-name', 
        default='Subhash',
        help='Last name for output filename'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.input, args.directory, args.json]):
        print("Error: Please provide an input source (-i, -d, or -j)")
        parser.print_help()
        sys.exit(1)
    
    # Create parser instance
    flight_parser = FlightParser()
    
    # Load data from appropriate source
    if args.json:
        # Load existing JSON database
        print(f"Loading existing database from {args.json}")
        flight_parser.load_json_database(args.json)
        
    elif args.input or args.directory:
        # Parse CSV files
        if args.input:
            print(f"Parsing CSV file: {args.input}")
            flight_parser.parse_csv_file(args.input)
        elif args.directory:
            print(f"Parsing CSV folder: {args.directory}")
            flight_parser.parse_csv_folder(args.directory)
        
        # Export results
        flight_parser.export_valid_flights(args.output)
        flight_parser.export_errors()
        
    # Execute queries if requested
    if args.query:
        print(f"Executing queries from: {args.query}")
        results = flight_parser.execute_queries_from_file(args.query)
        flight_parser.save_query_results(
            results, 
            args.student_id, 
            args.first_name, 
            args.last_name
        )
        
        # Print query summary
        print("\nQuery Results Summary:")
        for i, result in enumerate(results):
            print(f"  Query {i+1}: {len(result['matches'])} matches")
    
    print("\nFlight parsing completed successfully!")


if __name__ == "__main__":
    main()
