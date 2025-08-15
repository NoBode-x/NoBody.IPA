#!/usr/bin/env python3
"""
instagram_growth_helper.py

Ethical Instagram growth planning tool.

This script generates a compliant, non-automated growth plan, content calendar,
caption templates, and hashtag sets based on a provided Instagram username and
optional topics. It does NOT automate interactions, scrape Instagram, or offer
any ban-evasion techniques. It is designed to help creators plan content while
complying with platform rules and terms of service.

Usage:
  python instagram_growth_helper.py --username myaccount \
    --days 30 --posts-week 4 --reels-week 2 --stories-week 7 \
    --topics "fitness, nutrition, wellness"

Outputs are written to: ./output/<username>/

All operations are local and use only Python's standard library.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


VALID_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._]{1,30}$")

# Default content pillars used as fallback and for filling to minimum count
DEFAULT_PILLARS: List[str] = [
    "behind the scenes",
    "tips and tutorials",
    "community highlights",
    "personal stories",
    "product or service features",
    "industry insights",
    "user-generated content",
]


def validate_username(username: str) -> None:
    """Validate Instagram-like username format.

    Instagram usernames are 1-30 characters, alphanumeric plus underscores and periods.
    """
    if not isinstance(username, str):
        raise ValueError("Username must be a string.")
    if not VALID_USERNAME_PATTERN.match(username):
        raise ValueError(
            "Invalid username. Use 1-30 chars: letters, numbers, underscores, or periods."
        )


def get_seed_from_username(username: str) -> int:
    """Derive a deterministic random seed from the username."""
    # Simple deterministic hash-like seed
    seed_value = 0
    for index, character in enumerate(username):
        seed_value += (index + 1) * ord(character)
    return seed_value % (2 ** 31 - 1)


def sanitize_topics(topics: Optional[str]) -> List[str]:
    """Split a comma-separated topics string into clean topic list."""
    if not topics:
        return []
    parts = [topic.strip() for topic in topics.split(",")]
    parts = [topic for topic in parts if topic]
    # Normalize whitespace and casing
    normalized = [re.sub(r"\s+", " ", p).lower() for p in parts]
    # Deduplicate preserving order
    seen = set()
    unique = []
    for p in normalized:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return unique


def generate_content_pillars(username: str, provided_topics: Sequence[str]) -> List[str]:
    """Generate 3-5 content pillars, using provided topics if available."""
    seed_value = get_seed_from_username(username)
    rng = random.Random(seed_value)

    # If topics provided, prefer them
    if provided_topics:
        base_topics = list(provided_topics)
    else:
        # Derive naive tokens from username to inspire pillars
        tokens = re.split(r"[._]+", username)
        tokens = [t for t in tokens if t and not t.isdigit()]
        tokens = [t.lower() for t in tokens]
        # Fallback themes
        fallback = DEFAULT_PILLARS
        base_topics = tokens if tokens else fallback

    # Normalize and pick 3-5 pillars
    cleaned = []
    for topic in base_topics:
        topic_clean = re.sub(r"\s+", " ", topic.strip().lower())
        if topic_clean and topic_clean not in cleaned:
            cleaned.append(topic_clean)

    # Ensure at least 3 pillars by filling from defaults
    if len(cleaned) < 3:
        for candidate in DEFAULT_PILLARS:
            if candidate not in cleaned:
                cleaned.append(candidate)
            if len(cleaned) >= 3:
                break

    rng.shuffle(cleaned)
    # Cap to 5 max
    return cleaned[:5]


def get_recommended_posting_hours() -> Dict[int, List[int]]:
    """Return recommended local posting hours per weekday.

    Keys are Monday=0 through Sunday=6. Hours are 24h local times.
    """
    return {
        0: [9, 12, 18],   # Monday
        1: [9, 13, 19],   # Tuesday
        2: [8, 12, 18],   # Wednesday
        3: [9, 12, 17],   # Thursday
        4: [9, 12, 16],   # Friday
        5: [10, 14, 18],  # Saturday
        6: [10, 15, 19],  # Sunday
    }


def generate_weekly_schedule(
    seed_value: int,
    posts_per_week: int,
    reels_per_week: int,
    stories_per_week: int,
) -> Dict[str, List[int]]:
    """Generate a weekly schedule of which weekdays to post and story.

    Returns a dict with keys: "post_days", "reel_days", "story_days" mapping to weekday indices
    (0=Monday..6=Sunday). Deterministic given seed_value.
    """
    rng = random.Random(seed_value)
    all_days = list(range(7))

    # Choose post days
    post_days = list(all_days)
    rng.shuffle(post_days)
    post_days = sorted(post_days[: max(0, min(posts_per_week, 7))])

    # Choose reel subset among post days
    reel_days = list(post_days)
    rng.shuffle(reel_days)
    reel_days = sorted(reel_days[: max(0, min(reels_per_week, len(post_days)))])

    # Choose story days (may include all days if desired)
    story_days = list(all_days)
    rng.shuffle(story_days)
    story_days = sorted(story_days[: max(0, min(stories_per_week, 7))])

    return {
        "post_days": post_days,
        "reel_days": reel_days,
        "story_days": story_days,
    }


def pick_post_type_for_day(
    weekday_index: int,
    reel_days: Sequence[int],
    rng: random.Random,
) -> str:
    """Decide the content type for a given day.

    Prioritize Reels on designated reel days; otherwise choose Carousel vs Photo.
    """
    if weekday_index in reel_days:
        return "Reel"
    # Weighted choice between Carousel and Photo
    return rng.choices(population=["Carousel", "Photo"], weights=[0.6, 0.4], k=1)[0]


def idea_for_post(content_type: str, pillar: str, rng: random.Random) -> Tuple[str, str]:
    """Generate a simple content idea and a CTA for the post."""
    ctas = [
        "Save this for later",
        "Share with a friend",
        "Comment your thoughts",
        "Double-tap if this helped",
        "Follow for more like this",
        "Try this and tag me",
    ]
    if content_type == "Reel":
        idea = f"Quick {pillar} tip in 15 seconds with on-screen captions"
    elif content_type == "Carousel":
        idea = f"Step-by-step {pillar} guide in 5-7 slides"
    elif content_type == "Photo":
        idea = f"Before-and-after or behind-the-scenes related to {pillar}"
    else:
        idea = f"Casual story moment highlighting {pillar}"

    cta = rng.choice(ctas)
    return idea, cta


def generate_calendar(
    username: str,
    start_date: dt.date,
    num_days: int,
    posts_per_week: int,
    reels_per_week: int,
    stories_per_week: int,
    pillars: Sequence[str],
) -> List[Dict[str, str]]:
    """Generate a content calendar entries list.

    Each entry has: date_iso, day_name, time_local, content_type, pillar, idea, cta.
    Includes both posts (Reel/Carousel/Photo) and Story items.
    """
    seed_value = get_seed_from_username(username)
    rng = random.Random(seed_value)
    posting_hours = get_recommended_posting_hours()

    entries: List[Dict[str, str]] = []

    current_date = start_date
    end_date = start_date + dt.timedelta(days=num_days)
    week_index = 0

    while current_date < end_date:
        # Recompute weekly schedule at the start of each ISO week chunk
        weekly_schedule = generate_weekly_schedule(
            seed_value=seed_value + week_index,  # vary slightly per week
            posts_per_week=posts_per_week,
            reels_per_week=reels_per_week,
            stories_per_week=stories_per_week,
        )

        # Iterate through days of this week
        for i in range(7):
            day = current_date + dt.timedelta(days=i)
            if day >= end_date:
                break

            weekday_index = day.weekday()  # 0=Mon..6=Sun
            hours_for_day = posting_hours.get(weekday_index, [12])
            time_hour = rng.choice(hours_for_day)
            time_local = f"{time_hour:02d}:00"

            # Schedule primary post if day is selected
            if weekday_index in weekly_schedule["post_days"]:
                content_type = pick_post_type_for_day(
                    weekday_index=weekday_index,
                    reel_days=weekly_schedule["reel_days"],
                    rng=rng,
                )
                pillar = rng.choice(pillars)
                idea, cta = idea_for_post(content_type, pillar, rng)
                entries.append(
                    {
                        "date_iso": day.isoformat(),
                        "day_name": day.strftime("%A"),
                        "time_local": time_local,
                        "content_type": content_type,
                        "pillar": pillar,
                        "idea": idea,
                        "cta": cta,
                    }
                )

            # Schedule story if day is selected for stories
            if weekday_index in weekly_schedule["story_days"]:
                pillar_story = rng.choice(pillars)
                idea_story, cta_story = idea_for_post("Story", pillar_story, rng)
                # Choose a different time for story if possible
                story_hour_candidates = [h for h in hours_for_day if h != time_hour]
                story_hour = rng.choice(story_hour_candidates or hours_for_day)
                entries.append(
                    {
                        "date_iso": day.isoformat(),
                        "day_name": day.strftime("%A"),
                        "time_local": f"{story_hour:02d}:00",
                        "content_type": "Story",
                        "pillar": pillar_story,
                        "idea": idea_story,
                        "cta": cta_story,
                    }
                )

        current_date += dt.timedelta(days=7)
        week_index += 1

    # Sort entries by date then time
    entries.sort(key=lambda e: (e["date_iso"], e["time_local"]))
    return entries


def generate_caption_templates(username: str, pillars: Sequence[str]) -> List[str]:
    """Generate caption templates with pillar placeholders."""
    rng = random.Random(get_seed_from_username(username) + 42)
    templates: List[str] = []
    starters = [
        "3 things I wish I knew about {pillar}…",
        "The biggest mistake in {pillar} (and how to avoid it)",
        "A simple {pillar} framework you can use today",
        "Stop doing this in {pillar}: do this instead",
        "The 80/20 of {pillar}: focus on what matters",
        "Beginner to pro in {pillar}: step-by-step",
        "Try this {pillar} challenge for 7 days",
        "You asked about {pillar}—here's my take",
        "My favorite tools for {pillar}",
        "Let me make {pillar} simple",
    ]
    closers = [
        "Comment your questions 👇",
        "Save this so you don't forget",
        "Share with someone who needs this",
        "Follow for more concise tips",
        "Tag me when you try this",
        "What should I cover next?",
    ]

    for _ in range(20):
        pillar = rng.choice(list(pillars))
        start = rng.choice(starters).format(pillar=pillar)
        close = rng.choice(closers)
        templates.append(f"{start}. {close}.")

    # Add a few value-rich long-form templates
    long_templates = [
        "{pillar}: the 5-part checklist you need today → Hook, Context, Steps, Example, CTA.",
        "If you're overwhelmed by {pillar}, start here: 1) Define goal 2) Remove friction 3) Take one tiny action today.",
        "The mini playbook for {pillar}: mistakes to avoid, quick wins to try, and how to measure progress.",
    ]
    for lt in long_templates:
        pillar = rng.choice(list(pillars))
        templates.append(lt.format(pillar=pillar))

    # Branded CTA reminder
    templates.append(f"Want more like this? Follow @{username} and save this post for later.")

    return templates


def generate_hashtag_sets(username: str, pillars: Sequence[str], num_sets: int = 15) -> List[List[str]]:
    """Generate hashtag sets with a mix of branded, niche, and broad tags.

    Avoids spammy or engagement-bait tags; focuses on relevance and discoverability.
    """
    rng = random.Random(get_seed_from_username(username) + 99)

    broad_tags = [
        "#learnontheinternet",
        "#education",
        "#howto",
        "#tutorial",
        "#tips",
        "#smallbusiness",
        "#creativeprocess",
        "#behindthescenes",
        "#contentstrategy",
        "#community",
    ]

    pillar_to_tags: Dict[str, List[str]] = {}
    for pillar in pillars:
        slug = re.sub(r"[^a-z0-9]+", "", pillar.lower())
        pillar_tags = list({
            f"#{slug}",
            f"#{slug}tips",
            f"#{slug}guide",
            f"#{slug}101",
            f"#{slug}ideas",
            f"#{slug}community",
        })
        pillar_to_tags[pillar] = pillar_tags

    branded = [f"#{username}", f"#{username}tips", f"#{username}community"]

    hashtag_sets: List[List[str]] = []
    for _ in range(num_sets):
        pillar = rng.choice(list(pillars))
        niche = rng.sample(pillar_to_tags[pillar], k=min(3, len(pillar_to_tags[pillar])))
        broad = rng.sample(broad_tags, k=5)
        brand = rng.sample(branded, k=min(2, len(branded)))
        extra_generic_pool = [
            "#value",
            "#growthmindset",
            "#productivity",
            "#maker",
            "#entrepreneur",
            "#creator",
            "#startup",
        ]
        extra = rng.sample(extra_generic_pool, k=3)
        combined = list(dict.fromkeys(niche + broad + brand + extra))
        hashtag_sets.append(combined[:15])

    return hashtag_sets


def profile_optimization_checklist(username: str, pillars: Sequence[str]) -> List[str]:
    """Return a concise checklist for optimizing profile and content."""
    return [
        f"Username @{username} is clear and on-brand",
        "Profile photo is high-contrast and recognizable at small sizes",
        "Bio communicates who it's for, what you do, and a clear CTA",
        "Link-in-bio points to a simple landing page or lead magnet",
        f"Pin 3 posts that introduce your {', '.join(pillars)} pillars",
        "Story highlights cover: Start Here, FAQs, Social Proof, Offers",
        "Use consistent brand colors and typography in posts",
        "Add alt text to improve accessibility and reach",
        "Batch-create content weekly; schedule in advance with approved tools",
        "Respond to comments and DMs within 24 hours to build community",
    ]


def write_calendar_csv(output_dir: Path, entries: Sequence[Dict[str, str]]) -> Path:
    path = output_dir / "calendar.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date_iso",
                "day_name",
                "time_local",
                "content_type",
                "pillar",
                "idea",
                "cta",
            ],
        )
        writer.writeheader()
        for row in entries:
            writer.writerow(row)
    return path


def write_captions_txt(output_dir: Path, captions: Sequence[str]) -> Path:
    path = output_dir / "captions.txt"
    with path.open("w", encoding="utf-8") as f:
        for index, caption in enumerate(captions, start=1):
            f.write(f"[{index}] {caption}\n")
    return path


def write_hashtags_csv(output_dir: Path, hashtag_sets: Sequence[Sequence[str]]) -> Path:
    path = output_dir / "hashtags.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["set_index", "hashtags_space_separated"])
        for index, tags in enumerate(hashtag_sets, start=1):
            writer.writerow([index, " ".join(tags)])
    return path


def write_checklist_txt(output_dir: Path, checklist: Sequence[str]) -> Path:
    path = output_dir / "profile_checklist.txt"
    with path.open("w", encoding="utf-8") as f:
        for item in checklist:
            f.write(f"- {item}\n")
    return path


def write_plan_json(
    output_dir: Path,
    username: str,
    pillars: Sequence[str],
    posts_per_week: int,
    reels_per_week: int,
    stories_per_week: int,
    num_days: int,
) -> Path:
    path = output_dir / "plan.json"
    payload = {
        "username": username,
        "pillars": list(pillars),
        "config": {
            "posts_per_week": posts_per_week,
            "reels_per_week": reels_per_week,
            "stories_per_week": stories_per_week,
            "num_days": num_days,
        },
        "notes": [
            "This tool is for planning only and does not automate actions.",
            "Always follow Instagram's Terms of Use and Community Guidelines.",
        ],
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an ethical Instagram growth plan and content calendar from a username."
        )
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Instagram username (for planning context only)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to plan (default: 30)",
    )
    parser.add_argument(
        "--posts-week",
        type=int,
        default=4,
        help="Number of posts per week (Reels/Carousels/Photos). Default: 4",
    )
    parser.add_argument(
        "--reels-week",
        type=int,
        default=2,
        help="Number of Reels per week (subset of posts). Default: 2",
    )
    parser.add_argument(
        "--stories-week",
        type=int,
        default=7,
        help="Number of Story days per week (0-7). Default: 7",
    )
    parser.add_argument(
        "--topics",
        type=str,
        default="",
        help="Optional comma-separated topics to inform pillars",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=dt.date.today().isoformat(),
        help="Start date in ISO format YYYY-MM-DD (default: today)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    validate_username(args.username)

    try:
        start_date = dt.date.fromisoformat(args.start_date)
    except Exception as exc:  # noqa: BLE001 - provide a clear message
        raise SystemExit(f"Invalid --start-date: {exc}")

    if args.days <= 0:
        raise SystemExit("--days must be a positive integer")
    if not (0 <= args.stories_week <= 7):
        raise SystemExit("--stories-week must be between 0 and 7")
    if args.posts_week < 0 or args.reels_week < 0:
        raise SystemExit("--posts-week and --reels-week must be non-negative")
    if args.reels_week > args.posts_week:
        raise SystemExit("--reels-week cannot exceed --posts-week")

    provided_topics = sanitize_topics(args.topics)
    pillars = generate_content_pillars(args.username, provided_topics)

    calendar_entries = generate_calendar(
        username=args.username,
        start_date=start_date,
        num_days=args.days,
        posts_per_week=args.posts_week,
        reels_per_week=args.reels_week,
        stories_per_week=args.stories_week,
        pillars=pillars,
    )

    captions = generate_caption_templates(args.username, pillars)
    hashtag_sets = generate_hashtag_sets(args.username, pillars)
    checklist = profile_optimization_checklist(args.username, pillars)

    output_dir = Path("output") / args.username
    output_dir.mkdir(parents=True, exist_ok=True)

    calendar_path = write_calendar_csv(output_dir, calendar_entries)
    captions_path = write_captions_txt(output_dir, captions)
    hashtags_path = write_hashtags_csv(output_dir, hashtag_sets)
    checklist_path = write_checklist_txt(output_dir, checklist)
    plan_path = write_plan_json(
        output_dir,
        username=args.username,
        pillars=pillars,
        posts_per_week=args.posts_week,
        reels_per_week=args.reels_week,
        stories_per_week=args.stories_week,
        num_days=args.days,
    )

    disclaimer = (
        "This tool does not automate Instagram actions, does not scrape data, and does not "
        "offer any ban evasion. It helps you plan content ethically while complying with "
        "Instagram's rules."
    )

    print("\nDone. Files created:")
    print(f"- {calendar_path}")
    print(f"- {captions_path}")
    print(f"- {hashtags_path}")
    print(f"- {checklist_path}")
    print(f"- {plan_path}")
    print("\nPillars:", ", ".join(pillars))
    print("\n" + disclaimer + "\n")


if __name__ == "__main__":
    main()