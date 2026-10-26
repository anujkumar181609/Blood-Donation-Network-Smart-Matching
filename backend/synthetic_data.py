"""
Synthetic Dataset Generator
Generates realistic datasets of hospitals, blood requests, and donors
with realistic demographic blood group distributions and geographic coordinates
modeled after Chandigarh Tricity (Chandigarh, Mohali, Panchkula & CU Campus).
"""

import random
from typing import List
from datetime import date, timedelta
from backend.models import (
    BloodGroup,
    Gender,
    Donor,
    Hospital,
    UrgencyLevel
)

# Realistic Blood Group Proportions (reflecting NBTC / Indian Red Cross demographics)
BLOOD_GROUP_WEIGHTS = {
    BloodGroup.O_POS: 0.370,
    BloodGroup.B_POS: 0.320,
    BloodGroup.A_POS: 0.220,
    BloodGroup.AB_POS: 0.060,
    BloodGroup.O_NEG: 0.015,
    BloodGroup.B_NEG: 0.010,
    BloodGroup.A_NEG: 0.003,
    BloodGroup.AB_NEG: 0.002,
}

FIRST_NAMES_MALE = [
    "Aarav", "Rohan", "Vikram", "Aditya", "Kabir", "Arjun", "Karan", "Dev",
    "Manish", "Gaurav", "Harsh", "Nikhil", "Rahul", "Sameer", "Varun", "Amit",
    "Siddharth", "Prateek", "Shubham", "Aniket", "Shlok", "Anuj", "Tarun", "Aman"
]

FIRST_NAMES_FEMALE = [
    "Ananya", "Diya", "Pooja", "Simran", "Neha", "Priya", "Sneha", "Kritika",
    "Rhea", "Isha", "Meera", "Tanvi", "Avani", "Kavya", "Jaspreet", "Amanpreet",
    "Divya", "Sanya", "Swati", "Nandini", "Pallavi", "Shreya", "Aditi", "Preeti"
]

LAST_NAMES = [
    "Sharma", "Verma", "Singh", "Kandola", "Kumar", "Kaur", "Gupta", "Malhotra",
    "Bhatia", "Mehta", "Chawla", "Patel", "Joshi", "Bansal", "Gill", "Sandhu",
    "Grewal", "Aggarwal", "Kapoor", "Dhillon", "Soni", "Chopra", "Mittal", "Sethi"
]

TRICITY_LOCALITIES = [
    ("Sector 17, Chandigarh", 30.7398, 76.7827),
    ("Sector 35, Chandigarh", 30.7245, 76.7645),
    ("Sector 43, Chandigarh", 30.7188, 76.7456),
    ("Sector 22, Chandigarh", 30.7356, 76.7725),
    ("Phase 7, Mohali", 30.7102, 76.7214),
    ("Phase 3B2, Mohali", 30.7025, 76.7118),
    ("Sector 70, Mohali", 30.6872, 76.7055),
    ("Sector 62, Mohali", 30.6963, 76.7380),
    ("Sector 20, Panchkula", 30.6780, 76.8520),
    ("Sector 4, Panchkula", 30.6980, 76.8610),
    ("MDC Sector 5, Panchkula", 30.7190, 76.8450),
    ("Zirakpur VIP Road", 30.6425, 76.8180),
    ("Kharar Bus Stand Area", 30.7450, 76.6450),
    ("Chandigarh University Campus, Gharuan", 30.7699, 76.5760),
    ("New Chandigarh, Mullanpur", 30.7850, 76.7250)
]

DEFAULT_HOSPITALS = [
    Hospital(
        id="hosp_pgimer",
        name="PGIMER Super Specialty Hospital",
        email="emergency@pgimer.edu.in",
        phone="+91-172-2746018",
        address="Sector 12, Chandigarh",
        latitude=30.7628,
        longitude=76.7766,
        hospital_type="Apex Trauma & Research Institute"
    ),
    Hospital(
        id="hosp_gmch32",
        name="GMCH Sector 32 Medical College & Hospital",
        email="trauma@gmch.gov.in",
        phone="+91-172-2665253",
        address="Sector 32B, Chandigarh",
        latitude=30.7082,
        longitude=76.7820,
        hospital_type="Government Tertiary Hospital"
    ),
    Hospital(
        id="hosp_fortis",
        name="Fortis Hospital Mohali",
        email="emergency@fortismohali.com",
        phone="+91-172-5021222",
        address="Sector 62, Phase 8, Mohali",
        latitude=30.6974,
        longitude=76.7288,
        hospital_type="Super Specialty & Cardiac Centre"
    ),
    Hospital(
        id="hosp_max",
        name="Max Super Speciality Hospital Mohali",
        email="emergency.mohali@maxhealthcare.com",
        phone="+91-172-5212000",
        address="Phase 6, Mohali",
        latitude=30.7180,
        longitude=76.7110,
        hospital_type="Super Specialty Hospital"
    ),
    Hospital(
        id="hosp_alchemist",
        name="Alchemist Hospital Panchkula",
        email="care@alchemist.net.in",
        phone="+91-172-4500000",
        address="Sector 21, Panchkula",
        latitude=30.6860,
        longitude=76.8620,
        hospital_type="Multi-Specialty Hospital"
    ),
    Hospital(
        id="hosp_cu",
        name="Chandigarh University Health Center",
        email="healthcentre@cumail.in",
        phone="+91-160-3051000",
        address="NH-05, Ludhiana - Chandigarh State Hwy, Gharuan",
        latitude=30.7699,
        longitude=76.5760,
        hospital_type="Campus Health Center & Emergency Care"
    )
]


def sample_blood_group(rng: random.Random) -> BloodGroup:
    groups = list(BLOOD_GROUP_WEIGHTS.keys())
    weights = list(BLOOD_GROUP_WEIGHTS.values())
    return rng.choices(groups, weights=weights, k=1)[0]


def generate_synthetic_donors(count: int = 50, seed: int = 42) -> List[Donor]:
    """Generates synthetic donors with realistic attributes, coordinates, and cooldown states."""
    rng = random.Random(seed)
    today = date.today()
    donors: List[Donor] = []

    for i in range(1, count + 1):
        is_male = rng.random() < 0.65  # NBTC statistics show ~65-70% registered male donors
        gender = Gender.MALE if is_male else Gender.FEMALE
        first_name = rng.choice(FIRST_NAMES_MALE if is_male else FIRST_NAMES_FEMALE)
        last_name = rng.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"

        blood_group = sample_blood_group(rng)
        age = rng.randint(19, 58)
        weight_kg = round(rng.uniform(52.0, 88.0), 1)

        locality_name, base_lat, base_lon = rng.choice(TRICITY_LOCALITIES)
        # Add slight GPS jitter (~0.5 - 2 km)
        lat = round(base_lat + rng.uniform(-0.018, 0.018), 5)
        lon = round(base_lon + rng.uniform(-0.018, 0.018), 5)

        # Donation history and cooldown:
        # 30% first-time donors (never donated), 45% past cooldown (ready), 25% currently in cooldown
        history_roll = rng.random()
        cooldown_needed = 90 if is_male else 120

        if history_roll < 0.30:
            last_donation_date = None
            total_donations = 0
        elif history_roll < 0.75:
            # Fully eligible, donated 100 - 300 days ago
            days_ago = rng.randint(cooldown_needed + 5, cooldown_needed + 220)
            last_donation_date = (today - timedelta(days=days_ago)).isoformat()
            total_donations = rng.randint(1, 8)
        else:
            # Currently in cooldown (donated recently, e.g., 10 to 60 days ago)
            days_ago = rng.randint(8, cooldown_needed - 10)
            last_donation_date = (today - timedelta(days=days_ago)).isoformat()
            total_donations = rng.randint(1, 5)

        # 92% available
        is_available = rng.random() < 0.92
        # Response history rate (e.g. 0.75 - 0.98)
        response_history = round(rng.uniform(0.75, 0.99), 2)

        phone = f"+91-98{rng.randint(10000000, 99999999)}"
        email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"

        donor = Donor(
            id=f"donor_{i:04d}",
            name=name,
            email=email,
            phone=phone,
            blood_group=blood_group,
            gender=gender,
            age=age,
            weight_kg=weight_kg,
            latitude=lat,
            longitude=lon,
            address=f"{locality_name}",
            is_available=is_available,
            last_donation_date=last_donation_date,
            health_eligible=True,
            response_history_rate=response_history,
            total_donations=total_donations
        )
        donors.append(donor)

    return donors
