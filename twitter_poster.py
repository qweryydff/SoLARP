"""
Twitter (X) integration using Tweepy v4 (API v2).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    logger.warning("tweepy not installed – Twitter posting disabled")


class TwitterPoster:
    def __init__(self):
        self.client: Optional[object] = None
        self._setup()

    def _setup(self):
        from config import (
            TWITTER_ENABLED,
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_SECRET,
            TWITTER_BEARER_TOKEN,
        )

        if not TWITTER_ENABLED:
            logger.info("Twitter posting is DISABLED (set TWITTER_ENABLED=true in .env to enable)")
            return

        if not TWEEPY_AVAILABLE:
            logger.error("tweepy package is required for Twitter. Run: pip install tweepy")
            return

        if not TWITTER_API_KEY:
            logger.error("Twitter API credentials not set in .env")
            return

        try:
            self.client = tweepy.Client(
                bearer_token        = TWITTER_BEARER_TOKEN,
                consumer_key        = TWITTER_API_KEY,
                consumer_secret     = TWITTER_API_SECRET,
                access_token        = TWITTER_ACCESS_TOKEN,
                access_token_secret = TWITTER_ACCESS_SECRET,
                wait_on_rate_limit  = True,
            )
            logger.info("Twitter client ready ✅")
        except Exception as e:
            logger.error(f"Twitter setup failed: {e}")

    def post(self, text: str) -> bool:
        """Post a tweet. Returns True on success."""
        if not self.client:
            logger.info(f"[TWITTER DISABLED] Would tweet:\n{text}\n")
            return False

        # Twitter has a 280-char limit
        if len(text) > 280:
            text = text[:277] + "..."

        try:
            response = self.client.create_tweet(text=text)
            tweet_id = response.data["id"]
            logger.info(f"Tweet posted: https://x.com/i/web/status/{tweet_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return False
