#!/usr/bin/env python3
"""
Baby Stats Analyzer (Global Regular vs Other with Stale Event Hiding)

This script parses baby schedule logs in the standard row format:
    "Mar 11, 2025 - 5:48 AM: Breastfeeding"
It first computes the overall occurrence count for each event (case–insensitive).
Then, for each day:
  - If an event is globally regular (overall count >= 3), its occurrences for that day
    are counted and placed in its own column.
  - Otherwise, the occurrence is listed in the "Other" column.
"Other" events are sorted by time and their time portion is right–justified to a global fixed width.
Additionally, if the toggle (hide_stale_events) is enabled (default True), any globally regular event
that has not occurred in each of the last three days is hidden from the main table.
A summary table of the hidden events is printed below the main table.

Usage:
    Run this script directly. Modify baby_data or adapt the input method as needed.

Note:
    Requires the pandas and tabulate libraries.
    Install via: pip install pandas tabulate
"""

import re
from typing import Dict, List, Any, Tuple
from datetime import datetime
import pandas as pd
from tabulate import tabulate


class BabyStatsAnalyzer:
    """
    Parses baby schedule data (standard rows) and generates a table that:
      - Uses a global classification of events into:
          • Regular events (overall count >= 3) as separate columns.
          • Other events (overall count < 3) combined into a single column.
      - Aligns the time portions in the "Other" column (right–justified to a global width).
      - Optionally hides (by default) any regular event that has been absent for three consecutive days.
      - Displays a hidden-events summary below the main table.
    """

    def __init__(self, data: str, hide_stale_events: bool = True):
        """
        Args:
            data (str): Raw text containing the baby schedule in standard row format.
            hide_stale_events (bool): If True, hide events that haven't occurred for three days in a row.
        """
        self.data = data
        self.hide_stale_events = hide_stale_events
        # Dictionary: date string -> list of events (each is a dict with keys "time" and "description")
        self.events_by_date: Dict[str, List[Dict[str, str]]] = {}
        # Per-day stats: each date maps to a dict with keys 'regular' (dict) and 'other_raw' (list of tuples)
        self.day_stats: Dict[str, Dict[str, Any]] = {}
        # Global counts for events (using lower-case keys)
        self.global_event_count: Dict[str, int] = {}
        # Map lower-case event key to its original text (for header display)
        self.global_event_original: Dict[str, str] = {}

    def parse_standard_rows(self) -> None:
        """
        Parse only rows matching:
            "Mar 11, 2025 - 5:48 AM: Breastfeeding"
        """
        pattern = re.compile(
            r"^(?P<date>[A-Za-z]{3}\s+\d{1,2},\s+\d{4})\s*-\s*"
            r"(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM)):\s*(?P<event>.+)$"
        )
        for line in self.data.splitlines():
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if match:
                date_str = match.group("date")
                time_str = match.group("time")
                event_text = match.group("event").strip()
                if date_str not in self.events_by_date:
                    self.events_by_date[date_str] = []
                self.events_by_date[date_str].append(
                    {"time": time_str, "description": event_text}
                )

    def compute_global_event_counts(self) -> None:
        """
        Compute overall (global) count for each event (case-insensitive) and record its original text.
        """
        self.global_event_count = {}
        self.global_event_original = {}
        for events in self.events_by_date.values():
            for event in events:
                key = event["description"].strip().lower()
                self.global_event_count[key] = self.global_event_count.get(key, 0) + 1
                if key not in self.global_event_original:
                    self.global_event_original[key] = event["description"].strip()

    def analyze_events_by_day(self) -> None:
        """
        For each day, classify each event occurrence based on global counts.
          - If the event is globally regular (overall count >= 3), add to that day’s regular dict.
          - Otherwise, add it to that day’s "Other" list (storing its non–zero–padded time and description).
        """
        self.compute_global_event_counts()
        # Determine the set of globally regular event keys.
        globally_regular = {
            key for key, cnt in self.global_event_count.items() if cnt >= 3
        }

        for date, events in self.events_by_date.items():
            regular_events: Dict[str, int] = {}
            other_events_raw: List[Tuple[str, str]] = []
            for event in events:
                key = event["description"].strip().lower()
                d = datetime.strptime(event["time"], "%I:%M %p")
                # Get non-zero–padded time (e.g. "4:15 PM")
                non_zero_time = d.strftime("%I:%M %p").lstrip("0")
                if key in globally_regular:
                    header = self.global_event_original[key]
                    regular_events[header] = regular_events.get(header, 0) + 1
                else:
                    other_events_raw.append((non_zero_time, event["description"]))
            # Sort the "Other" events by time.
            other_events_raw.sort(key=lambda x: datetime.strptime(x[0], "%I:%M %p"))
            self.day_stats[date] = {
                "regular": regular_events,
                "other_raw": other_events_raw,
            }

    def format_other_events(self) -> None:
        """
        Format each day’s "Other" events so that the time portion is right–justified
        to a global maximum width (across all days).
        """
        all_other_times: List[str] = []
        for stats in self.day_stats.values():
            for t, _ in stats.get("other_raw", []):
                all_other_times.append(t)
        global_max_width = max((len(t) for t in all_other_times), default=0)

        for date, stats in self.day_stats.items():
            other_raw = stats.get("other_raw", [])
            formatted_lines = [
                f"{t.rjust(global_max_width)} - {desc}" for t, desc in other_raw
            ]
            self.day_stats[date]["other"] = "\n".join(formatted_lines)
            del self.day_stats[date]["other_raw"]

    def generate_table(self) -> None:
        """
        Build and print the main table with:
        - 'Date' column (sorted ascending)
        - One column per globally regular event (that is not stale)
        - 'Other' column with aligned events.
        If stale events (no occurrence in the last three days) are hidden,
        print their overall stats below.
        """
        # Get sorted dates.
        sorted_dates = sorted(
            self.day_stats.keys(), key=lambda x: datetime.strptime(x, "%b %d, %Y")
        )
        last_three = sorted_dates[-3:] if len(sorted_dates) >= 3 else sorted_dates

        # Build the union of globally regular event headers.
        globally_regular_headers = {
            self.global_event_original[key]
            for key, cnt in self.global_event_count.items()
            if cnt >= 3
        }
        sorted_regular_events = sorted(globally_regular_headers)

        hidden_events: Dict[str, int] = {}
        if self.hide_stale_events and len(last_three) >= 3:
            # For each regular event, check if it is absent (0 count) in all of the last three days.
            events_to_keep = []
            for event in sorted_regular_events:
                absent_in_all = True
                for date in last_three:
                    count = (
                        self.day_stats.get(date, {}).get("regular", {}).get(event, 0)
                    )
                    if count > 0:
                        absent_in_all = False
                        break
                if absent_in_all:
                    # Determine overall count from global counts.
                    # Find the lower-case key whose original text matches this event.
                    for key, orig in self.global_event_original.items():
                        if orig == event:
                            hidden_events[event] = self.global_event_count.get(key, 0)
                            break
                else:
                    events_to_keep.append(event)
            sorted_regular_events = events_to_keep

        # Build table rows.
        table_rows = []
        for date in sorted_dates:
            row = {"Date": date}
            for event in sorted_regular_events:
                row[event] = (
                    self.day_stats.get(date, {}).get("regular", {}).get(event, 0)
                )
            row["Other"] = self.day_stats.get(date, {}).get("other", "")
            table_rows.append(row)

        df = pd.DataFrame(table_rows)
        df["dt"] = df["Date"].apply(lambda x: datetime.strptime(x, "%b %d, %Y"))
        df = df.sort_values(by="dt").drop(columns=["dt"]).reset_index(drop=True)
        # Remove the year from the printed Date column (retain it internally for sorting)
        df["Date"] = df["Date"].apply(lambda x: x.split(",")[0])
        print(
            tabulate(
                df, headers="keys", tablefmt="grid", showindex=False, stralign="left"
            )
        )

        # If any events were hidden, print a summary table.
        if hidden_events:
            print("\nHidden Events (absent for 3 consecutive days):")
            hidden_table = [
                {"Event": event, "Total Count": count}
                for event, count in hidden_events.items()
            ]
            print(
                tabulate(
                    hidden_table,
                    headers="keys",
                    tablefmt="grid",
                    showindex=False,
                    stralign="left",
                )
            )

    def run_analysis(self) -> None:
        """
        Run the full analysis: parse rows, classify events globally and per day,
        format the "Other" events, and print the final table (with hidden event summary if applicable).
        """
        self.parse_standard_rows()
        self.analyze_events_by_day()
        self.format_other_events()
        self.generate_table()


if __name__ == "__main__":
    # Example baby schedule data with standard format rows.
    baby_data = """
Kirat’s Schedule

Feb 25 - Started on Synthroid
Feb 26
7:00 AM poop, red spots on face
10:00 AM Synthroid
11:00 AM poop
12:00 PM poop

Feb 27

7:41 am wet diaper 
10:30 Synthroid
12:00 PM feed, wet diaper
1:20 PM feed, wet diaper
2:20 PM feed, poopy (light) diaper
3:50 PM feed
5:30 PM feed, poopy diaper
7:30 PM feed, wet diaper
9:00 PM feed, wet diaper
9:30 PM feed, wet diaper

Feb 28

12:30 AM feed, wet diaper
3:30 AM feed, poopy diaper 
4:30 AM formula 10 ml
5:30 AM poopy diaper
3:30 - 06:00 AM awake 
6:00 - feed and sleep
8:00 - feed and wet diaper
9:00 - Synthroid
10:00 - feed
11:00 - feed
12:30 - feed
2:00 - feed
4:00 - feed, poopy diaper 
6:30 - feed
8:30 - feed

March 1
9:00 - feed

March 2
4:30 - poopy diaper

Mar 2, 2025 - 7:34 PM: Breastfeeding
Mar 2, 2025 - 10:16 PM: Breastfeeding
Mar 2, 2025 - 10:19 PM: Wet diaper
Mar 3, 2025 - 2:06 AM: Breastfeeding
Mar 3, 2025 - 5:05 AM: Breastfeeding
Mar 3, 2025 - 5:23 AM: Wet diaper
Mar 3, 2025 - 6:54 AM: Breastfeeding
Mar 3, 2025 - 8:11 AM: Wet diaper
Mar 3, 2025 - 8:16 AM: Breastfeeding
Mar 3, 2025 - 9:53 AM: Breastfeeding
Mar 3, 2025 - 10:06 AM: Poopy diaper
Mar 3, 2025 - 11:47 AM: Breastfeeding
Mar 3, 2025 - 12:01 PM: Wet diaper
Mar 3, 2025 - 1:46 PM: Breastfeeding
Mar 3, 2025 - 1:48 PM: Wet diaper
Mar 3, 2025 - 1:49 PM: Poopy diaper
Mar 3, 2025 - 4:30 PM: Breastfeeding
Mar 3, 2025 - 6:30 PM: Breastfeeding
Mar 3, 2025 - 6:43 PM: Wet diaper
Mar 3, 2025 - 9:08 PM: Breastfeeding
Mar 3, 2025 - 10:05 PM: Wet diaper
Mar 3, 2025 - 10:24 PM: Breastfeeding
Mar 4, 2025 - 12:30 AM: Breastfeeding
Mar 4, 2025 - 3:46 AM: Breastfeeding
Mar 4, 2025 - 4:08 AM: Wet diaper
Mar 4, 2025 - 5:38 AM: Breastfeeding
Mar 4, 2025 - 6:56 AM: Breastfeeding
Mar 4, 2025 - 9:06 AM: Breastfeeding
Mar 4, 2025 - 9:26 AM: Wet diaper
Mar 4, 2025 - 9:44 AM: Poopy diaper
Mar 4, 2025 - 11:33 AM: Breastfeeding
Mar 4, 2025 - 11:47 AM: Wet diaper
Mar 4, 2025 - 1:35 PM: Breastfeeding
Mar 4, 2025 - 2:16 PM: Poopy diaper
Mar 4, 2025 - 3:34 PM: Wet diaper
Mar 4, 2025 - 3:35 PM: Breastfeeding
Mar 4, 2025 - 4:33 PM: Struggling to sleep
Mar 4, 2025 - 5:50 PM: Breastfeeding
Mar 4, 2025 - 6:15 PM: Wet diaper
Mar 4, 2025 - 9:03 PM: Breastfeeding
Mar 4, 2025 - 9:34 PM: Wet diaper
Mar 4, 2025 - 11:55 PM: Breastfeeding
Mar 5, 2025 - 1:27 AM: Breastfeeding
Mar 5, 2025 - 2:00 AM: Poopy diaper
Mar 5, 2025 - 12:00 - 2:30 AM: Struggling to sleep
Mar 5, 2025 - 5:36 AM: Breastfeeding
Mar 5, 2025 - 8:02 AM: Breastfeeding
Mar 5, 2025 - 8:17 AM: Wet diaper
Mar 5, 2025 - 9:19 AM: Breastfeeding
Mar 5, 2025 - 10:30 AM: Sleeping
Mar 5, 2025 - 11:36 AM: Breastfeeding
Mar 5, 2025 - 11:47 AM: Wet diaper
Mar 5, 2025 - 11:47 AM: Sleeping
Mar 5, 2025 - 11:58 AM: Wake up
Mar 5, 2025 - 12:21 PM: Sleeping
Mar 5, 2025 - 12:22 PM: Wake up
Mar 5, 2025 - 12:22 PM: Sleeping
Mar 5, 2025 - 1:17 PM: Wake up 
Mar 5, 2025 - 1:17 PM: Breastfeeding
Mar 5, 2025 - 1:38 PM: Wet diaper
Mar 5, 2025 - 1:38 PM: Sleeping
Mar 5, 2025 - 3:19 PM: Wake up
Mar 5, 2025 - 3:25 PM: Breastfeeding
Mar 5, 2025 - 3:50 PM: Sleeping
Mar 5, 2025 - 4:48 PM: Wake up
Mar 5, 2025 - 4:48 PM: Wet diaper
Mar 5, 2025 - 4:50 PM: Breastfeeding
Mar 5, 2025 - 5:52 PM: Breastfeeding
Mar 5, 2025 - 9:20 PM: Breastfeeding
Mar 5, 2025 - 11:13 PM: Breastfeeding
Mar 5, 2025 - 11:21 PM: Poopy diaper
Mar 5, 2025 - 11:40 PM: Sleeping
Mar 6, 2025 - 2:11 AM: Wake up
Mar 6, 2025 - 2:11 AM: Breastfeeding
Mar 6, 2025 - 2:20 AM: Sleeping
Mar 6, 2025 - 2:27 AM: Wake up
Mar 6, 2025 - 2:27 AM: Breastfeeding
Mar 6, 2025 - 2:37 AM: Sleeping
Mar 6, 2025 - 3:10 AM: Wake up
Mar 6, 2025 - 4:13 AM: Breastfeeding
Mar 6, 2025 - 4:41 AM: Sleeping
Mar 6, 2025 - 6:12 AM: Wake up
Mar 6, 2025 - 6:17 AM: Wet diaper
Mar 6, 2025 - 6:17 AM: Breastfeeding
Mar 6, 2025 - 6:45 AM: Breastfeeding
Mar 6, 2025 - 7:31 AM: Wet diaper
Mar 6, 2025 - 7:33 AM: Wet diaper
Mar 6, 2025 - 9:25 AM: Breastfeeding
Mar 6, 2025 - 11:17 AM: Breastfeeding
Mar 6, 2025 - 11:39 AM: Wet diaper
Mar 6, 2025 - 2:00 PM: Breastfeeding
Mar 6, 2025 - 2:12 PM: Wet diaper
Mar 6, 2025 - 3:50 PM: Breastfeeding
Mar 6, 2025 - 4:32 PM: Poopy diaper (light)
Mar 6, 2025 - 4:32 PM: Wet diaper
Mar 6, 2025 - 5:59 PM: Wet diaper
Mar 6, 2025 - 5:59 PM: Breastfeeding
Mar 6, 2025 - 8:30 PM: Breastfeeding
Mar 6, 2025 - 8:47 PM: Wet diaper
Mar 6, 2025 - 9:30 PM: Pumping
Mar 6, 2025 - 11:00 PM: Breastfeeding
Mar 6, 2025 - 11:12 PM: Wet diaper
Mar 7, 2025 - 12:49 AM: Breastfeeding
Mar 7, 2025 - 2:26 AM: Breastfeeding
Mar 7, 2025 - 5:01 AM: Breastfeeding
Mar 7, 2025 - 5:16 AM: Wet diaper
Mar 7, 2025 - 6:13 AM: Breastfeeding
Mar 7, 2025 - 7:25 AM: Breastfeeding
Mar 7, 2025 - 9:45 AM: Breastfeeding
Mar 7, 2025 - 9:45 AM: Poopy diaper
Mar 7, 2025 - 9:45 AM: Wet diaper 
Mar 7, 2025 - 11:49 AM: Breastfeeding
Mar 7, 2025 - 2:32 PM: Breastfeeding
Mar 7, 2025 - 2:45 PM: Wet diaper
Mar 7, 2025 - 2:32 PM: Breastfeeding
Mar 7, 2025 - 5:00 PM: Breastfeeding
Mar 7, 2025 - 8:05 PM: Breastfeeding
Mar 7, 2025 - 8:30 PM: Wet diaper
Mar 7, 2025 - 9:58 PM: Breastfeeding
Mar 8, 2025 - 12:00 AM: Breastfeeding
Mar 8, 2025 - 1:54 AM: Breastfeeding
Mar 8, 2025 - 1:56 AM: Wet diaper
Mar 8, 2025 - 3:34 AM: Breastfeeding
Mar 8, 2025 - 4:21 AM: Breastfeeding
Mar 8, 2025 - 7:00 AM: Breastfeeding
Mar 8, 2025 - 7:41 AM: Wet diaper
Mar 8, 2025 - 8:00 AM: Breastfeeding
Mar 8, 2025 - 9:49 AM: Breastfeeding
Mar 8, 2025 - 10:01 AM: Wet diaper
Mar 8, 2025 - 10:11 AM: Poopy diaper
Mar 8, 2025 - 1:15 PM: Breastfeeding
Mar 8, 2025 - 1:31 PM: Wet diaper
Mar 8, 2025 - 3:45 PM: Breastfeeding
Mar 8, 2025 - 4:44 PM: Wet diaper
Mar 8, 2025 - 5:10 PM: Breastfeeding
Mar 8, 2025 - 7:11 PM: Breastfeeding
Mar 8, 2025 - 9:00 PM: Breastfeeding
Mar 8, 2025 - 9:37 PM: Wet diaper
Mar 9, 2025 - 1:37 AM: Breastfeeding
Mar 9, 2025 - 1:47 AM: Wet diaper
Mar 9, 2025 - 4:32 AM: Breastfeeding
Mar 9, 2025 - 6:06 AM: Breastfeeding
Mar 9, 2025 - 6:17 AM: Wet diaper
Mar 9, 2025 - 7:32 AM: Breastfeeding
Mar 9, 2025 - 10:11 AM: Synthroid 
Mar 9, 2025 - 10:53 AM: Breastfeeding
Mar 9, 2025 - 12:31 PM: Breastfeeding
Mar 9, 2025 - 2:17 PM: Breastfeeding
Mar 9, 2025 - 2:30 PM: Wet diaper
Mar 9, 2025 - 4:15 PM: Poopy diaper(light)
Mar 9, 2025 - 4:17 PM: Breastfeeding
Mar 9, 2025 - 4:20 PM: Straining to poop all day
Mar 9, 2025 - 6:15 PM: Breastfeeding
Mar 9, 2025 - 8:57 PM: Breastfeeding
Mar 9, 2025 - 9:30 PM: Wet diaper
Mar 9, 2025 - 9:58 PM: Breastfeeding
Mar 9, 2025 - 10:33 PM: Breastfeeding
Mar 10, 2025 - 12:55 AM: Breastfeeding
Mar 10, 2025 - 1:11 AM: Wet diaper
Mar 10, 2025 - 1:11 AM: Poopy diaper(light)
Mar 10, 2025 - 3:40 AM: Breastfeeding
Mar 10, 2025 - 5:13 AM: Breastfeeding
Mar 10, 2025 - 5:50 AM: Breastfeeding
Mar 10, 2025 - 7:15 AM: Wet diaper
Mar 10, 2025 - 7:15 AM: Breastfeeding
Mar 10, 2025 - 9:38 AM: Breastfeeding
Mar 10, 2025 - 9:49 AM: Wet diaper
Mar 10, 2025 - 10:15 AM: Synthroid
Mar 10, 2025 - 12:02 PM: Breastfeeding
Mar 10, 2025 - 12:09 PM: Poopy diaper
Mar 10, 2025 - 2:41 PM: Breastfeeding
Mar 10, 2025 - 2:50 PM: Poopy diaper
Mar 10, 2025 - 5:27 PM: Breastfeeding
Mar 10, 2025 - 8:15 PM: Breastfeeding
Mar 10, 2025 - 9:19 PM: Poopy diaper
Mar 10, 2025 - 9:37 PM: Breastfeeding
Mar 10, 2025 - 11:16 PM: Breastfeeding
Mar 10, 2025 - 11:33 PM: Wet diaper
Mar 11, 2025 - 1:29 AM: Breastfeeding
Mar 11, 2025 - 3:59 AM: Breastfeeding
Mar 11, 2025 - 4:11 AM: Wet diaper
Mar 11, 2025 - 5:48 AM: Breastfeeding
Mar 11, 2025 - 7:32 AM: Breastfeeding
Mar 11, 2025 - 8:49 AM: Wet diaper
    """

    analyzer = BabyStatsAnalyzer(baby_data)
    analyzer.run_analysis()
