import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

DATA_FILE = Path("tiles.json")


# Модель даних для плитки
class Tile(BaseModel):
    id: int
    title: str
    desc: Optional[str] = ""
    url: str


# Функції роботи з JSON-файлом
def read_tiles() -> List[dict]:
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def write_tiles(tiles: List[dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tiles, f, ensure_ascii=False, indent=2)


# API Ендпоінти
@app.get("/api/tiles", response_model=List[Tile])
def get_tiles():
    """Отримати всі плитки із сервера"""
    return read_tiles()


@app.post("/api/tiles", response_model=Tile)
def create_tile(tile: Tile):
    """Зберегти нову плитку на сервері"""
    tiles = read_tiles()
    tiles.append(tile.dict())
    write_tiles(tiles)
    return tile


@app.delete("/api/tiles/{tile_id}")
def delete_tile(tile_id: int):
    """Видалити плитку за ID"""
    tiles = read_tiles()
    updated_tiles = [t for t in tiles if t["id"] != tile_id]
    write_tiles(updated_tiles)
    return {"status": "success"}


# Віддача фронтенду (статичні файли html/css/js з поточної папки)
app.mount("/", StaticFiles(directory=".", html=True), name="static")