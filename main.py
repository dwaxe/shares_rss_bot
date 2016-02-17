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
            return 'Already feeding {} to /r/{}.'.format(feed, subreddit)
    else:
        feeds_dict[feed] = subreddit
    logging.info('Now feeding {} to {}'.format(feed, subreddit))
    title = 'New feed for r/{}'.format(subreddit)
    submit_post(title, feed, 'shares_rss_bot')
    return 'Successfully added {} to /r/{}.'.format(feed, subreddit)


def remove_feed(feed, subreddit):
    """Remove feed subreddit pair from dictionary"""
    if feed in feeds_dict:
        subreddits = feeds_dict[feed].split()
        if subreddit in subreddits:
            subreddits.remove(subreddit)
            feeds_dict[feed] = ' '.join(subreddits)
            logging.info('Removed {} from {}'.format(feed, subreddit))
            title = 'Removed feed from r/{}'.format(subreddit)
            submit_post(title, feed, 'shares_rss_bot')
            return 'Successfully removed {} from /r/{}.'.format(feed, subreddit)
        else:
            return 'Are you sure the subreddit is capitalized correctly?'
    else:
        return 'Are you sure the feed is spelled exactly?'


def process_messages():
    """Process messages searching for new feeds."""
    messages = r.get_unread()
    for m in messages:
        m.mark_as_read()
        try:
            read_message(m)
        except praw.errors.NotFound as e:
            logging.debug(e)


def read_message(message):
    """Process an individual message object for a new feed."""
    author = message.author
    subreddit = message.subject
    feed = message.body
    add = True
    if 'delete' == feed[:6]:
        feed = feed[7:]
        add = False
    try:
        mods = r.get_moderators(subreddit)
        subreddit = r.get_subreddit(subreddit).url[3:-1]
        if author in mods:
            if add:
                response = add_feed(feed, subreddit)
            else:
                response = remove_feed(feed, subreddit)
            message.reply(response)
        else:
            message.reply("You are not a mod of /r/{}.".format(subreddit))
    except praw.errors.InvalidSubreddit:
        message.reply("/r/{} does not exist.".format(subreddit))


def update_feeds():
    """Update all feeds in feeds_dict."""
    thread_limit = 100
    logging.debug('Updating {} feeds'.format(len(feeds_dict)))
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
        logging.warning(str(e) + ': ' + feed)
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


try:
    r = praw.Reddit(user_agent='shares_rss')
    r.login(REDDIT_USER, REDDIT_PASS, disable_warning=True)
except praw.errors.HTTPException as e:
    logging.debug(e)
    raise SystemExit

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
filename = os.path.join(__location__, 'bot.log')
logging.basicConfig(filename=filename, level=logging.INFO,
                    format='%(asctime)s %(message)s')

load_feeds()
process_messages()
update_feeds()
save_feeds()
