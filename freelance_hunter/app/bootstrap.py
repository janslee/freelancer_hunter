from freelance_hunter.app.settings import load_settings
from freelance_hunter.domain.services.scorer import ProjectScorer
from freelance_hunter.domain.services.pricing_engine import PricingEngine
from freelance_hunter.domain.services.proposal_generator import ProposalGenerator
from freelance_hunter.repositories.sqlite.project_repo import ProjectRepository
from freelance_hunter.repositories.sqlite.evaluation_repo import EvaluationRepository
from freelance_hunter.repositories.sqlite.pricing_repo import PricingRepository
from freelance_hunter.repositories.sqlite.bid_repo import BidRepository
from freelance_hunter.repositories.sqlite.db import get_connection, init_db


class AppContainer:
    def __init__(self, db_path: str = "freelance_hunter.db"):
        self.settings = load_settings()
        self.conn = get_connection(db_path)
        init_db(self.conn)

        self.scorer = ProjectScorer(
            profile_cfg=self.settings.get("filters", {}),
            risk_cfg=self.settings.get("risk", {}),
        )
        self.pricing_engine = PricingEngine({"pricing": self.settings.get("pricing", {})})
        self.proposal_generator = ProposalGenerator()

        self.project_repo = ProjectRepository(self.conn)
        self.evaluation_repo = EvaluationRepository(self.conn)
        self.pricing_repo = PricingRepository(self.conn)
        self.bid_repo = BidRepository(self.conn)


def bootstrap_app(db_path: str = "freelance_hunter.db") -> AppContainer:
    return AppContainer(db_path=db_path)
