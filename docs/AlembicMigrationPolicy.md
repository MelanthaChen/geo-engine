# Alembic Migration Policy

Alembic revisions are immutable after they may have been applied outside a disposable local database.

Once a revision may exist in a shared, staging, or production database, never edit that revision to add, remove, or reinterpret schema operations. Create a new forward migration instead. When an earlier revision was already edited, the repair migration must inspect the live schema, add only missing objects, preserve existing data, and be tested against both a clean replay and a simulated stale database carrying the earlier revision history.

Never use `Base.metadata.create_all()`, revision stamping, exception swallowing, or destructive downgrade/rebuild operations as a production schema-repair substitute.
