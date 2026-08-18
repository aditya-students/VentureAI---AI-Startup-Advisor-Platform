"""
Seed script to create 6 dummy mentors with rich, realistic profiles in the database.
Run with:
    python -m app.seed_mentors
"""

from app.database.connection import SessionLocal, engine
from app.database.base import Base
from app.users import models as _users_models  # noqa: F401
from app.startup import models as _startup_models  # noqa: F401
from app.users.models import User, Role, RoleName, MentorProfile
from app.auth.jwt import hash_password
from app.mentor.service import calculate_profile_completion

DUMMY_MENTORS = [
    {
        "name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "password": "Password123!",
        "headline": "Startup Advisor & SaaS Growth Strategist",
        "bio": "12+ years building and scaling B2B SaaS companies. Former VP of Product at TechFlow. Helped 15+ startups raise Seed to Series A funding. Passionate about GTM execution, unit economics, and product-led growth.",
        "current_role": "Managing Director",
        "company": "ScaleVenture Partners",
        "location": "Bengaluru, India",
        "years_of_experience": 12,
        "startup_experience": 8,
        "mentoring_experience": 5,
        "industries": ["SaaS", "AI/ML", "FinTech"],
        "areas_of_expertise": ["Product Strategy", "Go-To-Market", "Fundraising", "Product-Market Fit"],
        "startup_stages": ["Idea Stage", "MVP", "Early Revenue", "Growth Stage"],
        "mentorship_areas": ["Product Development", "Go-To-Market", "Fundraising", "Pitching"],
        "availability": "Available",
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@example.com",
        "password": "Password123!",
        "headline": "FinTech Lead & Angel Investor",
        "bio": "Serial entrepreneur with 2 successful exits in FinTech and Payments. Active angel investor in South Asia. Advises early-stage founders on regulatory strategy, financial modeling, and investor pitching.",
        "current_role": "Partner",
        "company": "FinCapital Ventures",
        "location": "Mumbai, India",
        "years_of_experience": 15,
        "startup_experience": 10,
        "mentoring_experience": 6,
        "industries": ["FinTech", "Cybersecurity", "Consumer Tech"],
        "areas_of_expertise": ["Finance", "Business Strategy", "Fundraising", "Legal/Compliance"],
        "startup_stages": ["MVP", "Early Revenue", "Growth Stage", "Scaling"],
        "mentorship_areas": ["Business Model", "Fundraising", "Pitching", "Scaling"],
        "availability": "Available",
    },
    {
        "name": "David Chen",
        "email": "david.chen@example.com",
        "password": "Password123!",
        "headline": "AI/ML Tech Architect & Ex-Founder",
        "bio": "PhD in Artificial Intelligence. Built LLM and computer vision infrastructure for enterprise clients. Love working with technical founders translating cutting-edge AI technology into commercial products.",
        "current_role": "Head of AI Research",
        "company": "Apex AI Labs",
        "location": "Singapore",
        "years_of_experience": 10,
        "startup_experience": 6,
        "mentoring_experience": 4,
        "industries": ["AI/ML", "HealthTech", "SaaS"],
        "areas_of_expertise": ["Technology", "AI/ML", "Product Strategy", "Customer Discovery"],
        "startup_stages": ["Idea Stage", "Pre-MVP", "MVP"],
        "mentorship_areas": ["Idea Validation", "Product Development", "Technology"],
        "availability": "Limited Availability",
    },
    {
        "name": "Ananya Roy",
        "email": "ananya.roy@example.com",
        "password": "Password123!",
        "headline": "Growth Marketing & Brand Specialist",
        "bio": "Specialized in performance marketing, user acquisition, and SEO/SEM strategies for D2C and E-commerce startups. Scaled brand revenue from zero to $5M ARR.",
        "current_role": "CMO in Residence",
        "company": "HyperGrowth Studio",
        "location": "Delhi, India",
        "years_of_experience": 9,
        "startup_experience": 5,
        "mentoring_experience": 3,
        "industries": ["E-commerce", "Consumer Tech", "EdTech"],
        "areas_of_expertise": ["Marketing", "Sales", "Go-To-Market", "Customer Discovery"],
        "startup_stages": ["Pre-MVP", "MVP", "Early Revenue"],
        "mentorship_areas": ["Go-To-Market", "Idea Validation", "Business Model"],
        "availability": "Available",
    },
    {
        "name": "Marcus Vance",
        "email": "marcus.vance@example.com",
        "password": "Password123!",
        "headline": "Operations & CleanTech Advisor",
        "bio": "18+ years operating experience across logistics, supply chain, and clean technology startups. Deep expertise in operational unit economics, hardware-software integration, and team scaling.",
        "current_role": "Chief Operating Officer",
        "company": "EcoMotion Systems",
        "location": "London, UK",
        "years_of_experience": 18,
        "startup_experience": 12,
        "mentoring_experience": 7,
        "industries": ["CleanTech", "Logistics", "Other"],
        "areas_of_expertise": ["Operations", "Business Model", "Business Strategy"],
        "startup_stages": ["Early Revenue", "Growth Stage", "Scaling"],
        "mentorship_areas": ["Operations", "Scaling", "Business Model"],
        "availability": "Available",
    },
    {
        "name": "Dr. Aris Mehta",
        "email": "aris.mehta@example.com",
        "password": "Password123!",
        "headline": "HealthTech Innovation Lead & Medical Advisor",
        "bio": "Physician turned healthtech entrepreneur. Co-founded a tele-health platform acquired in 2023. Advises digital health founders on clinical trials, HIPAA/FDA compliance, and B2B hospital sales.",
        "current_role": "Venture Partner",
        "company": "BioHealth Catalyst",
        "location": "Boston, USA",
        "years_of_experience": 14,
        "startup_experience": 7,
        "mentoring_experience": 4,
        "industries": ["HealthTech", "AI/ML"],
        "areas_of_expertise": ["Legal/Compliance", "Product Strategy", "Sales", "Business Strategy"],
        "startup_stages": ["Idea Stage", "MVP", "Early Revenue"],
        "mentorship_areas": ["Idea Validation", "Product Development", "Pitching"],
        "availability": "Limited Availability",
    },
]


def seed_mentors():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        mentor_role = db.query(Role).filter(Role.name == RoleName.MENTOR.value).first()
        if not mentor_role:
            print("ERROR: Mentor role not found in database. Run python -m app.seed first.")
            return

        seeded_count = 0
        for data in DUMMY_MENTORS:
            existing_user = db.query(User).filter(User.email == data["email"]).first()
            if existing_user:
                print(f"Mentor already exists, skipping: {data['email']}")
                continue

            user = User(
                name=data["name"],
                email=data["email"],
                password_hash=hash_password(data["password"]),
                role_id=mentor_role.id,
            )
            db.add(user)
            db.flush()

            profile = MentorProfile(
                user_id=user.id,
                headline=data["headline"],
                bio=data["bio"],
                current_role=data["current_role"],
                company=data["company"],
                location=data["location"],
                years_of_experience=data["years_of_experience"],
                startup_experience=data["startup_experience"],
                mentoring_experience=data["mentoring_experience"],
                industries=data["industries"],
                areas_of_expertise=data["areas_of_expertise"],
                startup_stages=data["startup_stages"],
                mentorship_areas=data["mentorship_areas"],
                availability=data["availability"],
                is_discoverable=True,
            )
            profile.profile_completion = calculate_profile_completion(profile)
            db.add(profile)
            seeded_count += 1
            print(f"Seeded mentor: {data['name']} ({data['email']})")

        db.commit()
        print(f"\nSuccessfully seeded {seeded_count} new mentors!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding mentors: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_mentors()
