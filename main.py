"""This bot shares RSS feeds to subreddits
"""

import logging
import os
import threading
import time

import feedparser
import praw

try:
    REDDIT_USER = os.environ['REDDIT_USER']
    REDDIT_PASS = os.environ['REDDIT_PASS']
except:
    # If you don't have environment variables, fallback to this
    REDDIT_USER = 'whoami'
    REDDIT_PASS = 'mysecret'

feeds_dict = {
    'http://fivethirtyeight.com/economics/feed/': 'economics',
    'http://www.voxeu.org/feed/recent/rss.xml': 'economics',
    'http://feeds.reuters.com/news/economy': 'economics',
    'http://feeds.bbci.co.uk/news/business/economy/rss.xml': 'economics'
}

# Will go this many entries into the feed checking for new stuff
FEED_DEPTH = 2


def update_feeds():
    """Update all feeds in feeds_dict."""
    thread_limit = 100
    for feed in feeds_dict:
        if len(threading.enumerate()) >= thread_limit:
            time.sleep(10)
        t = threading.Thread(target=update_feed, args=(feed,))
        t.start()


def update_feed(feed):
    """Update a single feed."""
    d = feedparser.parse(feed)
    try:
        link = d.entries[0].link
    except (AttributeError, IndexError) as e:
        logging.debug(e)
        return
    for entry in d.entries[:FEED_DEPTH]:
        logging.info('Updating {}'.format(feed))
        title = entry.title
        link = entry.link
        subreddit = feeds_dict[feed]
        submit_post(title, link, subreddit)


def submit_post(title, link, subreddit):
    """Submit a single post to Reddit, ignoring AlreadySubmitted errors."""
    try:
        logging.info('Submitting {} to {}'.format(link, subreddit))
        r.submit(subreddit, title, url=link)
    except praw.errors.AlreadySubmitted:
        pass
    except (praw.errors.RateLimitExceeded, praw.errors.HTTPException) as e:
        logging.debug(e)


r = praw.Reddit(user_agent='shares_rss')
r.login(REDDIT_USER, REDDIT_PASS, disable_warning=True)

update_feeds()
