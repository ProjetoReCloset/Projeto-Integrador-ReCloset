from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Categoria
from app.schemas import CategoriaPublica

router = APIRouter(prefix="/categorias", tags=["Categorias"])


@router.get("", response_model=list[CategoriaPublica], summary="Listar categorias")
def listar_categorias(db: Session = Depends(get_db)):
    return db.scalars(select(Categoria).order_by(Categoria.id)).all()
