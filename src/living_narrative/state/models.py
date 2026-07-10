"""Pydantic v2 models for project and state files."""

import re
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from living_narrative.state.ids import id_type


class AutonomyLevel(StrEnum):
    MANUAL = "manual"
    ASSIST = "assist"
    AUTO = "auto"
    WATCH = "watch"
    GOD = "god"


class UserMode(StrEnum):
    WATCHER = "watcher"
    ASSISTANT_GM = "assistant_gm"
    FULL_GM = "full_gm"
    AUTHOR = "author"
    PLAYER_CHARACTER = "player_character"
    GOD = "god"


PromptRecording = Literal["full", "hash_only"]
Percent = Annotated[int, Field(ge=0, le=100)]

WorldId = id_type("world")
FactionId = id_type("faction")
CharacterId = id_type("char")
SceneId = id_type("scene")
CanonId = id_type("canon")
ReaderStateId = id_type("reader_state")
GmVaultId = id_type("gm_vault")
EventId = id_type("event")
RollId = id_type("roll")
ThreadId = id_type("thread")
FactId = id_type("fact")
ThreatId = id_type("threat")
MemoryId = id_type("memory")

_BINDING_KEY_FIXED = {
    "narrator",
    "world_simulator",
    "conflict_resolver",
    "state_manager",
    "checker",
    "interpreter",
    "character_default",
}
_BINDING_KEY_CHARACTER_RE = re.compile(r"^character:char_\d+$")
_PLAYER_CHAR_ID_RE = re.compile(r"^char_\d+$")
STOP_CONDITION_NAMES = {
    "character_death",
    "major_canon_change",
    "relationship_threshold_crossing",
    "major_secret_reveal",
    "checker_error",
    "leak_suspicion",
    "heavy_roll_failure",
    "scene_end",
    "target_turn_count_reached",
}
THRESHOLD_STOP_CONDITIONS = {"relationship_threshold_crossing"}


def _is_valid_binding_key(key: str) -> bool:
    return key in _BINDING_KEY_FIXED or bool(_BINDING_KEY_CHARACTER_RE.match(key))


class LLMConfig(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    timeout_seconds: int = Field(default=30, gt=0)
    prompt_recording: PromptRecording = "full"


class WorkspaceConfig(BaseModel):
    root: str
    state: str
    runs: str
    exports: str


class StopConditionConfig(BaseModel):
    enabled: bool = True
    threshold: int | None = None


class ProjectConfig(BaseModel):
    model_config = {"extra": "allow"}

    schema_version: Annotated[int, Field(strict=True, ge=1)] = 1
    id: str
    title: str
    genre: str
    tone: str
    language: str = "ja"
    autonomy_level: AutonomyLevel
    user_mode: UserMode
    random_seed: str
    renderer: str
    llm: LLMConfig
    workspace: WorkspaceConfig
    llm_profiles: dict[str, LLMConfig] = Field(default_factory=dict)
    llm_bindings: dict[str, str] = Field(default_factory=dict)
    stop_conditions: dict[str, StopConditionConfig] = Field(default_factory=dict)
    player_char_id: str | None = None

    @model_validator(mode="after")
    def _validate_session_fields(self) -> "ProjectConfig":
        for key, profile_name in self.llm_bindings.items():
            if not _is_valid_binding_key(key):
                raise ValueError(
                    f"llm_bindings key {key!r} is not a valid binding key "
                    "(expected one of "
                    f"{sorted(_BINDING_KEY_FIXED)} or 'character:char_<n>')"
                )
            if profile_name not in self.llm_profiles:
                raise ValueError(
                    f"llm_bindings[{key!r}] references undefined llm_profiles "
                    f"entry {profile_name!r}"
                )
        for key, config in self.stop_conditions.items():
            if key == "stop_condition":
                raise ValueError("stop_condition cannot be disabled by project config")
            if key not in STOP_CONDITION_NAMES:
                raise ValueError(f"unknown stop_conditions key {key!r}")
            if config.threshold is not None and key not in THRESHOLD_STOP_CONDITIONS:
                raise ValueError(f"stop_conditions[{key!r}] does not support threshold")
        if self.user_mode == UserMode.PLAYER_CHARACTER:
            if self.player_char_id is None:
                raise ValueError("player_char_id is required when user_mode is player_character")
            if not _PLAYER_CHAR_ID_RE.match(self.player_char_id):
                raise ValueError("player_char_id must match char_<number>")
        elif self.player_char_id is not None:
            raise ValueError("player_char_id is only valid when user_mode is player_character")
        return self


class Visibility(StrEnum):
    GM_ONLY = "gm_only"
    CANON = "canon"
    CHARACTER = "character"
    SCENE = "scene"
    READER = "reader"


class CharacterStatus(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"
    MISSING = "missing"


class SceneStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"


class StateBaseModel(BaseModel):
    model_config = {"extra": "allow"}


class BackgroundEventTableEntry(StateBaseModel):
    text: str = Field(min_length=1)
    weight: int = Field(ge=1)


class ThreatStage(StateBaseModel):
    """A one-shot escalation point in a ``ThreatTrack``, fired once pressure crosses ``at``."""

    at: Annotated[int, Field(ge=1, le=100)]
    text: str = Field(min_length=1)
    visibility: Visibility
    effects: dict[str, Any] = Field(default_factory=dict)


class ThreatTrack(StateBaseModel):
    """Issue 008: a data-driven plot-pressure track (e.g. a pursuer closing in)."""

    id: ThreatId
    name: str
    pressure: Annotated[int, Field(ge=0, le=100)] = 0
    pressure_per_turn: str
    stages: list[ThreatStage] = Field(default_factory=list)


class PacingConfig(StateBaseModel):
    """Issue 011: narrative-stall detection/response tuning (0 window = off, back-compat)."""

    stall_window: Annotated[int, Field(ge=0)] = 0
    pressure_boost: Annotated[int, Field(ge=0)] = 4


class WorldState(StateBaseModel):
    id: WorldId
    name: str
    summary: str
    laws: list[str] = Field(default_factory=list)
    parameters: dict[str, Percent] = Field(default_factory=dict)
    background_events: list[BackgroundEventTableEntry] = Field(default_factory=list)
    threats: list[ThreatTrack] = Field(default_factory=list)
    # Issue 010: engine-side emotion homeostasis rate (0 = off, back-compat).
    emotion_decay_per_turn: Annotated[int, Field(ge=0)] = 0
    # Issue 011: narrative-stall detection/response tuning.
    pacing: PacingConfig = Field(default_factory=PacingConfig)
    # Issue 015: turn interval at which the narrator is asked to fold reader-visible history
    # into a running memory summary (0 = off, back-compat).
    memory_summary_interval: Annotated[int, Field(ge=0)] = 0


class FactionState(StateBaseModel):
    id: FactionId
    name: str
    public_face: str
    goals: list[str] = Field(default_factory=list)
    resources: dict[str, Percent] = Field(default_factory=dict)
    relations: dict[CharacterId | FactionId | str, Percent] = Field(default_factory=dict)


class CharacterGoals(StateBaseModel):
    short_term: list[str] = Field(default_factory=list)
    long_term: list[str] = Field(default_factory=list)


class CharacterKnowledge(StateBaseModel):
    knows: list[str] = Field(default_factory=list)
    believes: list[str] = Field(default_factory=list)
    does_not_know: list[str] = Field(default_factory=list)


class SpeechProfile(StateBaseModel):
    """Issue 012: this character's speech register, so first-person pronoun errors and
    other register slips can be prevented (prompt) and detected (checker)."""

    first_person: str | None = None
    forbidden_terms: list[str] = Field(default_factory=list)


class CharacterState(StateBaseModel):
    """Character state. ``private_mind`` is visible only to this character."""

    id: CharacterId
    name: str
    role: str
    stats: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    traits: list[str] = Field(default_factory=list)
    goals: CharacterGoals = Field(default_factory=CharacterGoals)
    emotions: dict[str, Percent] = Field(default_factory=dict)
    # Issue 010: this character's resting/平常値 emotion levels. Empty = decay does not
    # apply to this character (back-compat); only keys also present in ``emotions`` decay.
    emotions_baseline: dict[str, Percent] = Field(default_factory=dict)
    knowledge: CharacterKnowledge = Field(default_factory=CharacterKnowledge)
    secrets: list[str] = Field(default_factory=list)
    private_mind: list[str] = Field(default_factory=list)
    inventory: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    status: CharacterStatus = CharacterStatus.ALIVE
    # Issue 012: speech register (first-person pronoun, forbidden terms). Default is an
    # empty profile (back-compat) that never affects prompts or checkers.
    speech: SpeechProfile = Field(default_factory=SpeechProfile)


class RelationshipState(StateBaseModel):
    from_: CharacterId = Field(alias="from")
    to: CharacterId
    trust: Percent
    affection: Percent
    tension: Percent
    suspicion: Percent
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reject_self_reference(self) -> "RelationshipState":
        if self.from_ == self.to:
            raise ValueError("relationship cannot reference the same character")
        return self


class HiddenFact(StateBaseModel):
    id: FactId
    text: str
    visibility: Visibility
    known_by: list[CharacterId] = Field(default_factory=list)


class SceneState(StateBaseModel):
    id: SceneId
    location: str
    time: str
    active_characters: list[CharacterId] = Field(default_factory=list)
    mood: str = ""
    stakes: str = ""
    summary: str = ""
    reader_visible_facts: list[str] = Field(default_factory=list)
    hidden_facts: list[HiddenFact] = Field(default_factory=list)
    status: SceneStatus = SceneStatus.ACTIVE


class CanonEntry(StateBaseModel):
    id: CanonId
    text: str
    established_turn: int
    source_event: EventId | None = None


class ReaderStateEntry(StateBaseModel):
    id: ReaderStateId
    text: str
    established_turn: int
    source_event: EventId | None = None
    disclosed_turn: int


class GmVaultEntry(StateBaseModel):
    id: GmVaultId
    text: str
    reveal_condition: str | None = None


class TimelineEntry(StateBaseModel):
    turn: int
    event_ids: list[EventId] = Field(default_factory=list)


class UnresolvedThread(StateBaseModel):
    id: ThreadId
    description: str
    status: str
    related_event_ids: list[EventId] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    opened_turn: int | None = None


class MemorySummary(StateBaseModel):
    """Issue 015: a narrator-written 通史要約 covering reader-visible history up to a turn."""

    id: MemoryId
    up_to_turn: int
    text: str


def latest_memory_summary(summaries: list[MemorySummary]) -> str:
    """The most recently-covering memory summary's text, or ``""`` when none exist yet."""
    if not summaries:
        return ""
    return max(summaries, key=lambda summary: summary.up_to_turn).text


class Event(StateBaseModel):
    id: EventId
    turn: int
    type: str
    cause: str | None = None
    text: str = Field(min_length=1)
    visibility: Visibility
    known_by: list[CharacterId] = Field(default_factory=list)
    hidden_from: list[CharacterId] = Field(default_factory=list)
    effects: dict[str, Any] = Field(default_factory=dict)
    roll_ids: list[RollId] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def _reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @model_validator(mode="after")
    def _known_by_and_hidden_from_do_not_overlap(self) -> "Event":
        overlap = set(self.known_by) & set(self.hidden_from)
        if overlap:
            raise ValueError(f"known_by and hidden_from overlap: {sorted(overlap)}")
        return self


class WorldStateBundle(StateBaseModel):
    world: WorldState
    factions: list[FactionState] = Field(default_factory=list)
    characters: list[CharacterState] = Field(default_factory=list)
    relationships: list[RelationshipState] = Field(default_factory=list)
    scenes: list[SceneState] = Field(default_factory=list)
    canon: list[CanonEntry] = Field(default_factory=list)
    reader_state: list[ReaderStateEntry] = Field(default_factory=list)
    gm_vault: list[GmVaultEntry] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    unresolved_threads: list[UnresolvedThread] = Field(default_factory=list)
    memory_summaries: list[MemorySummary] = Field(default_factory=list)
