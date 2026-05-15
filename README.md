# CUMENE_Process_Simulation

Aspen Plus 모사 결과를 기반으로 재순환 공정을 설계하고,  
Python으로 최적 재순환 비율 탐색 및 공정 조건을 분석한 프로젝트입니다.

---

## 배경 및 문제 정의

기존 CUMENE 생산 공정에서 단순 촉매 교체 시 단기 생산성은 향상되지만,  
반응기 부하 증가로 장기적인 안정성과 경제성이 저하되는 문제가 있었습니다.

Aspen Plus로 기존 공정 P&ID를 모사한 결과:

| 항목 | 기존 공정 | 개선 목표 |
|------|-----------|-----------|
| 반응기 전환율 | 61.56% | 70% 이상 |
| 미반응 원료 배출 | 약 10~15% | 최소화 |
| 개선 방향 | 촉매 교체 | **재순환 공정 설계** |

---

## 개선 접근법

미반응 원료를 다시 반응기로 재투입하는 **재순환(Recycle) 공정**을 설계했습니다.  
단, 재순환 비율이 과도하면 반응기 부하가 급증하여 오히려 경제성이 저하됩니다.  
수십 회의 반복 시뮬레이션을 통해 최적 재순환 비율을 정량적으로 탐색했습니다.

---

## 주요 기능

### 1. 재순환 비율 최적화 (`optimize_recycle_ratio`)
- 재순환 비율 0.00 ~ 0.70 구간을 71단계로 분할하여 전수 탐색
- 각 단계마다 전환율, 미반응 원료, 반응기 부하, 경제성 점수 계산
- 최적점 자동 출력 및 결과 CSV 저장

```python
df_opt = optimize_recycle_ratio(T_in=420, P_in=30, steps=71)
# → recycle_optimization_results.csv 저장
```

### 2. 공정 조건 시간 축 추적 (`track_process_conditions`)
- 온도(°C), 압력(bar), 유량(kmol/h)을 시간 축으로 추적
- 재순환 루프 안정화 효과 및 공정 변동 모사
- 결과 DataFrame 반환 및 CSV 저장

```python
df_process = track_process_conditions(
    recycle_ratio=0.35, T_in=420, P_in=30, flow_in=100, duration_min=50
)
# → process_conditions_log.csv 저장
```

### 3. 결과 분석 및 시각화
- `plot_recycle_optimization()` — 재순환 비율 vs 전환율·경제성·부하 곡선
- `plot_process_conditions()` — 온도·압력·유량 시간 추적 라인 차트 (3단 subplot)
- `plot_comparison()` — 기존 vs 개선 공정 4개 지표 비교 바 차트

---

## 사용 방법

### 환경 설치

```bash
pip install numpy pandas matplotlib
```

### 실행

```bash
python cumene_process_simulation.py
```

실행 시 순서대로 3단계가 진행됩니다.

```
[ 1단계 ] 재순환 비율 최적화 시뮬레이션
[ 2단계 ] 공정 조건 시간 축 추적
[ 3단계 ] 시각화 출력
```

### 출력 파일

| 파일명 | 설명 |
|--------|------|
| `recycle_optimization_results.csv` | 재순환 비율별 전체 시뮬레이션 결과 |
| `process_conditions_log.csv` | 시간 축 온도·압력·유량 로그 |
| `recycle_optimization.png` | 재순환 비율 최적화 그래프 |
| `process_conditions.png` | 공정 조건 시간 추적 그래프 |
| `process_comparison.png` | 기존 vs 개선 공정 비교 그래프 |

---

## 주요 결과

| 항목 | 기존 공정 | 개선 공정 | 변화 |
|------|-----------|-----------|------|
| 전환율 | 61.56% | 74.0% | **+12.4%p** |
| 미반응 원료 | 13.5% | 3.2% | **−10.3%p** |
| 경제성 점수 | 58/100 | 87/100 | **+29** |
| 안정성 점수 | 72/100 | 91/100 | **+19** |

최적 재순환 비율: **0.35**  
(재순환 비율 > 0.5 초과 시 반응기 부하 급증으로 경제성 역전 확인)

---

## Aspen Plus 연동 방법

현재 코드는 모사 데이터 기반으로 동작합니다.  
실제 Aspen Plus와 연동하려면 `simulate_reactor()` 내부 계산 로직을 Aspen API 호출로 교체하세요.

```python
def simulate_reactor(recycle_ratio, T_in=420.0, P_in=30.0):
    # 기존 모사 계산 → 아래 API 호출로 교체
    result = aspen_api.run(recycle_ratio=recycle_ratio, T_in=T_in, P_in=P_in)
    return {
        "conversion": result.conversion,
        "unreacted": result.unreacted_fraction,
        "reactor_load": result.load,
        "econ_score": result.economic_score,
    }
```

---

## 프로젝트 구조

```
.
├── cumene_process_simulation.py   # 메인 시뮬레이션 코드
├── README.md                      # 이 문서
├── recycle_optimization_results.csv
├── process_conditions_log.csv
├── recycle_optimization.png
├── process_conditions.png
└── process_comparison.png
```

---

## 기술 스택

- Python 3.9+
- NumPy — 수치 계산 및 배열 연산
- Pandas — 결과 데이터 관리 및 CSV 입출력
- Matplotlib — 공정 조건 및 최적화 결과 시각화
- Aspen Plus — 기존 공정 P&ID 모사 (별도 라이선스)
