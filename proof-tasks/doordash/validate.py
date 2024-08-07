import json
import sys

def validate_doordash_profile(profile):
    required_fields = ['id', 'name', 'email', 'phone']
    return all(field in profile for field in required_fields)

if __name__ == "__main__":
    profile_data = json.load(sys.stdin)
    is_valid = validate_doordash_profile(profile_data)
    print(json.dumps({"is_valid": is_valid}))
