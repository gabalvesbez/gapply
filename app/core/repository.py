"""Consulta comum: carrega um registro ou informa que não existe."""
from fastapi import HTTPException


def require(db, model, id):
    item = db.get(model, id)
    if item is None:
        raise HTTPException(404, "Registro não encontrado.")
    return item
