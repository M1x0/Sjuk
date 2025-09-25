"""Core simulation logic for the autonomous organization."""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .agents import AgentContext, CEOBot, ChaosBot, DevBot, FinanceBot, HRBot
from .database import Database


@dataclass
class Project:
    id: int
    name: str
    category: str
    description: str
    status: str
    budget: float
    progress: float = 0.0
    owner: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    outcome: Optional[str] = None
    accounted: bool = False
    risk: bool = False


class Organization:
    """Manages agents, projects and finances for the simulation."""

    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or Database()
        self.db.connection.execute("DELETE FROM messages")
        self.db.connection.execute("DELETE FROM projects")
        self.db.connection.execute("DELETE FROM agents")
        self.db.connection.execute("DELETE FROM finances")
        self.db.connection.execute("DELETE FROM mistakes")
        self.db.connection.execute("DELETE FROM chaos_events")
        self.db.connection.commit()
        self.cash: float = 250_000.0
        self.reputation: float = 1.0
        self.mistake_memory: Dict[str, int] = {}
        self.projects: List[Project] = []
        self.agents: Dict[str, List] = {}
        self.cycle_time: float = 2.5
        self.chaos_probability: float = 0.35
        self.loop_task: Optional[asyncio.Task] = None
        self._project_counter = 0
        self._init_agents()

    def _init_agents(self) -> None:
        self.ceo = CEOBot("CEO-bot", "CEO", self.db, self)
        self.finance = FinanceBot("Finance-bot", "Finance", self.db, self)
        self.dev_team: List[DevBot] = [DevBot("Dev-bot", "Dev", self.db, self)]
        self.hr = HRBot("HR-bot", "HR", self.db, self)
        self.chaos = ChaosBot("Chaos-bot", "Chaos", self.db, self)
        for agent in [self.ceo, self.finance, *self.dev_team, self.hr, self.chaos]:
            self.db.upsert_agent(agent.name, agent.role, agent.status)

    # region Properties -------------------------------------------------
    @property
    def active_projects(self) -> List[Dict[str, Any]]:
        return [p.__dict__ for p in self.projects if p.status == "active"]

    @property
    def completed_projects(self) -> List[Dict[str, Any]]:
        return [p.__dict__ for p in self.projects if p.status == "completed"]

    # endregion ---------------------------------------------------------

    def should_launch_project(self) -> bool:
        active_count = len([p for p in self.projects if p.status == "active"])
        return active_count < 3 and random.random() > 0.4

    def generate_project_idea(self, agent: CEOBot) -> Optional[Dict[str, str]]:
        ideas = [
            {"name": "Aurora Analytics", "category": "data", "description": "AI-analysplattform för sjukvård."},
            {"name": "Nordic Pulse", "category": "wellness", "description": "Wearable som upptäcker stress i realtid."},
            {"name": "FrostPay", "category": "fintech", "description": "Krypto-betalningar för småföretag."},
            {"name": "Glacial Guard", "category": "security", "description": "Automatiserad cybersäkerhetsövervakning."},
            {"name": "SjöAI", "category": "saas", "description": "Virtuell assistent för nordiska rederier."},
        ]
        weighted: List[Dict[str, str]] = []
        for idea in ideas:
            penalty = self.mistake_memory.get(idea["category"], 0)
            weight = max(1, 3 - penalty)
            weighted.extend([idea] * weight)
        if not weighted:
            return None
        choice = random.choice(weighted)
        return choice

    def launch_project(self, idea: Dict[str, str]) -> Optional[Dict[str, Any]]:
        self._project_counter += 1
        budget = random.randint(20_000, 80_000)
        project = Project(
            id=self._project_counter,
            name=idea["name"],
            category=idea["category"],
            description=idea["description"],
            status="active",
            budget=budget,
        )
        self.projects.append(project)
        project_dict = project.__dict__.copy()
        project_dict["id"] = self.db.record_project({**project_dict})
        project.id = project_dict["id"]
        self.db.log_message(
            sender="Board",
            sender_role="System",
            content=f"Styrelsen godkänner projekt {project.name} med budget {budget:.0f} kr.",
            message_type="board",
        )
        return project.__dict__

    def allocate_budget(self, project: Dict[str, Any]) -> float:
        spend = min(project["budget"] * 0.1, max(5_000.0, project["budget"] * 0.05))
        project["budget"] = max(0.0, project["budget"] - spend)
        self.db.update_project(project["id"], budget=project["budget"])
        return spend

    def update_project_progress(self, project: Dict[str, Any], progress_delta: float) -> None:
        project["progress"] = min(1.0, project.get("progress", 0.0) + progress_delta)
        if project["progress"] >= 1.0:
            project["status"] = "completed"
            project["finished_at"] = time.time()
            project["outcome"] = "success"
            self.db.update_project(
                project["id"],
                progress=project["progress"],
                status=project["status"],
                finished_at=project["finished_at"],
                outcome=project["outcome"],
            )
            self.db.log_message(
                sender="PMO",
                sender_role="System",
                content=f"Projekt {project['name']} är levererat!",
                message_type="status",
                metadata={"project_id": str(project["id"])}
            )
        else:
            self.db.update_project(project["id"], progress=project["progress"])

    def calculate_revenue(self, project: Dict[str, Any]) -> float:
        base = random.randint(50_000, 150_000)
        multiplier = 1 + (self.reputation - 1) * 0.5
        revenue = max(0.0, base * multiplier)
        if project.get("outcome") == "failed":
            revenue = 0.0
        return revenue

    def mark_project_failed(self, project: Dict[str, Any], reason: str, category: str) -> None:
        project["status"] = "failed"
        project["finished_at"] = time.time()
        project["outcome"] = reason
        project["risk"] = True
        self.db.update_project(
            project["id"],
            status=project["status"],
            finished_at=project["finished_at"],
            outcome=project["outcome"],
        )
        self.db.record_mistake(category, reason)
        self.mistake_memory[category] = self.mistake_memory.get(category, 0) + 1
        self.db.log_message(
            sender="Risk",
            sender_role="System",
            content=f"Projekt {project['name']} misslyckades: {reason}",
            message_type="alert",
            metadata={"project_id": str(project["id"])}
        )

    def can_hire(self) -> bool:
        return len(self.dev_team) < 4 and self.cash > 30_000

    def hire_dev(self) -> DevBot:
        new_name = f"Dev-bot-{len(self.dev_team) + 1}"
        dev = DevBot(new_name, "Dev", self.db, self)
        self.dev_team.append(dev)
        self.db.upsert_agent(dev.name, dev.role, dev.status)
        return dev

    def should_fire_dev(self) -> Optional[DevBot]:
        if len(self.dev_team) <= 1:
            return None
        troubled = [dev for dev in self.dev_team if dev.memory.get("failures", 0) > 2]
        if troubled:
            return random.choice(troubled)
        return None

    def fire_dev(self, dev: DevBot) -> None:
        self.dev_team.remove(dev)
        dev.update_status("terminated")
        self.db.log_message(
            sender=self.hr.name,
            sender_role=self.hr.role,
            content=f"Avslutar kontraktet med {dev.name} p.g.a. underprestation.",
            message_type="hr",
        )

    def handle_chaos_event(self, event: str) -> str:
        impact = ""
        if event == "fusk-skandal":
            self.reputation = max(0.2, self.reputation - 0.3)
            impact = "Reputationen rasar, kunder kräver svar."
            if self.projects:
                project = random.choice(self.projects)
                self.mark_project_failed(project.__dict__, "Skandalen skrämde kunderna", project.category)
        elif event == "ny konkurrent":
            self.reputation = max(0.5, self.reputation - 0.1)
            impact = "En aggressiv konkurrent pressar priserna."
            for project in self.projects:
                if project.status == "active":
                    project.risk = True
                    self.db.update_project(project.id, status=project.status)
        elif event == "krypto-krasch":
            loss = min(self.cash, random.uniform(50_000, 120_000))
            self.cash -= loss
            impact = f"Finance-bot spelade bort {loss:.0f} kr på krypto."
            if self.cash < 20_000 and self.dev_team:
                victim = random.choice(self.dev_team)
                victim.remember_failure("finance_crash")
        self.db.record_chaos_event(event, impact)
        return impact

    async def run(self) -> None:
        context = AgentContext(db=self.db, organization=self)
        agents = [self.ceo, self.finance, *self.dev_team, self.hr, self.chaos]
        while True:
            for agent in list(agents):
                agent.act(context)
            self._post_cycle_checks()
            agents = [self.ceo, self.finance, *self.dev_team, self.hr, self.chaos]
            await asyncio.sleep(self.cycle_time)

    def _post_cycle_checks(self) -> None:
        for project in list(self.projects):
            if project.status == "active" and project.progress < 0.3 and project.budget < 5_000:
                self.mark_project_failed(project.__dict__, "Pengarna tog slut innan MVP", project.category)
        fired = self.should_fire_dev()
        if fired:
            self.fire_dev(fired)

    def handle_interview(self, agent_name: str, question: str) -> str:
        agent_map = {
            self.ceo.name: self.ceo,
            self.finance.name: self.finance,
            self.hr.name: self.hr,
            self.chaos.name: self.chaos,
        }
        for dev in self.dev_team:
            agent_map[dev.name] = dev
        agent = agent_map.get(agent_name)
        if not agent:
            return "Agenten finns inte längre i organisationen."
        responses = {
            "CEO": [
                "Vår strategi är adaptiv. Vi lär oss av varje iteration.",
                "Fokus ligger på skalbara intäkter och hållbart team.",
            ],
            "Finance": [
                "Vi balanserar risk och potential, även om krypto var en miss.",
                "Kassan är under kontroll, vi justerar budgetar löpande.",
            ],
            "HR": [
                "Jag följer välmåendet i teamet noga.",
                "Kulturarbete är lika viktigt som leverans.",
            ],
            "Chaos": [
                "Jag finns för att testa er resiliens.",
                "Förbered er på det oväntade!",
            ],
            "Dev": [
                "Vi shippar kod varje cykel, även när det stormar.",
                "Sprintplanen justerades, men vi håller riktningen.",
            ],
        }
        role = agent.role
        reply = random.choice(responses.get(role, ["Inget att rapportera just nu."]))
        agent.speak(f"Svarar på intervju: {reply}", recipient="Intervjuare", message_type="interview")
        return reply

    def should_launch_dashboard_event(self) -> bool:
        return True

