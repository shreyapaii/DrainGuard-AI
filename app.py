"""DrainGuard AI by PrimeOps: Streamlit web application."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

from drainguard import analytics, public_data, ui, vision
from drainguard.db import (
    STATUSES,
    add_inspection,
    add_model_inference,
    connect,
    infrastructure_counts,
    list_data_sources,
    list_infrastructure_records,
    list_inspections,
    list_model_inferences,
    update_status,
    upsert_data_source,
)
from drainguard.scoring import OBSTRUCTION_POINTS, RAINFALL_POINTS, WATER_POINTS, assess_priority

DB_PATH = "data/drainguard.db"
NOT_RECORDED = "Not recorded"
PAGES = [
    "Operations overview",
    "Public infrastructure",
    "New inspection",
    "Maintenance queue",
    "Data sources",
]

st.set_page_config(page_title="DrainGuard AI by PrimeOps", layout="wide")
ui.inject_css()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def register_reference_sources(conn) -> None:
    """Store verified reference-source notes without importing operational records."""
    upsert_data_source(
        conn,
        source_name=public_data.TACO_SOURCE_NAME,
        source_url=public_data.TACO_ZENODO_URL,
        source_description=(
            "Real litter annotation dataset investigated for future model work. "
            "It is not used by the current runtime detector."
        ),
        retrieved_at=public_data.TACO_VERIFIED["retrieved_at"],
        status="verified_reference",
        metadata=public_data.TACO_VERIFIED,
    )
    upsert_data_source(
        conn,
        source_name=public_data.DATA_GOV_SOURCE_NAME,
        source_url=public_data.DATA_GOV_URL,
        source_description="Official Indian open-data portal investigated for relevant datasets.",
        retrieved_at=public_data.DATA_GOV_INVESTIGATION["retrieved_at"],
        status="investigated_not_imported",
        metadata=public_data.DATA_GOV_INVESTIGATION,
    )


@st.cache_resource
def get_connection():
    conn = connect(DB_PATH)
    register_reference_sources(conn)
    return conn


@st.cache_resource
def get_detector():
    return vision.load_detector()


def opt(value):
    """Convert the UI placeholder back into a true missing value."""
    return None if value == NOT_RECORDED else value


def load_inspection_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if not df.empty:
        df["source"] = df["source_name"].fillna("User entry")
    return df


def image_analysis_section() -> dict | None:
    """Upload an image and run real detection. Returns metadata to save, or None."""
    ui.section("1 · AI image analysis (optional)")
    available, message = vision.detector_status()
    if available:
        st.caption(message)
    else:
        ui.banner(message, warn=True)

    uploaded = st.file_uploader(
        "Drain or street-litter photo (JPG or PNG)",
        type=["jpg", "jpeg", "png"],
        key="upload",
    )
    if uploaded is None:
        st.session_state.pop("analysis", None)
        return None

    image = Image.open(uploaded).convert("RGB")
    image_key = f"{uploaded.name}-{uploaded.size}"

    if st.button("Run AI detection", type="primary", disabled=not available):
        try:
            with st.spinner("Loading detector and analysing the image on CPU..."):
                bundle = get_detector()
                detections = vision.run_detector(bundle, image)
            st.session_state["analysis"] = {
                "key": image_key,
                "detections": detections,
                "detections_json": vision.detections_to_records(detections),
                "summary": vision.summarize(detections),
                "annotated": vision.render_annotated(image, detections),
                "inference_date": utc_now(),
                "model_name": vision.MODEL_NAME,
                "model_version": vision.MODEL_VERSION,
                "dataset_name": vision.MODEL_DATASET_NAME,
                "source_name": vision.MODEL_SOURCE_NAME,
                "source_url": vision.MODEL_SOURCE_URL,
                "threshold": vision.SCORE_THRESHOLD,
            }
        except Exception as err:  # surface model or download problems to the user
            st.error(f"Detection failed: {err}")

    analysis = st.session_state.get("analysis")
    if analysis and analysis["key"] == image_key:
        c1, c2 = st.columns(2)
        c1.image(image, caption="Uploaded image", width="stretch")
        c2.image(analysis["annotated"], caption="Model detections", width="stretch")
        if analysis["detections"]:
            st.dataframe(
                pd.DataFrame([
                    {"Detected class": d.label, "Confidence": round(d.score, 3)}
                    for d in analysis["detections"]
                ]),
                hide_index=True,
                width="stretch",
            )
        st.info(analysis["summary"])
        st.caption(
            f"{vision.LIMITATION_TEXT} Inference timestamp: {analysis['inference_date']}."
        )
        return analysis

    st.image(image, caption="Uploaded image", width="stretch")
    return None


def render_inspection_metrics(records: list[dict]) -> None:
    m = analytics.overview_metrics(records)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("Registered drains", m["registered_drains"], "User inspection drain IDs", icon="drop")
    with c2:
        ui.metric_card("Inspections recorded", m["inspections_recorded"], "User-entered records", icon="clipboard")
    with c3:
        ui.metric_card("Open maintenance tasks", m["open_tasks"], "From inspection records only", icon="list")
    with c4:
        ui.metric_card("High-priority findings", m["high_findings"], "Based on field observations", icon="alert")


def render_overview(conn) -> None:
    ui.page_header(
        "Operations overview",
        "Operational metrics are calculated only from genuine user-entered inspection records.",
    )
    records = list_inspections(conn)
    render_inspection_metrics(records)
    ui.banner(
        "Public infrastructure imports and AI model detections are stored separately. "
        "They do not create inspections, maintenance tasks, blockage claims, or priority findings."
    )

    if not records:
        ui.empty_state(
            "No inspection records yet",
            "Conduct the first verified inspection or register a drain from confirmed field evidence.",
        )
        return

    ui.section("Recent inspections")
    left, right = st.columns([3, 2])
    with left:
        feed_html = "".join(
            ui.feed_item(
                title=f"{r['drain_id']}  ·  {r['area_description'] or 'No area description'}",
                meta=(
                    f"{r['inspection_date']}  ·  {r['status']}  ·  "
                    f"score {r['priority_score']}  ·  {r['source_name']}"
                ),
                badge_html=ui.priority_badge(r["priority"]),
            )
            for r in analytics.recent_records(records)
        )
        st.markdown(f'<div class="dg-card dg-feed-card">{feed_html}</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="dg-chart-title">Severity distribution</div>',
                    unsafe_allow_html=True)
        sev = analytics.severity_counts(records)
        fig = px.bar(
            x=list(sev.keys()), y=list(sev.values()), text=list(sev.values()),
            color=list(sev.keys()), color_discrete_map=ui.PRIORITY_COLORS,
            labels={"x": "Priority", "y": "Records"},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(ui.style_figure(fig, 300))

    ui.section("Maintenance and activity")
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="dg-chart-title">Maintenance status</div>',
                    unsafe_allow_html=True)
        status = analytics.status_breakdown(records)
        fig = px.bar(x=list(status.keys()), y=list(status.values()), text=list(status.values()),
                     labels={"x": "Status", "y": "Records"})
        fig.update_traces(marker_color=ui.EMERALD, textposition="outside", cliponaxis=False)
        st.plotly_chart(ui.style_figure(fig, 280))
    with right:
        st.markdown('<div class="dg-chart-title">Inspection activity over time</div>',
                    unsafe_allow_html=True)
        activity = analytics.activity_by_date(records)
        if len(activity) >= 2:
            fig = px.line(x=list(activity.keys()), y=list(activity.values()), markers=True,
                          labels={"x": "Inspection date", "y": "Records"})
            fig.update_traces(line_color=ui.EMERALD)
            st.plotly_chart(ui.style_figure(fig, 280))
        else:
            ui.empty_state(
                "Not enough dates yet",
                "An activity trend appears once records exist on at least two different dates.",
            )

    points = analytics.geo_points(records)
    ui.section("Inspection locations")
    if points:
        geo = pd.DataFrame(points).rename(columns={"lat": "latitude", "lon": "longitude"})
        st.map(geo, latitude="latitude", longitude="longitude", size=60)
        st.caption(f"{len(points)} user inspection record(s) with coordinates.")
    else:
        ui.empty_state(
            "No located inspection records",
            "Add latitude and longitude on the inspection form to plot inspections here. "
            "Coordinates are never guessed.",
        )

    with st.expander("Full inspection history"):
        st.dataframe(
            load_inspection_frame(records)[["id", "drain_id", "area_description", "inspection_date",
                                            "priority", "priority_score", "status", "source"]],
            width="stretch",
            hide_index=True,
        )


def _valid_lon_lat(lon: float, lat: float) -> bool:
    return -180 <= lon <= 180 and -90 <= lat <= 90


def _map_data(records: list[dict]) -> tuple[list[dict], list[dict], list[tuple[float, float]]]:
    lines: list[dict] = []
    points: list[dict] = []
    coords: list[tuple[float, float]] = []
    for record in records:
        geometry = json.loads(record["geometry_json"]) if record.get("geometry_json") else None
        if geometry and geometry.get("paths"):
            for path in geometry["paths"]:
                clean_path = []
                for coord in path:
                    if len(coord) >= 2:
                        lon, lat = float(coord[0]), float(coord[1])
                        if _valid_lon_lat(lon, lat):
                            clean_path.append([lon, lat])
                            coords.append((lat, lon))
                if len(clean_path) >= 2:
                    lines.append({
                        "path": clean_path,
                        "label": record.get("label") or record["source_object_id"],
                        "record_type": record["record_type"],
                        "source_name": record["source_name"],
                    })
        elif record.get("latitude") is not None and record.get("longitude") is not None:
            lat, lon = float(record["latitude"]), float(record["longitude"])
            if _valid_lon_lat(lon, lat):
                points.append({
                    "latitude": lat,
                    "longitude": lon,
                    "label": record.get("label") or record["source_object_id"],
                    "record_type": record["record_type"],
                    "source_name": record["source_name"],
                })
                coords.append((lat, lon))
    return lines, points, coords


def render_infrastructure_map(records: list[dict]) -> None:
    lines, points, coords = _map_data(records)
    if not coords:
        ui.empty_state(
            "No valid geometries to map",
            "Imported records are shown on the map only when the source provides valid coordinates.",
        )
        return

    center_lat = sum(lat for lat, _ in coords) / len(coords)
    center_lon = sum(lon for _, lon in coords) / len(coords)

    try:
        import pydeck as pdk
    except ImportError:
        fallback = pd.DataFrame(
            [{"latitude": lat, "longitude": lon} for lat, lon in coords[:5000]]
        )
        st.map(fallback, latitude="latitude", longitude="longitude", size=30)
        st.caption("pydeck is unavailable, so valid source coordinates are shown as points.")
        return

    layers = []
    if lines:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=lines,
                get_path="path",
                get_color=[22, 132, 91, 210],
                width_min_pixels=2,
                pickable=True,
            )
        )
    if points:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=points,
                get_position="[longitude, latitude]",
                get_fill_color=[183, 121, 31, 190],
                radius_min_pixels=4,
                pickable=True,
            )
        )
    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=10),
        layers=layers,
        tooltip={"text": "{label}\n{record_type}\n{source_name}"},
    )
    st.pydeck_chart(deck, use_container_width=True)
    st.caption(
        f"Showing {len(lines)} drain path segment(s) and {len(points)} point feature(s) "
        "from source-provided geometries."
    )


def render_public_infrastructure(conn) -> None:
    ui.page_header(
        "Public infrastructure",
        "Imported public GIS records are reference infrastructure, not inspection findings.",
    )
    counts = infrastructure_counts(conn)
    drains = counts.get(public_data.RECORD_TYPE_STORM_DRAIN, 0)
    manholes = counts.get(public_data.RECORD_TYPE_STORM_MANHOLE, 0)
    c1, c2, c3 = st.columns(3)
    with c1:
        ui.metric_card("Public drain records", drains, "MCGM layer 7, not inspections", icon="drop")
    with c2:
        ui.metric_card("Public manhole records", manholes, "MCGM layer 6 reference points", icon="list")
    with c3:
        ui.metric_card("Operational tasks from import", 0, "Infrastructure imports never create tasks", icon="alert")

    ui.banner(
        "The MCGM/BMC source covers Mumbai stormwater infrastructure. It is not Belagavi data "
        "and does not imply blockage, inspection status, maintenance status, or flood risk."
    )

    ui.section("Import from MCGM ArcGIS REST")
    with st.form("mcgm_import"):
        col1, col2, col3 = st.columns(3)
        include_drains = col1.checkbox("Storm Water Drains, layer 7", value=True)
        include_manholes = col2.checkbox("Storm Water Manholes, layer 6", value=True)
        limit_per_layer = col3.number_input(
            "Maximum records per selected layer",
            min_value=1,
            max_value=8000,
            value=100,
            step=100,
        )
        submitted = st.form_submit_button("Import real public records", type="primary")

    if submitted:
        layer_ids = []
        if include_drains:
            layer_ids.append(public_data.MCGM_STORM_DRAINS_LAYER_ID)
        if include_manholes:
            layer_ids.append(public_data.MCGM_STORM_MANHOLES_LAYER_ID)
        if not layer_ids:
            st.error("Select at least one MCGM stormwater layer to import.")
        else:
            try:
                with st.spinner("Fetching real features from the MCGM ArcGIS REST service..."):
                    summary = public_data.import_mcgmgis_stormwater(
                        conn,
                        layer_ids=tuple(layer_ids),
                        limit_per_layer=int(limit_per_layer),
                    )
                st.success(
                    f"Import complete: {summary.inserted} new record(s), "
                    f"{summary.duplicates} duplicate(s) skipped."
                )
                st.json({
                    "source": summary.source_name,
                    "retrieved_at": summary.retrieved_at,
                    "requested_features": summary.requested,
                    "layers": summary.layers,
                }, expanded=False)
            except public_data.PublicDataUnavailable as err:
                upsert_data_source(
                    conn,
                    source_name=public_data.MCGM_SOURCE_NAME,
                    source_url=public_data.MCGM_MAPSERVER_URL,
                    source_description=public_data.MCGM_SOURCE_DESCRIPTION,
                    retrieved_at=utc_now(),
                    status="unavailable",
                    metadata={"error": str(err)},
                )
                st.error(
                    "MCGM source is currently unavailable from this environment. "
                    f"No fallback data was fabricated. Details: {err}"
                )

    ui.section("Imported records")
    f1, f2 = st.columns([2, 3])
    type_filter = f1.multiselect(
        "Record type",
        [public_data.RECORD_TYPE_STORM_DRAIN, public_data.RECORD_TYPE_STORM_MANHOLE],
        default=[public_data.RECORD_TYPE_STORM_DRAIN, public_data.RECORD_TYPE_STORM_MANHOLE],
    )
    search = f2.text_input("Search public object ID, node ID, or layer")
    records = list_infrastructure_records(
        conn,
        record_types=type_filter or None,
        search=search.strip() or None,
        limit=3000,
    )
    if not records:
        ui.empty_state(
            "No public infrastructure records imported",
            "Use the MCGM import above to fetch real records. If the source is unreachable, "
            "the app reports it instead of using fabricated fallback data.",
        )
        return

    render_infrastructure_map(records)
    frame = pd.DataFrame(records)
    st.dataframe(
        frame[["id", "record_type", "label", "source_layer_name", "source_object_id",
               "external_id", "latitude", "longitude", "import_date", "source_name"]],
        width="stretch",
        hide_index=True,
    )


def render_new_inspection(conn) -> None:
    ui.page_header(
        "New inspection",
        "Leave an observation as 'Not recorded' if it was not observed. It will not be guessed.",
    )
    ai_analysis = image_analysis_section()
    st.divider()
    ui.section("2 · Inspection details")

    with st.form("inspection_form"):
        drain_id = st.text_input("Drain identifier *", placeholder="e.g. verified drain ID or field label")
        area = st.text_input("Area description (optional)")
        col1, col2 = st.columns(2)
        obstruction = col1.selectbox("Visible obstruction", [NOT_RECORDED] + list(OBSTRUCTION_POINTS))
        water = col2.selectbox("Observed water level", [NOT_RECORDED] + list(WATER_POINTS))
        rainfall = col1.selectbox("Recent rainfall category", [NOT_RECORDED] + list(RAINFALL_POINTS))
        inspection_date = col2.date_input("Inspection date", value=date.today())
        lat_col, lon_col = st.columns(2)
        latitude = lat_col.number_input("Latitude (optional)", min_value=-90.0, max_value=90.0,
                                        value=None, format="%.6f", placeholder="Leave blank if unknown")
        longitude = lon_col.number_input("Longitude (optional)", min_value=-180.0, max_value=180.0,
                                         value=None, format="%.6f", placeholder="Leave blank if unknown")
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Save inspection", type="primary")

    if submitted:
        try:
            new_id = add_inspection(
                conn,
                drain_id=drain_id,
                inspection_date=str(inspection_date),
                area_description=area,
                latitude=latitude,
                longitude=longitude,
                obstruction=opt(obstruction),
                water_level=opt(water),
                rainfall=opt(rainfall),
                notes=notes,
                ai_summary=ai_analysis["summary"] if ai_analysis else None,
            )
            if ai_analysis:
                add_model_inference(
                    conn,
                    inspection_id=new_id,
                    model_name=ai_analysis["model_name"],
                    model_version=ai_analysis["model_version"],
                    dataset_name=ai_analysis["dataset_name"],
                    source_name=ai_analysis["source_name"],
                    source_url=ai_analysis["source_url"],
                    inference_date=ai_analysis["inference_date"],
                    threshold=ai_analysis["threshold"],
                    detections=ai_analysis["detections_json"],
                    summary=ai_analysis["summary"],
                )
            result = assess_priority(opt(obstruction), opt(water), opt(rainfall))
            st.success(
                f"Saved as inspection #{new_id}. Priority: {result.priority} "
                f"(score {result.score} of {result.max_score})."
            )
            ui.section("Why this priority")
            st.dataframe(
                pd.DataFrame([
                    {
                        "Factor": f.name,
                        "Observation": f.value or "Not recorded",
                        "Points": "-" if f.points is None else f"{f.points}/{f.max_points}",
                        "Explanation": f.explanation,
                    }
                    for f in result.factors
                ]),
                hide_index=True,
                width="stretch",
            )
            st.caption(result.evidence)
            if ai_analysis:
                st.caption(
                    "Model detections were saved as a separate inference record and were not used "
                    "to calculate the inspection priority."
                )
        except ValueError as err:
            st.error(str(err))


def render_queue(conn) -> None:
    ui.page_header(
        "Maintenance queue",
        "Filter, search, and update maintenance status for user-entered inspections.",
    )
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))

    f1, f2, f3 = st.columns([1, 1, 2])
    priority_filter = f1.multiselect("Priority", ["High", "Medium", "Low"],
                                     default=["High", "Medium", "Low"])
    status_filter = f2.multiselect("Status", list(STATUSES), default=list(STATUSES))
    search = f3.text_input("Search drain ID or area")

    records = list_inspections(
        conn,
        priorities=priority_filter or None,
        statuses=status_filter or None,
        search=search.strip() or None,
    )
    if not records:
        ui.empty_state(
            "No inspection records match these filters",
            "Create the first verified inspection to populate the maintenance queue.",
        )
        return

    frame = load_inspection_frame(records)
    st.dataframe(
        frame[["id", "drain_id", "area_description", "priority", "priority_score",
               "status", "inspection_date", "source", "record_type"]],
        width="stretch",
        hide_index=True,
    )

    export_cols = ["id", "drain_id", "area_description", "latitude", "longitude",
                   "inspection_date", "priority", "priority_score", "status",
                   "source", "record_type"]
    csv_bytes = frame[export_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Export filtered queue (CSV)",
        data=csv_bytes,
        file_name="drainguard_queue.csv",
        mime="text/csv",
    )

    ui.section("Update maintenance status")
    ids = [r["id"] for r in records]
    u1, u2, u3 = st.columns(3)
    chosen_id = u1.selectbox("Inspection ID", ids)
    current = next(r["status"] for r in records if r["id"] == chosen_id)
    new_status = u2.selectbox("New status", list(STATUSES), index=list(STATUSES).index(current))
    if u3.button("Update status", type="primary"):
        update_status(conn, chosen_id, new_status)
        st.session_state["flash"] = f"Inspection #{chosen_id} set to '{new_status}'."
        st.rerun()


def render_data_sources(conn) -> None:
    ui.page_header(
        "Data sources",
        "Traceability for imported infrastructure, reference datasets, and model output.",
    )
    sources = list_data_sources(conn)
    if sources:
        frame = pd.DataFrame(sources)
        st.dataframe(
            frame[["source_name", "status", "retrieved_at", "source_url", "source_description"]],
            width="stretch",
            hide_index=True,
        )
    else:
        ui.empty_state("No source metadata stored", "Source records appear after the app initializes.")

    ui.section("Verified MCGM stormwater layers")
    st.markdown(
        f"""
- Source: [{public_data.MCGM_SOURCE_NAME}]({public_data.MCGM_MAPSERVER_URL})
- Verified retrieval date: 2026-10-09
- Stormwater group layer: `{public_data.MCGM_STORM_GROUP_ID}` / `Storm Water Drainage`
- Drain sublayer: `{public_data.MCGM_STORM_DRAINS_LAYER_ID}` / `Storm Water Drains`, geometry `esriGeometryPolyline`
- Related manhole sublayer: `{public_data.MCGM_STORM_MANHOLES_LAYER_ID}` / `Storm Water Manholes`, geometry `esriGeometryPoint`
- Coverage observed from service extent: Mumbai-area coordinates, source spatial reference EPSG:32643; queried features are requested as WGS84 (`outSR=4326`)
- Copyright text reported by service: `MCGM, Esri India`
        """
    )

    ui.section("TACO dataset investigation")
    taco_rows = [{"Field": key, "Verified value": value} for key, value in public_data.TACO_VERIFIED.items()]
    st.dataframe(pd.DataFrame(taco_rows), width="stretch", hide_index=True)
    st.caption(
        "TACO is a real litter dataset, but the current runtime detector remains a COCO-pretrained "
        "general object detector. Litter detection is not treated as proof of drain blockage."
    )

    ui.section("data.gov.in investigation")
    data_gov_rows = [
        {"Field": key, "Verified value": value}
        for key, value in public_data.DATA_GOV_INVESTIGATION.items()
    ]
    st.dataframe(pd.DataFrame(data_gov_rows), width="stretch", hide_index=True)

    ui.section("Saved model inferences")
    inferences = list_model_inferences(conn)
    if inferences:
        frame = pd.DataFrame(inferences)
        st.dataframe(
            frame[["inspection_id", "model_name", "dataset_name", "inference_date",
                   "threshold", "summary", "source_name"]],
            width="stretch",
            hide_index=True,
        )
    else:
        ui.empty_state(
            "No saved model inferences",
            "Model output appears here only after a user uploads an image and runs detection.",
        )


conn = get_connection()
ui.sidebar_brand()
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption(
    "Operational metrics use user-entered inspections only. Public imports and AI detections are separate."
)

if page == "Operations overview":
    render_overview(conn)
elif page == "Public infrastructure":
    render_public_infrastructure(conn)
elif page == "New inspection":
    render_new_inspection(conn)
elif page == "Maintenance queue":
    render_queue(conn)
else:
    render_data_sources(conn)
