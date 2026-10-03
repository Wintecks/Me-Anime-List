import json
import logging
import os
from typing import Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CONFIG_FILE = "config.json"
app = FastAPI(title="Media Control WebSocket Hub")


class ConfigManager:
    @staticmethod
    def load_config() -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Помилка зчитання {CONFIG_FILE}: {e}")
        return {"theme": "dark", "selected_player": "auto"}

    @staticmethod
    def save_config(config: dict):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Помилка збереження {CONFIG_FILE}: {e}")


class ConnectionManager:
    def __init__(self):
        self.active_clients: Set[WebSocket] = set()
        self.agent_websocket: Optional[WebSocket] = None
        self.config = ConfigManager.load_config()
        self.latest_state: Optional[dict] = None

    @property
    def is_agent_connected(self) -> bool:
        return self.agent_websocket is not None

    async def connect_client(self, websocket: WebSocket):
        await websocket.accept()
        self.active_clients.add(websocket)
        logging.info(f"Клієнт підключився. Всього клієнтів: {len(self.active_clients)}")
        
        # Надсилаємо початкові налаштування та актуальний стан агента
        init_payload = {
            "type": "init_config",
            "theme": self.config.get("theme", "dark"),
            "selected_player": self.config.get("selected_player", "auto"),
            "agent_connected": self.is_agent_connected,
            "media_state": self.latest_state
        }
        await websocket.send_json(init_payload)

    def disconnect_client(self, websocket: WebSocket):
        self.active_clients.remove(websocket)
        logging.info(f"Клієнт відключився. Залишилось клієнтів: {len(self.active_clients)}")

    async def connect_agent(self, websocket: WebSocket):
        await websocket.accept()
        if self.agent_websocket and self.agent_websocket != websocket:
            logging.warning("Підключився новий агент, закриваємо старе з'єднання.")
            await self.agent_websocket.close()
            
        self.agent_websocket = websocket
        logging.info("Агент ПК успішно підключився до сервера.")
        
        # Сповіщаємо всі веб-клієнти, що агент ПК активний
        await self.broadcast_to_clients({
            "type": "agent_status",
            "agent_connected": True
        })

        # Передаємо агенту збережений плеєр
        await self.send_to_agent({
            "action": "select_player", 
            "value": self.config.get("selected_player", "auto")
        })

    async def disconnect_agent(self, websocket: WebSocket):
        if self.agent_websocket == websocket:
            self.agent_websocket = None
            logging.info("Агент ПК відключився.")
            
            # Сповіщаємо веб-клієнти про відключення агента
            await self.broadcast_to_clients({
                "type": "agent_status",
                "agent_connected": False
            })

    async def broadcast_to_clients(self, data: dict):
        if data.get("type") == "state_update":
            self.latest_state = data
            
        disconnected = set()
        for client in self.active_clients:
            try:
                await client.send_json(data)
            except Exception as e:
                logging.error(f"Помилка відправки клієнту: {e}")
                disconnected.add(client)
        
        for client in disconnected:
            self.active_clients.remove(client)

    async def send_to_agent(self, command: dict):
        if self.agent_websocket:
            try:
                await self.agent_websocket.send_json(command)
            except Exception as e:
                logging.error(f"Не вдалося відправити команду агенту: {e}")
                self.agent_websocket = None
                await self.broadcast_to_clients({
                    "type": "agent_status",
                    "agent_connected": False
                })
        else:
            logging.warning("Спроба відправити команду, але агент ПК не підключений!")


manager = ConnectionManager()

@app.get("/")
async def get_index():
    return FileResponse("index.html")

# ================= WebSocket Endpoints =================

@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    await manager.connect_agent(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            data["agent_connected"] = True
            await manager.broadcast_to_clients(data)
    except WebSocketDisconnect:
        await manager.disconnect_agent(websocket)
    except Exception as e:
        logging.error(f"Помилка в WebSocket агента: {e}")
        await manager.disconnect_agent(websocket)


@app.websocket("/ws/client")
async def websocket_client_endpoint(websocket: WebSocket):
    await manager.connect_client(websocket)
    try:
        while True:
            command = await websocket.receive_json()
            action = command.get("action")

            if action == "set_theme":
                theme = command.get("value", "dark")
                manager.config["theme"] = theme
                ConfigManager.save_config(manager.config)
                await manager.broadcast_to_clients({"type": "theme_changed", "theme": theme})

            elif action == "select_player":
                player = command.get("value", "auto")
                manager.config["selected_player"] = player
                ConfigManager.save_config(manager.config)
                await manager.send_to_agent(command)
                await manager.broadcast_to_clients({"type": "player_changed", "selected_player": player})

            else:
                logging.info(f"Отримано команду від веб-клієнта: {command}")
                await manager.send_to_agent(command)

    except WebSocketDisconnect:
        manager.disconnect_client(websocket)
    except Exception as e:
        logging.error(f"Помилка в WebSocket клієнта: {e}")
        manager.disconnect_client(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8337, reload=True)