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


# ---------------------------------------------------------------- 계산 함수
def aggregate(df, start, end):
    """선택 기간의 DALY, 연구 건수를 합산한 뒤 점유율과 비율을 다시 계산한다."""
    sub = df[(df["year"] >= start) & (df["year"] <= end)]
    g = sub.groupby("cause_name", as_index=False).agg(
        daly=("daly", "sum"),
        research_count=("research_count", "sum"),
        weighted_research_count=("weighted_research_count", "sum"),
    )
    g["daly_share"] = g["daly"] / g["daly"].sum() * 100
    total_w = g["weighted_research_count"].sum()
    g["research_share"] = g["weighted_research_count"] / total_w * 100 if total_w else 0.0
    g["share_gap"] = g["daly_share"] - g["research_share"]
    # 연구 점유율이 0이면 비율을 계산할 수 없으므로 NaN 처리
    g["ratio"] = g["daly_share"] / g["research_share"].where(g["research_share"] > 0)
    return g


def fmt_daly(x):
    """DALY 값을 '3,143만'처럼 읽기 쉽게 바꾼다."""
    return f"{x / 1e4:,.0f}만"


def corr_text(r):
    """상관계수 크기를 쉬운 말로 바꾼다."""
    a = abs(r)
    if a >= 0.7:
        strength = "강한"
    elif a >= 0.4:
        strength = "중간 정도의"
    else:
        strength = "약한"
    direction = "양(+)의" if r >= 0 else "음(-)의"
    return f"{strength} {direction} 관계"


def explain(text):
    """그래프 아래에 넣는 줄글 설명."""
    st.markdown(text)


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
n_years = end_year - start_year + 1

# ---------------------------------------------------------------- 본문 머리
st.title("국내 질병군별 질병부담과 임상연구 분포의 불균형 분석")
st.caption(
    "DALY: IHME GBD 2023 (대한민국) · 임상연구: 질병관리청 CRIS 등록 중재연구 · "
    f"선택 기간: {start_year}~{end_year}년"
)

st.markdown(
    "**이 웹앱은 무엇을 보여주나요?** 질병마다 사람들이 겪는 건강 손실의 크기(질병부담)와, "
    "그 질병을 대상으로 등록된 임상연구의 양이 서로 비슷한 비율로 나타나는지를 비교합니다. "
    "질병부담에 비해 연구가 적은 질병군을 찾아 보는 것이 목적입니다."
)

with st.expander("처음 보시나요? 용어 풀이"):
    st.markdown(
        "- **질병군**: 비슷한 질병을 묶은 분류입니다. 이 앱은 국제 질병부담 연구(GBD)의 분류에 따라 "
        "심혈관 질환, 신생물(암 등), 정신 장애처럼 17개 질병군으로 나누어 봅니다.\n"
        "- **DALY(장애보정생명년)**: 질병 때문에 잃어버린 건강한 삶의 햇수를 나타내는 지표입니다. "
        "일찍 사망해서 잃은 햇수와, 아프거나 장애를 안고 살아서 잃은 햇수를 더한 값이며, "
        "DALY가 클수록 그 질병이 사회에 주는 건강 손실이 크다는 뜻입니다. 이 앱에서는 이를 '질병부담'이라고 부릅니다.\n"
        "- **CRIS와 중재연구**: CRIS는 질병관리청의 임상연구 등록 사이트이고, 중재연구는 약, 시술, 운동처럼 "
        "무언가를 사람에게 적용해 보고 효과를 확인하는 연구입니다. 이 앱의 '연구 건수'는 CRIS에 등록된 중재연구의 수입니다.\n"
        "- **점유율**: 전체를 100으로 보았을 때 해당 질병군이 차지하는 비중(%)입니다. "
        "예를 들어 DALY 점유율 20%는 전체 질병부담의 20%가 그 질병군에서 나왔다는 뜻입니다.\n"
        "- **부담/연구 비율**: DALY 점유율을 연구 점유율로 나눈 값입니다. 1이면 부담과 연구 비중이 비슷하고, "
        "1보다 크면 질병부담에 비해 연구 비중이 작다는 뜻입니다."
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

    explain(
        "**이 그래프(히트맵)는 어떻게 읽나요?** 가로는 연도, 세로는 질병군이고, 칸의 색이 진할수록 "
        "그 해 그 질병군의 DALY(질병부담)가 크다는 뜻입니다. 질병군은 위쪽일수록 선택한 기간의 "
        "DALY가 큰 순서로 정렬했습니다. 같은 줄에서 색이 어떻게 변하는지 보면 그 질병군의 부담이 "
        "해마다 늘었는지 줄었는지 알 수 있고, 같은 열에서 색을 비교하면 그 해에 어떤 질병군의 부담이 컸는지 알 수 있습니다. "
        "칸 위에 손가락이나 마우스를 올리면 정확한 값이 나옵니다."
    )

    bar = px.bar(
        agg.sort_values("daly", ascending=True),
        x="daly",
        y="cause_name",
        orientation="h",
        labels={"daly": f"DALY 합계 ({start_year}~{end_year})", "cause_name": ""},
    )
    st.plotly_chart(bar, width="stretch")

    top = agg.sort_values("daly", ascending=False).iloc[0]
    low = agg.sort_values("daly", ascending=True).iloc[0]
    sum_note = (
        f"선택한 {n_years}년 동안 해마다의 DALY를 모두 더한 값입니다. "
        if n_years > 1
        else "선택한 한 해의 DALY입니다. "
    )
    explain(
        f"**이 그래프(막대그래프)는 무엇을 뜻하나요?** 막대가 길수록 질병부담이 큰 질병군입니다. {sum_note}"
        f"선택한 기간에 질병부담이 가장 큰 질병군은 **{top['cause_name']}**으로 전체의 약 {top['daly_share']:.1f}%"
        f"(약 {fmt_daly(top['daly'])} DALY)를 차지하고, 가장 작은 질병군은 **{low['cause_name']}**으로 "
        f"약 {low['daly_share']:.1f}%입니다. DALY가 작다고 해서 중요하지 않은 질병이라는 뜻은 아니며, "
        "사망이나 장애로 잃는 건강 햇수가 상대적으로 적다는 뜻입니다."
    )

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

    peak = yearly.loc[yearly["research_count"].idxmax()]
    if len(yearly) > 1:
        first = yearly.iloc[0]
        last = yearly.iloc[-1]
        trend = (
            f"{int(first['year'])}년에는 {int(first['research_count']):,}건, "
            f"{int(last['year'])}년에는 {int(last['research_count']):,}건이 등록되었고, "
            f"등록이 가장 많았던 해는 {int(peak['year'])}년({int(peak['research_count']):,}건)입니다. "
        )
    else:
        trend = f"선택한 해에는 {int(peak['research_count']):,}건이 등록되었습니다. "
    explain(
        "**이 그래프(선그래프)는 무엇을 뜻하나요?** 해마다 CRIS에 새로 등록된 임상연구가 몇 건인지 보여줍니다. "
        f"{trend}다만 이 숫자는 '등록된 연구 수'이므로, 등록 제도의 변화나 연구자들의 등록 습관에 따라 달라질 수 있습니다. "
        "그래서 등록 건수가 늘었다고 해서 실제로 수행된 임상연구가 그만큼 늘었다고 단정할 수는 없습니다. "
        "또한 이 앱은 질병군을 분류할 수 있었던 연구만 센 값이라서 CRIS 전체 등록 건수보다 적습니다."
    )

    st.subheader("질병군별 연구 건수")
    bar2 = px.bar(
        agg.sort_values("research_count", ascending=True),
        x="research_count",
        y="cause_name",
        orientation="h",
        labels={"research_count": "연구 건수", "cause_name": ""},
    )
    st.plotly_chart(bar2, width="stretch")

    most = agg.sort_values("research_count", ascending=False).iloc[0]
    least = agg.sort_values("research_count", ascending=True).iloc[0]
    zero = agg[agg["research_count"] == 0]["cause_name"].tolist()
    zero_note = f" 이 기간에 등록된 연구가 한 건도 없는 질병군은 {', '.join(zero)}입니다." if zero else ""
    explain(
        "**이 그래프는 무엇을 뜻하나요?** 선택한 기간 동안 질병군마다 등록된 중재연구가 몇 건인지 비교합니다. "
        f"연구가 가장 많은 질병군은 **{most['cause_name']}**({int(most['research_count']):,}건, 전체의 "
        f"{most['research_share']:.1f}%)이고, 가장 적은 질병군은 **{least['cause_name']}**"
        f"({int(least['research_count']):,}건)입니다.{zero_note} "
        "연구 건수만으로는 어떤 질병군에 연구가 '충분한지' 알 수 없으므로, 다음 탭에서 질병부담과 함께 비교합니다."
    )

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
        explain(
            "**이 그래프는 무엇을 뜻하나요?** 위에서 고른 질병군의 연도별 등록 건수를 선 하나씩으로 보여줍니다. "
            "선이 위로 올라가면 그 질병군의 연구 등록이 늘어난 것이고, 선이 서로 가까우면 연구 건수가 비슷하다는 뜻입니다. "
            "질병군마다 연구가 늘어난 시기가 다른지 비교해 보세요."
        )

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

        parts = []
        if "daly" in selected:
            parts.append(
                "**심각성(DALY 합계)**: 막대가 길수록 질병 때문에 잃은 건강한 삶의 햇수가 많다는 뜻입니다."
            )
        if "count" in selected:
            parts.append(
                "**연구율(연구 건수)**: 막대가 길수록 그 질병군을 대상으로 등록된 임상연구가 많다는 뜻입니다."
            )
        if "ratio" in selected:
            r = agg.dropna(subset=["ratio"])
            n_over = int((r["ratio"] > 1).sum())
            zero_cnt = int((agg["research_count"] == 0).sum())
            zero_txt = (
                f" 연구가 0건인 {zero_cnt}개 질병군은 0으로 나눌 수 없어 이 그래프에서 빠졌습니다."
                if zero_cnt
                else ""
            )
            parts.append(
                "**부담/연구 비율**: 점선(1)이 기준선입니다. 1이면 질병부담의 비중과 연구의 비중이 같고, "
                "1보다 크면 부담에 비해 연구 비중이 작으며(연구가 상대적으로 부족), 1보다 작으면 부담에 비해 연구 비중이 큽니다. "
                f"그래프에 표시된 {len(r)}개 질병군 중 {n_over}개가 1보다 큽니다.{zero_txt}"
            )
        explain("**각 그래프는 무엇을 뜻하나요?**\n\n" + "\n\n".join(f"- {p}" for p in parts))
        st.caption("비율은 연구가 아주 적은 질병군에서 작은 변화에도 크게 달라질 수 있으니 연구 건수와 함께 보세요.")

    st.subheader("점유율 비교")
    share = agg.sort_values("share_gap", ascending=False)
    fig = go.Figure()
    fig.add_bar(x=share["cause_name"], y=share["daly_share"], name="DALY 점유율 (%)")
    fig.add_bar(x=share["cause_name"], y=share["research_share"], name="연구 점유율 (%)")
    fig.update_layout(barmode="group", yaxis_title="%", xaxis_title="", legend_title="")
    st.plotly_chart(fig, width="stretch")

    big = share.head(3)
    big_txt = ", ".join(
        f"{row.cause_name}(DALY {row.daly_share:.1f}% vs 연구 {row.research_share:.1f}%)"
        for row in big.itertuples()
    )
    over = share.sort_values("share_gap", ascending=True).iloc[0]
    explain(
        "**이 그래프는 어떻게 읽나요?** 질병군마다 막대가 두 개 있습니다. 하나는 전체 질병부담 중 그 질병군의 비중(DALY 점유율), "
        "다른 하나는 전체 임상연구 중 그 질병군의 비중(연구 점유율)입니다. 두 막대의 높이가 비슷하면 부담과 연구가 균형을 이루고, "
        "DALY 막대가 연구 막대보다 훨씬 높으면 부담에 비해 연구가 적은 질병군입니다. 질병군은 두 점유율의 차이가 큰 순서"
        f"(왼쪽일수록 연구가 부족한 쪽)로 나열했습니다. 이 기간에 차이가 가장 큰 세 질병군은 {big_txt}입니다. "
        f"반대로 연구 비중이 부담 비중보다 가장 크게 앞선 질병군은 **{over['cause_name']}**입니다."
    )

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
    explain(
        "**이 표는 무엇을 뜻하나요?** 위 그래프의 숫자를 질병군별로 정리한 표이며, 점유율 차이가 큰 순서로 정렬했습니다. "
        "**점유율 차이(%p)**는 DALY 점유율에서 연구 점유율을 뺀 값입니다. 플러스(+)이면 부담에 비해 연구 비중이 작고, "
        "마이너스(-)이면 연구 비중이 부담 비중보다 큽니다. (%p는 퍼센트 점수의 차이를 뜻합니다.) "
        "**부담/연구 비율**은 앞에서 설명한 대로 1보다 클수록 연구가 상대적으로 부족하다는 뜻이며, "
        "연구가 0건이면 계산할 수 없어 '연구 0건'으로 표시합니다. 두 기준은 순위가 서로 다르게 나올 수 있으므로 함께 봐야 합니다."
    )

    st.subheader("DALY와 연구 건수의 관계")
    log_axes = st.checkbox("로그 축으로 보기", value=False)
    sc = px.scatter(agg, x="daly", y="research_count", text="cause_name",
                    labels={"daly": "DALY 합계", "research_count": "연구 건수"})
    sc.update_traces(textposition="top center")
    if log_axes:
        sc.update_xaxes(type="log")
        sc.update_yaxes(type="log")
    st.plotly_chart(sc, width="stretch")

    # 스피어먼 = 순위로 바꾼 값의 피어슨 상관계수 (scipy 없이 계산)
    pearson = agg["daly"].corr(agg["research_count"], method="pearson")
    spearman = agg["daly"].rank().corr(agg["research_count"].rank(), method="pearson")
    c1, c2 = st.columns(2)
    c1.metric("피어슨 상관계수", f"{pearson:.2f}")
    c2.metric("스피어먼 순위상관계수", f"{spearman:.2f}")

    explain(
        "**이 그래프(산점도)는 어떻게 읽나요?** 점 하나가 질병군 하나입니다. 오른쪽에 있을수록 질병부담(DALY)이 크고, "
        "위쪽에 있을수록 연구 건수가 많습니다. 점들이 왼쪽 아래에서 오른쪽 위로 이어지는 모양이면 질병부담이 큰 질병군일수록 "
        "연구도 많다는 뜻이고, 같은 가로 위치(비슷한 부담)인데 점이 아래에 있다면 비슷한 부담의 다른 질병군보다 연구가 적다는 뜻입니다. "
        "'로그 축으로 보기'를 켜면 값의 차이가 큰 점들이 한쪽에 몰리지 않고 고르게 펼쳐져 보입니다.\n\n"
        "**상관계수는 무엇인가요?** 두 값이 얼마나 함께 움직이는지를 -1에서 1 사이의 수로 나타낸 것입니다. 1에 가까울수록 "
        "질병부담이 클 때 연구도 많은 경향이 강하고, 0에 가까우면 관계가 거의 없으며, -1에 가까우면 반대로 움직입니다. "
        "피어슨은 실제 값의 관계를, 스피어먼은 값의 순위(몇 번째로 큰지)의 관계를 봅니다. "
        f"지금 선택한 기간에서는 피어슨 {pearson:.2f}, 스피어먼 {spearman:.2f}로 **{corr_text(pearson)}**가 나타납니다.\n\n"
        "**주의할 점**: 상관계수가 높다고 해서 질병부담이 연구 건수를 결정한다는 뜻은 아닙니다. "
        "또한 17개 질병군만으로 계산했기 때문에 몇몇 질병군의 영향이 크고, 전체적으로 비례하더라도 "
        "개별 질병군에서는 부담에 비해 연구가 적을 수 있습니다."
    )

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
    explain(
        "**이 숫자는 무엇을 뜻하나요?** CRIS에는 연구가 어떤 질병을 대상으로 하는지 적는 항목이 따로 없어서, "
        "연구 제목과 요약에 나온 질병 이름을 바탕으로 17개 질병군에 연결했습니다. "
        f"2010~2023년에 등록된 중재연구 {total:,}건 가운데 질병군을 정할 수 있었던 {classified:,}건만 분석에 사용했고, "
        f"나머지 {unclassified:,}건({unclassified / total * 100:.1f}%)은 대상 질병을 알 수 없거나 분석 대상 질병군에 "
        "해당하지 않아 제외했습니다. 제외된 연구가 많으면 결과가 실제와 다를 수 있으므로 이 비율을 함께 공개합니다."
    )

    st.subheader("분류 정확도 검수")
    st.info("무작위 표본 검수는 아직 진행되지 않았습니다. 검수 후 표본 수와 정확도를 여기에 표시할 예정입니다.")

    st.subheader("분석에 포함된 질병군")
    st.write("GBD Level 2 질병군 22개 중 17개 질병군을 분석했습니다. "
             "교통 상해, 비의도적 상해, 소외열대질환 및 말라리아, 영양 결핍, 자해 및 대인 폭력은 제외되었습니다.")

    st.subheader("이 결과를 해석할 때 주의할 점")
    st.markdown(
        "- 질병군별 임상연구 건수는 질병부담뿐 아니라 기술 수준, 임상시험 난이도, 환자 모집 가능성, 경제성 등 "
        "여러 요인의 영향을 받습니다. 그래서 이 분석만으로 불균형이 생긴 원인을 밝힐 수는 없습니다.\n"
        "- CRIS에 등록된 중재연구만 분석하므로 국내 모든 임상연구를 포함하지 않으며, 연구의 규모와 질, "
        "실제 성과는 반영하지 못합니다.\n"
        "- 질환명 사전을 이용한 자동 분류에서 오분류와 미분류가 생길 수 있습니다.\n"
        "- DALY는 실제로 센 값이 아니라 추정치이므로 불확실성이 있습니다.\n"
        "- 이 결과는 연구 지원 우선순위를 확정하는 근거가 아니라, 추가로 살펴볼 질병군을 찾는 자료로 활용해야 합니다."
    )
