#!/usr/bin/env python3
"""Print an Apex Legends stats summary using the Tracker Network API.

Get a free API key at https://tracker.gg/developers, then:

    export TRN_API_KEY=your-key
    python apex_stats.py YourName                 # platform defaults to origin (PC)
    python apex_stats.py YourName -p psn          # psn | xbl | origin
    python apex_stats.py YourName --raw           # dump the raw overview stats (debugging)

Standard library only; no installs needed.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://public-api.tracker.gg/v2/apex/standard/profile"
PLATFORMS = ("origin", "psn", "xbl")


def fetch_profile(platform, name, api_key):
    url = f"{BASE_URL}/{platform}/{urllib.parse.quote(name, safe='')}"
    req = urllib.request.Request(
        url,
        headers={
            "TRN-Api-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "apex-stats-script/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        hints = {
            400: "Bad request - check the platform and username.",
            401: "Invalid or missing API key.",
            403: "Key not authorized for this endpoint (or Apex access is restricted).",
            404: "Player not found - check spelling and platform (origin/psn/xbl).",
            429: "Rate limited - wait a bit and try again.",
        }
        sys.exit(f"Error {e.code}: {hints.get(e.code, e.reason)}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e.reason}")


def overview_stats(payload):
    """Return the lifetime 'overview' segment's stats dict."""
    segments = payload.get("data", {}).get("segments", [])
    for seg in segments:
        if seg.get("type") == "overview":
            return seg.get("stats", {})
    sys.exit("No overview stats found in response (profile may be private).")


def stat(stats, *keys):
    """First matching stat entry by key, or None."""
    for k in keys:
        if k in stats:
            return stats[k]
    return None


def num(entry):
    return entry.get("value") if entry else None


def fmt(value, spec=",.0f", suffix=""):
    return "N/A" if value is None else f"{format(value, spec)}{suffix}"


def summarize(payload):
    stats = overview_stats(payload)
    handle = payload["data"]["platformInfo"].get("platformUserHandle", "?")

    rank_entry = stat(stats, "rankScore")
    rank_name = (rank_entry or {}).get("metadata", {}).get("rankName") or "Unranked"
    rp = num(rank_entry)

    kd = num(stat(stats, "kd", "kdr"))
    wins = num(stat(stats, "wins"))
    matches = num(stat(stats, "matchesPlayed", "gamesPlayed"))
    win_rate = num(stat(stats, "winPercentage", "winPct"))
    if win_rate is None and wins is not None and matches:
        win_rate = wins / matches * 100

    width = 30
    lines = [
        "=" * width,
        f" APEX LEGENDS - {handle}",
        "=" * width,
        f" Rank      : {rank_name}",
        f" RP        : {fmt(rp)}",
        f" K/D       : {fmt(kd, '.2f')}",
        f" Win rate  : {fmt(win_rate, '.1f', '%')}",
    ]
    if wins is not None:
        lines.append(f" Wins      : {fmt(wins)}")
    if matches is not None:
        lines.append(f" Matches   : {fmt(matches)}")
    lines.append("=" * width)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Apex Legends stats via Tracker Network")
    parser.add_argument("username", help="Platform username (EA/Origin, PSN, or Xbox gamertag)")
    parser.add_argument("-p", "--platform", choices=PLATFORMS, default="origin")
    parser.add_argument("--raw", action="store_true", help="Print raw overview stats JSON")
    args = parser.parse_args()

    api_key = os.environ.get("TRN_API_KEY")
    if not api_key:
        sys.exit("Set your key first: export TRN_API_KEY=your-key (from tracker.gg/developers)")

    payload = fetch_profile(args.platform, args.username, api_key)
    if args.raw:
        print(json.dumps(overview_stats(payload), indent=2))
    else:
        print(summarize(payload))


if __name__ == "__main__":
    main()
