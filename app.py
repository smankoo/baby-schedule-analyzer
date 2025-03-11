import streamlit as st
import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple
import altair as alt

# -------------------------------------------------------
# BabyStatsAnalyzer class (same logic as before)
# -------------------------------------------------------


class BabyStatsAnalyzer:
    def __init__(self, data: str, hide_stale_events: bool = True):
        self.data = data
        self.hide_stale_events = hide_stale_events
        self.events_by_date: Dict[str, List[Dict[str, str]]] = {}
        self.day_stats: Dict[str, Dict[str, Any]] = {}
        self.global_event_count: Dict[str, int] = {}
        self.global_event_original: Dict[str, str] = {}

    def parse_standard_rows(self) -> None:
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
        self.global_event_count = {}
        self.global_event_original = {}
        for events in self.events_by_date.values():
            for event in events:
                key = event["description"].strip().lower()
                self.global_event_count[key] = self.global_event_count.get(key, 0) + 1
                if key not in self.global_event_original:
                    self.global_event_original[key] = event["description"].strip()

    def analyze_events_by_day(self) -> None:
        self.compute_global_event_counts()
        globally_regular = {
            key for key, cnt in self.global_event_count.items() if cnt >= 3
        }
        for date, events in self.events_by_date.items():
            regular_events: Dict[str, int] = {}
            other_events_raw: List[Tuple[str, str]] = []
            for event in events:
                key = event["description"].strip().lower()
                d = datetime.strptime(event["time"], "%I:%M %p")
                non_zero_time = d.strftime("%I:%M %p").lstrip("0")
                if key in globally_regular:
                    header = self.global_event_original[key]
                    regular_events[header] = regular_events.get(header, 0) + 1
                else:
                    other_events_raw.append((non_zero_time, event["description"]))
            other_events_raw.sort(key=lambda x: datetime.strptime(x[0], "%I:%M %p"))
            self.day_stats[date] = {
                "regular": regular_events,
                "other_raw": other_events_raw,
            }

    def format_other_events(self) -> None:
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

    def get_tables(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        sorted_dates = sorted(
            self.day_stats.keys(), key=lambda x: datetime.strptime(x, "%b %d, %Y")
        )
        last_three = sorted_dates[-3:] if len(sorted_dates) >= 3 else sorted_dates

        globally_regular_headers = {
            self.global_event_original[key]
            for key, cnt in self.global_event_count.items()
            if cnt >= 3
        }
        sorted_regular_events = sorted(globally_regular_headers)

        hidden_events: Dict[str, int] = {}
        if self.hide_stale_events and len(last_three) >= 3:
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
                    for key, orig in self.global_event_original.items():
                        if orig == event:
                            hidden_events[event] = self.global_event_count.get(key, 0)
                            break
                else:
                    events_to_keep.append(event)
            sorted_regular_events = events_to_keep

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
        df["Date_dt"] = df["Date"].apply(lambda x: datetime.strptime(x, "%b %d, %Y"))
        df = df.sort_values(by="Date_dt").reset_index(drop=True)

        # Build display version with the year removed.
        df_display = df.copy()
        df_display["Date"] = df_display["Date"].apply(lambda x: x.split(",")[0])
        df_display = df_display.drop(columns=["Date_dt"])

        hidden_df = (
            pd.DataFrame(
                [
                    {"Event": event, "Total Count": count}
                    for event, count in hidden_events.items()
                ]
            )
            if hidden_events
            else pd.DataFrame()
        )

        return df_display, df, hidden_df

    def run_analysis(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        self.parse_standard_rows()
        self.analyze_events_by_day()
        self.format_other_events()
        return self.get_tables()


# -------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------

st.title("Baby Schedule Analyzer")

st.markdown(
    """
Paste your baby schedule data (in the standard format):

Mar 11, 2025 - 5:48 AM: Breastfeeding

Then click **Analyze** to view the table and interactive grouped bar chart.
"""
)

default_data = """Mar 2, 2025 - 7:34 PM: Breastfeeding
Mar 2, 2025 - 10:16 PM: Breastfeeding
Mar 2, 2025 - 10:19 PM: Wet diaper
Mar 2, 2025 - 11:00 PM: Breastfeeding
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
Mar 9, 2025 - 10:11 AM: Synthroid
Mar 9, 2025 - 4:15 PM: Poopy diaper(light)
Mar 9, 2025 - 5:00 PM: Struggling to sleep
Mar 10, 2025 - 10:15 AM: Synthroid
Mar 10, 2025 - 4:21 AM: Struggling to poop
Mar 10, 2025 - 4:30 AM: Breastfeeding
Mar 10, 2025 - 5:00 AM: Breastfeeding
Mar 10, 2025 - 6:00 AM: Breastfeeding
"""

baby_data = st.text_area("Baby Data", value=default_data, height=300)
hide_stale = st.checkbox(
    "Hide stale events (absent for 3 consecutive days)", value=True
)

if st.button("Analyze"):
    if baby_data.strip() == "":
        st.error("Please enter baby schedule data.")
    else:
        analyzer = BabyStatsAnalyzer(baby_data, hide_stale_events=hide_stale)
        main_table_df, chart_df, hidden_df = analyzer.run_analysis()

        st.subheader("Data Table")
        st.dataframe(main_table_df)

        # Prepare data for charting: melt the regular event columns (ignoring 'Other')
        chart_columns = [
            col for col in chart_df.columns if col not in ["Date", "Other", "Date_dt"]
        ]
        if chart_columns:
            # Melt into long form
            chart_data = chart_df.melt(
                id_vars=["Date_dt"],
                value_vars=chart_columns,
                var_name="Event",
                value_name="Count",
            )
            # Create a label for each day (no year), e.g. "Mar 2"
            chart_data["DayString"] = chart_data["Date_dt"].dt.strftime("%b %-d")
            # Sort days in ascending order
            unique_days = (
                chart_data[["Date_dt", "DayString"]]
                .drop_duplicates()
                .sort_values("Date_dt")["DayString"]
                .tolist()
            )

            # Build a grouped bar chart using x=DayString as a discrete scale,
            # and xOffset=Event to group them side by side.
            chart = (
                alt.Chart(chart_data)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "DayString:N", sort=unique_days, axis=alt.Axis(labelAngle=-45)
                    ),
                    xOffset=alt.X("Event:N"),
                    y=alt.Y("Count:Q", title="Count"),
                    color=alt.Color("Event:N", title="Event"),
                    tooltip=["DayString", "Event", "Count"],
                )
                .properties(width=600)
                .interactive()
            )
            st.subheader("Interactive Grouped Bar Chart of Regular Events")
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No regular events available for charting.")

        if not hidden_df.empty:
            st.subheader("Hidden Events (Absence for 3+ Days)")
            st.dataframe(hidden_df)
