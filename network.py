import socket
import threading
import json
import time
import math
from collections import OrderedDict

PORT = 54321
BUFSIZE = 65536
TIMEOUT = 0.05
MAX_CLIENTS = 4


class NetworkEncoder(json.JSONEncoder):
    def default(self, obj):
        return str(obj)


def _serialize_state(game):
    players = []
    if hasattr(game, 'network_players'):
        for pid, pdata in game.network_players.items():
            players.append({
                "id": pid,
                "x": pdata.get("x", game.player_x),
                "y": pdata.get("y", game.player_y),
                "angle": pdata.get("angle", game.player_angle),
                "light_on": pdata.get("light_on", True),
                "color": pdata.get("color", [0, 240, 0]),
            })

    state = {
        "tick": getattr(game, '_network_tick', 0),
        "grid_size": game.grid_size,
        "map": game.map_grid,
        "cell_size": game.cell_size,
        "player_spawn": [game.spawn_x, game.spawn_y],
        "players": players,
        "static_lights": [
            {"x": l.x, "y": l.y, "radius_cells": l.radius_cells, "intensity": l.intensity, "color": list(l.color)}
            for l in game.static_lights
        ],
        "dynamic_objects": [
            {"x": o.x, "y": o.y, "light_radius": o.light_radius, "light_intensity": o.light_intensity,
             "color": list(o.color), "size": o.size}
            for o in game.dynamic_objects
        ],
        "bots": [
            {"x": b.x, "y": b.y, "angle": b.angle, "color": list(b.color), "state": b.state,
             "light_radius": b.light_radius, "light_intensity": b.light_intensity, "speed": b.speed}
            for b in game.bots
        ],
    }
    return json.dumps(state, cls=NetworkEncoder) + "\n"


def _serialize_input(client_id, keys, angle=0.0, light_on=True):
    return json.dumps({
        "id": client_id,
        "input": {
            "keys": keys,
            "angle": angle,
            "light_on": light_on,
        }
    }) + "\n"


class GameServer:
    def __init__(self, game, host="0.0.0.0", port=PORT):
        self.game = game
        self.host = host
        self.port = port
        self.clients = {}
        self.next_id = 1
        self.running = False
        self._lock = threading.Lock()
        self._server_sock = None

        game.network_mode = "server"
        game.network_players = {}
        game.network_server = self

    def start(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(MAX_CLIENTS)
        self._server_sock.settimeout(0.5)
        self.running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        print(f"[NET] Server started on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        with self._lock:
            for conn in list(self.clients.values()):
                try:
                    conn.close()
                except Exception:
                    pass
            self.clients.clear()
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        self.game.network_players.clear()
        print("[NET] Server stopped")

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self._server_sock.accept()
                conn.settimeout(TIMEOUT)
                with self._lock:
                    cid = self.next_id
                    self.next_id += 1
                    self.clients[cid] = conn
                    self.game.network_players[cid] = {
                        "x": self.game.spawn_x + 0.5 + random_offset(),
                        "y": self.game.spawn_y + 0.5 + random_offset(),
                        "angle": 0.0,
                        "light_on": True,
                        "color": _player_color(cid),
                    }
                t = threading.Thread(target=self._client_loop, args=(cid, conn), daemon=True)
                t.start()
                print(f"[NET] Client {cid} connected from {addr}")
            except socket.timeout:
                pass
            except OSError:
                break

    def _client_loop(self, cid, conn):
        buf = b""
        while self.running:
            try:
                data = conn.recv(BUFSIZE)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    self._handle_message(cid, line.decode("utf-8").strip())
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
        with self._lock:
            if cid in self.clients:
                del self.clients[cid]
            self.game.network_players.pop(cid, None)
        try:
            conn.close()
        except Exception:
            pass
        print(f"[NET] Client {cid} disconnected")

    def _handle_message(self, cid, msg):
        if not msg:
            return
        try:
            data = json.loads(msg)
            inp = data.get("input", {})
            keys = inp.get("keys", {})
            with self._lock:
                if cid in self.game.network_players:
                    p = self.game.network_players[cid]
                    angle = inp.get("angle", p.get("angle", 0.0))
                    p["angle"] = angle
                    if keys:
                        speed = 3.0
                        dx, dy = 0.0, 0.0
                        if keys.get("w"): dy = -speed * 0.05
                        if keys.get("s"): dy = speed * 0.05
                        if keys.get("a"): dx = -speed * 0.05
                        if keys.get("d"): dx = speed * 0.05
                        p["x"] = max(1, min(self.game.grid_size - 1, p["x"] + dx))
                        p["y"] = max(1, min(self.game.grid_size - 1, p["y"] + dy))
                    if "light_on" in inp:
                        p["light_on"] = inp["light_on"]
        except (json.JSONDecodeError, KeyError):
            pass

    def broadcast_state(self):
        state_str = _serialize_state(self.game)
        data = state_str.encode("utf-8")
        with self._lock:
            dead = []
            for cid, conn in self.clients.items():
                try:
                    conn.sendall(data)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    dead.append(cid)
            for cid in dead:
                if cid in self.clients:
                    del self.clients[cid]
                self.game.network_players.pop(cid, None)

    def get_client_count(self):
        with self._lock:
            return len(self.clients)


class GameClient:
    def __init__(self, host="127.0.0.1", port=PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.latest_state = None
        self.my_id = -1
        self._lock = threading.Lock()
        self.connected = False
        self._buf = b""

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        try:
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(TIMEOUT)
            self.connected = True
            self.running = True
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
            print(f"[NET] Connected to {self.host}:{self.port}")
            return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"[NET] Connection failed: {e}")
            return False

    def disconnect(self):
        self.running = False
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        print("[NET] Disconnected")

    def _recv_loop(self):
        while self.running:
            try:
                data = self.sock.recv(BUFSIZE)
                if not data:
                    break
                self._buf += data
                while b"\n" in self._buf:
                    line, self._buf = self._buf.split(b"\n", 1)
                    msg = line.decode("utf-8").strip()
                    if msg:
                        try:
                            state = json.loads(msg)
                            state["_players"] = state.get("players", [])
                            with self._lock:
                                self.latest_state = state
                                # Find my ID if not known
                                if self.my_id < 0 and state.get("players"):
                                    # First player is us
                                    pass
                        except json.JSONDecodeError:
                            pass
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
        self.connected = False

    def send_input(self, keys_set, angle=0.0, light_on=True):
        if not self.connected or not self.running:
            return
        key_dict = {}
        for k in ["w", "a", "s", "d", "l"]:
            key_dict[k] = k in keys_set
        msg = _serialize_input(self.my_id, key_dict, angle, light_on)
        try:
            self.sock.sendall(msg.encode("utf-8"))
        except (ConnectionResetError, BrokenPipeError, OSError):
            self.connected = False

    def get_state(self):
        with self._lock:
            return self.latest_state


def _player_color(cid):
    pal = [
        (0, 240, 0),
        (240, 60, 60),
        (60, 120, 240),
        (240, 200, 60),
    ]
    return pal[cid % len(pal)]


def random_offset():
    import random
    return random.uniform(-2, 2)
