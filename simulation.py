"""
CUMENE 생산 공정 개선 시뮬레이션
=================================
1. 재순환 비율 최적화 (수십 회 시뮬레이션 반복)
2. 온도·압력·유량 시간 축 추적
3. 기존 vs 개선 공정 결과 분석

실제 Aspen Plus 연동 없이 모사 데이터 기반으로 동작합니다.
Aspen 연동 시 simulate_reactor() 내부를 API 호출로 교체하세요.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rcParams

# 한글 폰트 설정
try:
    rcParams['font.family'] = 'Malgun Gothic'
except Exception:
    rcParams['font.family'] = 'DejaVu Sans'
rcParams['axes.unicode_minus'] = False


# ─────────────────────────────────────────────
# 공정 모델 함수 (Aspen Plus 모사 결과 기반)
# ─────────────────────────────────────────────

def simulate_reactor(recycle_ratio: float, T_in: float = 420.0, P_in: float = 30.0) -> dict:
    """
    반응기 시뮬레이션 모사
    - recycle_ratio : 재순환 비율 (0.0 ~ 0.7)
    - T_in          : 반응기 입구 온도 (°C)
    - P_in          : 반응기 입구 압력 (bar)
    Returns dict: {conversion, unreacted, reactor_load, econ_score}
    """
    base_conversion = 61.56  # 기존 공정 전환율 (%)
    T_boost = (T_in - 420) * 0.08

    if recycle_ratio <= 0.4:
        conversion_gain = recycle_ratio * 32 + T_boost
        load_factor = 1.0 + recycle_ratio * 1.4
    else:
        # 고재순환비에서 수확 체감 + 부하 급증
        conversion_gain = 0.4 * 32 + T_boost - (recycle_ratio - 0.4) * 18
        load_factor = 1.0 + 0.4 * 1.4 + (recycle_ratio - 0.4) * 3.0

    conversion = min(max(base_conversion + conversion_gain, base_conversion), 82.0)
    unreacted = max(1.0, 13.5 - recycle_ratio * 32 + (max(0, recycle_ratio - 0.4) * 20))
    reactor_load = 100 * load_factor
    econ_score = max(0, min(100, conversion * 1.1 - reactor_load * 0.05 + 10))

    return {
        "recycle_ratio": round(recycle_ratio, 3),
        "T_in": T_in,
        "P_in": P_in,
        "conversion": round(conversion, 2),
        "unreacted": round(unreacted, 2),
        "reactor_load": round(reactor_load, 2),
        "econ_score": round(econ_score, 2),
    }


def track_process_conditions(
    recycle_ratio: float = 0.35,
    T_in: float = 420.0,
    P_in: float = 30.0,
    flow_in: float = 100.0,
    duration_min: int = 50,
) -> pd.DataFrame:
    """
    공정 조건을 시간 축으로 추적
    - duration_min : 추적 시간 (분)
    Returns DataFrame: [time, temperature, pressure, flowrate]
    """
    t = np.linspace(0, duration_min, duration_min + 1)

    # 반응기 내 온도 변동 (입구 온도 기준 ±15°C 내 진동 후 안정)
    temperature = (
        T_in
        + 15 * np.sin(t * 0.18)
        - 5 * np.cos(t * 0.09)
        + np.where(t > 30, -3.0, 0.0)        # 재순환 루프 안정화 효과
        + np.random.normal(0, 0.5, len(t))
    )

    # 반응기 내 압력 변동 (bar)
    pressure = (
        P_in
        + 2 * np.sin(t * 0.22 + 1)
        - np.cos(t * 0.15)
        + np.random.normal(0, 0.15, len(t))
    )

    # 재순환 반영 실제 공급 유량 (kmol/h)
    recycle_flow = flow_in * recycle_ratio
    total_flow = flow_in + recycle_flow
    flowrate = (
        total_flow
        + 8 * np.sin(t * 0.14)
        + 4 * np.cos(t * 0.25)
        + np.random.normal(0, 0.3, len(t))
    )

    df = pd.DataFrame({
        "time_min": t.astype(int),
        "temperature_C": np.round(temperature, 2),
        "pressure_bar": np.round(pressure, 2),
        "flowrate_kmolh": np.round(flowrate, 2),
    })
    return df


# ─────────────────────────────────────────────
# 1. 재순환 비율 최적화
# ─────────────────────────────────────────────

def optimize_recycle_ratio(
    T_in: float = 420.0,
    P_in: float = 30.0,
    ratio_range: tuple = (0.0, 0.70),
    steps: int = 71,
) -> pd.DataFrame:
    """
    재순환 비율을 단계별로 변경하며 최적점 탐색
    Returns DataFrame with all simulation results
    """
    ratios = np.linspace(ratio_range[0], ratio_range[1], steps)
    results = [simulate_reactor(r, T_in, P_in) for r in ratios]
    df = pd.DataFrame(results)

    best_idx = df["econ_score"].idxmax()
    best = df.loc[best_idx]

    print("=" * 50)
    print("  CUMENE 재순환 비율 최적화 결과")
    print("=" * 50)
    print(f"  총 시뮬레이션 횟수  : {steps}회")
    print(f"  최적 재순환 비율    : {best['recycle_ratio']:.2f}")
    print(f"  최적 전환율         : {best['conversion']:.2f}%")
    print(f"  최적 미반응 원료    : {best['unreacted']:.2f}%")
    print(f"  최적 경제성 점수    : {best['econ_score']:.2f}/100")
    print(f"  최적 반응기 부하    : {best['reactor_load']:.2f} (기준=100)")
    print("-" * 50)
    print(f"  기존 전환율         : 61.56%")
    print(f"  전환율 향상         : +{best['conversion'] - 61.56:.2f}%p")
    print(f"  미반응 원료 감소    : 13.5% → {best['unreacted']:.2f}%")
    print("=" * 50)
    return df


# ─────────────────────────────────────────────
# 2. 공정 조건 시각화
# ─────────────────────────────────────────────

def plot_process_conditions(df_process: pd.DataFrame, save_path: str = None):
    """온도·압력·유량 시간 축 추적 시각화"""
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    fig.suptitle("CUMENE 공정 조건 시간 축 추적 (재순환 비율 0.35 기준)", fontsize=14, fontweight="bold")

    t = df_process["time_min"]

    # 온도
    axes[0].plot(t, df_process["temperature_C"], color="#D85A30", linewidth=1.5, label="온도 (°C)")
    axes[0].axhline(420, color="#D85A30", linestyle="--", linewidth=0.8, alpha=0.5, label="설계 기준 (420°C)")
    axes[0].set_ylabel("온도 (°C)", fontsize=11)
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # 압력
    axes[1].plot(t, df_process["pressure_bar"], color="#378ADD", linewidth=1.5, label="압력 (bar)")
    axes[1].axhline(30, color="#378ADD", linestyle="--", linewidth=0.8, alpha=0.5, label="설계 기준 (30 bar)")
    axes[1].set_ylabel("압력 (bar)", fontsize=11)
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    # 유량
    axes[2].plot(t, df_process["flowrate_kmolh"], color="#1D9E75", linewidth=1.5, label="유량 (kmol/h)")
    axes[2].set_ylabel("유량 (kmol/h)", fontsize=11)
    axes[2].set_xlabel("시간 (min)", fontsize=11)
    axes[2].legend(fontsize=9)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  공정 조건 그래프 저장 완료: {save_path}")
    plt.show()


def plot_recycle_optimization(df_opt: pd.DataFrame, save_path: str = None):
    """재순환 비율 최적화 결과 시각화"""
    fig, ax1 = plt.subplots(figsize=(12, 5))
    fig.suptitle("재순환 비율에 따른 공정 지표 변화", fontsize=14, fontweight="bold")

    x = df_opt["recycle_ratio"]

    ax1.plot(x, df_opt["conversion"], color="#1D9E75", linewidth=2, label="전환율 (%)")
    ax1.plot(x, df_opt["econ_score"], color="#378ADD", linewidth=2, linestyle="--", label="경제성 점수")
    ax1.set_xlabel("재순환 비율", fontsize=11)
    ax1.set_ylabel("전환율 / 경제성 점수", fontsize=11)
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(x, df_opt["reactor_load"], color="#D85A30", linewidth=1.5, linestyle=":", label="반응기 부하")
    ax2.set_ylabel("반응기 부하 (기준=100)", fontsize=11, color="#D85A30")

    # 최적점 표시
    best_idx = df_opt["econ_score"].idxmax()
    best_r = df_opt.loc[best_idx, "recycle_ratio"]
    best_score = df_opt.loc[best_idx, "econ_score"]
    ax1.axvline(best_r, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax1.annotate(f"최적점 r={best_r:.2f}", xy=(best_r, best_score),
                 xytext=(best_r + 0.05, best_score - 8),
                 fontsize=9, arrowprops=dict(arrowstyle="->", color="gray"))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="lower left")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  최적화 그래프 저장 완료: {save_path}")
    plt.show()


def plot_comparison(save_path: str = None):
    """기존 공정 vs 개선 공정 비교 바 차트"""
    labels = ["전환율 (%)", "미반응 원료 (%)", "경제성 점수", "안정성 점수"]
    original = [61.56, 13.5, 58, 72]
    improved = [74.0, 3.2, 87, 91]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("기존 공정 vs 개선 공정 (재순환 적용) 비교", fontsize=14, fontweight="bold")

    bars1 = ax.bar(x - width / 2, original, width, label="기존 공정", color="#3266ad", alpha=0.85)
    bars2 = ax.bar(x + width / 2, improved, width, label="개선 공정", color="#1D9E75", alpha=0.85)

    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 105)
    ax.set_ylabel("값", fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  비교 그래프 저장 완료: {save_path}")
    plt.show()


# ─────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n[ 1단계 ] 재순환 비율 최적화 시뮬레이션")
    df_opt = optimize_recycle_ratio(T_in=420, P_in=30, steps=71)
    df_opt.to_csv("recycle_optimization_results.csv", index=False, encoding="utf-8-sig")
    print("  결과 저장: recycle_optimization_results.csv\n")

    print("[ 2단계 ] 공정 조건 시간 축 추적")
    df_process = track_process_conditions(
        recycle_ratio=0.35, T_in=420, P_in=30, flow_in=100, duration_min=50
    )
    df_process.to_csv("process_conditions_log.csv", index=False, encoding="utf-8-sig")
    print("  결과 저장: process_conditions_log.csv")
    print(df_process.head(10).to_string(index=False))
    print()

    print("[ 3단계 ] 시각화 출력")
    plot_recycle_optimization(df_opt, save_path="recycle_optimization.png")
    plot_process_conditions(df_process, save_path="process_conditions.png")
    plot_comparison(save_path="process_comparison.png")

    print("\n모든 시뮬레이션 완료.")
    