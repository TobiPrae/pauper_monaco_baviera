import json
from typing import Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from auth import require_auth
from datastore_client import get_client
from prediction import PredictionConfig
from prediction.explainability_engine import FEATURE_LABELS
from prediction.explanation import build_playoff_overview
from prediction.report import PredictionService
from prediction.scenario_explorer import build_scenario_cards, build_scenario_report
from prediction.what_if import RESULT_TO_CODE, recalculate_with_overrides

st.set_page_config(page_title="League Predictor", layout="wide")

require_auth()
client = get_client()

selected_league = st.session_state.get("current_league")
if not selected_league:
    st.info("No leagues found. Please create a league in League Management.")
    st.stop()

st.title("League Predictor")
st.caption("Deterministic, modular season projection engine")
st.markdown(
    """
    <style>
      .scenario-card {
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 8px;
        color: #111827;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
      }
      .scenario-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 4px;
      }
      .scenario-prob {
        font-size: 1.6rem;
        font-weight: 800;
        margin: 2px 0 6px 0;
      }
      .scenario-chip {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        background: rgba(17, 24, 39, 0.12);
      }
      .badge-pill {
        display: inline-block;
        margin: 2px 6px 2px 0;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        background: #eef2ff;
        color: #1f2937;
      }
      div[data-testid="stButton"] > button[kind="primary"] {
        background: #16a34a;
        border-color: #16a34a;
        color: #ffffff;
        box-shadow: 0 0 0.55rem rgba(22, 163, 74, 0.45);
      }
      div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: #15803d;
        border-color: #15803d;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

SIM_OPTIONS = [1_000, 5_000, 10_000, 25_000, 50_000, 100_000]

with st.expander("Prediction Settings", expanded=False):
    simulations = st.selectbox("Monte Carlo simulations", options=SIM_OPTIONS, index=4)
    playoff_cut = st.number_input("Playoff cutoff (Top N)", min_value=1, max_value=16, value=4, step=1)
    seed = st.number_input("Random seed", min_value=1, max_value=999999, value=42, step=1)
    st.caption("Feature weights (JSON)")
    default_weights = PredictionConfig().feature_weights
    weights_text = st.text_area("Weights", value=json.dumps(default_weights, indent=2), height=220)

try:
    parsed_weights = json.loads(weights_text)
except json.JSONDecodeError:
    st.error("Invalid weights JSON.")
    st.stop()


@st.cache_data(show_spinner=True)
def build_prediction_report(
    league_id: str,
    simulation_count: int,
    playoff_cutoff: int,
    random_seed: int,
    weights_json: str,
    report_schema_version: int,
):
    leagues = client.list_leagues()
    league = next((l for l in leagues if l.id == league_id), None)
    if league is None:
        return None
    cfg = PredictionConfig(
        simulations=simulation_count,
        random_seed=random_seed,
        playoff_cut=playoff_cutoff,
        feature_weights=json.loads(weights_json),
    )
    service = PredictionService(cfg)
    return service.build_report(client, league)


REPORT_SCHEMA_VERSION = 3
report = build_prediction_report(
    selected_league.id,
    simulations,
    int(playoff_cut),
    int(seed),
    json.dumps(parsed_weights, sort_keys=True),
    REPORT_SCHEMA_VERSION,
)
if report is None:
    st.error("Could not build prediction report for selected league.")
    st.stop()

top = report.player_predictions[0] if report.player_predictions else None
playoff_race_players = sum(1 for p in report.player_predictions if 0.2 <= p.playoff_probability <= 0.8)
overview = build_playoff_overview(report.player_predictions, report.league_summary.playoff_cut)
likely_playoff = [entry["player_name"] for entry in overview if entry["status"] == "Very Likely"][: report.league_summary.playoff_cut]
col1, col2, col3, col4 = st.columns(4)
col1.metric("League", report.league_name)
col2.metric("Simulations", f"{report.simulation_metadata.simulations:,}")
col3.metric("Title Favorite", top.player_name if top else "N/A")
col4.metric("Bubble Teams", playoff_race_players)


def _feature_label(name: str) -> str:
    return FEATURE_LABELS.get(name, name.replace("_", " ").title())


def _pp(value: float) -> str:
    return f"{value * 100:+.1f}%"


def _scenario_style(scenario_type: str) -> tuple[str, str]:
    if scenario_type == "most_likely":
        return ("linear-gradient(135deg, #dbeafe, #bfdbfe)", "#1d4ed8")
    if scenario_type == "bubble_race":
        return ("linear-gradient(135deg, #fef3c7, #fde68a)", "#b45309")
    return ("linear-gradient(135deg, #fee2e2, #fecaca)", "#b91c1c")

scenario_reports = getattr(report, "scenario_reports", [])
if not scenario_reports and report.internal_artifacts is not None:
    scenario_reports = build_scenario_report(
        artifacts=report.internal_artifacts,
        player_predictions=report.player_predictions,
        match_probabilities=report.match_probabilities,
        critical_matches=report.critical_matches,
        playoff_cut=report.league_summary.playoff_cut,
    )
scenario_cards = build_scenario_cards(scenario_reports)

dashboard_df = pd.DataFrame(
    [
        {
            "Player": p.player_name,
            "Playoff Probability": p.playoff_probability,
            "Champion Probability": p.champion_probability,
            "Expected Finish": p.expected_finish,
        }
        for p in report.player_predictions
    ]
)
overview_df = pd.DataFrame(
    [{"Player": entry["player_name"], "Trend": entry["status"], "Reason": entry["reason"]} for entry in overview]
)
expected_df = pd.DataFrame(
    [
        {
            "Player": p.player_name,
            "Expected Finish": p.expected_finish,
            "Most Likely": p.most_likely_finish,
            "Best": p.best_possible_finish,
            "Worst": p.worst_possible_finish,
        }
        for p in report.player_predictions
    ]
).sort_values("Expected Finish")
schedule_df = pd.DataFrame(
    [{"Round": m.round_nr, "Match": f"{m.player_a_name} vs {m.player_b_name}", "A Deck": m.player_a_deck, "B Deck": m.player_b_deck} for m in report.remaining_schedule]
)
critical_df = pd.DataFrame(
    [{"Round": m.round_nr, "Match": m.match_label, "Leverage": m.leverage_score, "Reason": m.reason} for m in report.critical_matches]
)
insight_df = pd.DataFrame(
    [
        {"Insight": "Most Influential Feature", "Value": report.league_insights.get("most_influential_feature", "N/A")},
        {"Insight": "Most Important Remaining Match", "Value": report.league_insights.get("most_important_remaining_match", "N/A")},
        {"Insight": "Largest Schedule Advantage", "Value": report.league_insights.get("largest_schedule_advantage", "N/A")},
        {"Insight": "Largest Deck Advantage", "Value": report.league_insights.get("largest_deck_advantage", "N/A")},
        {"Insight": "Most Balanced Matchup", "Value": report.league_insights.get("most_balanced_matchup", "N/A")},
        {"Insight": "Strongest Positive Driver", "Value": report.league_insights.get("strongest_positive_driver", "N/A")},
        {"Insight": "Strongest Negative Driver", "Value": report.league_insights.get("strongest_negative_driver", "N/A")},
    ]
)

overview_tab, explainability_tab, advanced_tab = st.tabs(["Overview", "Explainability", "Advanced"])

with overview_tab:
    st.subheader("Playoff Dashboard")
    dash_col1, dash_col2 = st.columns(2)
    with dash_col1:
        top_playoff_df = dashboard_df.sort_values("Playoff Probability", ascending=False).head(max(report.league_summary.playoff_cut + 2, 5))
        st.plotly_chart(
            px.bar(top_playoff_df, x="Player", y="Playoff Probability", title="Top Playoff Chances", color="Playoff Probability"),
            use_container_width=True,
        )
    with dash_col2:
        st.plotly_chart(
            px.scatter(
                dashboard_df,
                x="Playoff Probability",
                y="Champion Probability",
                color="Player",
                size="Expected Finish",
                title="Playoff vs Champion Probability",
            ),
            use_container_width=True,
        )
    st.subheader("Scenario Explorer")
    if not scenario_cards:
        st.info("No scenario data available.")
    else:
        selected_scenario_type = st.session_state.get("selected_scenario_type", "")
        available_types = {scenario.scenario_type for scenario in scenario_reports}
        if selected_scenario_type not in available_types and scenario_reports:
            selected_scenario_type = scenario_reports[0].scenario_type
            st.session_state["selected_scenario_type"] = selected_scenario_type
        card_columns = st.columns(3)
        for idx, card in enumerate(scenario_cards):
            card_bg, accent = _scenario_style(card["scenario_type"])
            with card_columns[idx % 3]:
                is_selected = card["scenario_type"] == selected_scenario_type
                st.markdown(
                    f"""
                    <div class="scenario-card" style="background:{card_bg}; border-left:6px solid {accent};">
                      <div class="scenario-title">{card['scenario_name']}</div>
                      <div class="scenario-prob">{card['scenario_probability']:.1%}</div>
                      <div>{card['short_description']}</div>
                      <div style="margin-top:8px;"><span class="scenario-chip">Confidence {card['confidence']:.0%}</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    "View Details",
                    key=f"view_scenario_{card['scenario_type']}",
                    type=("primary" if is_selected else "secondary"),
                ):
                    st.session_state["selected_scenario_type"] = card["scenario_type"]
                    selected_scenario_type = card["scenario_type"]
                    st.rerun()

        selected_scenario = next(
            (scenario for scenario in scenario_reports if scenario.scenario_type == selected_scenario_type),
            scenario_reports[0],
        )
        with st.container(border=True):
            st.markdown(f"### {selected_scenario.scenario_name} Details")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Scenario Probability", f"{selected_scenario.scenario_probability:.1%}")
            kpi2.metric("Confidence", f"{selected_scenario.confidence:.0%}")
            kpi3.metric("Champion", selected_scenario.champion)
            kpi4.metric("Playoff Teams", len(selected_scenario.playoff_teams))
            st.markdown(f"**Critical Match:** 🔥 {selected_scenario.critical_match}")
            st.markdown(f"**Summary:** {selected_scenario.summary}")

            st.markdown("**Final Standings**")
            standings_df = pd.DataFrame(selected_scenario.final_standings)
            st.dataframe(standings_df, use_container_width=True, hide_index=True)
            if not standings_df.empty:
                standings_chart = standings_df.copy()
                standings_chart["PlayoffColor"] = standings_chart["Playoff"].apply(lambda value: "Playoff" if value else "Non-Playoff")
                st.plotly_chart(
                    px.bar(
                        standings_chart.sort_values("Rank", ascending=False),
                        x="Points",
                        y="Player",
                        color="PlayoffColor",
                        orientation="h",
                        title="Final Standings Strength",
                        color_discrete_map={"Playoff": "#10b981", "Non-Playoff": "#9ca3af"},
                    ),
                    use_container_width=True,
                )

            with st.expander("Remaining match timeline and details", expanded=False):
                results_df = pd.DataFrame(selected_scenario.remaining_results)
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                if not results_df.empty:
                    timeline_df = results_df.copy()
                    timeline_df["ResultType"] = timeline_df["Result"].apply(
                        lambda value: "Draw" if value == "Draw" else ("Player A Win" if "win" in value.lower() else "Result")
                    )
                    st.plotly_chart(
                        px.scatter(
                            timeline_df,
                            x="Round",
                            y="Match",
                            color="ResultType",
                            title="Remaining Match Timeline",
                            color_discrete_map={"Player A Win": "#3b82f6", "Draw": "#f59e0b", "Result": "#ef4444"},
                        ),
                        use_container_width=True,
                    )

            if selected_scenario.playoff_teams:
                st.markdown("**Playoff Qualification Badges**")
                st.markdown("".join([f'<span class="badge-pill">✅ {name}</span>' for name in selected_scenario.playoff_teams]), unsafe_allow_html=True)
            if selected_scenario.champion:
                st.markdown("**Champion Badge**")
                st.markdown(f'<span class="badge-pill">🏆 {selected_scenario.champion}</span>', unsafe_allow_html=True)

    st.subheader("League Story")
    if likely_playoff:
        st.success(f"Most likely playoff teams right now: {', '.join(likely_playoff)}")
    else:
        st.info("No clear playoff favorites yet.")
    story_col1, story_col2 = st.columns(2)
    with story_col1:
        st.markdown("**AI Explanation**")
        st.write(report.ai_explanation)
    with story_col2:
        st.markdown("**League Insights**")
        st.dataframe(insight_df, use_container_width=True, hide_index=True)
    with st.expander("Detailed playoff overview", expanded=False):
        st.dataframe(overview_df, use_container_width=True, hide_index=True)

with explainability_tab:
    st.subheader("Prediction Explainability")
    selected_explainability_player = st.selectbox(
        "Select player for explainability",
        options=report.player_predictions,
        format_func=lambda p: p.player_name,
        key="explainability_player_filter",
    )

    if selected_explainability_player:
        player = selected_explainability_player
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{player.player_name} Playoff Probability", f"{player.playoff_probability:.0%}")
            c2.metric(f"{player.player_name} Champion Probability", f"{player.champion_probability:.0%}")
            c3.metric(f"{player.player_name} Prediction Confidence", f"{player.confidence:.0%}")

            waterfall_x = ["Baseline"] + [_feature_label(item.feature_name) for item in player.feature_contributions] + ["Final"]
            waterfall_measure = ["absolute"] + ["relative"] * len(player.feature_contributions) + ["total"]
            waterfall_y = [report.league_summary.playoff_cut / max(len(report.player_predictions), 1)] + [item.contribution for item in player.feature_contributions] + [0.0]
            fig_waterfall = go.Figure(
                go.Waterfall(
                    x=waterfall_x,
                    measure=waterfall_measure,
                    y=waterfall_y,
                    connector={"line": {"color": "rgba(90, 90, 90, 0.4)"}},
                    decreasing={"marker": {"color": "red"}},
                    increasing={"marker": {"color": "green"}},
                    totals={"marker": {"color": "gray"}},
                )
            )
            fig_waterfall.update_layout(title=f"{player.player_name} Playoff Probability Drivers", showlegend=False, yaxis_tickformat=".0%")
            st.plotly_chart(fig_waterfall, use_container_width=True)

            contribution_df = pd.DataFrame(
                [
                    {
                        "Feature": _feature_label(item.feature_name),
                        "Contribution": _pp(item.contribution),
                        "Confidence": f"{item.confidence:.0%}",
                        "Explanation": item.explanation,
                    }
                    for item in player.feature_contributions
                ]
            )
            st.dataframe(contribution_df, use_container_width=True, hide_index=True)

            with st.expander("🔍 Why?"):
                st.write(f"Prediction: {player.playoff_probability:.0%}")
                st.write("Biggest Positive Factors")
                for item in player.positive_drivers:
                    st.write(f"{_pp(item.contribution)} {_feature_label(item.feature_name)}")
                st.write("Biggest Negative Factors")
                for item in player.negative_drivers:
                    st.write(f"{_pp(item.contribution)} {_feature_label(item.feature_name)}")
                st.write(f"Prediction Confidence: {player.confidence:.0%}")

    with st.expander("Expected Final Ranking", expanded=False):
        fig_expected = px.scatter(
            expected_df,
            x="Player",
            y="Expected Finish",
            error_y=expected_df["Worst"] - expected_df["Expected Finish"],
            error_y_minus=expected_df["Expected Finish"] - expected_df["Best"],
            title="Expected Finish Range",
        )
        st.plotly_chart(fig_expected, use_container_width=True)
        st.dataframe(expected_df, use_container_width=True, hide_index=True)

    with st.expander("Critical Matches", expanded=False):
        st.dataframe(critical_df, use_container_width=True, hide_index=True)
    with st.expander("Remaining Schedule", expanded=False):
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)

with advanced_tab:
    st.subheader("What-If Scenario Overrides")
    overrides: Dict[str, int] = {}
    for match in report.remaining_schedule:
        selection = st.selectbox(
            f"{match.player_a_name} vs {match.player_b_name}",
            options=["Simulation Default", "Player A Win", "Draw", "Player B Win"],
            key=f"what_if_{match.match_id}",
        )
        if selection != "Simulation Default":
            overrides[match.match_id] = RESULT_TO_CODE[selection]

    if overrides:
        rank_matrix = recalculate_with_overrides(report, overrides)
        if rank_matrix.size > 0:
            player_ids = report.internal_artifacts.player_order if report.internal_artifacts else []
            id_to_name = {p.player_id: p.player_name for p in report.player_predictions}
            rank_positions = {pid: [] for pid in player_ids}
            for sim_idx in range(rank_matrix.shape[0]):
                for rank_idx, player_idx in enumerate(rank_matrix[sim_idx], start=1):
                    rank_positions[player_ids[player_idx]].append(rank_idx)
            what_if_df = pd.DataFrame(
                [
                    {
                        "Player": id_to_name.get(pid, pid),
                        "Expected Finish": sum(vals) / len(vals),
                        "Playoff Probability": sum(1 for value in vals if value <= report.league_summary.playoff_cut) / len(vals),
                        "Champion Probability": sum(1 for value in vals if value == 1) / len(vals),
                    }
                    for pid, vals in rank_positions.items()
                    if vals
                ]
            ).sort_values("Expected Finish")
            st.dataframe(what_if_df, use_container_width=True, hide_index=True)
            st.plotly_chart(px.bar(what_if_df, x="Player", y="Champion Probability", title="What-If Champion Odds"), use_container_width=True)

    with st.expander("Player Details", expanded=False):
        player_choice = st.selectbox("Select Player", options=report.player_predictions, format_func=lambda p: p.player_name, key="advanced_player_details")
        st.write(
            {
                "Most Likely Finish": player_choice.most_likely_finish,
                "Best Possible Finish": player_choice.best_possible_finish,
                "Worst Possible Finish": player_choice.worst_possible_finish,
                "Playoff Probability": player_choice.playoff_probability,
                "Champion Probability": player_choice.champion_probability,
                "Remaining SoS": player_choice.remaining_strength_of_schedule,
                "Required Results": player_choice.required_results,
                "Helpful Results": player_choice.helpful_results,
                "Eliminating Results": player_choice.eliminating_results,
            }
        )

    with st.expander("Prediction Confidence", expanded=False):
        confidence_df = pd.DataFrame([{"Metric": key, "Value": value} for key, value in report.confidence_metrics.items()])
        st.dataframe(confidence_df, hide_index=True, use_container_width=True)

    with st.expander("Prediction Diagnostics", expanded=False):
        diag = report.diagnostics
        diag_df = pd.DataFrame(
            [
                {"Metric": "Prediction Accuracy", "Value": diag.prediction_accuracy},
                {"Metric": "Calibration Error", "Value": diag.prediction_calibration_error},
                {"Metric": "Average Prediction Error", "Value": diag.average_prediction_error},
                {"Metric": "Historical Performance", "Value": diag.historical_performance_score},
            ]
        )
        st.dataframe(diag_df, hide_index=True, use_container_width=True)
        st.plotly_chart(
            px.bar(
                pd.DataFrame([{"Feature": key, "Contribution": value} for key, value in diag.feature_contributions.items()]),
                x="Feature",
                y="Contribution",
                title="Feature Contributions",
            ),
            use_container_width=True,
        )

    with st.expander("Export Prediction Report JSON", expanded=False):
        st.download_button(
            "Download JSON",
            data=report.to_json(),
            file_name=f"league_predictor_{report.league_nr}.json",
            mime="application/json",
        )
