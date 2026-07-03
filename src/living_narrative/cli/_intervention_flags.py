"""``turn --type`` direct-input flag mapping (cli/spec.md Requirement "構造化介入フラグ").

``InterventionDraft`` requires ``target.kind`` and ``visibility``, but the CLI's terse
``--type ... --target <id> --content ...`` form (per the spec's own example) supplies
neither explicitly. These per-type defaults are a CLI-layer convenience, not engine
policy — ``--visibility`` always overrides the default when passed.
"""

from living_narrative.intervention.schema import InterventionType, TargetKind
from living_narrative.state.models import Visibility

TYPE_TARGET_KIND: dict[InterventionType, TargetKind] = {
    InterventionType.SCENE_DIRECTIVE: "scene",
    InterventionType.CHARACTER_DIRECTIVE: "character",
    InterventionType.WORLD_DIRECTIVE: "world",
    InterventionType.EVENT_INJECTION: "scene",
    InterventionType.PROBABILITY_BIAS: "roll",
    InterventionType.TONE_CONTROL: "scene",
    InterventionType.PACING_CONTROL: "scene",
    InterventionType.REVEAL_CONTROL: "reader_state",
    InterventionType.HIDDEN_TRUTH_EDIT: "gm_vault",
    InterventionType.CANON_EDIT: "canon",
    InterventionType.DICE_ROLL_REQUEST: "roll",
    InterventionType.STOP_CONDITION: "world",
    InterventionType.SCENE_PIVOT: "scene",
    InterventionType.RELATIONSHIP_EDIT: "relationship",
    InterventionType.MEMORY_EDIT: "character",
}

# GM-authored structured directives default to gm_only (a GM note, not inherently reader
# visible) except the two types that are inherently about disclosure/established fact.
DEFAULT_VISIBILITY: dict[InterventionType, Visibility] = {
    intervention_type: Visibility.GM_ONLY for intervention_type in InterventionType
} | {
    InterventionType.REVEAL_CONTROL: Visibility.READER,
    InterventionType.CANON_EDIT: Visibility.CANON,
}
