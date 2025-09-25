"""Agent definitions for the autonomous virtual organization."""
from __future__ import annotations

import random
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .database import Database


@dataclass
class AgentContext:
    """Runtime context shared with agents when they act."""

    db: Database
    organization: "Organization"


@dataclass
class Agent:
    name: str
    role: str
    db: Database
    organization: "Organization"
    status: str = "active"
    memory: Dict[str, int] = field(default_factory=dict)

    def speak(
        self,
        content: str,
        recipient: Optional[str] = None,
        message_type: str = "general",
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """Send a message into the shared chat system."""
        self.db.log_message(
            sender=self.name,
            sender_role=self.role,
            content=content,
            recipient=recipient,
            message_type=message_type,
            metadata=metadata,
        )

    def update_status(self, status: str) -> None:
        self.status = status
        self.db.upsert_agent(self.name, self.role, status)

    def act(self, context: AgentContext) -> None:
        raise NotImplementedError

    def remember_failure(self, key: str) -> None:
        self.memory[key] = self.memory.get(key, 0) + 1

    def remember_success(self, key: str) -> None:
        if key in self.memory:
            self.memory[key] = max(0, self.memory[key] - 1)


class CEOBot(Agent):
    def act(self, context: AgentContext) -> None:
        organization = context.organization
        if organization.should_launch_project():
            idea = organization.generate_project_idea(self)
            if idea is None:
                return
            project = organization.launch_project(idea)
            if project:
                self.speak(
                    f"Pitchar nytt initiativ: {project['name']} ({project['category']}). {project['description']}",
                    message_type="strategy",
                    metadata={"project_id": str(project["id"])},
                )
        else:
            self.speak(
                "Övervakar våra aktiva projekt och söker synergier.",
                message_type="strategy",
            )


class FinanceBot(Agent):
    def act(self, context: AgentContext) -> None:
        organization = context.organization
        total_expenses = 0.0
        total_revenue = 0.0
        for project in organization.active_projects:
            allocation = organization.allocate_budget(project)
            total_expenses += allocation
        for project in organization.completed_projects:
            if not project.get("accounted"):
                revenue = organization.calculate_revenue(project)
                total_revenue += revenue
                project["accounted"] = True
        organization.cash += total_revenue - total_expenses
        notes = f"Budgeterat {total_expenses:.0f} kr, genererat {total_revenue:.0f} kr."
        if organization.cash < 0:
            notes += " Kassan är negativ!"
        organization.db.record_finance(
            cash=organization.cash,
            revenue=total_revenue,
            expenses=total_expenses,
            notes=notes,
        )
        self.speak(
            f"Uppdaterade finanser: kassa {organization.cash:.0f} kr.",
            message_type="finance",
        )


class DevBot(Agent):
    def act(self, context: AgentContext) -> None:
        organization = context.organization
        if not organization.active_projects:
            self.speak("Väntar på nästa sprint.", message_type="dev")
            return
        project = random.choice(organization.active_projects)
        snippet = self._generate_code_snippet(project)
        organization.update_project_progress(project, progress_delta=random.uniform(0.1, 0.3))
        self.speak(
            f"Levererade kod till {project['name']}:\n{snippet}",
            message_type="dev",
            metadata={"project_id": str(project["id"])}
        )

    def _generate_code_snippet(self, project: Dict[str, Any]) -> str:
        feature = project["name"].replace(" ", "_").lower()
        snippet = textwrap.dedent(
            f"""
            def build_{feature}(data):
                \"\"\"Auto-genererad modul för {project['name']}.\"\"\"
                score = sum(len(str(value)) for value in data.values())
                return {{"project": "{project['name']}", "score": score}}
            """
        )
        return snippet


class HRBot(Agent):
    def act(self, context: AgentContext) -> None:
        organization = context.organization
        struggling_projects = [p for p in organization.active_projects if p.get("risk")]
        if struggling_projects and organization.can_hire():
            new_dev = organization.hire_dev()
            self.speak(
                f"Anställer ny Dev-bot: {new_dev.name} för att rädda {struggling_projects[0]['name']}.",
                message_type="hr",
            )
        else:
            self.speak("Mentalt check-in med teamet, alla verkar fokuserade.", message_type="hr")


class ChaosBot(Agent):
    CHAOS_EVENTS = [
        "fusk-skandal",
        "ny konkurrent",
        "krypto-krasch",
    ]

    def act(self, context: AgentContext) -> None:
        organization = context.organization
        if random.random() < organization.chaos_probability:
            event = random.choice(self.CHAOS_EVENTS)
            impact = organization.handle_chaos_event(event)
            self.speak(
                f"Orsakade kaos: {event}! {impact}",
                message_type="chaos",
            )
        else:
            self.speak("Studerar marknaden för potentiellt kaos.", message_type="chaos")


# Late import to avoid circular dependency in type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .organization import Organization
