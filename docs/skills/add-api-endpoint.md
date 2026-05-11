# Skill: Add a New API Endpoint

Use this skill when adding a route to the FastAPI backend.

## Rules

- Handlers are **sync** — never `async def` for route handlers (SQLAlchemy sync engine).
- Always use `Annotated[Session, Depends(get_db)]` for the DB session parameter.
- Return Pydantic response models — never raw dicts or ORM objects directly.
- Use `model_validate(orm_obj)` (not `.from_orm()`) for ORM → schema conversion.
- If reading from the DB and a Redis cache exists, check Redis first.
- New routers must be registered in `backend/app/main.py` with `app.include_router(…, prefix="/api")`.

## Minimal route template

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schemas import MyResponse

router = APIRouter(tags=["my-tag"])


@router.get("/my-resource/{resource_id}", response_model=MyResponse)
def get_my_resource(
    resource_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> MyResponse:
    obj = db.query(MyModel).filter(MyModel.id == resource_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return MyResponse.model_validate(obj)
```

## Pydantic schema notes

- Use `model_config = {"from_attributes": True, "populate_by_name": True}`.
- If the ORM field name differs from the JSON key, use `Field(validation_alias="orm_field_name")`.
  - `validation_alias` — reads from the ORM attribute name, keeps the declared field name in JSON output.
  - Do NOT use plain `alias` if you need the JSON key to differ from the ORM attribute.

## Register the router

```python
# backend/app/main.py
from app.routers import my_module
app.include_router(my_module.router, prefix="/api")
```
