"""
Publisher Import Script

This script helps you import your 12,500+ publishers into the database.
It handles batch processing for optimal performance.

Usage:
    1. Update the load_publishers_from_file() function to read your data source
    2. Run: python import_publishers_example.py
"""

import requests
import json
import csv
import time

API_URL = 'http://localhost:5001'
BATCH_SIZE = 1000  # Process 1000 publishers at a time

def load_publishers_from_csv(file_path):
    """
    Load publishers from CSV file.
    
    Expected CSV format:
    name,email,category,status
    Publisher 1,pub1@example.com,Technology,active
    Publisher 2,pub2@example.com,News,active
    """
    publishers = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            publishers.append({
                'name': row['name'],
                'email': row['email'],
                'category': row.get('category', ''),
                'status': row.get('status', 'active')
            })
    
    return publishers

def load_publishers_from_json(file_path):
    """
    Load publishers from JSON file.
    
    Expected JSON format:
    [
        {
            "name": "Publisher 1",
            "email": "pub1@example.com",
            "category": "Technology",
            "status": "active"
        },
        ...
    ]
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_publishers_from_excel(file_path):
    """
    Load publishers from Excel file.
    Requires: pip install openpyxl
    
    Expected Excel format: Same as CSV
    """
    import openpyxl
    
    publishers = []
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    
    # Assume first row is header
    headers = [cell.value for cell in sheet[1]]
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        publisher = {}
        for i, value in enumerate(row):
            publisher[headers[i]] = value
        
        publishers.append({
            'name': publisher['name'],
            'email': publisher['email'],
            'category': publisher.get('category', ''),
            'status': publisher.get('status', 'active')
        })
    
    return publishers

def import_publishers_in_batches(publishers, batch_size=BATCH_SIZE):
    """
    Import publishers to database in batches for optimal performance.
    
    Args:
        publishers: List of publisher dictionaries
        batch_size: Number of publishers per batch
    
    Returns:
        dict: Import statistics
    """
    total = len(publishers)
    imported = 0
    failed = 0
    
    print(f"Starting import of {total} publishers...")
    print(f"Using batch size: {batch_size}")
    print("-" * 50)
    
    for i in range(0, total, batch_size):
        batch = publishers[i:i+batch_size]
        batch_number = (i // batch_size) + 1
        
        try:
            response = requests.post(
                f'{API_URL}/api/publishers/bulk-import',
                json=batch,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                batch_imported = data.get('imported', 0)
                imported += batch_imported
                
                print(f"Batch {batch_number}: Imported {batch_imported}/{len(batch)} publishers")
            else:
                print(f"Batch {batch_number}: Failed - {response.status_code}")
                failed += len(batch)
                
        except Exception as e:
            print(f"Batch {batch_number}: Error - {str(e)}")
            failed += len(batch)
        
        # Small delay to avoid overwhelming server
        time.sleep(0.1)
    
    print("-" * 50)
    print(f"Import complete!")
    print(f"Total: {total}")
    print(f"Imported: {imported}")
    print(f"Failed: {failed}")
    
    return {
        'total': total,
        'imported': imported,
        'failed': failed
    }

def example_manual_data():
    """
    Example: Create publishers manually in Python.
    Use this if you have data in a database or API.
    """
    publishers = []
    
    # Example: Generate test data
    for i in range(1, 101):
        publishers.append({
            'name': f'Publisher {i}',
            'email': f'publisher{i}@example.com',
            'category': 'Technology',
            'status': 'active'
        })
    
    return publishers

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    print("Publisher Import Tool")
    print("=" * 50)
    
    # Choose your data source:
    
    # Option 1: Load from CSV
    # publishers = load_publishers_from_csv('publishers.csv')
    
    # Option 2: Load from JSON
    # publishers = load_publishers_from_json('publishers.json')
    
    # Option 3: Load from Excel
    # publishers = load_publishers_from_excel('publishers.xlsx')
    
    # Option 4: Manual data (example)
    publishers = example_manual_data()
    
    # Validate data
    if not publishers:
        print("Error: No publishers to import")
        exit(1)
    
    print(f"Loaded {len(publishers)} publishers")
    print("Sample data:")
    print(json.dumps(publishers[0], indent=2))
    print()
    
    # Confirm import
    response = input(f"Import {len(publishers)} publishers? (yes/no): ")
    if response.lower() != 'yes':
        print("Import cancelled")
        exit(0)
    
    # Import
    results = import_publishers_in_batches(publishers)
    
    # Summary
    print()
    print("Import Summary:")
    print(f"- Success rate: {(results['imported']/results['total']*100):.1f}%")
    
    if results['failed'] > 0:
        print(f"- {results['failed']} publishers failed to import")
        print("  Check if emails are duplicates or invalid")