import asyncio
import json
import logging
import xml.etree.ElementTree as ET
import websockets
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from dbus_next.message import Message
from dbus_next.introspection import Node
from pulsectl_asyncio import PulseAsync

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SERVER_WS_URL = "ws://192.168.1.108:8337/ws/agent"

MPRIS_PREFIX = "org.mpris.MediaPlayer2"
MPRIS_INTERFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"


class LinuxMediaAgent:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.bus: MessageBus = None
        self.pulse: PulseAsync = None
        self.ws = None

        self.target_player_bus_name = "auto"
        self.current_player_bus_name = None
        self.player_proxy = None
        self.props_interface = None

        self.state = {
            "type": "state_update",
            "title": "Нічого не грає",
            "artist": "—",
            "is_playing": False,
            "volume": 50,
            "available_players": [],
        }

    async def init_dbus_and_pulse(self):
        """Ініціалізація підключень до DBus та PulseAudio/PipeWire."""
        self.bus = await MessageBus(bus_type=BusType.SESSION).connect()
        logging.info("Підключено до DBus Session Bus.")

        self.pulse = PulseAsync("media-agent")
        await self.pulse.connect()
        logging.info("Підключено до PulseAudio/PipeWire.")

        asyncio.create_task(self.listen_volume_changes())
        asyncio.create_task(self.poll_mpris_loop())

    # ================= MPRIS / DBus Логіка =================

    async def get_all_mpris_players(self) -> list:
        """Повертає список усіх зареєстрованих MPRIS-плеєрів."""
        try:
            reply = await self.bus.call(
                Message(
                    destination="org.freedesktop.DBus",
                    path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus",
                    member="ListNames",
                )
            )
            names = reply.body[0]
            # Дозволяємо всі сервіси, що починаються з org.mpris.MediaPlayer2,
            # включаючи chrome, chromium, brave, vivaldi та plasma-browser-integration
            return [n for n in names if n.startswith(MPRIS_PREFIX)]
        except Exception as e:
            logging.error(f"Помилка отримання списку DBus імен: {e}")
            return []

    async def find_active_player(self):
        """Шукає та підключається до обраного або доступного MPRIS-плеєра."""
        mpris_names = await self.get_all_mpris_players()
        self.state["available_players"] = mpris_names

        if not mpris_names:
            self._reset_player_state()
            return False

        if self.target_player_bus_name != "auto" and self.target_player_bus_name in mpris_names:
            target_list = [self.target_player_bus_name]
        else:
            target_list = mpris_names

        for bus_name in target_list:
            try:
                intro_reply = await self.bus.call(
                    Message(
                        destination=bus_name,
                        path="/org/mpris/MediaPlayer2",
                        interface="org.freedesktop.DBus.Introspectable",
                        member="Introspect",
                    )
                )
                xml_data = intro_reply.body[0]

                root = ET.fromstring(xml_data)
                for node in root.findall(".//node[@flags]"):
                    del node.attrib["flags"]
                clean_xml = ET.tostring(root, encoding="unicode")

                intro_node = Node.parse(clean_xml)
                player_proxy = self.bus.get_proxy_object(
                    bus_name, "/org/mpris/MediaPlayer2", intro_node
                )
                props_interface = player_proxy.get_interface(PROPERTIES_INTERFACE)

                if bus_name != self.current_player_bus_name:
                    self.current_player_bus_name = bus_name
                    self.player_proxy = player_proxy
                    self.props_interface = props_interface
                    self.props_interface.on_properties_changed(self._on_mpris_properties_changed)
                    logging.info(f"Знайдено та підключено медіаплеєр: {bus_name}")

                return True
            except Exception as e:
                logging.debug(f"Не вдалося ініціалізувати {bus_name}: {e}")
                continue

        self._reset_player_state()
        return False

    def _reset_player_state(self):
        self.current_player_bus_name = None
        self.player_proxy = None
        self.props_interface = None
        self.state["title"] = "Нічого не грає"
        self.state["artist"] = "—"
        self.state["is_playing"] = False

    def _on_mpris_properties_changed(self, interface_name, changed_properties, invalidated_properties):
        if interface_name == MPRIS_INTERFACE:
            asyncio.create_task(self.update_and_send_state())

    async def fetch_mpris_state(self):
        if not self.props_interface:
            if not await self.find_active_player():
                return

        try:
            playback_status_variant = await self.props_interface.call_get(MPRIS_INTERFACE, "PlaybackStatus")
            metadata_variant = await self.props_interface.call_get(MPRIS_INTERFACE, "Metadata")

            playback_status = playback_status_variant.value
            metadata = metadata_variant.value

            self.state["is_playing"] = (playback_status == "Playing")

            title = metadata.get("xesam:title")
            self.state["title"] = title.value if title else "Невідомий трек"

            artist = metadata.get("xesam:artist")
            if artist and artist.value:
                self.state["artist"] = ", ".join(artist.value)
            else:
                self.state["artist"] = "Невідомий виконавець"

        except Exception as e:
            logging.error(f"Помилка зчитування MPRIS стану: {e}")
            self.current_player_bus_name = None
            self.player_proxy = None
            self.props_interface = None
            await self.find_active_player()

    async def poll_mpris_loop(self):
        while True:
            await asyncio.sleep(3)
            old_players = list(self.state["available_players"])
            old_title = self.state["title"]
            old_playing = self.state["is_playing"]

            await self.fetch_mpris_state()

            if (old_players != self.state["available_players"] or 
                old_title != self.state["title"] or 
                old_playing != self.state["is_playing"]):
                await self.send_state()

    # ================= PulseAudio / Гучність =================

    async def get_system_volume(self):
        try:
            server_info = await self.pulse.server_info()
            sink = await self.pulse.get_sink_by_name(server_info.default_sink_name)
            vol_percent = round(sink.volume.value_flat * 100)
            self.state["volume"] = min(vol_percent, 100)
        except Exception as e:
            logging.error(f"Помилка зчитування гучності: {e}")

    async def set_system_volume(self, percent: int):
        try:
            server_info = await self.pulse.server_info()
            sink = await self.pulse.get_sink_by_name(server_info.default_sink_name)
            new_volume = max(0.0, min(1.0, percent / 100.0))
            await self.pulse.volume_set_all_chans(sink, new_volume)
            self.state["volume"] = percent
            await self.send_state()
        except Exception as e:
            logging.error(f"Помилка встановлення гучності: {e}")

    async def listen_volume_changes(self):
        async for event in self.pulse.subscribe_events("sink"):
            if event.t == "change":
                old_vol = self.state["volume"]
                await self.get_system_volume()
                if old_vol != self.state["volume"]:
                    await self.send_state()

    # ================= Керування відтворенням =================

    async def handle_command(self, command: dict):
        action = command.get("action")

        if action == "select_player":
            self.target_player_bus_name = command.get("value", "auto")
            self.current_player_bus_name = None
            self.player_proxy = None
            self.props_interface = None
            await self.update_and_send_state()
            return

        if action == "set_volume":
            val = command.get("value", 50)
            await self.set_system_volume(val)
            return

        if not self.player_proxy:
            await self.find_active_player()

        if not self.player_proxy:
            logging.warning("Команда отримана, але активний плеєр не знайдено.")
            return

        try:
            mpris_player = self.player_proxy.get_interface(MPRIS_INTERFACE)

            if action == "play_pause":
                await mpris_player.call_play_pause()
            elif action == "next":
                await mpris_player.call_next()
            elif action == "previous":
                await mpris_player.call_previous()

            await asyncio.sleep(0.15)
            await self.update_and_send_state()

        except Exception as e:
            logging.error(f"Помилка виконання команди {action}: {e}")

    # ================= Синхронізація з сервером =================

    async def update_and_send_state(self):
        await self.fetch_mpris_state()
        await self.get_system_volume()
        self.state["available_players"] = await self.get_all_mpris_players()
        await self.send_state()

    async def send_state(self):
        if self.ws:
            try:
                await self.ws.send(json.dumps(self.state))
            except Exception as e:
                logging.error(f"Помилка надсилання стану: {e}")

    async def run(self):
        await self.init_dbus_and_pulse()

        while True:
            try:
                logging.info(f"Підключення до WebSocket сервера: {self.server_url}")
                async with websockets.connect(self.server_url) as ws:
                    self.ws = ws
                    logging.info("Успішно підключено до WebSocket сервера!")

                    await self.update_and_send_state()

                    async for message in ws:
                        try:
                            command = json.loads(message)
                            logging.info(f"Отримано команду: {command}")
                            await self.handle_command(command)
                        except json.JSONDecodeError:
                            logging.error("Отримано некоректний JSON")

            except (websockets.exceptions.ConnectionClosedError, OSError) as e:
                logging.warning(f"З'єднання втрачено ({e}). Повторна спроба через 5 секунд...")
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"Критична помилка в циклі агента: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    agent = LinuxMediaAgent(SERVER_WS_URL)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logging.info("Агент зупинений користувачем.")