import pandas as pd
import matplotlib.pyplot as plt
import folium
import streamlit as st
from streamlit_folium import st_folium

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="San Diego Widow Spider Tracker",
    page_icon="🕷️",
    layout="wide",
)

# ── Load & clean data ─────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("data/observations-spiders.csv")

    df = df.dropna()
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]

    duplicate_columns = ["observed_on", "time_observed_at", "latitude", "longitude", "scientific_name"]
    df = df.drop_duplicates(subset=duplicate_columns, keep="first").copy()

    df["scientific_name"] = df["scientific_name"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)

    df["observed_on"] = pd.to_datetime(df["observed_on"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["observed_on"])

    species = ["Latrodectus geometricus", "Latrodectus hesperus"]
    df = df[df["scientific_name"].isin(species)].copy()

    return df

df = load_data()

INVASIVE = "Latrodectus geometricus"
NATIVE   = "Latrodectus hesperus"
SPECIES_COLORS = {INVASIVE: "red", NATIVE: "blue"}
SPECIES_LABELS = {
    INVASIVE: "Brown Widow (invasive)",
    NATIVE:   "Western Black Widow (native)",
}

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🕷️ San Diego Widow Spider Distribution")
st.markdown(
    """
    This dashboard explores **iNaturalist** citizen-science observations of two widow spider species
    in the San Diego area — and what their populations reveal about **invasive species spread**.

    > **Data source:** [iNaturalist](https://www.inaturalist.org/) — a platform where anyone can log
    > wildlife sightings. The data here was exported as a CSV and loaded with **pandas**.
    """
)

# ── Research question ─────────────────────────────────────────────────────────
st.info(
    "**Research Question:** Does the spatial and seasonal distribution of the invasive "
    "Brown Widow Spider (*Latrodectus geometricus*) correlate with a displacement of the "
    "native Western Black Widow (*Latrodectus hesperus*) in San Diego County?"
)

# ── Spider photos ─────────────────────────────────────────────────────────────
img_col1, img_col2 = st.columns(2)
with img_col1:
    st.image("images/brown_widow.png", caption="🔴 Brown Widow — Latrodectus geometricus (Invasive)", use_container_width=True)
with img_col2:
    st.image("images/western_black_widow.png", caption="🔵 Western Black Widow — Latrodectus hesperus (Native)", use_container_width=True)

st.divider()

# ── Key stats ─────────────────────────────────────────────────────────────────
counts = df["scientific_name"].value_counts()
invasive_count = counts.get(INVASIVE, 0)
native_count   = counts.get(NATIVE, 0)
total          = invasive_count + native_count
year_range     = f"{df['observed_on'].dt.year.min()} – {df['observed_on'].dt.year.max()}"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Observations", f"{total:,}")
col2.metric("🔴 Brown Widow (invasive)", f"{invasive_count:,}")
col3.metric("🔵 Western Black Widow (native)", f"{native_count:,}")
col4.metric("Years of Data", year_range)

st.divider()

# ── Map ───────────────────────────────────────────────────────────────────────
st.subheader("Geographic Distribution")
st.markdown(
    "Each pin is a recorded sighting. **Red = invasive Brown Widow**, **Blue = native Western Black Widow**."
)

map_center = [df["latitude"].mean(), df["longitude"].mean()]
mymap = folium.Map(
    location=map_center,
    zoom_start=10,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
)

for _, row in df.iterrows():
    species = row["scientific_name"]
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=4,
        color=SPECIES_COLORS[species],
        fill=True,
        fill_opacity=0.7,
        popup=f"{SPECIES_LABELS[species]}<br>{row['observed_on'].date()}",
        tooltip=SPECIES_LABELS[species],
    ).add_to(mymap)

st_folium(mymap, use_container_width=True, height=500, returned_objects=[])

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
st.subheader("Observation Trends")

# Prepare data
species_by_year = (
    df.groupby([df["observed_on"].dt.year, "scientific_name"])
    .size()
    .unstack(fill_value=0)
    .sort_index()
)
species_by_year.index = species_by_year.index.astype(int)

species_by_month = (
    df.groupby([df["observed_on"].dt.month, "scientific_name"])
    .size()
    .unstack(fill_value=0)
    .reindex(range(1, 13), fill_value=0)
)
month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

chart_colors = {INVASIVE: "#e05c5c", NATIVE: "#5c8de0"}

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("**Observations by Year**")
    fig, ax = plt.subplots(figsize=(7, 4))
    bottom = None
    for species in [NATIVE, INVASIVE]:
        if species in species_by_year.columns:
            values = species_by_year[species]
            ax.bar(
                species_by_year.index,
                values,
                bottom=bottom,
                label=SPECIES_LABELS[species],
                color=chart_colors[species],
                alpha=0.85,
            )
            bottom = values if bottom is None else bottom + values
    ax.set_xlabel("Year")
    ax.set_ylabel("Observations")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

with col_right:
    st.markdown("**Observations by Month (all years combined)**")
    fig, ax = plt.subplots(figsize=(7, 4))
    bottom = None
    for species in [NATIVE, INVASIVE]:
        if species in species_by_month.columns:
            values = species_by_month[species]
            ax.bar(
                range(1, 13),
                values,
                bottom=bottom,
                label=SPECIES_LABELS[species],
                color=chart_colors[species],
                alpha=0.85,
            )
            bottom = values if bottom is None else bottom + values
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_labels)
    ax.set_xlabel("Month")
    ax.set_ylabel("Observations")
    ax.legend(fontsize=8)
    plt.tight_layout()
    st.pyplot(fig)

st.divider()

# ── Conclusion ────────────────────────────────────────────────────────────────
st.subheader("Conclusion")

invasive_pct = invasive_count / total * 100
native_pct   = native_count   / total * 100

st.markdown(
    f"""
    The iNaturalist data provides compelling evidence that the invasive Brown Widow
    (*Latrodectus geometricus*) has established a dominant presence in San Diego County.
    Of the **{total:,}** combined observations, the Brown Widow accounts for
    **{invasive_pct:.0f}%** ({invasive_count:,} sightings) compared to only **{native_pct:.0f}%**
    ({native_count:,} sightings) for the native Western Black Widow (*Latrodectus hesperus*).
    The year-over-year chart shows a sharp rise in Brown Widow reports beginning around 2018,
    while Western Black Widow observations have remained relatively flat — a pattern consistent
    with competitive displacement, where an invasive species outcompetes a native one for
    overlapping habitat and resources.

    Spatially, both species appear across the same general region of San Diego County, suggesting
    they share territory rather than occupying completely separate zones. Seasonally, both peak
    in the warmer summer and fall months, which aligns with spider activity cycles and increased
    human outdoor activity driving more iNaturalist submissions. While this dataset alone cannot
    prove causation, the temporal and spatial overlap — combined with the growing dominance of
    the Brown Widow — is consistent with the hypothesis that *L. geometricus* is displacing
    *L. hesperus* in this region. Further controlled field studies would be needed to confirm a
    direct competitive relationship.
    """
)
