You're in a `uv` project, so before running anything from venv, better use `uv run`. Add dependencies with `uv add`.
Project uses alembic for migrations, so to create migrations, first update models and then use `uv run alembic revision --autogenerate` to autogenerate the migration, but do not apply it yourself.
After developing the feature, ask confirmation to implement proper documentation under `docs/features/feature.md`.
Before performing any updates, make sure to read `docs/design/requirements.md` (more new and detailed) and `docs/design/architecture.md` (older and more general) for implementaion details and contraints.
And if `docs/features/` contain any relevant features, read it as well as their codefiles before using them.
DO NOT use git worktrees or whatever, git is FULLY managed by the user.
