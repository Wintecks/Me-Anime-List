import json
import os

import fastapi

app = fastapi.FastAPI()

from fastapi.middleware.cors import CORSMiddleware


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FILE_PATH = "data/setting.json"

@app.get("/loadSetting")
def getData():
    if not os.path.exists(FILE_PATH):
        os.makedirs("data", exist_ok=True)
        data = {}
        with open(FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        return data
    with open(FILE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)

@app.post("/saveSetting")
def saveData(newData: dict):
    with open(FILE_PATH, "w", encoding="utf-8") as file:
        json.dump(newData, file, ensure_ascii=False, indent=4)