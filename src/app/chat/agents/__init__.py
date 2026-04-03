"""Agents package."""

from .base import BaseAgent
from ..state import AgentInput, AgentOutput
from .router_agent import RouterAgent
from .support_agent import SupportAgent
from .events_agent import EventsAgent
from .staff_agent import StaffAgent
from .qa_agent import QAAgent
from .summarizer_agent import SummarizerAgent
from .abstract_agent import (
    AbstractAgent,
    PlannerAgent,
    ChapterWriterAgent,
    ChapterSummarizerAgent,
)
from .presentation_agent import (
    PresentationAgent,
    SlidePlannerAgent,
    SliderAgent,
    SlideSummarizerAgent,
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
    "PresentationAgent",
    "SlidePlannerAgent",
    "SliderAgent",
    "SlideSummarizerAgent",
]
