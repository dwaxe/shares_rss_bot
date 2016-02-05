"""This bot shares RSS feeds to subreddits
"""

import json
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

# Great big list of feeds to subreddits
feeds_dict = {}

# Will go this many entries into the feed checking for new stuff
FEED_DEPTH = 2


def load_feeds():
    """Load feeds from feeds.json"""
    with open(os.path.join(__location__, 'feeds.json'), 'r') as f:
        global feeds_dict
        feeds_dict = json.load(f)


def save_feeds():
    """Save feeds to feeds.json"""
    with open(os.path.join(__location__, 'feeds.json'), 'w') as f:
        json.dump(feeds_dict, f)


def add_feed(feed, subreddit):
    """Add feed subreddit pair to dictionary"""
    if feed in feeds_dict:
        subreddits = feeds_dict[feed].split()
        if subreddit not in subreddits:
            feeds_dict[feed] = feeds_dict[feed] + " " + subreddit
    else:
        feeds_dict[feed] = subreddit
    logging.info('Now feeding {} to {}'.format(feed, subreddit))


def process_messages():
    """Process messages searching for new feeds."""
    messages = r.get_unread()
    for m in messages:
        m.mark_as_read()
        read_message(m)


def read_message(message):
    """Process an individual message object for a new feed."""
    author = message.author
    subreddit = message.subject
    feed = message.body
    try:
        mods = r.get_moderators(subreddit)
        subreddit = r.get_subreddit(subreddit).url[3:-1]
        if author in mods:
            add_feed(feed, subreddit)
            body = "Successfully added {} to {}".format(feed, subreddit)
            message.reply(body)
        else:
            message.reply("You are not a mod of {}".format(subreddit))
    except praw.errors.InvalidSubreddit:
        message.reply("{} does not exist".format(subreddit))


def update_feeds():
    """Update all feeds in feeds_dict."""
    thread_limit = 100
    logging.info('Updating feeds')
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
        logging.debug('Updating {}'.format(feed))
    except (AttributeError, IndexError) as e:
        logging.warning(e)
        return
    for entry in d.entries[:FEED_DEPTH]:
        title = entry.title
        link = entry.link
        subreddits = feeds_dict[feed].split()
        for subreddit in subreddits:
            submit_post(title, link, subreddit)


def submit_post(title, link, subreddit):
    """Submit a single post to Reddit, ignoring AlreadySubmitted errors."""
    try:
        r.submit(subreddit, title, url=link)
        logging.info('Submitted {} to {}'.format(link, subreddit))
    except praw.errors.AlreadySubmitted:
        pass
    except praw.errors.HTTPException as e:
        logging.debug(e)
    except praw.errors.RateLimitExceeded as e:
        logging.debug(e)
        raise SystemExit
    except praw.errors.APIException as e:
        logging.warning(e)


r = praw.Reddit(user_agent='shares_rss')
r.login(REDDIT_USER, REDDIT_PASS, disable_warning=True)

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
filename = os.path.join(__location__, 'bot.log')
logging.basicConfig(filename=filename, level=logging.INFO,
                    format='%(asctime)s %(message)s')

load_feeds()
process_messages()
update_feeds()
save_feeds()
