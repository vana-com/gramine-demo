import json
import sys

def validate_browsing_session(session):
    # Simple metrics for a valuable session
    MIN_DURATION = 60  # 1 minute in seconds
    MIN_PAGES = 3
    VALUABLE_KEYWORDS = {'buy', 'cart', 'checkout'}

    duration = session.get('duration', 0)
    pages = session.get('pages', [])
    
    is_valuable = (
        duration >= MIN_DURATION and
        len(pages) >= MIN_PAGES and
        any(kw in ' '.join(pages).lower() for kw in VALUABLE_KEYWORDS)
    )

    return is_valuable

if __name__ == "__main__":
    session_data = json.load(sys.stdin)
    is_valid = validate_browsing_session(session_data)
    print(json.dumps({"is_valid": is_valid}))
