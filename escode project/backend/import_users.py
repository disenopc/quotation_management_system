"""
Import users from JSON file
Usage: python import_users.py
"""

import json
from models import User

def import_users_from_json(json_file_path='users.json'):
    """
    Import users from JSON file.
    
    Args:
        json_file_path: Path to JSON file (default: users.json)
    
    Returns:
        dict: Statistics of import
    """
    imported = 0
    skipped = 0
    failed = 0
    errors = []
    
    print(f"Reading users from: {json_file_path}")
    print("=" * 60)
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        print(f"Found {len(users_data)} users in file\n")
        
        for user_data in users_data:
            try:
                username = user_data['username']
                
                # Check if user already exists
                existing = User.get_by_username(username)
                if existing:
                    print(f"⚠️  User '{username}' already exists, skipping...")
                    skipped += 1
                    continue
                
                # Create user
                user_id = User.create(
                    username=user_data['username'],
                    password=user_data['password'],
                    full_name=user_data['full_name'],
                    email=user_data['email']
                )
                
                print(f"✓ Created user: {username} (ID: {user_id})")
                print(f"  Name: {user_data['full_name']}")
                print(f"  Email: {user_data['email']}")
                print(f"  Password: {user_data['password']}")
                print()
                
                imported += 1
                
            except KeyError as e:
                error_msg = f"Missing field: {str(e)}"
                print(f"✗ Error with user: {error_msg}")
                failed += 1
                errors.append({
                    'username': user_data.get('username', 'unknown'),
                    'error': error_msg
                })
            except Exception as e:
                error_msg = str(e)
                print(f"✗ Error creating user '{user_data.get('username', 'unknown')}': {error_msg}")
                failed += 1
                errors.append({
                    'username': user_data.get('username', 'unknown'),
                    'error': error_msg
                })
        
    except FileNotFoundError:
        print(f" Error: File '{json_file_path}' not found")
        print("Make sure the file exists in the backend directory")
        return None
    except json.JSONDecodeError as e:
        print(f" Error: Invalid JSON format - {str(e)}")
        return None
    except Exception as e:
        print(f" Error reading file: {str(e)}")
        return None
    
    print("=" * 60)
    print("Import Summary:")
    print(f"  ✓ Imported: {imported}")
    print(f"    Skipped: {skipped}")
    print(f"  ✗ Failed: {failed}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error['username']}: {error['error']}")
    
    print("\nYou can now login with any of these users!")
    print("=" * 60)
    
    return {
        'imported': imported,
        'skipped': skipped,
        'failed': failed,
        'errors': errors
    }

if __name__ == '__main__':
    import sys
    
    # Allow custom file path as argument
    json_file = sys.argv[1] if len(sys.argv) > 1 else 'users.json'
    
    print("User Import Tool")
    print("=" * 60)
    
    result = import_users_from_json(json_file)
    
    if result is None:
        print("\n Import failed!")
        sys.exit(1)
    elif result['imported'] > 0:
        print("\n✓ Import successful!")
        sys.exit(0)
    else:
        print("\n No new users were imported")
        sys.exit(0)