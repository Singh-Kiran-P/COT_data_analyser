import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re
import numpy as np
from io import StringIO
import requests

st.set_page_config(layout="wide", page_title="COT Analysis Dashboard")

# Custom CSS
st.markdown(
    """
<style>
    .title {
        font-size: 42px;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 20px;
    }
    .subtitle {
        font-size: 26px;
        font-weight: bold;
        color: #3B82F6;
        margin-top: 30px;
        margin-bottom: 10px;
    }
    .metal-selector {
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .chart-section {
        margin-top: 30px;
        margin-bottom: 40px;
    }
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .highlight {
        color: #2563EB;
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='title'>Commitments of Traders (COT) Analysis Dashboard</div>",
    unsafe_allow_html=True,
)
st.markdown("Analyze Commitments of Traders data for precious metals futures markets")


# Function to parse COT data from text
def parse_cot_data(text):
    # Split by sections (each metal)
    sections = re.split(r"(?=Disaggregated Commitments of Traders)", text)

    results = []

    for section in sections:
        if not section.strip():
            continue
        # Extract the date
        date_match = re.search(r"as of (\w+\s+\d{1,2},\s+\d{4})", section)
        # Extract metal name, exchange, and CFTC code
        metal_match = re.search(
            r"([A-Z\s]+) - ([^(]+).*?CFTC Code #(\d+)", section, re.DOTALL
        )
        if not metal_match:
            continue

        metal_full_name = metal_match.group(1).strip()
        # For MICRO GOLD, handle the "MICRO" prefix
        metal = (
            "MICRO " + metal_full_name.split(" ")[-1]
            if "MICRO" in metal_full_name
            else metal_full_name
        )
        exchange = metal_match.group(2).strip()
        cftc_code = metal_match.group(3)

        # Extract open interest
        open_interest_match = re.search(r"Open Interest is\s+([0-9,]+)", section)
        open_interest = (
            int(open_interest_match.group(1).replace(",", ""))
            if open_interest_match
            else None
        )

        # Extract positions data
        positions_match = re.search(
            r": Positions\s+:\s*\n\s*:\s*([0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+)",
            section,
            re.DOTALL,
        )
        positions = None
        if positions_match:
            positions = [
                int(num.replace(",", ""))
                for num in positions_match.group(1).strip().split()
            ]

        # Extract changes data
        changes_match = re.search(
            r": Changes from:.+?\n\s*:\s*(-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+\s+-?[0-9,]+)",
            section,
            re.DOTALL,
        )
        changes = None
        if changes_match:
            changes = [
                int(num.replace(",", ""))
                for num in changes_match.group(1).strip().split()
            ]

        # Extract percentages data
        percents_match = re.search(
            r": Percent of Open Interest.+?\n\s*:\s*([0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+[0-9.]+)",
            section,
            re.DOTALL,
        )
        percents = None
        if percents_match:
            percents = [float(num) for num in percents_match.group(1).strip().split()]

        # Extract traders count data
        traders_match = re.search(
            r": Number of Traders.+?Total Traders:\s+(\d+).+?\n\s*:\s*([0-9.\s]+)",
            section,
            re.DOTALL,
        )
        total_traders = None
        traders_by_category = None
        if traders_match:
            total_traders = int(traders_match.group(1))
            traders_by_category = []
            for num in traders_match.group(2).strip().split():
                if num == ".":
                    traders_by_category.append(None)
                else:
                    traders_by_category.append(int(num))

        # Category labels
        category_labels = [
            "Producer/Merchant Long",
            "Producer/Merchant Short",
            "Swap Dealers Long",
            "Swap Dealers Short",
            "Swap Dealers Spreading",
            "Managed Money Long",
            "Managed Money Short",
            "Managed Money Spreading",
            "Other Reportables Long",
            "Other Reportables Short",
            "Other Reportables Spreading",
        ]

        structured_data = {
            "metal": metal,
            "exchange": exchange,
            "cftc_code": cftc_code,
            "open_interest": open_interest,
            "date": date_match.group(1) if date_match else None,
        }

        if positions:
            for i, label in enumerate(category_labels):
                structured_data[label] = positions[i]

        if changes:
            for i, label in enumerate(category_labels):
                structured_data[f"{label} Change"] = changes[i]

        if percents:
            for i, label in enumerate(category_labels):
                structured_data[f"{label} %"] = percents[i]

        if traders_by_category:
            for i, label in enumerate(category_labels):
                structured_data[f"{label} Traders"] = (
                    traders_by_category[i] if i < len(traders_by_category) else None
                )

        structured_data["total_traders"] = total_traders

        # Calculate net positions
        if positions:
            structured_data["Producer/Merchant Net"] = (
                structured_data["Producer/Merchant Long"]
                - structured_data["Producer/Merchant Short"]
            )
            structured_data["Swap Dealers Net"] = (
                structured_data["Swap Dealers Long"]
                + structured_data["Swap Dealers Spreading"]
            ) - structured_data["Swap Dealers Short"]
            structured_data["Managed Money Net"] = (
                structured_data["Managed Money Long"]
                + structured_data["Managed Money Spreading"]
            ) - structured_data["Managed Money Short"]
            structured_data["Other Reportables Net"] = (
                structured_data["Other Reportables Long"]
                + structured_data["Other Reportables Spreading"]
            ) - structured_data["Other Reportables Short"]

        # Calculate net changes
        if changes:
            structured_data["Producer/Merchant Net Change"] = (
                structured_data["Producer/Merchant Long Change"]
                - structured_data["Producer/Merchant Short Change"]
            )
            structured_data["Swap Dealers Net Change"] = (
                structured_data["Swap Dealers Long Change"]
                + structured_data["Swap Dealers Spreading Change"]
            ) - structured_data["Swap Dealers Short Change"]
            structured_data["Managed Money Net Change"] = (
                structured_data["Managed Money Long Change"]
                + structured_data["Managed Money Spreading Change"]
            ) - structured_data["Managed Money Short Change"]
            structured_data["Other Reportables Net Change"] = (
                structured_data["Other Reportables Long Change"]
                + structured_data["Other Reportables Spreading Change"]
            ) - structured_data["Other Reportables Short Change"]

        results.append(structured_data)

    return results


def download_data():
    url = "https://www.cftc.gov/dea/futures/"

    data_ = ["ag_sf", "petroleum_sf", "nat_gas_sf", "electricity_sf", "other_sf"]
    data_txt = ""
    for metal in data_:
        response = requests.get(url + metal + ".htm")
        if response.status_code == 200:
            data_txt += response.text
            st.toast(f"Downloaded {metal}.txt")
        else:
            st.toast(f"Failed to download {metal}.txt")
    return data_txt


# Initialize session state if not already set
if "text_data" not in st.session_state:
    st.session_state.text_data = None

if st.button("Download COT Data"):
    st.session_state.text_data = download_data()

# Access the stored data later like this:
text_data = st.session_state.text_data


def show_price_analysis(selected_metal):
    filtered_df = df[df["metal"] == selected_metal].copy()

    st.markdown(
        f"<div class='subtitle'>Summary for {selected_metal}</div>",
        unsafe_allow_html=True,
    )

    # Display key metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Open Interest", f"{filtered_df['open_interest'].values[0]:,}")
    col2.metric("Total Traders", f"{filtered_df['total_traders'].values[0]:,}")
    col3.metric("Date", filtered_df["date"].values[0])

    # Show the raw DataFrame
    with st.expander("Show Raw Data Table"):
        st.dataframe(filtered_df.T)

    # Net Position Chart
    st.markdown(f"<div class='subtitle'>Net Positions</div>", unsafe_allow_html=True)
    net_positions = {
        "Producer/Merchant": filtered_df["Producer/Merchant Net"].values[0],
        "Swap Dealers": filtered_df["Swap Dealers Net"].values[0],
        "Managed Money": filtered_df["Managed Money Net"].values[0],
        "Other Reportables": filtered_df["Other Reportables Net"].values[0],
    }

    net_fig = px.bar(
        x=list(net_positions.keys()),
        y=list(net_positions.values()),
        labels={"x": "Trader Category", "y": "Net Position"},
        title="Net Positions by Trader Category",
        color=list(net_positions.values()),
        color_continuous_scale="Blues",
    )
    st.plotly_chart(net_fig, use_container_width=True)

    # Net Changes
    st.markdown(
        f"<div class='subtitle'>Net Position Changes (Week-over-Week)</div>",
        unsafe_allow_html=True,
    )
    net_changes = {
        "Producer/Merchant": filtered_df["Producer/Merchant Net Change"].values[0],
        "Swap Dealers": filtered_df["Swap Dealers Net Change"].values[0],
        "Managed Money": filtered_df["Managed Money Net Change"].values[0],
        "Other Reportables": filtered_df["Other Reportables Net Change"].values[0],
    }

    change_fig = px.bar(
        x=list(net_changes.keys()),
        y=list(net_changes.values()),
        labels={"x": "Trader Category", "y": "Net Change"},
        title="Weekly Change in Net Positions",
        color=list(net_changes.values()),
        color_continuous_scale="RdBu",
    )
    st.plotly_chart(change_fig, use_container_width=True)

    # Percent of Open Interest
    st.markdown(
        f"<div class='subtitle'>Percent of Open Interest by Category</div>",
        unsafe_allow_html=True,
    )
    percent_cols = [col for col in filtered_df.columns if "%" in col]
    percent_data = filtered_df[percent_cols].T.reset_index()
    percent_data.columns = ["Category", "Percent"]
    percent_data["Category"] = percent_data["Category"].str.replace(
        " %", "", regex=False
    )

    percent_fig = px.bar(
        percent_data,
        x="Category",
        y="Percent",
        title="Percent of Open Interest by Trader Category",
        color="Percent",
        color_continuous_scale="Purples",
    )
    percent_fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(percent_fig, use_container_width=True)


if text_data is not None:
    parsed_data = parse_cot_data(text_data)
    df = pd.DataFrame(parsed_data)

    if df.empty:
        st.warning("No valid data found in the uploaded file.")
    else:
        metals = df["metal"].unique()

        # Create two columns
        col1, col2 = st.columns(2)

        with col1:
            selected_metal1 = st.selectbox("Select Metal1", metals, index=1)
            st.subheader("Price Analysis")
            show_price_analysis(selected_metal1)  # a part of your `show_analysis`

        with col2:
            selected_metal2 = st.selectbox(
                "Select Metal2",
                metals,
            )
            st.subheader("Price Analysis")
            show_price_analysis(selected_metal2)  # another part of your `show_analysis`
