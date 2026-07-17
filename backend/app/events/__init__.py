"""Internal event bus, schemas, and envelope helpers."""

from app.events.bus import drain as drain
from app.events.bus import publish as publish
from app.events.bus import subscribe as subscribe
from app.events.schemas import EventEnvelope as EventEnvelope
from app.events.schemas import ProjectStatusPayload as ProjectStatusPayload
from app.events.schemas import StepProgressPayload as StepProgressPayload
from app.events.schemas import project_status as project_status
from app.events.schemas import step_progress as step_progress

# Note: this package must not import from app.services.* -- state_machine.py
# imports app.events.bus, so re-exporting state-machine symbols here creates
# a circular import (events -> services.state_machine -> events.bus ->
# triggers this __init__ -> services.state_machine, partially initialized).
# Import ProjectStateMachine/EDGES/etc. from app.services.state_machine
# directly instead.
