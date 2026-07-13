"""``living-narrative`` typer app (cli/spec.md, project-workspace/spec.md).

Each subcommand is a thin call into an engine-layer capability (design.md D1): no state
diff computation, visibility judgment, or stop-condition logic lives in this package.
"""

import typer

from living_narrative.cli import auto as _auto
from living_narrative.cli import backup as _backup
from living_narrative.cli import branch as _branch
from living_narrative.cli import doctor as _doctor
from living_narrative.cli import export as _export
from living_narrative.cli import init as _init
from living_narrative.cli import metrics as _metrics
from living_narrative.cli import review as _review
from living_narrative.cli import rollback as _rollback
from living_narrative.cli import serve as _serve
from living_narrative.cli import status as _status
from living_narrative.cli import turn as _turn

# Imported as modules (not `from living_narrative.cli.turn import turn`, etc.): each
# submodule's public function shares its module's name, and binding that name directly
# into this package's namespace would shadow the submodule attribute (`living_narrative
# .cli.turn` would resolve to the function, not the module) for anyone importing it later.
app = typer.Typer(name="living-narrative", no_args_is_help=True)

app.command("init")(_init.init)
app.command("turn")(_turn.turn)
app.command("auto")(_auto.auto)
app.command("review")(_review.review)
app.command("status")(_status.status)
app.command("metrics")(_metrics.metrics)
app.command("serve")(_serve.serve)
app.command("rollback")(_rollback.rollback)
app.command("branch")(_branch.branch)
app.command("doctor")(_doctor.doctor)
app.command("backup")(_backup.backup)
app.command("restore")(_backup.restore)
app.add_typer(_export.app, name="export")

__all__ = ["app"]

if __name__ == "__main__":
    app()
