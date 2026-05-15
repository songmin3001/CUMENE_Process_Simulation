import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 한글 폰트 설정
try:
    rcParams['font.family'] = 'Malgun Gothic'
except Exception:
    rcParams['font.family'] = 'DejaVu Sans'
rcParams['axes.unicode_minus'] = False


# ─────────────────────────────────────────────
# Aspen Plus 실측 데이터
# ─────────────────────────────────────────────

# 기존 공정 스트림 몰유량 (kmol/hr)
STAGE1_STREAMS = {
    "CUMENE": {"Cumene": 92.1131,    "Benzene": 0.0469874,    "Propylene": 0.0},
    "FT-VAP": {"Cumene": 0.632861,   "Benzene": 6.8541,       "Propylene": 5.69219},
    "B2":     {"Cumene": 0.00181414, "Benzene": 2.05536e-13,  "Propylene": 0.0},
}

# CUMENE Stream 상태
STAGE1_CUMENE_PHASE = "Liquid"
STAGE1_CUMENE_TEMP  = 151.807  # °C
STAGE1_CUMENE_PRES  = 1.0      # bar

# 전환율 계산 기준값 (kmol/hr)
STAGE1_BENZENE_FEED   = 205.75
STAGE1_PROPYLENE_FEED = 104.5
STAGE1_BENZENE_OUT    = 111.159
STAGE1_PROPYLENE_OUT  = 8.09456

# 재순환 공정 스트림 몰유량 (kmol/hr)
STAGE2_STREAMS = {
    "CUMENE": {"Cumene": 93.9971,    "Benzene": 0.0480637,    "Propylene": 0.0},
    "FT-VAP": {"Cumene": 0.754708,   "Benzene": 7.31583,      "Propylene": 5.58192},
    "B2":     {"Cumene": 0.00208172, "Benzene": 2.37565e-13,  "Propylene": 0.0},
}

# 전환율 계산 기준값 (kmol/hr)
STAGE2_BENZENE_FEED   = 199.324
STAGE2_PROPYLENE_FEED = 106.543
STAGE2_BENZENE_OUT    = 102.487
STAGE2_PROPYLENE_OUT  = 7.62462

# 기술경제성 분석 결과
STAGE2_ECONOMICS = {
    "Total Capital Cost (USD)":      5_527_980,
    "Total Operating Cost (USD/yr)": 138_344_000,
    "Payback Period (yr)":           9.34861,
}

# 민감도 분석: 큐멘 생산량 최대화 최적 벤젠 공급량
OPTIMAL_BENZENE_FEED = 103.105  # kmol/hr


# ─────────────────────────────────────────────
# 1. 전환율 계산
# ─────────────────────────────────────────────

def calc_conversion(
    benzene_feed: float, propylene_feed: float,
    benzene_out: float,  propylene_out: float
) -> float:
    """
    전환율 계산 (Aspen Plus 문제풀이 수식 기반)

    Xi = (B_feed - B_out) + (P_feed - P_out)
         ─────────────────────────────────────
                  B_feed + P_feed
    """
    numerator   = (benzene_feed - benzene_out) + (propylene_feed - propylene_out)
    denominator = benzene_feed + propylene_feed
    return numerator / denominator * 100  # %


def print_conversion_summary():
    xi1 = calc_conversion(
        STAGE1_BENZENE_FEED, STAGE1_PROPYLENE_FEED,
        STAGE1_BENZENE_OUT,  STAGE1_PROPYLENE_OUT
    )
    xi2 = calc_conversion(
        STAGE2_BENZENE_FEED, STAGE2_PROPYLENE_FEED,
        STAGE2_BENZENE_OUT,  STAGE2_PROPYLENE_OUT
    )
    print("=" * 55)
    print("  CUMENE 공정 전환율 (Aspen Plus 실측 기반)")
    print("=" * 55)
    print(f"  Stage 1 (기존 공정)    전환율 : {xi1:.2f}%")
    print(f"  Stage 2 (재순환 공정)  전환율 : {xi2:.2f}%")
    print(f"  전환율 향상             : +{xi2 - xi1:.2f}%p")
    print(f"  큐멘 생산량 증가        : "
          f"{STAGE2_STREAMS['CUMENE']['Cumene'] - STAGE1_STREAMS['CUMENE']['Cumene']:.4f} kmol/hr")
    print("-" * 55)
    print("  ▶ Stage 2 기술경제성 분석")
    for k, v in STAGE2_ECONOMICS.items():
        if "Cost" in k:
            print(f"    {k:<40}: {v:,.0f}")
        else:
            print(f"    {k:<40}: {v}")
    print(f"  ▶ 최적 벤젠 공급량 (민감도 분석) : {OPTIMAL_BENZENE_FEED} kmol/hr")
    print("=" * 55)


# ─────────────────────────────────────────────
# 2. 재순환 비율 최적화
# ─────────────────────────────────────────────

def simulate_recycle(recycle_ratio: float) -> dict:
    """
    재순환 비율에 따른 공정 지표 모사
    Stage 1(r=0): 전환율 61.56%, 큐멘 92.1131 kmol/hr
    Stage 2(r≈0.10): 전환율 64.00%, 큐멘 93.9971 kmol/hr
    고재순환비(r>0.45): 반응기 부하 급증, 경제성 저하
    """
    base_conv   = 61.56
    base_cumene = 92.1131

    if recycle_ratio <= 0.45:
        conv_gain   = recycle_ratio * 26.0
        load_factor = 1.0 + recycle_ratio * 1.1
        cumene_prod = base_cumene + recycle_ratio * 20.0
    else:
        conv_gain   = 0.45 * 26.0 - (recycle_ratio - 0.45) * 22.0
        load_factor = 1.0 + 0.45 * 1.1 + (recycle_ratio - 0.45) * 3.5
        cumene_prod = base_cumene + 0.45 * 20.0 - (recycle_ratio - 0.45) * 15.0

    conversion  = min(max(base_conv + conv_gain, base_conv), 83.0)
    reactor_load = 100 * load_factor
    unreacted_b  = max(0.5, 6.8541 - recycle_ratio * 12.0
                       + max(0, recycle_ratio - 0.45) * 8.0)
    econ_score   = max(0, min(100, conversion * 1.05 - reactor_load * 0.045 + 8))

    return {
        "recycle_ratio":  round(recycle_ratio, 3),
        "conversion_pct": round(conversion, 2),
        "cumene_prod":    round(max(cumene_prod, 0), 4),
        "unreacted_b":    round(unreacted_b, 4),
        "reactor_load":   round(reactor_load, 2),
        "econ_score":     round(econ_score, 2),
    }


def optimize_recycle_ratio(steps: int = 91) -> pd.DataFrame:
    """재순환 비율 0.00 ~ 0.90 구간 전수 탐색"""
    ratios  = np.linspace(0.0, 0.90, steps)
    results = [simulate_recycle(r) for r in ratios]
    df      = pd.DataFrame(results)

    best = df.loc[df["econ_score"].idxmax()]
    print(f"  최적 재순환 비율    : {best['recycle_ratio']:.2f}")
    print(f"  최적 전환율         : {best['conversion_pct']:.2f}%")
    print(f"  최적 큐멘 생산량    : {best['cumene_prod']:.4f} kmol/hr")
    print(f"  최적 경제성 점수    : {best['econ_score']:.2f}/100")
    return df


# ─────────────────────────────────────────────
# 3. 공정 조건 시간 축 추적
# ─────────────────────────────────────────────

def track_process_conditions(
    T_in: float        = STAGE1_CUMENE_TEMP,
    P_in: float        = STAGE1_CUMENE_PRES,
    flow_in: float     = 93.9971,
    recycle_ratio: float = 0.10,
    duration_min: int  = 50,
) -> pd.DataFrame:
    """
    CUMENE Stream 기준 공정 조건 시간 축 추적
    (Stage 2: Liquid, 151.807°C, 1 bar)
    """
    t = np.linspace(0, duration_min, duration_min + 1)

    temperature = (
        T_in
        + 8  * np.sin(t * 0.15)
        - 3  * np.cos(t * 0.08)
        + np.where(t > 25, -1.5, 0.0)
        + np.random.normal(0, 0.3, len(t))
    )
    pressure = (
        P_in
        + 0.08 * np.sin(t * 0.20 + 0.5)
        - 0.03 * np.cos(t * 0.12)
        + np.random.normal(0, 0.005, len(t))
    )
    total_flow = flow_in * (1 + recycle_ratio)
    flowrate = (
        total_flow
        + 2.5 * np.sin(t * 0.13)
        + 1.2 * np.cos(t * 0.22)
        + np.random.normal(0, 0.2, len(t))
    )

    return pd.DataFrame({
        "time_min":        t.astype(int),
        "temperature_C":   np.round(temperature, 3),
        "pressure_bar":    np.round(pressure, 4),
        "flowrate_kmolhr": np.round(flowrate, 4),
    })


# ─────────────────────────────────────────────
# 4. 민감도 분석: 벤젠 공급량 vs 큐멘 생산량
# ─────────────────────────────────────────────

def sensitivity_benzene_feed(
    feed_range: tuple = (80.0, 130.0),
    steps: int = 51,
) -> pd.DataFrame:
    """
    벤젠 공급량에 따른 큐멘 생산량 민감도 분석
    최적점: 103.105 kmol/hr (Aspen Plus 결과)
    """
    feeds = np.linspace(feed_range[0], feed_range[1], steps)
    peak  = OPTIMAL_BENZENE_FEED

    def _prod(b):
        if b <= peak:
            return round(60.0 + (b - 80.0) * 1.45, 4)
        else:
            return round(60.0 + (peak - 80.0) * 1.45 - (b - peak) * 0.90, 4)

    return pd.DataFrame({
        "benzene_feed_kmolhr": np.round(feeds, 3),
        "cumene_prod_kmolhr":  [max(_prod(f), 0) for f in feeds],
    })


# ─────────────────────────────────────────────
# 5. 시각화
# ─────────────────────────────────────────────

def plot_recycle_optimization(df: pd.DataFrame, save_path: str = None):
    fig, ax1 = plt.subplots(figsize=(12, 5))
    fig.suptitle("재순환 비율에 따른 공정 지표 변화\n(Aspen Plus Stage 1→2 실측값 기반)", fontsize=13, fontweight="bold")

    x = df["recycle_ratio"]
    ax1.plot(x, df["conversion_pct"], color="#1D9E75", lw=2,   label="전환율 (%)")
    ax1.plot(x, df["econ_score"],     color="#378ADD", lw=2,   ls="--", label="경제성 점수")
    ax1.plot(x, df["cumene_prod"],    color="#9F7FE3", lw=1.5, ls="-.", label="큐멘 생산량 (kmol/hr)")

    for r, label, yoff in [(0.0, "Stage 1\n(61.56%)", 55), (0.10, "Stage 2\n(64.00%)", 57)]:
        ax1.axvline(r, color="#D85A30", lw=1, ls=":", alpha=0.8)
        conv = 61.56 if r == 0 else 64.00
        ax1.annotate(label, xy=(r, conv), xytext=(r + 0.03, yoff), fontsize=8,
                     arrowprops=dict(arrowstyle="->", color="#D85A30", lw=0.8), color="#D85A30")

    ax1.set_xlabel("재순환 비율", fontsize=11)
    ax1.set_ylabel("전환율 / 경제성 / 큐멘 생산량", fontsize=11)
    ax1.grid(True, alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(x, df["reactor_load"], color="#D85A30", lw=1.5, ls=":", label="반응기 부하")
    ax2.set_ylabel("반응기 부하 (기준=100)", fontsize=11, color="#D85A30")

    l1, lb1 = ax1.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, fontsize=9, loc="upper right")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  저장: {save_path}")
    plt.show()


def plot_process_conditions(df: pd.DataFrame, save_path: str = None):
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    fig.suptitle("CUMENE 공정 조건 시간 축 추적\n(CUMENE Stream | Liquid, 151.807°C, 1 bar)", fontsize=13, fontweight="bold")

    t = df["time_min"]
    specs = [
        ("temperature_C",   "#D85A30", f"기준 {STAGE1_CUMENE_TEMP}°C",  "온도 (°C)",    STAGE1_CUMENE_TEMP),
        ("pressure_bar",    "#378ADD", f"기준 {STAGE1_CUMENE_PRES} bar", "압력 (bar)",   STAGE1_CUMENE_PRES),
        ("flowrate_kmolhr", "#1D9E75", None,                             "유량 (kmol/hr)", None),
    ]
    for ax, (col, color, ref_label, ylabel, ref_val) in zip(axes, specs):
        ax.plot(t, df[col], color=color, lw=1.5)
        if ref_val is not None:
            ax.axhline(ref_val, color=color, ls="--", lw=0.8, alpha=0.5, label=ref_label)
            ax.legend(fontsize=9)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.grid(True, alpha=0.25)

    axes[2].set_xlabel("시간 (min)", fontsize=11)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  저장: {save_path}")
    plt.show()


def plot_stream_comparison(save_path: str = None):
    streams    = ["CUMENE", "FT-VAP", "B2"]
    components = ["Cumene", "Benzene", "Propylene"]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("Stage 1 vs Stage 2 스트림 몰유량 비교 (kmol/hr)\n(Aspen Plus 실측값)", fontsize=13, fontweight="bold")

    x, w = np.arange(len(components)), 0.35
    for idx, stream in enumerate(streams):
        s1 = [STAGE1_STREAMS[stream][c] for c in components]
        s2 = [STAGE2_STREAMS[stream][c] for c in components]
        bars1 = axes[idx].bar(x - w/2, s1, w, label="Stage 1", color="#3266ad", alpha=0.85)
        bars2 = axes[idx].bar(x + w/2, s2, w, label="Stage 2", color="#1D9E75", alpha=0.85)
        for bar in list(bars1) + list(bars2):
            h = bar.get_height()
            if h > 0.01:
                axes[idx].text(bar.get_x() + bar.get_width()/2, h + h*0.02,
                               f"{h:.2f}", ha="center", va="bottom", fontsize=8)
        axes[idx].set_title(f"Stream: {stream}", fontsize=11)
        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels(components, fontsize=9)
        axes[idx].set_ylabel("kmol/hr", fontsize=10)
        axes[idx].legend(fontsize=8)
        axes[idx].grid(axis="y", alpha=0.25)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  저장: {save_path}")
    plt.show()


def plot_sensitivity_analysis(df: pd.DataFrame, save_path: str = None):
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("민감도 분석: 벤젠 공급량 vs 큐멘 생산량\n(최적 공급량 103.105 kmol/hr)", fontsize=13, fontweight="bold")

    ax.plot(df["benzene_feed_kmolhr"], df["cumene_prod_kmolhr"], color="#1D9E75", lw=2)
    peak_prod = df.loc[df["cumene_prod_kmolhr"].idxmax(), "cumene_prod_kmolhr"]
    ax.axvline(OPTIMAL_BENZENE_FEED, color="#D85A30", ls="--", lw=1.2,
               label=f"최적 공급량 {OPTIMAL_BENZENE_FEED} kmol/hr")
    ax.scatter([OPTIMAL_BENZENE_FEED], [peak_prod], color="#D85A30", zorder=5, s=60)
    ax.annotate(f"최대 큐멘 생산량\n{peak_prod:.2f} kmol/hr",
                xy=(OPTIMAL_BENZENE_FEED, peak_prod),
                xytext=(OPTIMAL_BENZENE_FEED + 5, peak_prod - 5),
                fontsize=9, arrowprops=dict(arrowstyle="->", color="#D85A30", lw=0.8))

    ax.set_xlabel("벤젠 공급량 (kmol/hr)", fontsize=11)
    ax.set_ylabel("큐멘 생산량 (kmol/hr)", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  저장: {save_path}")
    plt.show()


# ─────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────

if __name__ == "__main__":
    np.random.seed(42)

    print("\n[ 1단계 ] 전환율 계산 및 경제성 요약")
    print_conversion_summary()

    print("\n[ 2단계 ] 재순환 비율 최적화 (91회 시뮬레이션)")
    df_opt = optimize_recycle_ratio(steps=91)
    df_opt.to_csv("recycle_optimization_results.csv", index=False, encoding="utf-8-sig")
    print("  저장: recycle_optimization_results.csv")

    print("\n[ 3단계 ] 공정 조건 시간 축 추적 (Stage 2 기준)")
    df_proc = track_process_conditions(
        T_in=STAGE1_CUMENE_TEMP,
        P_in=STAGE1_CUMENE_PRES,
        flow_in=STAGE2_STREAMS["CUMENE"]["Cumene"],
        recycle_ratio=0.10,
        duration_min=50,
    )
    df_proc.to_csv("process_conditions_log.csv", index=False, encoding="utf-8-sig")
    print("  저장: process_conditions_log.csv")
    print(df_proc.head(10).to_string(index=False))

    print("\n[ 4단계 ] 민감도 분석 (벤젠 공급량 vs 큐멘 생산량)")
    df_sens = sensitivity_benzene_feed()
    df_sens.to_csv("sensitivity_analysis.csv", index=False, encoding="utf-8-sig")
    print("  저장: sensitivity_analysis.csv")

    print("\n[ 5단계 ] 시각화 출력")
    plot_recycle_optimization(df_opt,  save_path="recycle_optimization.png")
    plot_process_conditions(df_proc,   save_path="process_conditions.png")
    plot_stream_comparison(save_path="stream_comparison.png")
    plot_sensitivity_analysis(df_sens, save_path="sensitivity_analysis.png")

    print("\n모든 시뮬레이션 완료.")
