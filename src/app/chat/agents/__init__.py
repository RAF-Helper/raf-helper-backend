"""Agents package."""

from app.chat.agents.base import BaseAgent
from app.chat.state import AgentInput, AgentOutput
from app.chat.agents.router_agent import RouterAgent
from app.chat.agents.support_agent import SupportAgent
from app.chat.agents.events_agent import EventsAgent
from app.chat.agents.staff_agent import StaffAgent
from app.chat.agents.qa_agent import QAAgent
from app.chat.agents.summarizer_agent import SummarizerAgent
from app.chat.agents.abstract_agent import (
    AbstractAgent,
    PlannerAgent,
    ChapterWriterAgent,
    ChapterSummarizerAgent,
    ChapterReviewerAgent,
)
from app.chat.agents.presentation_agent import (
    PresentationAgent,
    SlidePlannerAgent,
    SliderAgent,
    SlideSummarizerAgent,
    SlidesReviewerAgent,
)

__all__ = [
    "BaseAgent",
    "RouterAgent",
    "SupportAgent",
    "EventsAgent",
    "StaffAgent",
    "QAAgent",
    "SummarizerAgent",
    "AbstractAgent",
    "PlannerAgent",
    "ChapterWriterAgent",
    "ChapterSummarizerAgent",
    "ChapterReviewerAgent",
    "PresentationAgent",
    "SlidePlannerAgent",
    "SliderAgent",
    "SlideSummarizerAgent",
    "SlidesReviewerAgent",
]
