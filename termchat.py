#!/usr/bin/env python3
"""TermChat - aplikasi chat TUI (Textual) untuk API OpenAI-compatible.

Tanpa server tambahan, tanpa SDK openai (hanya textual + httpx, murni Python).
Data disimpan di ~/.config/termchat/ (config.json, chats.json).
"""
import asyncio
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import httpx
from rich.markdown import Markdown
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (Button, Footer, Header, Input, Label, ListItem,
                             ListView, Static)

HOME = Path(os.environ.get("TERMCHAT_HOME", Path.home() / ".config" / "termchat"))
CONF_FILE = HOME / "config.json"
DATA_FILE = HOME / "chats.json"
MAX_CONTEXT = 40  # jumlah pesan terakhir yang dikirim ke API
NARROW = 90       # lebar (kolom) di bawah ini = mode HP, sidebar disembunyikan

DEFAULT_CONF = {
    "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model": "gpt-4o-mini",
    "system": "Kamu asisten yang membantu. Jawab dalam bahasa Indonesia, ringkas dan jelas.",
    "temperature": None,
}


def load_json(path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return default


def save_json(path, data):
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    os.replace(tmp, path)
    if path == CONF_FILE:
        os.chmod(path, 0o600)  # API key: hanya bisa dibaca pemilik


def endpoint(base, path):
    base = base.strip().rstrip("/")
    return base if base.endswith(path) else base + path


def headers(key):
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def new_chat():
    return {"id": uuid.uuid4().hex[:8], "title": "Chat baru", "messages": [],
            "updated": time.time()}


class Bubble(Static):
    """Satu gelembung pesan."""

    def __init__(self, role, body=""):
        self.msg_role, self.msg_text = role, body
        super().__init__(self._make(False), classes=f"bubble {role}")
        self.border_title = {"user": "Kamu", "assistant": "AI"}.get(role, "")

    def _make(self, streaming):
        if self.msg_role == "assistant" and not streaming and self.msg_text:
            return Markdown(self.msg_text)
        return Text(self.msg_text + ("▌" if streaming else ""))

    def set_text(self, body, streaming=False):
        self.msg_text = body
        self.update(self._make(streaming))


class ModelPicker(ModalScreen):
    BINDINGS = [("escape", "dismiss(None)", "Batal")]

    def __init__(self, ids):
        super().__init__()
        self.ids = ids

    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            yield Label(f"{len(self.ids)} model - pilih satu")
            yield ListView(*[ListItem(Label(i, markup=False)) for i in self.ids])

    @on(ListView.Selected)
    def pick(self, e):
        self.dismiss(self.ids[e.list_view.index])


class SettingsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss(None)", "Batal")]

    def __init__(self, conf):
        super().__init__()
        self.conf = conf

    def compose(self) -> ComposeResult:
        c = self.conf
        temp = "" if c.get("temperature") is None else str(c["temperature"])
        with VerticalScroll(id="settings"):
            yield Label("Pengaturan API (OpenAI-compatible)", id="set-title")
            yield Label("Base URL")
            yield Input(c["base_url"], id="base_url")
            yield Label("API key (boleh kosong untuk server lokal)")
            yield Input(c["api_key"], password=True, id="api_key")
            yield Label("Model")
            yield Input(c["model"], id="model")
            yield Label("System prompt")
            yield Input(c["system"], id="system")
            yield Label("Temperature (kosong = default penyedia)")
            yield Input(temp, id="temperature")
            with Horizontal(id="set-btns"):
                yield Button("Simpan", id="save", variant="success")
                yield Button("Daftar model", id="models")
                yield Button("Batal", id="cancel")

    def val(self, i):
        return self.query_one(f"#{i}", Input).value.strip()

    @on(Button.Pressed, "#cancel")
    def cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#save")
    def save(self):
        t = self.val("temperature")
        try:
            temp = float(t) if t else None
        except ValueError:
            self.app.notify("Temperature harus berupa angka", severity="error")
            return
        self.dismiss({"base_url": self.val("base_url"), "api_key": self.val("api_key"),
                      "model": self.val("model"), "system": self.val("system"),
                      "temperature": temp})

    @on(Button.Pressed, "#models")
    def models(self):
        self.fetch_models()

    @work(exclusive=True)
    async def fetch_models(self):
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.get(endpoint(self.val("base_url"), "/models"),
                                headers=headers(self.val("api_key")))
                r.raise_for_status()
                ids = sorted(m["id"] for m in r.json()["data"])
        except Exception as e:
            self.app.notify(f"Gagal ambil model: {e}", severity="error")
            return
        if not ids:
            self.app.notify("Daftar model kosong", severity="warning")
            return

        def chosen(mid):
            if mid:
                self.query_one("#model", Input).value = mid

        self.app.push_screen(ModelPicker(ids), chosen)


class TermChat(App):
    TITLE = "TermChat"
    BINDINGS = [
        Binding("ctrl+n", "new_chat", "Baru"),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+r", "regenerate", "Ulang"),
        Binding("ctrl+o", "settings", "Setelan"),
        Binding("escape", "stop", "Stop"),
    ]
    CSS = """
    #body { height: 1fr; }
    #sidebar { width: 26; border-right: tall $primary; }
    #chats { height: 1fr; }
    #main { width: 1fr; }
    #log { height: 1fr; padding: 0 1; scrollbar-size-vertical: 1; }
    .bubble { margin-top: 1; padding: 0 1; }
    .bubble.user { border: round $accent; }
    .bubble.assistant { border: round $success; }
    .bubble.error { border: round $error; }
    .hint { color: grey; text-style: italic; padding: 1; }
    #toolbar { height: 1; }
    Button.flat { border: none; height: 1; min-width: 0; padding: 0 1; margin: 0 1 0 0; }
    #s-new { width: 100%; margin: 0; }
    SettingsScreen, ModelPicker { align: center middle; }
    #settings { width: 92%; max-width: 72; height: auto; max-height: 92%;
                border: thick $primary; background: $surface; padding: 0 1; }
    #set-title { text-style: bold; padding-bottom: 1; }
    #set-btns { height: 3; margin-top: 1; }
    #set-btns Button { min-width: 8; margin-right: 1; }
    #picker { width: 92%; max-width: 60; height: 80%; border: thick $primary;
              background: $surface; padding: 0 1; }
    """
    ACTIONS = {"b-new": "new_chat", "s-new": "new_chat", "b-side": "toggle_sidebar",
               "b-stop": "stop", "b-redo": "regenerate", "b-copy": "copy",
               "b-del": "delete_chat", "b-set": "settings"}
    TOOLBAR = [("b-side", "☰"), ("b-new", "Baru"), ("b-stop", "Stop"),
               ("b-redo", "Ulang"), ("b-copy", "Salin"), ("b-del", "Hapus"),
               ("b-set", "⚙")]

    def __init__(self):
        super().__init__()
        self.conf = {**DEFAULT_CONF, **load_json(CONF_FILE, {})}
        self.chats = load_json(DATA_FILE, [])
        self.cur_id = None
        self.busy = False
        self.del_armed = False

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Button("+ Chat baru", id="s-new", classes="flat")
                yield ListView(id="chats")
            with Vertical(id="main"):
                yield VerticalScroll(id="log")
                with Horizontal(id="toolbar"):
                    for bid, label in self.TOOLBAR:
                        yield Button(label, id=bid, classes="flat")
                yield Input(placeholder="Ketik pesan, Enter untuk kirim…", id="prompt")
        yield Footer()

    async def on_mount(self):
        if self.narrow:
            self.query_one("#sidebar").display = False
        if not self.chats:
            self.chats.append(new_chat())
        self.chats.sort(key=lambda c: c.get("updated", 0), reverse=True)
        await self.open_chat(self.chats[0]["id"])
        self.set_busy(False)
        self.query_one("#prompt").focus()
        if not CONF_FILE.exists() and not self.conf["api_key"]:
            self.notify("Isi dulu Base URL, API key, dan model.")
            await self.action_settings()

    @property
    def narrow(self):
        return self.size.width < NARROW

    def chat(self):
        return next(c for c in self.chats if c["id"] == self.cur_id)

    def set_busy(self, v):
        self.busy = v
        self.query_one("#b-stop", Button).disabled = not v

    def persist(self):
        save_json(DATA_FILE, self.chats)

    # ---------- daftar & isi chat ----------
    async def refresh_chats(self):
        self.chats.sort(key=lambda c: c.get("updated", 0), reverse=True)
        lv = self.query_one("#chats", ListView)
        items = []
        for c in self.chats:
            it = ListItem(Label(c["title"], markup=False))
            it.chat_id = c["id"]
            items.append(it)
        await lv.clear()
        await lv.extend(items)
        lv.index = next(i for i, c in enumerate(self.chats) if c["id"] == self.cur_id)

    async def open_chat(self, cid):
        self.cur_id = cid
        view = self.query_one("#log", VerticalScroll)
        await view.remove_children()
        msgs = self.chat()["messages"]
        if msgs:
            await view.mount_all([Bubble(m["role"], m["content"]) for m in msgs])
        else:
            await view.mount(Static("Mulai percakapan baru…", classes="hint"))
        view.scroll_end(animate=False)
        self.sub_title = self.chat()["title"]
        await self.refresh_chats()

    @on(ListView.Selected, "#chats")
    async def pick_chat(self, e):
        cid = getattr(e.item, "chat_id", None)
        if cid and cid != self.cur_id:
            self.workers.cancel_group(self, "stream")
            await self.open_chat(cid)
        if self.narrow:
            self.query_one("#sidebar").display = False
        self.query_one("#prompt").focus()

    # ---------- kirim & streaming ----------
    @on(Input.Submitted, "#prompt")
    async def submit(self, e):
        text = e.value.strip()
        if not text:
            return
        if self.busy:
            self.notify("Masih menjawab. Tekan Stop dulu.", severity="warning")
            return
        e.input.value = ""
        chat = self.chat()
        chat["messages"].append({"role": "user", "content": text})
        chat["updated"] = time.time()
        if len(chat["messages"]) == 1:
            chat["title"] = text.replace("\n", " ")[:28]
            self.sub_title = chat["title"]
        self.persist()
        view = self.query_one("#log", VerticalScroll)
        await view.query(".hint").remove()
        await view.mount(Bubble("user", text))
        view.scroll_end(animate=False)
        await self.refresh_chats()
        self.stream_reply()

    @work(exclusive=True, group="stream")
    async def stream_reply(self):
        chat = self.chat()
        view = self.query_one("#log", VerticalScroll)
        bubble = Bubble("assistant", "")
        bubble.set_text("", streaming=True)
        await view.mount(bubble)
        view.scroll_end(animate=False)
        self.set_busy(True)

        msgs = [{"role": "system", "content": self.conf["system"]}] if self.conf["system"] else []
        msgs += chat["messages"][-MAX_CONTEXT:]
        payload = {"model": self.conf["model"], "messages": msgs, "stream": True}
        if self.conf.get("temperature") is not None:
            payload["temperature"] = self.conf["temperature"]

        buf, err, last = "", None, 0.0
        try:
            timeout = httpx.Timeout(connect=15, read=120, write=30, pool=15)
            async with httpx.AsyncClient(timeout=timeout) as c:
                async with c.stream("POST", endpoint(self.conf["base_url"], "/chat/completions"),
                                    headers=headers(self.conf["api_key"]), json=payload) as r:
                    if r.status_code >= 400:
                        body = (await r.aread()).decode("utf-8", "replace")
                        raise RuntimeError(f"HTTP {r.status_code}: {body[:400]}")
                    async for line in r.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            delta = json.loads(data)["choices"][0]["delta"].get("content")
                        except (KeyError, IndexError, ValueError, TypeError, AttributeError):
                            continue
                        if delta:
                            buf += delta
                            now = time.monotonic()
                            if now - last > 0.08:  # batasi redraw supaya HP tetap mulus
                                bubble.set_text(buf, streaming=True)
                                view.scroll_end(animate=False)
                                last = now
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            err = f"{type(ex).__name__}: {ex}"
        finally:
            if buf:
                chat["messages"].append({"role": "assistant", "content": buf})
                chat["updated"] = time.time()
                self.persist()
            if err:
                bubble.add_class("error")
                bubble.update(Text(buf + f"\n⚠ {err}"))
            elif buf:
                bubble.set_text(buf)
            else:
                bubble.remove()
            view.scroll_end(animate=False)
            self.set_busy(False)

    # ---------- aksi / tombol ----------
    @on(Button.Pressed)
    async def on_btn(self, e):
        name = self.ACTIONS.get(e.button.id or "")
        if name:
            await self.run_action(name)

    def hide_sidebar_if_narrow(self):
        if self.narrow:
            self.query_one("#sidebar").display = False

    async def action_new_chat(self):
        self.workers.cancel_group(self, "stream")
        if self.chat()["messages"]:
            ch = new_chat()
            self.chats.insert(0, ch)
            self.persist()
            await self.open_chat(ch["id"])
        self.hide_sidebar_if_narrow()
        self.query_one("#prompt").focus()

    def action_toggle_sidebar(self):
        sb = self.query_one("#sidebar")
        sb.display = not sb.display

    def action_stop(self):
        self.workers.cancel_group(self, "stream")

    async def action_regenerate(self):
        if self.busy:
            return
        msgs = self.chat()["messages"]
        if msgs and msgs[-1]["role"] == "assistant":
            msgs.pop()
        if not msgs or msgs[-1]["role"] != "user":
            self.notify("Belum ada pesan untuk diulang.", severity="warning")
            return
        self.persist()
        await self.open_chat(self.cur_id)
        self.stream_reply()

    def action_copy(self):
        last = next((m["content"] for m in reversed(self.chat()["messages"])
                     if m["role"] == "assistant"), None)
        if not last:
            self.notify("Belum ada jawaban untuk disalin.", severity="warning")
            return
        if shutil.which("termux-clipboard-set"):
            try:
                subprocess.run(["termux-clipboard-set"], input=last.encode(), timeout=5, check=True)
                self.notify("Jawaban terakhir disalin.")
                return
            except Exception:
                pass
        self.copy_to_clipboard(last)
        self.notify("Disalin. Jika tak masuk clipboard: pkg install termux-api")

    async def action_delete_chat(self):
        if not self.del_armed:
            self.del_armed = True
            self.notify("Tekan Hapus sekali lagi untuk konfirmasi.", timeout=3)
            self.set_timer(3, lambda: setattr(self, "del_armed", False))
            return
        self.del_armed = False
        self.workers.cancel_group(self, "stream")
        self.chats = [c for c in self.chats if c["id"] != self.cur_id]
        if not self.chats:
            self.chats.append(new_chat())
        self.persist()
        await self.open_chat(self.chats[0]["id"])

    async def action_settings(self):
        def done(result):
            if result:
                self.conf = {**self.conf, **result}
                save_json(CONF_FILE, self.conf)
                self.notify(f"Tersimpan. Model: {self.conf['model']}")
            self.query_one("#prompt").focus()

        await self.push_screen(SettingsScreen(self.conf), done)


def main():
    TermChat().run()


if __name__ == "__main__":
    main()
