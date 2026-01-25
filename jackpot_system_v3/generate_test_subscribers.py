#!/usr/bin/env python3
"""
BOOK3 TEST SUBSCRIBER GENERATOR v3.7
Generate 2000 BOOK3 subscribers with random TOBs and US locations
"""

import os
import sys
import json
import random
from datetime import datetime, date

# Set up project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# US Cities and States for realistic birth locations
US_LOCATIONS = [
    ("Atlanta", "Georgia"), ("Chicago", "Illinois"), ("Houston", "Texas"),
    ("Phoenix", "Arizona"), ("Philadelphia", "Pennsylvania"), ("San Antonio", "Texas"),
    ("San Diego", "California"), ("Dallas", "Texas"), ("San Jose", "California"),
    ("Austin", "Texas"), ("Jacksonville", "Florida"), ("Fort Worth", "Texas"),
    ("Columbus", "Ohio"), ("Charlotte", "North Carolina"), ("San Francisco", "California"),
    ("Indianapolis", "Indiana"), ("Seattle", "Washington"), ("Denver", "Colorado"),
    ("Boston", "Massachusetts"), ("El Paso", "Texas"), ("Detroit", "Michigan"),
    ("Nashville", "Tennessee"), ("Portland", "Oregon"), ("Memphis", "Tennessee"),
    ("Oklahoma City", "Oklahoma"), ("Las Vegas", "Nevada"), ("Louisville", "Kentucky"),
    ("Baltimore", "Maryland"), ("Milwaukee", "Wisconsin"), ("Albuquerque", "New Mexico"),
    ("Tucson", "Arizona"), ("Fresno", "California"), ("Sacramento", "California"),
    ("Kansas City", "Missouri"), ("Long Beach", "California"), ("Mesa", "Arizona"),
    ("Virginia Beach", "Virginia"), ("Atlanta", "Georgia"), ("Colorado Springs", "Colorado"),
    ("Raleigh", "North Carolina"), ("Omaha", "Nebraska"), ("Miami", "Florida"),
    ("Oakland", "California"), ("Minneapolis", "Minnesota"), ("Tulsa", "Oklahoma"),
    ("Cleveland", "Ohio"), ("Wichita", "Kansas"), ("Arlington", "Texas"),
    ("New Orleans", "Louisiana"), ("Bakersfield", "California"), ("Tampa", "Florida"),
    ("Honolulu", "Hawaii"), ("Aurora", "Colorado"), ("Anaheim", "California"),
    ("Santa Ana", "California"), ("St. Louis", "Missouri"), ("Riverside", "California"),
    ("Corpus Christi", "Texas"), ("Lexington", "Kentucky"), ("Pittsburgh", "Pennsylvania"),
    ("Anchorage", "Alaska"), ("Stockton", "California"), ("Cincinnati", "Ohio"),
    ("St. Paul", "Minnesota"), ("Toledo", "Ohio"), ("Greensboro", "North Carolina"),
    ("Newark", "New Jersey"), ("Plano", "Texas"), ("Henderson", "Nevada"),
    ("Lincoln", "Nebraska"), ("Buffalo", "New York"), ("Jersey City", "New Jersey"),
    ("Chula Vista", "California"), ("Fort Wayne", "Indiana"), ("Orlando", "Florida"),
    ("St. Petersburg", "Florida"), ("Chandler", "Arizona"), ("Laredo", "Texas"),
    ("Norfolk", "Virginia"), ("Durham", "North Carolina"), ("Madison", "Wisconsin"),
    ("Lubbock", "Texas"), ("Irvine", "California"), ("Winston-Salem", "North Carolina"),
    ("Glendale", "Arizona"), ("Garland", "Texas"), ("Hialeah", "Florida"),
    ("Reno", "Nevada"), ("Chesapeake", "Virginia"), ("Gilbert", "Arizona"),
    ("Baton Rouge", "Louisiana"), ("Irving", "Texas"), ("Scottsdale", "Arizona"),
    ("North Las Vegas", "Nevada"), ("Fremont", "California"), ("Boise", "Idaho"),
    ("Richmond", "Virginia"), ("San Bernardino", "California"), ("Birmingham", "Alabama"),
    ("Spokane", "Washington"), ("Rochester", "New York"), ("Des Moines", "Iowa"),
    ("Modesto", "California"), ("Fayetteville", "North Carolina"), ("Tacoma", "Washington"),
    ("Oxnard", "California"), ("Fontana", "California"), ("Columbus", "Georgia"),
    ("Montgomery", "Alabama"), ("Moreno Valley", "California"), ("Shreveport", "Louisiana"),
    ("Aurora", "Illinois"), ("Yonkers", "New York"), ("Akron", "Ohio"),
    ("Huntington Beach", "California"), ("Little Rock", "Arkansas"), ("Augusta", "Georgia"),
    ("Amarillo", "Texas"), ("Glendale", "California"), ("Mobile", "Alabama"),
    ("Grand Rapids", "Michigan"), ("Salt Lake City", "Utah"), ("Tallahassee", "Florida"),
    ("Huntsville", "Alabama"), ("Grand Prairie", "Texas"), ("Knoxville", "Tennessee"),
    ("Worcester", "Massachusetts"), ("Newport News", "Virginia"), ("Brownsville", "Texas"),
    ("Overland Park", "Kansas"), ("Santa Clarita", "California"), ("Providence", "Rhode Island"),
    ("Garden Grove", "California"), ("Chattanooga", "Tennessee"), ("Oceanside", "California"),
    ("Jackson", "Mississippi"), ("Fort Lauderdale", "Florida"), ("Santa Rosa", "California"),
    ("Rancho Cucamonga", "California"), ("Port St. Lucie", "Florida"), ("Tempe", "Arizona"),
    ("Ontario", "California"), ("Vancouver", "Washington"), ("Cape Coral", "Florida"),
    ("Sioux Falls", "South Dakota"), ("Springfield", "Missouri"), ("Peoria", "Arizona"),
    ("Pembroke Pines", "Florida"), ("Elk Grove", "California"), ("Salem", "Oregon"),
    ("Lancaster", "California"), ("Corona", "California"), ("Eugene", "Oregon"),
    ("Palmdale", "California"), ("Salinas", "California"), ("Springfield", "Massachusetts"),
    ("Pasadena", "California"), ("Fort Collins", "Colorado"), ("Hayward", "California"),
    ("Pomona", "California"), ("Cary", "North Carolina"), ("Rockford", "Illinois"),
    ("Alexandria", "Virginia"), ("Escondido", "California"), ("McKinney", "Texas"),
    ("Kansas City", "Kansas"), ("Joliet", "Illinois"), ("Sunnyvale", "California"),
    ("Torrance", "California"), ("Bridgeport", "Connecticut"), ("Lakewood", "Colorado"),
    ("Hollywood", "Florida"), ("Paterson", "New Jersey"), ("Naperville", "Illinois"),
    ("Syracuse", "New York"), ("Mesquite", "Texas"), ("Dayton", "Ohio"),
    ("Savannah", "Georgia"), ("Clarksville", "Tennessee"), ("Orange", "California"),
    ("Pasadena", "Texas"), ("Fullerton", "California"), ("Killeen", "Texas"),
    ("Frisco", "Texas"), ("Hampton", "Virginia"), ("McAllen", "Texas"),
    ("Warren", "Michigan"), ("Bellevue", "Washington"), ("West Valley City", "Utah"),
    ("Columbia", "Missouri"), ("Olathe", "Kansas"), ("Sterling Heights", "Michigan"),
    ("New Haven", "Connecticut"), ("Miramar", "Florida"), ("Waco", "Texas"),
    ("Thousand Oaks", "California"), ("Cedar Rapids", "Iowa"), ("Charleston", "South Carolina"),
    ("Visalia", "California"), ("Topeka", "Kansas"), ("Elizabeth", "New Jersey"),
    ("Gainesville", "Florida"), ("Thornton", "Colorado"), ("Roseville", "California"),
    ("Carrollton", "Texas"), ("Coral Springs", "Florida"), ("Stamford", "Connecticut"),
    ("Simi Valley", "California"), ("Concord", "California"), ("Hartford", "Connecticut"),
    ("Kent", "Washington"), ("Lafayette", "Louisiana"), ("Midland", "Texas"),
    ("Surprise", "Arizona"), ("Denton", "Texas"), ("Victorville", "California"),
    ("Evansville", "Indiana"), ("Santa Clara", "California"), ("Abilene", "Texas"),
    ("Athens", "Georgia"), ("Vallejo", "California"), ("Allentown", "Pennsylvania"),
    ("Norman", "Oklahoma"), ("Beaumont", "Texas"), ("Independence", "Missouri"),
    ("Murfreesboro", "Tennessee"), ("Ann Arbor", "Michigan"), ("Springfield", "Illinois"),
    ("Berkeley", "California"), ("Peoria", "Illinois"), ("Provo", "Utah"),
    ("El Monte", "California"), ("Columbia", "South Carolina"), ("Lansing", "Michigan"),
    ("Fargo", "North Dakota"), ("Downey", "California"), ("Costa Mesa", "California"),
    ("Wilmington", "North Carolina"), ("Arvada", "Colorado"), ("Inglewood", "California"),
    ("Miami Gardens", "Florida"), ("Carlsbad", "California"), ("Westminster", "Colorado"),
    ("Rochester", "Minnesota"), ("Odessa", "Texas"), ("Manchester", "New Hampshire"),
    ("Elgin", "Illinois"), ("West Jordan", "Utah"), ("Round Rock", "Texas"),
    ("Clearwater", "Florida"), ("Waterbury", "Connecticut"), ("Gresham", "Oregon"),
    ("Fairfield", "California"), ("Billings", "Montana"), ("Lowell", "Massachusetts"),
    ("San Buenaventura", "California"), ("Pueblo", "Colorado"), ("High Point", "North Carolina"),
    ("West Covina", "California"), ("Richmond", "California"), ("Murrieta", "California"),
    ("Cambridge", "Massachusetts"), ("Antioch", "California"), ("Temecula", "California"),
    ("Norwalk", "California"), ("Centennial", "Colorado"), ("Everett", "Washington"),
    ("Palm Bay", "Florida"), ("Wichita Falls", "Texas"), ("Green Bay", "Wisconsin"),
    ("Daly City", "California"), ("Burbank", "California"), ("Richardson", "Texas"),
    ("Pompano Beach", "Florida"), ("North Charleston", "South Carolina"), ("Broken Arrow", "Oklahoma"),
    ("Boulder", "Colorado"), ("West Palm Beach", "Florida"), ("Santa Maria", "California"),
    ("El Cajon", "California"), ("Davenport", "Iowa"), ("Rialto", "California"),
    ("Las Cruces", "New Mexico"), ("San Mateo", "California"), ("Lewisville", "Texas"),
    ("South Bend", "Indiana"), ("Lakeland", "Florida"), ("Erie", "Pennsylvania"),
    ("Tyler", "Texas"), ("Pearland", "Texas"), ("College Station", "Texas"),
    ("Kenosha", "Wisconsin"), ("Sandy Springs", "Georgia"), ("Clovis", "California"),
    ("Flint", "Michigan"), ("Columbia", "Maryland"), ("Edison", "New Jersey"),
    ("Orem", "Utah"), ("Meridian", "Idaho"), ("Garden Grove", "California"),
    ("Woodbury", "Minnesota"), ("Fort Smith", "Arkansas"), ("Maple Grove", "Minnesota"),
    ("Pembroke Pines", "Florida"), ("Brooklyn Park", "Minnesota")
]

# Common first names for variety
FIRST_NAMES = [
    "James", "Robert", "John", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
    "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George",
    "Timothy", "Ronald", "Jason", "Edward", "Jeffrey", "Ryan", "Jacob", "Gary",
    "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott", "Brandon",
    "Benjamin", "Samuel", "Gregory", "Alexander", "Patrick", "Frank", "Raymond", "Jack",
    "Dennis", "Jerry", "Tyler", "Aaron", "Jose", "Henry", "Adam", "Douglas",
    "Nathan", "Peter", "Zachary", "Kyle", "Noah", "Alan", "Ethan", "Jeremy",
    "Lionel", "Arthur", "Wayne", "Eugene", "Sean", "Christian", "Austin", "Noah",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica",
    "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Helen", "Sandra", "Donna",
    "Carol", "Ruth", "Sharon", "Michelle", "Laura", "Sarah", "Kimberly", "Deborah",
    "Dorothy", "Lisa", "Nancy", "Karen", "Betty", "Helen", "Sandra", "Donna",
    "Carol", "Ruth", "Sharon", "Michelle", "Laura", "Emily", "Kimberly", "Deborah",
    "Amy", "Angela", "Ashley", "Brenda", "Emma", "Olivia", "Cynthia", "Marie",
    "Janet", "Catherine", "Frances", "Christine", "Samantha", "Debra", "Rachel", "Carolyn",
    "Janet", "Virginia", "Maria", "Heather", "Diane", "Julie", "Joyce", "Victoria",
    "Christina", "Joan", "Evelyn", "Lauren", "Judith", "Megan", "Andrea", "Cheryl",
    "Hannah", "Jacqueline", "Martha", "Gloria", "Teresa", "Sara", "Janice", "Marie",
    "Julia", "Heather", "Diane", "Ruth", "Julie", "Joyce", "Virginia", "Victoria"
]

# Common last names for variety
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
    "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers",
    "Long", "Ross", "Foster", "Jimenez", "Powell", "Jenkins", "Perry", "Russell",
    "Sullivan", "Bell", "Coleman", "Butler", "Henderson", "Barnes", "Gonzales", "Fisher",
    "Vasquez", "Simmons", "Romero", "Jordan", "Patterson", "Alexander", "Hamilton", "Graham",
    "Reynolds", "Griffin", "Wallace", "Moreno", "West", "Cole", "Hayes", "Bryant"
]

def generate_random_birth_date():
    """Generate random birth date between 1960-2005"""
    year = random.randint(1960, 2005)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Safe day range for all months
    return f"{year:04d}-{month:02d}-{day:02d}"

def generate_random_birth_time():
    """Generate random birth time in HH:MM format"""
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"

def generate_mmfsn_values():
    """Generate realistic MMFSN values for each game"""
    mmfsn = {
        "Cash3": {
            "type": "combination",
            "values": []
        },
        "Cash4": {
            "type": "combination", 
            "values": []
        },
        "MegaMillions": {
            "type": "ball-set",
            "main": sorted(random.sample(range(1, 71), 5)),
            "mega_ball": [random.randint(1, 25)]
        },
        "Powerball": {
            "type": "ball-set",
            "main": sorted(random.sample(range(1, 70), 5)),
            "power_ball": [random.randint(1, 26)]
        },
        "Cash4Life": {
            "type": "ball-set",
            "main": sorted(random.sample(range(1, 61), 5)),
            "cash_ball": [random.randint(1, 4)]
        }
    }
    
    # Generate Cash3 combinations (3-digit)
    cash3_count = random.randint(1, 5)
    for _ in range(cash3_count):
        combo = f"{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
        mmfsn["Cash3"]["values"].append(combo)
    
    # Generate Cash4 combinations (4-digit)  
    cash4_count = random.randint(1, 3)
    for _ in range(cash4_count):
        combo = f"{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
        mmfsn["Cash4"]["values"].append(combo)
    
    return mmfsn


def generate_subscriber(subscriber_id, kit_type):
    """Generate a single subscriber for the specified KIT with correct requirements"""
    birth_date = generate_random_birth_date()
    birth_city, birth_state = random.choice(US_LOCATIONS)
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    risk_profiles = ["conservative", "balanced", "assertive"]
    risk_profile = random.choice(risk_profiles)

    identity = {
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": birth_date,
        "birth_city": birth_city,
        "birth_state": birth_state
    }
    if kit_type in ("BOOK3", "BOOK"):
        birth_time = generate_random_birth_time()
        identity["birth_time"] = birth_time

    # BOSK only gets Cash3 & Cash4 (no jackpot games)
    if kit_type == "BOSK":
        games_list = ["Cash3", "Cash4"]
    else:
        games_list = ["Cash3", "Cash4", "MegaMillions", "Powerball", "Cash4Life"]
    
    subscriber = {
        "subscriber_id": subscriber_id,
        "kit_type": kit_type,
        "dob": birth_date,
        "coverage_start": "2025-01-01",
        "coverage_end": "2025-12-01",
        "formats": ["JSON"],
        "identity": identity,
        "preferences": {
            "games": games_list,
            "risk_profile": risk_profile
        },
        "meta": {
            "version": "v3.7",
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
    }

    if kit_type == "BOOK3":
        subscriber["engine_profile"] = {
            "mmfsn": generate_mmfsn_values(),
            "numerology": {
                "life_path_required": True,
                "personal_day_required": True
            },
            "astrology": {
                "requires_birth_time": True,
                "requires_location": True
            }
        }
    elif kit_type == "BOOK":
        subscriber["engine_profile"] = {
            "numerology": {
                "life_path_required": True,
                "personal_day_required": True
            },
            "astrology": {
                "requires_birth_time": True,
                "requires_location": True
            }
        }
    elif kit_type == "BOSK":
        subscriber["engine_profile"] = {
            "numerology": {
                "life_path_required": True,
                "personal_day_required": True
            },
            "astrology": {
                "requires_birth_time": False,
                "requires_location": True
            }
        }

    return subscriber



import argparse

def main():
    """Generate 1,500 test subscribers for specified KIT(s) (BOOK3, BOOK, BOSK)"""
    parser = argparse.ArgumentParser(description="Generate test subscribers for specified KIT(s)")
    parser.add_argument('--kit', nargs='+', choices=['BOOK3', 'BOOK', 'BOSK', 'ALL'], default=['ALL'],
                        help="Which KIT(s) to generate: BOOK3, BOOK, BOSK, or ALL (default: ALL)")
    args = parser.parse_args()

    kit_map = {
        "BOOK3": ("BOOK3", "data/subscribers/BOOK3_TEST"),
        "BOOK": ("BOOK", "data/subscribers/BOOK_TEST"),
        "BOSK": ("BOSK", "data/subscribers/BOSK_TEST"),
    }

    if 'ALL' in args.kit:
        kits_to_generate = [kit_map[k] for k in ["BOOK3", "BOOK", "BOSK"]]
    else:
        kits_to_generate = [kit_map[k] for k in args.kit]

    print("TEST SUBSCRIBER GENERATOR v3.7 (BOOK3, BOOK, BOSK)")
    print("="*60)
    for kit_type, output_dir in kits_to_generate:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Generating 1,500 {kit_type} test subscribers...")
        for i in range(1, 1501):
            subscriber_id = f"{kit_type}_TEST{i:04d}"
            subscriber = generate_subscriber(subscriber_id, kit_type)
            filename = f"{subscriber_id}.json"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(subscriber, f, indent=2)
            if i % 100 == 0:
                print(f"  Generated {i}/1500 {kit_type} subscribers...")
        print(f"✅ {kit_type}: 1,500 test subscribers generated in {output_dir}")
    print("\nAll test subscribers generated successfully for selected KIT(s).")

if __name__ == "__main__":
    main()