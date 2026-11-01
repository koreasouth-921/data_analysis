import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="질병부담과 임상연구 분포의 불균형 분석",
    page_icon="📊",
    layout="wide",
)

FINAL_PATH = "data/final_17groups.csv"
CRIS_PATH = "data/cris_17groups_webapp.csv"


# ---------------------------------------------------------------- 데이터 로드
@st.cache_data
def load_final():
    df = pd.read_csv(FINAL_PATH, encoding="utf-8-sig")
    df["cause_name"] = df["cause_name"].str.strip()
    return df


@st.cache_data
def load_cris():
    return pd.read_csv(CRIS_PATH, encoding="utf-8-sig")


final = load_final()
cris = load_cris()

YEAR_MIN, YEAR_MAX = int(final["year"].min()), int(final["year"].max())


# ---------------------------------------------------------------- 기간 재집계
def aggregate(df, start, end):
    """선택 기간의 DALY, 연구 건수를 합산한 뒤 점유율과 비율을 다시 계산한다."""
    sub = df[(df["year"] >= start) & (df["year"] <= end)]
    g = (
        sub.groupby("cause_name", as_index=False)
        .agg(
            daly=("daly", "sum"),
            research_count=("research_count", "sum"),
            weighted_research_count=("weighted_research_count", "sum"),
        )
    )
    g["daly_share"] = g["daly"] / g["daly"].sum() * 100
    total_w = g["weighted_research_count"].sum()
    g["research_share"] = g["weighted_research_count"] / total_w * 100 if total_w else 0.0
    g["share_gap"] = g["daly_share"] - g["research_share"]
    # 연구 점유율이 0이면 비율을 계산할 수 없으므로 NaN 처리
    g["ratio"] = g["daly_share"] / g["research_share"].where(g["research_share"] > 0)
    return g


# ---------------------------------------------------------------- 사이드바
st.sidebar.header("분석 조건 설정")

start_year, end_year = st.sidebar.slider(
    "분석 기간 (연도)",
    min_value=YEAR_MIN,
    max_value=YEAR_MAX,
    value=(YEAR_MIN, YEAR_MAX),
    step=1,
)
st.sidebar.caption(f"{start_year}~{end_year}년 · 총 {end_year - start_year + 1}년")

st.sidebar.markdown("**분석할 대상 (1~3개 선택)**")
use_daly = st.sidebar.checkbox("심각성 (DALY 값)", value=True)
use_count = st.sidebar.checkbox("연구율 (임상연구 건수)", value=True)
use_ratio = st.sidebar.checkbox("심각성 대비 연구율 (DALY 점유율 ÷ 연구 점유율)", value=True)

st.sidebar.markdown("**분석 범위**")
st.sidebar.selectbox(
    "범위",
    ["중분류 질병군 (17개)"],
    help="신생물·정신질환 세부 질병(소분류)은 GBD Level 3 데이터 확보 후 추가될 예정입니다.",
)

agg = aggregate(final, start_year, end_year)

# ---------------------------------------------------------------- 본문
st.title("국내 질병군별 질병부담과 임상연구 분포의 불균형 분석")
st.caption(
    "DALY: IHME GBD 2023 (대한민국) · 임상연구: 질병관리청 CRIS 등록 중재연구 · "
    f"선택 기간: {start_year}~{end_year}년"
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["1. 질병부담 현황", "2. 임상연구 현황", "3. 질병부담 vs 임상연구", "4. 데이터 설명·한계"]
)

# ---------------------------------------------------------------- 탭 1
with tab1:
    st.subheader("질병군별 DALY")
    sub = final[(final["year"] >= start_year) & (final["year"] <= end_year)]

    order = agg.sort_values("daly", ascending=False)["cause_name"].tolist()
    pivot = sub.pivot(index="cause_name", columns="year", values="daly").reindex(order)

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="Blues",
        labels=dict(x="연도", y="질병군", color="DALY"),
    )
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, width="stretch")

    bar = px.bar(
        agg.sort_values("daly", ascending=True),
        x="daly",
        y="cause_name",
        orientation="h",
        labels={"daly": f"DALY 합계 ({start_year}~{end_year})", "cause_name": ""},
    )
    st.plotly_chart(bar, width="stretch")

    top = agg.sort_values("daly", ascending=False).iloc[0]
    st.info(f"선택 기간에 DALY가 가장 큰 질병군은 **{top['cause_name']}** ({top['daly_share']:.1f}%)입니다.")

# ---------------------------------------------------------------- 탭 2
with tab2:
    st.subheader("연도별 CRIS 등록 임상연구 건수")
    yearly = (
        final[(final["year"] >= start_year) & (final["year"] <= end_year)]
        .groupby("year", as_index=False)["research_count"]
        .sum()
    )
    line = px.line(yearly, x="year", y="research_count", markers=True,
                   labels={"year": "연도", "research_count": "등록 건수"})
    line.update_xaxes(dtick=1)
    st.plotly_chart(line, width="stretch")
    st.caption("등록 건수의 증가가 실제 수행된 임상연구 전체의 증가를 뜻하지는 않습니다. (제도 변화 등의 영향 가능)")

    st.subheader("질병군별 연구 건수")
    bar2 = px.bar(
        agg.sort_values("research_count", ascending=True),
        x="research_count",
        y="cause_name",
        orientation="h",
        labels={"research_count": "연구 건수", "cause_name": ""},
    )
    st.plotly_chart(bar2, width="stretch")

    st.subheader("질병군별 연도 추이 비교")
    default_causes = agg.sort_values("research_count", ascending=False)["cause_name"].head(5).tolist()
    picked = st.multiselect("비교할 질병군", agg["cause_name"].tolist(), default=default_causes)
    if picked:
        t = final[
            (final["year"] >= start_year)
            & (final["year"] <= end_year)
            & (final["cause_name"].isin(picked))
        ]
        tl = px.line(t, x="year", y="research_count", color="cause_name", markers=True,
                     labels={"year": "연도", "research_count": "연구 건수", "cause_name": "질병군"})
        tl.update_xaxes(dtick=1)
        st.plotly_chart(tl, width="stretch")

# ---------------------------------------------------------------- 탭 3
with tab3:
    st.subheader("선택한 지표 비교")
    selected = []
    if use_daly:
        selected.append("daly")
    if use_count:
        selected.append("count")
    if use_ratio:
        selected.append("ratio")

    if not selected:
        st.warning("사이드바에서 비교할 대상을 1개 이상 선택해 주세요.")
    else:
        cols = st.columns(len(selected))
        for col, key in zip(cols, selected):
            with col:
                if key == "daly":
                    d = agg.sort_values("daly", ascending=True)
                    f = px.bar(d, x="daly", y="cause_name", orientation="h",
                               title="심각성 (DALY 합계)", labels={"daly": "DALY", "cause_name": ""})
                elif key == "count":
                    d = agg.sort_values("research_count", ascending=True)
                    f = px.bar(d, x="research_count", y="cause_name", orientation="h",
                               title="연구율 (연구 건수)", labels={"research_count": "건수", "cause_name": ""})
                else:
                    d = agg.dropna(subset=["ratio"]).sort_values("ratio", ascending=True)
                    f = px.bar(d, x="ratio", y="cause_name", orientation="h",
                               title="DALY 점유율 ÷ 연구 점유율", labels={"ratio": "비율", "cause_name": ""})
                    f.add_vline(x=1, line_dash="dash", line_color="gray")
                st.plotly_chart(f, width="stretch")
        if "ratio" in selected:
            st.caption("비율이 1보다 크면 질병부담에 비해 연구 비중이 낮은 질병군입니다. 연구가 0건인 질병군은 비율을 계산할 수 없어 제외했습니다.")

    st.subheader("점유율 비교")
    share = agg.sort_values("share_gap", ascending=False)
    fig = go.Figure()
    fig.add_bar(x=share["cause_name"], y=share["daly_share"], name="DALY 점유율 (%)")
    fig.add_bar(x=share["cause_name"], y=share["research_share"], name="연구 점유율 (%)")
    fig.update_layout(barmode="group", yaxis_title="%", xaxis_title="", legend_title="")
    st.plotly_chart(fig, width="stretch")

    st.subheader("불균형 지표 순위")
    table = share.copy()
    table["ratio"] = table["ratio"].round(2)
    table = table.rename(columns={
        "cause_name": "질병군",
        "daly_share": "DALY 점유율(%)",
        "research_share": "연구 점유율(%)",
        "share_gap": "점유율 차이(%p)",
        "ratio": "부담/연구 비율",
        "research_count": "연구 건수",
    })[["질병군", "DALY 점유율(%)", "연구 점유율(%)", "점유율 차이(%p)", "부담/연구 비율", "연구 건수"]]
    st.dataframe(
        table.style.format({
            "DALY 점유율(%)": "{:.1f}",
            "연구 점유율(%)": "{:.1f}",
            "점유율 차이(%p)": "{:.1f}",
            "부담/연구 비율": "{:.2f}",
        }, na_rep="연구 0건"),
        width="stretch",
        hide_index=True,
    )
    st.caption("점유율 차이가 클수록(+) 질병부담에 비해 연구 비중이 낮습니다.")

    st.subheader("DALY와 연구 건수의 관계")
    log_axes = st.checkbox("로그 축으로 보기", value=False)
    sc = px.scatter(agg, x="daly", y="research_count", text="cause_name",
                    labels={"daly": "DALY 합계", "research_count": "연구 건수"})
    sc.update_traces(textposition="top center")
    if log_axes:
        sc.update_xaxes(type="log")
        sc.update_yaxes(type="log")
    st.plotly_chart(sc, width="stretch")

    pearson = agg["daly"].corr(agg["research_count"], method="pearson")
    spearman = agg["daly"].corr(agg["research_count"], method="spearman")
    c1, c2 = st.columns(2)
    c1.metric("피어슨 상관계수", f"{pearson:.2f}")
    c2.metric("스피어먼 순위상관계수", f"{spearman:.2f}")
    st.caption("상관관계는 인과관계를 뜻하지 않으며, 17개 질병군만으로 계산한 값이라 해석에 주의가 필요합니다.")

# ---------------------------------------------------------------- 탭 4
with tab4:
    st.subheader("데이터 분류 현황")
    total = len(cris)
    classified = int(cris["updated_17_cause_name"].notna().sum())
    unclassified = total - classified
    m1, m2, m3 = st.columns(3)
    m1.metric("전체 등록 연구", f"{total:,}건")
    m2.metric("분석에 사용한 연구", f"{classified:,}건")
    m3.metric("미분류(제외)", f"{unclassified:,}건 ({unclassified / total * 100:.1f}%)")

    status = cris["updated_classification_status"].value_counts().rename_axis("분류 상태").reset_index(name="건수")
    st.dataframe(status, width="stretch", hide_index=True)
    st.caption("미분류 연구는 분석에서 제외되므로, 미분류 비율이 높으면 결과가 한쪽으로 치우쳤을 가능성이 있습니다.")

    st.subheader("분류 정확도 검수")
    st.info("무작위 표본 검수는 아직 진행되지 않았습니다. 검수 후 표본 수와 정확도를 여기에 표시할 예정입니다.")

    st.subheader("분석에 포함된 질병군")
    st.write("GBD Level 2 질병군 22개 중 17개 질병군을 분석했습니다. "
             "교통 상해, 비의도적 상해, 소외열대질환 및 말라리아, 영양 결핍, 자해 및 대인 폭력은 제외되었습니다.")

    st.subheader("한계")
    st.markdown(
        "- 질병군별 임상연구 건수는 질병부담뿐 아니라 기술 수준, 임상시험 난이도, 경제성 등 여러 요인의 영향을 받아, 이 분석만으로 불균형의 원인을 규명할 수 없습니다.\n"
        "- CRIS에 등록된 중재연구만 분석하므로 국내 모든 임상연구를 포괄하지 않으며, 연구의 규모와 질은 반영하지 못합니다.\n"
        "- 질환명 사전을 이용한 자동 분류에서 오분류와 미분류가 발생할 수 있습니다.\n"
        "- DALY는 추정치이므로 불확실성이 있습니다.\n"
        "- 본 결과는 연구 지원 우선순위를 확정하는 근거가 아니라, 추가 검토가 필요한 질병군을 탐색하는 자료입니다."
    )
