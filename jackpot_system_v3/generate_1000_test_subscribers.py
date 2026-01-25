"""
Generate 1000 test BOOK3 subscribers for comprehensive system validation.
Creates diverse profiles with varied DOBs, locations, and preferences.
"""
import json
import random
from datetime import datetime, timedelta
import os

# 1000+ diverse birth locations for unique astrological profiles
BIRTH_LOCATIONS = [
    # Major Cities
    ("New York", "New York"), ("Los Angeles", "California"), ("Chicago", "Illinois"),
    ("Houston", "Texas"), ("Phoenix", "Arizona"), ("Philadelphia", "Pennsylvania"),
    ("San Antonio", "Texas"), ("San Diego", "California"), ("Dallas", "Texas"),
    ("San Jose", "California"), ("Austin", "Texas"), ("Jacksonville", "Florida"),
    ("Fort Worth", "Texas"), ("Columbus", "Ohio"), ("Charlotte", "North Carolina"),
    ("San Francisco", "California"), ("Indianapolis", "Indiana"), ("Seattle", "Washington"),
    ("Denver", "Colorado"), ("Washington", "District of Columbia"), ("Boston", "Massachusetts"),
    ("El Paso", "Texas"), ("Detroit", "Michigan"), ("Nashville", "Tennessee"),
    ("Portland", "Oregon"), ("Memphis", "Tennessee"), ("Oklahoma City", "Oklahoma"),
    ("Las Vegas", "Nevada"), ("Louisville", "Kentucky"), ("Baltimore", "Maryland"),
    ("Milwaukee", "Wisconsin"), ("Albuquerque", "New Mexico"), ("Tucson", "Arizona"),
    ("Fresno", "California"), ("Sacramento", "California"), ("Kansas City", "Missouri"),
    ("Long Beach", "California"), ("Mesa", "Arizona"), ("Atlanta", "Georgia"),
    ("Colorado Springs", "Colorado"), ("Virginia Beach", "Virginia"), ("Raleigh", "North Carolina"),
    ("Omaha", "Nebraska"), ("Miami", "Florida"), ("Oakland", "California"),
    ("Minneapolis", "Minnesota"), ("Tulsa", "Oklahoma"), ("Wichita", "Kansas"),
    ("New Orleans", "Louisiana"), ("Arlington", "Texas"), ("Tampa", "Florida"),
    ("Honolulu", "Hawaii"), ("Anaheim", "California"), ("Santa Ana", "California"),
    ("St. Louis", "Missouri"), ("Riverside", "California"), ("Corpus Christi", "Texas"),
    ("Lexington", "Kentucky"), ("Pittsburgh", "Pennsylvania"), ("Anchorage", "Alaska"),
    ("Stockton", "California"), ("Cincinnati", "Ohio"), ("St. Paul", "Minnesota"),
    ("Toledo", "Ohio"), ("Greensboro", "North Carolina"), ("Newark", "New Jersey"),
    ("Plano", "Texas"), ("Henderson", "Nevada"), ("Lincoln", "Nebraska"),
    ("Buffalo", "New York"), ("Jersey City", "New Jersey"), ("Chula Vista", "California"),
    ("Orlando", "Florida"), ("Norfolk", "Virginia"), ("Chandler", "Arizona"),
    ("Laredo", "Texas"), ("Madison", "Wisconsin"), ("Durham", "North Carolina"),
    ("Lubbock", "Texas"), ("Winston-Salem", "North Carolina"), ("Garland", "Texas"),
    ("Glendale", "Arizona"), ("Hialeah", "Florida"), ("Reno", "Nevada"),
    ("Baton Rouge", "Louisiana"), ("Irvine", "California"), ("Chesapeake", "Virginia"),
    ("Irving", "Texas"), ("Scottsdale", "Arizona"), ("North Las Vegas", "Nevada"),
    ("Fremont", "California"), ("Gilbert", "Arizona"), ("San Bernardino", "California"),
    ("Boise", "Idaho"), ("Birmingham", "Alabama")
]

# Generate additional locations to ensure 1000+ unique places
for state_abbr, state_name in [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"), 
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
    ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
    ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
    ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming")
]:
    # Add multiple cities per state to reach 1000+
    for i in range(1, 21):  # 20 cities per state = 1000 more locations
        BIRTH_LOCATIONS.append((f"{state_name} City {i}", state_name))

# Risk profiles for varied engine behavior
RISK_PROFILES = ["conservative", "balanced", "assertive", "aggressive"]

def generate_random_dob():
    """Generate random date of birth between 1950 and 2000."""
    start_date = datetime(1950, 1, 1)
    end_date = datetime(2000, 12, 31)
    
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    
    return start_date + timedelta(days=random_days)

def generate_unique_time(subscriber_id):
    """Generate unique birth time based on subscriber ID to avoid collisions."""
    # Distribute 1000 subscribers across 1440 minutes in a day (24*60)
    # This ensures no time collisions for 1000 subscribers
    total_minutes = subscriber_id * 1.44  # 1440/1000 = 1.44 minutes per subscriber
    
    hour = int(total_minutes // 60) % 24
    minute = int(total_minutes % 60)
    
    return f"{hour:02d}:{minute:02d}"

def get_unique_location(subscriber_id):
    """Get unique birth location based on subscriber ID."""
    # Cycle through locations ensuring uniqueness
    location_index = (subscriber_id - 1) % len(BIRTH_LOCATIONS)
    return BIRTH_LOCATIONS[location_index]

def generate_mmfsn_values(dob):
    """Generate MMFSN values based on birth date."""
    day = dob.day
    month = dob.month
    year = dob.year % 100
    
    # Cash3 combination from birth digits - ensure proper format with comma
    cash3_combo = f"{day % 10}{month % 10}{year % 10},"
    
    # MegaMillions main numbers (5 numbers from 1-70)
    mega_main = sorted(random.sample(range(1, 71), 5))
    mega_ball = [random.randint(1, 25), random.randint(1, 25)]
    
    # Powerball main numbers (5 numbers from 1-69)
    power_main = sorted(random.sample(range(1, 70), 5))
    power_ball = [random.randint(1, 26), random.randint(1, 26)]
    
    # Cash4Life main numbers (5 numbers from 1-60)
    cash4life_main = sorted(random.sample(range(1, 61), 5))
    cash_ball = [random.randint(1, 4)]
    
    return {
        "Cash3": {
            "type": "combination",
            "values": [cash3_combo]
        },
        "Cash4": {
            "type": "combination", 
            "values": []
        },
        "MegaMillions": {
            "type": "ball-set",
            "main": mega_main,
            "mega_ball": mega_ball
        },
        "Powerball": {
            "type": "ball-set", 
            "main": power_main,
            "power_ball": power_ball
        },
        "Cash4Life": {
            "type": "ball-set",
            "main": cash4life_main,
            "cash_ball": cash_ball
        }
    }

def create_test_subscriber(subscriber_id):
    """Create a single test subscriber with unique profile."""
    dob = generate_random_dob()
    birth_time = generate_unique_time(subscriber_id)  # Unique time
    city, state = get_unique_location(subscriber_id)  # Unique location
    risk_profile = random.choice(RISK_PROFILES)
    
    # Create first/last names
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
                   "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
                   "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
                   "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna"]
    
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
                  "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
                  "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young"]
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    
    subscriber = {
        "subscriber_id": f"TEST{subscriber_id:04d}",
        "kit_type": "BOOK3",
        "dob": dob.strftime("%Y-%m-%d"),
        "coverage_start": "2025-01-01",  # Historical validation period start
        "coverage_end": "2025-11-10",    # Historical validation period end
        "formats": ["JSON"],
        "identity": {
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": dob.strftime("%Y-%m-%d"),
            "birth_time": birth_time,
            "birth_city": city,
            "birth_state": state
        },
        "preferences": {
            "games": ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"],
            "risk_profile": risk_profile
        },
        "engine_profile": {
            "mmfsn": generate_mmfsn_values(dob),
            "numerology": {
                "life_path_required": True,
                "personal_day_required": True
            },
            "astrology": {
                "requires_birth_time": True,
                "requires_location": True
            }
        },
        "meta": {
            "version": "v3.7",
            "created_at": "2025-12-20",
            "test_batch": "1000_validation"
        }
    }
    
    return subscriber

def main():
    """Generate 1000 test subscribers."""
    print("Generating 1000 test BOOK3 subscribers...")
    
    # Create test directory
    test_dir = "data/subscribers/TEST_BOOK3"
    os.makedirs(test_dir, exist_ok=True)
    
    # Generate subscribers
    for i in range(1, 1001):
        subscriber = create_test_subscriber(i)
        filename = f"{test_dir}/TEST{i:04d}_BOOK3.json"
        
        with open(filename, 'w') as f:
            json.dump(subscriber, f, indent=2)
        
        if i % 100 == 0:
            print(f"Generated {i} subscribers...")
    
    print("✅ Successfully generated 1000 test subscribers in data/subscribers/TEST_BOOK3/")
    
    # Create summary
    summary = {
        "total_subscribers": 1000,
        "kit_type": "BOOK3",
        "coverage_period": "2025-01-01 to 2025-11-10",  # Historical validation period
        "birth_year_range": "1950-2000",
        "locations_count": len(BIRTH_LOCATIONS),
        "risk_profiles": RISK_PROFILES,
        "generated_at": datetime.now().isoformat(),
        "files_location": "data/subscribers/TEST_BOOK3/",
        "target_games": ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"],
        "validation_note": "Generated for backtesting against historical results Jan-Nov 2025"
    }
    
    with open("test_1000_subscribers_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("📋 Summary saved to test_1000_subscribers_summary.json")

if __name__ == "__main__":
    main()