#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import urllib.request
import urllib.parse
import urllib.error


GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class GraphApiError(Exception):
    def __init__(self, message: str, status_code: int, payload: Optional[dict] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def _request_with_backoff(method: str, url: str, params: Dict[str, Any], max_retries: int = 5) -> dict:
    if method.upper() != "GET":
        raise ValueError("Only GET is supported in this client")

    backoff_seconds = 1.0
    last_status: Optional[int] = None
    last_payload: Optional[dict] = None

    for attempt in range(max_retries):
        try:
            full_url = url
            if params:
                query = urllib.parse.urlencode(params, doseq=True)
                sep = "&" if urllib.parse.urlparse(full_url).query else "?"
                full_url = f"{full_url}{sep}{query}"

            req = urllib.request.Request(full_url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.getcode()
                body_bytes = resp.read()
                body_text = body_bytes.decode("utf-8", errors="ignore")
                if status_code == 200:
                    try:
                        return json.loads(body_text)
                    except Exception:
                        raise GraphApiError("Invalid JSON response", status_code, {"raw_text": body_text})
                last_status = status_code
                last_payload = {"raw_text": body_text}
        except urllib.error.HTTPError as e:
            last_status = e.code
            try:
                err_text = e.read().decode("utf-8", errors="ignore")
                payload = json.loads(err_text)
            except Exception:
                payload = {"raw_text": err_text if 'err_text' in locals() else str(e)}

            # Immediate raise for non-transient errors
            if e.code not in (429, 500, 502, 503, 504):
                message = f"Graph API error {e.code}: {payload.get('error', {}).get('message') or payload}"
                raise GraphApiError(message, e.code, payload)
            last_payload = payload
        except urllib.error.URLError as e:
            # Network/connection error; treat as transient
            last_status = 0
            last_payload = {"error": {"message": str(e)}}

        if last_status in (429, 500, 502, 503, 504, 0) and attempt < max_retries - 1:
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 30)
            continue
        break

    status = last_status if last_status is not None else 0
    payload = last_payload if last_payload is not None else {}
    raise GraphApiError(
        f"Graph API transient error after {max_retries} retries: {payload}",
        status,
        payload,
    )


def get_user_profile(ig_user_id: str, access_token: str) -> dict:
    url = f"{GRAPH_API_BASE}/{ig_user_id}"
    params = {
        "fields": "username,followers_count,media_count,profile_picture_url,biography",
        "access_token": access_token,
    }
    return _request_with_backoff("GET", url, params)


def get_recent_media(ig_user_id: str, access_token: str, limit: int) -> List[dict]:
    url = f"{GRAPH_API_BASE}/{ig_user_id}/media"
    fields = [
        "id",
        "caption",
        "like_count",
        "comments_count",
        "media_type",
        "timestamp",
        "permalink",
        "media_url",
        "thumbnail_url",
    ]
    params = {
        "fields": ",".join(fields),
        "limit": max(1, min(limit, 200)),
        "access_token": access_token,
    }

    data: List[dict] = []
    page_count = 0
    while True:
        page_count += 1
        payload = _request_with_backoff("GET", url, params)
        items = payload.get("data", [])
        data.extend(items)
        # Stop if we reached desired count or there is no next page
        if len(data) >= limit:
            return data[:limit]
        paging = payload.get("paging", {})
        next_url = paging.get("next")
        if not next_url:
            break
        # Next page is a full URL that includes the token
        url = next_url
        params = {}
        if page_count >= 10:  # hard stop to avoid accidental deep paging
            break
    return data[:limit]


def _parse_iso8601_to_dt(ts: str) -> datetime:
    # Graph API returns RFC3339 timestamps; Python fromisoformat handles 'YYYY-MM-DDTHH:MM:SS+00:00'
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        # Fallback: try without timezone
        return datetime.strptime(ts.split("+")[0].split("Z")[0], "%Y-%m-%dT%H:%M:%S")


def compute_engagement_score(media: dict) -> int:
    likes = int(media.get("like_count") or 0)
    comments = int(media.get("comments_count") or 0)
    return likes + comments


def summarize_top_posts(media_items: List[dict], top_k: int = 5) -> List[Tuple[dict, int]]:
    scored: List[Tuple[dict, int]] = []
    for item in media_items:
        score = compute_engagement_score(item)
        scored.append((item, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def suggest_posting_windows(media_items: List[dict], top_k: int = 5) -> List[Tuple[str, int]]:
    # Aggregate engagement by (weekday, hour) in UTC
    # weekday: 0=Mon ... 6=Sun
    heatmap: Dict[Tuple[int, int], int] = defaultdict(int)
    for item in media_items:
        ts = item.get("timestamp")
        if not ts:
            continue
        dt = _parse_iso8601_to_dt(ts)
        weekday = dt.weekday()
        hour = dt.hour
        heatmap[(weekday, hour)] += compute_engagement_score(item)

    # Rank windows by total engagement
    ranked = sorted(heatmap.items(), key=lambda kv: kv[1], reverse=True)

    def format_slot(weekday: int, hour: int) -> str:
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        start = f"{hour:02d}:00"
        end = f"{(hour + 1) % 24:02d}:00"
        return f"{names[weekday]} {start}-{end} UTC"

    results: List[Tuple[str, int]] = []
    for (weekday, hour), total_eng in ranked[:top_k]:
        results.append((format_slot(weekday, hour), total_eng))
    return results


def print_report(profile: dict, media_items: List[dict]) -> None:
    username = profile.get("username") or "(unknown)"
    followers = profile.get("followers_count")
    media_count = profile.get("media_count")

    print("")
    print(f"Account: @{username}")
    if followers is not None:
        print(f"Followers: {followers}")
    if media_count is not None:
        print(f"Total posts: {media_count}")

    if not media_items:
        print("\nNo recent media found to analyze.")
        return

    print("\nTop posts by engagement (likes + comments):")
    top_posts = summarize_top_posts(media_items, top_k=5)
    for idx, (item, score) in enumerate(top_posts, start=1):
        dt = _parse_iso8601_to_dt(item.get("timestamp"))
        permalink = item.get("permalink")
        media_type = item.get("media_type")
        caption = (item.get("caption") or "").strip().replace("\n", " ")
        if len(caption) > 80:
            caption = caption[:77] + "..."
        print(f"  {idx}. {dt:%Y-%m-%d %H:%M} UTC | {media_type:<6} | Engagement={score:<4} | {permalink}")
        if caption:
            print(f"     Caption: {caption}")

    print("\nSuggested posting windows (based on historical engagement):")
    windows = suggest_posting_windows(media_items, top_k=5)
    for idx, (slot, total) in enumerate(windows, start=1):
        print(f"  {idx}. {slot} — cumulative engagement signal: {total}")

    print("\nNotes:")
    print("- All times are in UTC; adjust to your audience time zones.")
    print("- Recommendations are heuristic; validate by A/B testing and ongoing measurement.")
    print("- This tool is read-only and does not automate actions, in line with Instagram policies.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Instagram growth insights (compliant): analyze recent posts via Meta Graph API and "
            "suggest posting windows."
        )
    )
    parser.add_argument("--ig-user-id", default=os.getenv("IG_USER_ID"), help="Instagram Business/Creator user ID")
    parser.add_argument("--access-token", default=os.getenv("ACCESS_TOKEN"), help="Meta Graph API access token")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of recent media to analyze (max 200).",
    )
    parser.add_argument(
        "--dump-json",
        action="store_true",
        help="Print raw JSON for profile and the first 5 media items (for debugging).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.ig_user_id or not args.access_token:
        print(
            "Error: missing IG user ID or access token. Provide via --ig-user-id/--access-token or set IG_USER_ID/ACCESS_TOKEN env vars.",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        profile = get_user_profile(args.ig_user_id, args.access_token)
        media = get_recent_media(args.ig_user_id, args.access_token, args.limit)
    except GraphApiError as e:
        print(f"Failed to query Graph API: {e}", file=sys.stderr)
        # Surface helpful details if present
        if e.payload:
            try:
                print(json.dumps(e.payload, indent=2), file=sys.stderr)
            except Exception:
                pass
        sys.exit(1)

    if args.dump_json:
        print("\nRaw profile JSON (truncated):")
        print(json.dumps({k: profile.get(k) for k in ["id", "username", "followers_count", "media_count"]}, indent=2))
        print("\nFirst 5 media items (truncated fields):")
        brief = []
        for m in media[:5]:
            brief.append({
                "id": m.get("id"),
                "timestamp": m.get("timestamp"),
                "media_type": m.get("media_type"),
                "like_count": m.get("like_count"),
                "comments_count": m.get("comments_count"),
            })
        print(json.dumps(brief, indent=2))

    print_report(profile, media)


if __name__ == "__main__":
    main()