# Skill: Add a Liquibase Migration

Use this skill when adding new columns, tables, indexes, or constraints to the database.

## Rules

- Never modify an existing changeset — Liquibase checksums will fail. Always add a new file.
- File naming: `v{NNN}__{description}.yaml` where `NNN` is the next sequential number (zero-padded to 3 digits).
- Register the new file in `backend/db/changelog/db.changelog-root.yaml` as a new `- include:` entry.
- Use separate changesets for separate concerns (e.g. one changeset per `addColumn`).
- Changeset IDs must be globally unique — use the pattern `{vNNN}-{description}`.

## Template

```yaml
# v{NNN} — {Short description}

databaseChangeLog:

  - changeSet:
      id: {vNNN}-{change-description}
      author: asvs
      changes:
        - addColumn:
            tableName: {table}
            columns:
              - column:
                  name: {column_name}
                  type: {JSONB | TEXT | VARCHAR(n) | BOOLEAN | SMALLINT | BIGINT | UUID | TIMESTAMPTZ}
                  # add defaultValue / constraints only if required
```

## After creating the file

Add it to the root changelog:

```yaml
# db.changelog-root.yaml
  - include:
      file: changelog/releases/v{NNN}__{description}.yaml
```

Apply with:

```bash
cd backend && docker compose --profile migrate up liquibase
```
