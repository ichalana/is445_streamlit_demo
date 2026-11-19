import altair as alt
import pandas as pd
import streamlit as st

DATA_URL = (
    "https://raw.githubusercontent.com/UIUC-iSchool-DataViz/"
    "is445_data/main/building_inventory.csv"
)
TOP_USAGES = 7  # usage types kept by name; the rest become "Other"
TOP_AGENCIES = 12

st.set_page_config(page_title="Illinois State Buildings", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_URL)
    df["Usage Description"] = df["Usage Description"].replace(
        {"Utiility & Miscellan": "Utility & Misc.", "Detention & Correc": "Detention & Correction"}
    )
    top = df["Usage Description"].value_counts().index[:TOP_USAGES]
    df["Usage"] = df["Usage Description"].where(df["Usage Description"].isin(top), "Other")
    return df


df = load_data()

# Buildings with a real construction year and a non-zero footprint.
built = df[(df["Year Constructed"] >= 1800) & (df["Square Footage"] > 0)].copy()
built["Decade"] = (built["Year Constructed"] // 10) * 10

usage_order = (
    built.groupby("Usage")["Square Footage"].sum().sort_values(ascending=False).index.tolist()
)
usage_order = [u for u in usage_order if u != "Other"] + ["Other"]

st.title("What the State of Illinois Owns, and When It Was Built")
st.markdown(
    f"""
This report uses the [Illinois State Building Inventory]({DATA_URL}), a list of
**{len(df):,} buildings** owned by state agencies and universities, with each
building's agency, county, construction year, square footage, status and main use.
For the charts I drop the {len(df) - len(built):,} rows with a missing (zero)
construction year or square footage, which leaves **{len(built):,} buildings**.
"""
)

# ---------------------------------------------------------------- Viz 1
st.header("1. Two centuries of state construction")
st.caption(
    "Drag across the top chart to pick a range of decades; the bottom chart re-totals "
    "square footage by agency for just that range. Click a usage type in the legend "
    "(shift-click for several) to highlight it in both charts. Double-click to reset."
)

brush = alt.selection_interval(encodings=["x"], name="decades")
usage_pick = alt.selection_point(fields=["Usage"], bind="legend", name="usage")
usage_color = alt.Color(
    "Usage:N",
    sort=usage_order,
    scale=alt.Scale(domain=usage_order, scheme="tableau10"),
    legend=alt.Legend(title="Main use (click)", orient="right"),
)

timeline = (
    alt.Chart(built)
    .mark_bar()
    .encode(
        x=alt.X("Decade:O", title="Decade built", axis=alt.Axis(labelAngle=-45)),
        y=alt.Y(
            "sum(Square Footage):Q",
            title="Square footage built",
            axis=alt.Axis(format="~s"),
        ),
        color=usage_color,
        order=alt.Order("usage_rank:Q"),
        opacity=alt.condition(usage_pick, alt.value(1), alt.value(0.15)),
        tooltip=[
            alt.Tooltip("Decade:O", title="Decade"),
            alt.Tooltip("Usage:N"),
            alt.Tooltip("sum(Square Footage):Q", title="Sq ft", format=","),
            alt.Tooltip("count():Q", title="Buildings"),
        ],
    )
    .transform_calculate(usage_rank=f"indexof({usage_order}, datum.Usage)")
    .add_params(brush, usage_pick)
    .properties(height=300, title="Square footage built per decade, by main use")
)

agencies = (
    alt.Chart(built)
    .mark_bar()
    .encode(
        y=alt.Y("Agency Name:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300, labelOverlap=False)),
        x=alt.X(
            "sum(Square Footage):Q",
            title="Square footage (selected decades)",
            axis=alt.Axis(format="~s"),
        ),
        color=usage_color,
        order=alt.Order("usage_rank:Q"),
        opacity=alt.condition(usage_pick, alt.value(1), alt.value(0.15)),
        tooltip=[
            alt.Tooltip("Agency Name:N", title="Agency"),
            alt.Tooltip("Usage:N"),
            alt.Tooltip("sum(Square Footage):Q", title="Sq ft", format=","),
            alt.Tooltip("count():Q", title="Buildings"),
        ],
    )
    .transform_filter(brush)
    .transform_calculate(usage_rank=f"indexof({usage_order}, datum.Usage)")
    .transform_joinaggregate(agency_total="sum(Square Footage)", groupby=["Agency Name"])
    .transform_window(
        agency_rank="dense_rank()", sort=[alt.SortField("agency_total", order="descending")]
    )
    .transform_filter(f"datum.agency_rank <= {TOP_AGENCIES}")
    .properties(height=320, title=f"Top {TOP_AGENCIES} agencies by square footage in the selected decades")
)

st.altair_chart(
    alt.vconcat(timeline, agencies).resolve_scale(color="shared"),
    use_container_width=True,
)

st.subheader("Write-up")
st.markdown(
    """
This chart shows **when** the state's current buildings were built and **what kind**
of space each era added. The top panel is a stacked bar chart of total square footage
by decade of construction, split by each building's main use, and it highlights the
big postwar building boom of the 1950s–1970s, peaking in the 1960s with over 21
million square feet, followed by a steady slowdown in every decade since. I used
**square footage** rather than a count of buildings because thousands of the
buildings are small sheds and storage barns (the median building is about 1,800 sq ft),
so a count would make a tiny DNR storage shed look as important as a university hall.
Decade is an **ordinal** field on a banded x-axis, since it is binned time where the
order matters but each bar is a bucket, and the y-axis is a **quantitative**
sum shown with SI-style labels (`200k`, `1M`) so the numbers stay readable. Main use is
**nominal**, so I colored it with the categorical `tableau10` scheme and kept only the
seven largest categories plus "Other" so every color stays distinct; the stack order
and legend order both follow total square footage, so the biggest categories sit at
the bottom of each bar. The interaction is a linked **interval brush**: dragging over
some decades re-filters the agency chart below, so you can ask questions like "who
built most of the 1960s?" (the University of Illinois, by far) versus "who built
since 1990?" (Corrections, closely followed by the universities). Clicking the **legend** highlights one use type in
both panels at once. If I had more time, I would add a toggle between square footage
and building counts, and I would adjust for buildings whose "acquired" year differs
from their construction year, since some older buildings were bought by the state long
after they were built.
"""
)

# ---------------------------------------------------------------- Viz 2
st.header("2. Which agencies own which kinds of buildings?")
st.caption(
    "Use the controls to change what the heatmap measures and which buildings it includes. "
    "Building age is measured to 2019, the last year in the dataset."
)

c1, c2, c3 = st.columns([1.2, 1.4, 1.4])
with c1:
    metric = st.radio(
        "Color the cells by",
        ["Number of buildings", "Total square footage", "Median building age (years)"],
    )
with c2:
    statuses = st.multiselect(
        "Building status",
        sorted(df["Bldg Status"].unique()),
        default=sorted(df["Bldg Status"].unique()),
    )
with c3:
    yr_min, yr_max = int(built["Year Constructed"].min()), int(built["Year Constructed"].max())
    years = st.slider("Built between", yr_min, yr_max, (yr_min, yr_max))

subset = built[
    built["Bldg Status"].isin(statuses)
    & built["Year Constructed"].between(years[0], years[1])
]

if subset.empty:
    st.info("No buildings match these filters. Try widening the year range or adding a status.")
else:
    top_agencies = (
        subset["Agency Name"].value_counts().index[:TOP_AGENCIES].tolist()
    )
    grid = (
        subset[subset["Agency Name"].isin(top_agencies)]
        .assign(Age=lambda d: 2019 - d["Year Constructed"])
        .groupby(["Agency Name", "Usage"])
        .agg(
            Buildings=("Square Footage", "size"),
            SqFt=("Square Footage", "sum"),
            MedianAge=("Age", "median"),
        )
        .reset_index()
    )

    field, title, fmt, scheme = {
        "Number of buildings": ("Buildings", "Buildings", ",", "blues"),
        "Total square footage": ("SqFt", "Square footage", "~s", "greens"),
        "Median building age (years)": ("MedianAge", "Median age (yrs)", ".0f", "orangered"),
    }[metric]
    log = field in ("Buildings", "SqFt")

    base = alt.Chart(grid).encode(
        x=alt.X("Usage:N", sort=usage_order, title="Main use", axis=alt.Axis(labelAngle=-40, labelLimit=200, labelOverlap=False)),
        y=alt.Y("Agency Name:N", sort=top_agencies, title=None, axis=alt.Axis(labelLimit=300, labelOverlap=False)),
    )
    heat = base.mark_rect(stroke="white", strokeWidth=1).encode(
        color=alt.Color(
            f"{field}:Q",
            title=title,
            scale=alt.Scale(type="log" if log else "linear", scheme=scheme),
            legend=alt.Legend(format=fmt),
        ),
        tooltip=[
            alt.Tooltip("Agency Name:N", title="Agency"),
            alt.Tooltip("Usage:N", title="Main use"),
            alt.Tooltip("Buildings:Q", format=","),
            alt.Tooltip("SqFt:Q", title="Square footage", format=","),
            alt.Tooltip("MedianAge:Q", title="Median age (yrs)", format=".0f"),
        ],
    )
    # White text on the darkest third of the color range, black elsewhere.
    lo, hi = grid[field].min(), grid[field].max()
    cutoff = (lo * hi**2) ** (1 / 3) if log else lo + (hi - lo) * 2 / 3
    labels = base.mark_text(fontSize=10).encode(
        text=alt.Text(f"{field}:Q", format=fmt),
        color=alt.condition(f"datum.{field} > {cutoff}", alt.value("white"), alt.value("black")),
    )
    st.altair_chart(
        (heat + labels).properties(
            height=420,
            title=f"{metric} by agency and main use ({len(subset):,} buildings, top {TOP_AGENCIES} agencies by count)",
        ),
        use_container_width=True,
    )

st.subheader("Write-up")
st.markdown(
    """
The heatmap answers a different question than the first chart: instead of *when*,
it shows *who owns what*. Each row is one of the twelve agencies with the most
buildings (after filtering), each column is a main use, and each cell is colored by a
measure you choose with the radio buttons: the number of buildings, their total square
footage, or their median age. This makes each agency's "fingerprint" easy to spot:
Natural Resources is mostly storage and "unusual" structures, Corrections is about
half detention buildings, and the universities spread across industrial, business,
residential and education uses. I chose a **heatmap** (`mark_rect`)
because both axes are **nominal** categories and a grid lets you scan across a row (one
agency) or down a column (one use) without a dozen separate bar charts. Rows are
sorted by building count and columns follow the same use order as chart 1, so the two
charts read consistently. Color is a **quantitative** single-hue sequential scheme, and
I give each measure its own hue (blues, greens, orange-red) so it is obvious when the
measure has changed. Counts and square footage use a **log scale** because a few cells
(such as DNR storage) are hundreds of times larger than the rest and would otherwise
wash out the whole grid; median age is linear because it has a narrow, even range.
Each cell is also labeled with its value, and the tooltip always shows all three
measures. The Streamlit widgets add the interactivity: the **status** filter lets you
look only at abandoned buildings (mostly Natural Resources and Human Services sites), and
the **year slider** lets you see how the mix of owners changes for newer buildings.
With more time, I would let the user choose the number of agencies shown, add a
county filter or small map, and normalize each row to percentages so small agencies
could be compared with large ones.
"""
)

# ---------------------------------------------------------------- HW5 note
st.header("Relationship to Homework #5")
st.markdown(
    """
Nothing in this app is reused from my Homework #5. That homework used the NUFORC
UFO sightings dataset (a timeline with a shape bar chart, and a map). This app uses a
different dataset (the Illinois building inventory), different charts (a stacked bar
chart linked to an agency bar chart, and a widget-driven heatmap), and all of the
text above is newly written for this assignment, so no text is quoted from Homework #5.
"""
)
