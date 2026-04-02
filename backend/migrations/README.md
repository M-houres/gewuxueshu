# Migration Notes

- Dev bootstrap can rely on SQLAlchemy `Base.metadata.create_all` in app startup.
- Production should execute `migrations/001_initial_schema.sql` as baseline schema.
- Later migrations can be appended under this directory with version numbers.

