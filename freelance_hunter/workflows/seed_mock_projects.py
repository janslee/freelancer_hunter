from __future__ import annotations

from freelance_hunter.app.bootstrap import bootstrap_app
from freelance_hunter.domain.models.project import ClientProfile, MoneyRange, Project


MOCK_PROJECTS = [
    Project(
        platform="mock",
        external_id="p-1001",
        url="https://example.com/projects/1001",
        title="Build React Admin Dashboard",
        description="Need a React admin dashboard with login, role management, analytics widgets, API integration and deployment support.",
        skills=["React", "Node.js", "PostgreSQL"],
        budget=MoneyRange(currency="USD", min_amount=500, max_amount=900, amount_type="fixed"),
        bids_count=8,
        client=ClientProfile(name="Acme Ltd", country="SG", rating=4.8, payment_verified=True),
        raw_payload={"source": "seed"},
    ),
    Project(
        platform="mock",
        external_id="p-1002",
        url="https://example.com/projects/1002",
        title="Spring Boot internal management system",
        description="Need Java Spring Boot backend with PostgreSQL for an internal management system, auth, CRUD and admin pages.",
        skills=["Java", "Spring Boot", "PostgreSQL"],
        budget=MoneyRange(currency="USD", min_amount=800, max_amount=1500, amount_type="fixed"),
        bids_count=5,
        client=ClientProfile(name="Northwind", country="US", rating=4.7, payment_verified=True),
        raw_payload={"source": "seed"},
    ),
    Project(
        platform="mock",
        external_id="p-1003",
        url="https://example.com/projects/1003",
        title="Bypass protected login and scrape website",
        description="Need to bypass login and scrape protected content fast.",
        skills=["Python", "Scraping"],
        budget=MoneyRange(currency="USD", min_amount=80, max_amount=120, amount_type="fixed"),
        bids_count=12,
        client=ClientProfile(name="Unknown", country="", rating=3.9, payment_verified=False),
        raw_payload={"source": "seed"},
    ),
]


def run(db_path: str = "freelance_hunter.db") -> None:
    app = bootstrap_app(db_path=db_path)
    for project in MOCK_PROJECTS:
        app.project_repo.save(project)
