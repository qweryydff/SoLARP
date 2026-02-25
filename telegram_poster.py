"""
Telegram integration – posts messages to all authorized users.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class TelegramPoster:
    def __init__(self):
        self.bot_token:  Optional[str] = None
        self.channel_id: str           = ""
        self.enabled:    bool          = False
        self._setup()

    def _setup(self):
        from config import TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

        if not TELEGRAM_ENABLED:
            logger.info("Telegram posting is DISABLED (set TELEGRAM_ENABLED=true in .env to enable)")
            return

        if not REQUESTS_AVAILABLE:
            logger.error("requests package is required. Run: pip install requests")
            return

        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN must be set in .env")
            return

        self.bot_token   = TELEGRAM_BOT_TOKEN
        self.channel_id  = TELEGRAM_CHANNEL_ID.strip() if TELEGRAM_CHANNEL_ID else ""
        self.enabled     = True
        if self.channel_id:
            logger.info(f"Telegram client ready ✅  (kanał: {self.channel_id})")
        else:
            logger.info("Telegram client ready ✅")

    def post(self, text: str) -> bool:
        """Send a message to ALL authorized users AND the channel (if configured)."""
        if not self.enabled:
            logger.info(f"[TELEGRAM DISABLED] Would send:\n{text}\n")
            return False

        from auth import get_all_authorized
        recipients = list(get_all_authorized())

        # Dodaj kanał do listy odbiorców jeśli jest skonfigurowany
        if self.channel_id and self.channel_id not in [str(r) for r in recipients]:
            recipients.append(self.channel_id)

        if not recipients:
            logger.info("No authorized Telegram users yet – nobody to send to")
            return False

        success = False
        for chat_id in recipients:
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                    timeout=10,
                )
                r.raise_for_status()
                logger.info(f"Telegram message sent to {chat_id}")
                success = True
            except Exception as e:
                logger.error(f"Telegram send failed for {chat_id}: {e}")

        return success

