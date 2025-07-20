#!/usr/bin/env python3

# Python script for feeding magnet links from RSS feed into Real-Debrid
# Adapted for GitHub Actions integration with YTS RSS project

import json
import requests
import feedparser
import argparse
import datetime
import os
import sys
import time
import random

# Try to load python-dotenv for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, continue without it
    pass

# SECTION: VARIABLES
__location__ = os.path.realpath(os.path.join(
    os.getcwd(), os.path.dirname(__file__)))

# Save file information
save_file_name = "RDRSSconfig/rdrss.json"
save_file_path = os.path.join(__location__, save_file_name)

BASE_DATE_STRING = "2000-01-01 00:00:00"

# Rate limiting and retry configuration
RATE_LIMIT_DELAY = 1.0  # Base delay between requests in seconds
MAX_RETRIES = 3  # Maximum number of retries for failed requests
RETRY_DELAY_BASE = 2  # Base delay for exponential backoff
MAX_RETRY_DELAY = 30  # Maximum retry delay in seconds

# Variables loaded from file
_auth_token = ""
_data = {}
_headers = {"Authorization": "Bearer " + _auth_token}


# SECTION: METHODS

def load_data(initialize_if_not: bool) -> bool:
    """Load data from config file into data variable

    @param initialize_if_not Create empty boilerplate data if file didnt exist

    @return bool File does exist
    """
    global _data
    try:
        json_file = open(save_file_path, "r+", encoding="utf-8")
        _data = json.load(json_file)
        json_file.close()
        return True
    except Exception:
        if initialize_if_not:
            _data["rssUrls"] = []
            _data["updated"] = BASE_DATE_STRING
            _data["authToken"] = ""
        return False


def store_data() -> bool:
    """Store data to config file from data variable

    @return bool Storing was successful
    """

    try:
        os.makedirs(os.path.dirname(save_file_path), exist_ok=True)
        json_file = open(save_file_path, "w", encoding="utf-8")
        json.dump(_data, json_file, indent=4)
        json_file.close()
        return True
    except Exception:
        return False


def ready_and_parse():
    """Try to parse RSS urls to Real-Debrid """
    global _data

    # Check for token
    if not (token_check()):
        return

    # Load stored last updated time
    if not load_data(True):
        return
    try:
        last_updated_date = datetime.datetime.strptime(
            str(_data["updated"]), '%Y-%m-%d %H:%M:%S').timetuple()
    except Exception:
        last_updated_date = datetime.datetime.strptime(
            str(BASE_DATE_STRING), '%Y-%m-%d %H:%M:%S').timetuple()

    # Load stored urls
    urls = get_rss()
    if len(urls) < 1:
        print("Missing RSS url. To add RSS url, use --add <value>")
        return

    # For each url print info and fetch to Real-Debrid
    x = 0
    for rss in urls:
        x += 1
        print("(" + str(x) + "/" + str(len(urls)) + ") " + rss)
        parse_feed(rss, last_updated_date)

    # Store now as last update time
    _data["updated"] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    store_data()

    # Select files in Real-Debrid
    select_files()


def parse_feed(rss_url, last_load_date):
    """Parse RSS feed into Real-Debrid

    @param rss_url RSS feed url
    @param last_load_date Last date this feed was updated (when to fetch new entries from)
    """

    feed = feedparser.parse(rss_url)

    # If feed is empty return
    if len(feed.entries) == 0:
        print("-> Fetch from RSS failed. (RSS had no entries)")
        return

    # Try to add magnet from each entry that has not yet been added to Real-Debrid
    # based on update time
    added_count = 0
    cached_count = 0
    skipped_count = 0
    
    for entry in feed.entries:
        # Check if entry has updated_parsed field and it's newer than last_load_date
        # If updated_parsed is None, treat it as a new entry to process
        should_process = True
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed is not None:
            should_process = entry.updated_parsed > last_load_date
        
        if should_process:
            # Check if entry has a magnet link or torrent URL
            magnet_link = None
            
            # Try to get magnet link from entry
            if hasattr(entry, 'link') and entry.link.startswith('magnet:'):
                magnet_link = entry.link
            elif hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    if enclosure.href.startswith('magnet:'):
                        magnet_link = enclosure.href
                        break
                    elif enclosure.href.startswith('https://yts.mx/torrent/download/'):
                        # Convert YTS torrent URL to magnet link
                        magnet_link = convert_yts_to_magnet(enclosure.href)
                        break
            
            if magnet_link:
                # Check if torrent is cached before adding
                if check_torrent_cached(magnet_link):
                    cached_count += 1
                    if add_magnet(magnet_link):
                        added_count += 1
                else:
                    skipped_count += 1
                    print("---> Skipping uncached torrent")

    print(f"-> Found {cached_count} cached torrents, successfully added {added_count} to RD, skipped {skipped_count} uncached.")


def convert_yts_to_magnet(torrent_url):
    """Convert YTS torrent download URL to magnet link
    
    @param torrent_url YTS torrent download URL
    @return magnet link or None
    """
    try:
        # Extract hash from YTS URL
        hash_part = torrent_url.split('/')[-1]
        if len(hash_part) == 40:  # SHA1 hash length
            # Create magnet link with YTS trackers
            magnet = f"magnet:?xt=urn:btih:{hash_part}&tr=udp://open.demonii.com:1337/announce&tr=udp://tracker.openbittorrent.com:80&tr=udp://tracker.coppersurfer.tk:6969&tr=udp://glotorrents.pw:6969/announce&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://torrent.gresille.org:80/announce&tr=udp://p4p.arenabg.com:1337&tr=udp://tracker.leechers-paradise.org:6969"
            return magnet
    except Exception as e:
        print(f"-> Failed to convert YTS URL to magnet: {e}")
    return None


def rate_limited_request(func, *args, **kwargs):
    """Execute API request with rate limiting and retry logic
    
    @param func Function to execute (requests.get, requests.post, etc.)
    @param args Arguments to pass to the function
    @param kwargs Keyword arguments to pass to the function
    @return Response object or None if all retries failed
    """
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Add rate limiting delay before each request
            if attempt > 0:
                # Exponential backoff for retries
                delay = min(RETRY_DELAY_BASE ** attempt + random.uniform(0, 1), MAX_RETRY_DELAY)
                print(f"---> Retrying in {delay:.1f} seconds... (attempt {attempt + 1}/{MAX_RETRIES + 1})")
                time.sleep(delay)
            else:
                # Base rate limit delay for first attempt
                time.sleep(RATE_LIMIT_DELAY + random.uniform(0, 0.5))
            
            # Make the API request
            response = func(*args, **kwargs)
            
            # Check if we hit a rate limit
            if response.status_code == 429:
                if attempt < MAX_RETRIES:
                    print("---> Rate limit hit, will retry...")
                    continue
                else:
                    print("---> Rate limit hit, max retries exceeded")
                    return response
            
            # Check for service unavailable
            if response.status_code == 503:
                if attempt < MAX_RETRIES:
                    print("---> Service unavailable, will retry...")
                    continue
                else:
                    print("---> Service unavailable, max retries exceeded")
                    return response
            
            # For other status codes, return immediately
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES:
                print(f"---> Request failed ({e}), will retry...")
                continue
            else:
                print(f"---> Request failed ({e}), max retries exceeded")
                return None
    
    return None


def process_api_response(result, indent=1) -> bool:
    """Process response codes from Real-Debrid api

    @param result Received result
    @param indent Requested indentation size

    @returns bool Response is ok
    """

    if not result.ok:

        # Process error message indentation
        indent_string = ""
        for x in range(indent):
            indent_string += "-"
        if indent > 0:
            indent_string += "> "

        if result.status_code == 401:
            print(indent_string +
                  "Failed reaching RD: Invalid token, to enter authentication token, use --token <value>.")
        elif result.status_code == 402:
            print(indent_string + "Failed reaching RD: User not premium.")
        elif result.status_code == 503:
            print(indent_string + "Failed reaching RD: Service not available.")
        else:
            print(indent_string + f"Failed reaching RD: {result.status_code}")
        return False
    return True


def add_magnet(magnet) -> bool:
    """Add magnet url into Real-Debrid using API

    @param magnet Url to magnet

    @returns bool Magnet added successfully
    """

    print("--> Adding magnet: " + magnet[:60] + "...")

    # Add magnet to Real-Debrid and process response with rate limiting
    request_data = {"magnet": magnet, "host": "real-debrid.com"}
    try:
        result = rate_limited_request(
            requests.post,
            "https://api.real-debrid.com/rest/1.0/torrents/addMagnet", 
            headers=_headers, 
            data=request_data,
            timeout=30
        )
        
        if result is None:
            print("---> Failed to add magnet: No response received")
            return False
            
        if not process_api_response(result, 3):
            return False
        print("---> Magnet added successfully")
        return True
    except Exception as e:
        print(f"---> Failed to add magnet: {e}")
        return False


def select_files() -> bool:
    """Select files added into Real-Debrid using API

    @returns bool Files selected successfully
    """

    # Get files from Real-Debrid with rate limiting
    try:
        result = rate_limited_request(
            requests.get,
            "https://api.real-debrid.com/rest/1.0/torrents?limit=100", 
            headers=_headers,
            timeout=30
        )
        
        if result is None:
            print("-> Failed to get torrents: No response received")
            return False
            
        if not process_api_response(result):
            print("-> Selecting files on RD failed.")
            return False

        # Select correct files
        files = result.json()
        selected_count = 0
        for file in files:
            if file["status"] == "waiting_files_selection":
                result = rate_limited_request(
                    requests.post,
                    "https://api.real-debrid.com/rest/1.0/torrents/selectFiles/" + file["id"], 
                    data={"files": "all"}, 
                    headers=_headers, 
                    timeout=30
                )
                
                if result is None:
                    print("--> Failed to select file: No response received")
                    continue
                    
                if not process_api_response(result):
                    print("--> File could not be selected.")
                    continue
                selected_count += 1

        print(f"-> Successfully selected {selected_count} files on RD.")
        return True
    except Exception as e:
        print(f"-> Failed to select files: {e}")
        return False


def get_rss():
    """Retrieve stored RSS urls

    @return array of urls
    """

    if load_data(True):
        if ("rssUrls" in _data) and (len(_data["rssUrls"]) != 0):
            return _data["rssUrls"]
    return []


def set_token(token):
    """Store Real-Debrid token

    @param token Real-Debrid user token
    """
    global _data

    # Load data and store token
    load_data(True)
    _data["authToken"] = token

    # Store data
    if not store_data():
        print("Couldn't store token.")
        return
    print("Token successfully added.")


def token_check() -> bool:
    """Check if Real-Debrid token is stored

    @returns bool If true, token is stored
    """

    global _auth_token
    global _headers

    # Check if token is in loaded data
    if load_data(True):
        if len(_data["authToken"]) != 0:
            _auth_token = _data["authToken"]
            _headers = {"Authorization": "Bearer " + _auth_token}
            return True

    # Check for token in environment variable (for GitHub Actions)
    env_token = os.getenv('RD_TOKEN')
    if env_token:
        _auth_token = env_token
        _headers = {"Authorization": "Bearer " + _auth_token}
        return True

    print(
        "Missing Real-Debrid authentication token. Set RD_TOKEN environment variable or use --token <value>")
    return False


def add_rss(rss):
    """Store RSS url

    param rss Url to RSS feed
    """

    global _data

    # Load data and add new rss
    load_data(True)
    if "rssUrls" not in _data:
        _data["rssUrls"] = []
    _data["rssUrls"].append(rss)

    # Store data
    if not store_data():
        print("Couldn't store RSS url.")
        return
    print("RSS url successfully added.")


def list_rss():
    """List stored RSS urls"""

    if load_data(True):
        if ("rssUrls" in _data) and (len(_data["rssUrls"]) != 0):
            print("RSS urls stored:")

            # Loop through urls and print them numbered
            x = 0
            for rss in _data["rssUrls"]:
                x += 1
                print(" [" + str(x) + "] " + rss)
            if (x > 0):
                return

    print("No RSS url added. To add RSS url, use --add <value>")


def remove_rss(n):
    """Remove stored RSS url number n

    @param n Index of url to remove
    """

    global _data

    if not load_data(True):
        print("Configuration file is empty.")

    # Check if url at index exists
    if ("rssUrls" not in _data) or (len(_data["rssUrls"]) < n):
        print("No url at index " + str(n) + " found.")
        return

    # Remove url from data
    _data["rssUrls"].pop(n-1)

    # Store data back into file
    if not store_data():
        print("Couldn't remove RSS url.")
        return
    print("RSS url successfully removed.")


def auto_add_preferred_feeds():
    """Automatically add preferred RSS feeds from the feeds directory"""
    global _data
    
    # Load existing data
    load_data(True)
    if "rssUrls" not in _data:
        _data["rssUrls"] = []
    
    # Define the base URL for your RSS feeds
    base_url = "https://raw.githubusercontent.com/Zero0Q/yts-json-to-rss/refs/heads/main/feeds/"
    
    # List of preferred feed files to add (only high quality feeds)
    preferred_feeds = [
        "2160p.xml"           # 4K content

    ]
    
    added_count = 0
    for feed_file in preferred_feeds:
        feed_url = base_url + feed_file
        if feed_url not in _data["rssUrls"]:
            _data["rssUrls"].append(feed_url)
            added_count += 1
            print(f"Added preferred RSS feed: {feed_url}")
    
    if added_count > 0:
        if store_data():
            print(f"Successfully added {added_count} preferred RSS feeds.")
        else:
            print("Failed to save RSS feeds.")
    else:
        print("All preferred RSS feeds already added.")


def extract_hash_from_magnet(magnet_link):
    """Extract torrent hash from magnet link
    
    @param magnet_link Magnet URI
    @return torrent hash or None
    """
    try:
        # Look for xt=urn:btih: in the magnet link
        import re
        match = re.search(r'xt=urn:btih:([a-fA-F0-9]{40})', magnet_link)
        if match:
            return match.group(1).lower()
        
        # Also try 32-character hash (base32)
        match = re.search(r'xt=urn:btih:([a-zA-Z2-7]{32})', magnet_link)
        if match:
            # Convert base32 to hex if needed
            import base64
            try:
                decoded = base64.b32decode(match.group(1).upper() + '======')
                return decoded.hex()
            except:
                return match.group(1).lower()
    except Exception as e:
        print(f"---> Failed to extract hash from magnet: {e}")
    return None


def check_torrent_cached(magnet_link) -> bool:
    """Check if torrent is cached in Real-Debrid
    
    @param magnet_link Magnet URI to check
    @return bool True if cached, False if not cached or error
    """
    
    # Extract hash from magnet link
    torrent_hash = extract_hash_from_magnet(magnet_link)
    if not torrent_hash:
        print("---> Could not extract hash from magnet link")
        return False
    
    print(f"---> Checking cache for hash: {torrent_hash[:16]}...")
    
    try:
        # Use the correct instant availability endpoint format
        # Try multiple hash variations to ensure compatibility
        hash_variations = [torrent_hash.upper(), torrent_hash.lower()]
        
        for hash_variant in hash_variations:
            result = rate_limited_request(
                requests.get,
                f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{hash_variant}",
                headers=_headers,
                timeout=30
            )
            
            if result is None:
                continue
                
            # Handle 403 specifically - might indicate API limitation
            if result.status_code == 403:
                print("---> Cache check not available (403), assuming torrent is available")
                return True  # Fallback to allowing the torrent
                
            # Handle 404 - hash not found in cache
            if result.status_code == 404:
                print("---> Torrent not found in cache")
                return False
                
            if not process_api_response(result, 3):
                continue
            
            # Parse response
            availability = result.json()
            
            # Check if hash exists in response and has available files
            if hash_variant.lower() in availability or hash_variant.upper() in availability:
                hash_key = hash_variant.lower() if hash_variant.lower() in availability else hash_variant.upper()
                cached_info = availability[hash_key]
                
                if isinstance(cached_info, dict) and len(cached_info) > 0:
                    # Check if any variant has files
                    for variant_key, variant_data in cached_info.items():
                        if isinstance(variant_data, list) and len(variant_data) > 0:
                            print("---> Torrent is cached in RD!")
                            return True
                            
        print("---> Torrent is not cached in RD")
        return False
        
    except Exception as e:
        print(f"---> Cache check failed: {e}, allowing torrent anyway")
        return True  # Fallback to allowing the torrent if cache check fails


# SECTION: ARGUMENT PROCESSING
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RSS feed to Real-Debrid.')
    parser.add_argument('-t', '--token', type=str,
                        help='set Real-Debrid token (acquire token at https://real-debrid.com/apitoken)')
    parser.add_argument('-l', '--list',
                        help='list RSS urls', action='store_true')
    parser.add_argument('-a', '--add', type=str, help='add RSS url')
    parser.add_argument('-r', '--remove', type=int,
                        help='remove RSS url at index (obtained using --list)')
    parser.add_argument('-m', '--magnet', type=str,
                        help='add magnet to Real-Debrid')
    parser.add_argument('-s', '--select',
                        help='select added files on Real-Debrid', action='store_true')
    parser.add_argument('--auto-add-feeds',
                        help='automatically add local YTS RSS feeds', action='store_true')

    args = parser.parse_args()
    
    if args.token:
        set_token(args.token)
    elif args.list:
        list_rss()
    elif args.add:
        add_rss(args.add)
    elif args.remove:
        remove_rss(args.remove)
    elif args.magnet:
        if token_check():
            add_magnet(args.magnet)
    elif args.select:
        if token_check():
            select_files()
    elif args.auto_add_feeds:
        auto_add_preferred_feeds()
    else:
        ready_and_parse()