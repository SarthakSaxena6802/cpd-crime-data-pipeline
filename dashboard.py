"""Streamlit dashboard for the Cambridge (MA) Police Department daily log."""
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cpd_local.db")
BAR_COLOR = "#2a78d6"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

st.set_page_config(page_title="Cambridge Crime Trends", page_icon="🚓", layout="wide")


@st.cache_data(ttl=3600)  # re-read the database at most once an hour
def load_incidents() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    return pd.read_sql("SELECT * FROM cpd_incidents", engine, parse_dates=["date_time", "last_updated"])


def show(fig):
    """Apply a consistent, minimal style and draw the chart."""
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), showlegend=False)
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch")


def top_counts(series: pd.Series, name: str, n: int = 10) -> pd.DataFrame:
    return series.value_counts().head(n).rename_axis(name).reset_index(name="incidents")


# ---------- Data ----------
df = load_incidents()

st.title("🚓 Cambridge (MA) Crime Trends")
st.caption(
    "Source: Cambridge Police Department Daily Log (data.cambridgema.gov). "
    "Updated daily by an automated ETL pipeline."
)

# ---------- Filters (one row above the charts) ----------
min_date, max_date = df["date_time"].min().date(), df["date_time"].max().date()
f1, f2 = st.columns([1, 2])
date_range = f1.date_input("Date range", (min_date, max_date), min_value=min_date, max_value=max_date)
types = sorted(df["type"].dropna().unique())
selected_types = f2.multiselect("Record type", types, default=types)

if len(date_range) != 2:
    st.info("Select an end date.")
    st.stop()
start, end = date_range
mask = (
    df["date_time"].dt.date.between(start, end)
    & df["type"].isin(selected_types)
)
data = df[mask]
if data.empty:
    st.warning("No incidents match these filters.")
    st.stop()

# ---------- Key numbers ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total records", f"{len(data):,}")
k2.metric("Arrests", f"{(data['type'] == 'ARREST').sum():,}")
k3.metric("Most common offence", data["subtype"].mode().iat[0].title())
k4.metric("Latest record", data["date_time"].max().strftime("%d %b %Y"))

# ---------- Trends over time ----------
monthly = data.set_index("date_time").resample("MS").size().rename("incidents").reset_index()
fig = px.line(monthly, x="date_time", y="incidents", markers=True, title="Incidents per month")
fig.update_traces(line_color=BAR_COLOR, line_width=2)
fig.update_layout(xaxis_title=None, yaxis_title="Incidents")
show(fig)
st.caption("The most recent month may be incomplete.")

c1, c2 = st.columns(2)
with c1:
    hourly = data.groupby("hour").size().reindex(range(24), fill_value=0).rename("incidents").reset_index()
    fig = px.bar(hourly, x="hour", y="incidents", title="By hour of day")
    fig.update_traces(marker_color=BAR_COLOR)
    fig.update_layout(xaxis_title="Hour (0 = midnight)", yaxis_title="Incidents")
    show(fig)
with c2:
    daily = data["day_of_week"].value_counts().reindex(DAY_ORDER, fill_value=0)
    daily = daily.rename_axis("day").reset_index(name="incidents")
    fig = px.bar(daily, x="day", y="incidents", title="By day of week")
    fig.update_traces(marker_color=BAR_COLOR)
    fig.update_layout(xaxis_title=None, yaxis_title="Incidents")
    show(fig)

heat = pd.crosstab(data["day_of_week"], data["hour"]).reindex(index=DAY_ORDER, columns=range(24), fill_value=0)
fig = px.imshow(
    heat, aspect="auto", color_continuous_scale="Blues", title="When do incidents happen? (day × hour)",
    labels=dict(x="Hour of day", y="", color="Incidents"),
)
show(fig)

# ---------- What and where ----------
c3, c4 = st.columns(2)
with c3:
    top_sub = top_counts(data["subtype"], "offence")
    fig = px.bar(top_sub, x="incidents", y="offence", orientation="h", title="Top 10 offence types")
    fig.update_traces(marker_color=BAR_COLOR)
    fig.update_layout(yaxis=dict(autorange="reversed", title=None), xaxis_title="Incidents")
    show(fig)
with c4:
    top_loc = top_counts(data["location"], "street")
    fig = px.bar(top_loc, x="incidents", y="street", orientation="h", title="Top 10 streets")
    fig.update_traces(marker_color=BAR_COLOR)
    fig.update_layout(yaxis=dict(autorange="reversed", title=None), xaxis_title="Incidents")
    show(fig)

# ---------- Recent incidents ----------
st.subheader("Most recent incidents")
recent = data.sort_values("date_time", ascending=False).head(100)
st.dataframe(
    recent[["date_time", "type", "subtype", "location", "description"]],
    hide_index=True, width="stretch",
)
