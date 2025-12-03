import json
import time
import tempfile
import os
from pathlib import Path
from discord.ext import commands

FILE = Path(__file__).parent.parent / "data" / "sent_history.json"


class SentHistory:
    def __init__(self):
        self._path = FILE
        self._data = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def _atomic_write(self, data):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=self._path.stem, suffix=".tmp", dir=str(self._path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, str(self._path))
        except Exception:
            try:
                os.remove(tmp)
            except Exception:
                pass
            raise

    def has_been_sent(self, target_key: str, article_key: str, ttl_seconds: int = 7 * 24 * 3600) -> bool:
        now = int(time.time())
        sent = self._data.get(article_key, {})
        t = sent.get(target_key)
        if not t:
            return False
        if now - int(t) > ttl_seconds:
            # expired
            return False
        return True

    def mark_sent(self, target_key: str, article_key: str):
        now = int(time.time())
        if article_key not in self._data:
            self._data[article_key] = {}
        self._data[article_key][target_key] = now
        # atomic save
        try:
            self._atomic_write(self._data)
        except Exception:
            pass

    def prune_older_than(self, seconds: int):
        now = int(time.time())
        changed = False
        for a, targets in list(self._data.items()):
            for t, ts in list(targets.items()):
                if now - int(ts) > seconds:
                    del self._data[a][t]
                    changed = True
            if not self._data[a]:
                del self._data[a]
                changed = True
        if changed:
            try:
                self._atomic_write(self._data)
            except Exception:
                pass



class DedupeCog(commands.Cog):
    """Cog wrapper to expose SentHistory when extension is loaded."""

    def __init__(self, bot):
        self.bot = bot
        self.store = SentHistory()


async def setup(bot):
    await bot.add_cog(DedupeCog(bot))
