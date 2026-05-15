## 배경 및 문제 정의

기존 공정에서 단순 촉매 교체 시 단기 생산성은 향상되지만, 반응기 부하 증가로 장기적인 안정성과 경제성이 저하되는 문제가 있었습니다.  
Aspen Plus로 기존 공정을 모사한 결과, 이론적으로 70% 이상 달성 가능한 전환율이 실제로는 61.56%에 머물렀고 미반응 원료가 약 10~15% 배출되고 있음을 확인했습니다.  
단순 촉매 교체 대신 **미반응 원료를 반응기로 재투입하는 재순환 공정**을 설계했습니다.

---

## Aspen Plus 실측 수치

### Stage 1 — 기존 공정

| Stream | Cumene (kmol/hr) | Benzene (kmol/hr) | Propylene (kmol/hr) |
|--------|-----------------|-------------------|---------------------|
| CUMENE | 92.1131 | 0.0469874 | 0 |
| FT-VAP | 0.632861 | 6.8541 | 5.69219 |
| B2 | 0.00181414 | 2.05536e-13 | 0 |

CUMENE Stream 상태: **Liquid, 151.807°C, 1 bar**

전환율 계산:

$$X_i = \frac{(B_{feed} - B_{out}) + (P_{feed} - P_{out})}{B_{feed} + P_{feed}} = \frac{(205.75 - 111.159) + (104.5 - 8.09456)}{205.75 + 104.5} \approx 61.56\%$$

### Stage 2 — 재순환 공정

| Stream | Cumene (kmol/hr) | Benzene (kmol/hr) | Propylene (kmol/hr) |
|--------|-----------------|-------------------|---------------------|
| CUMENE | 93.9971 | 0.0480637 | 0 |
| FT-VAP | 0.754708 | 7.31583 | 5.58192 |
| B2 | 0.00208172 | 2.37565e-13 | 0 |

전환율:

$$X_i = \frac{(199.324 - 102.487) + (106.543 - 7.62462)}{199.324 + 106.543} \approx 64.00\%$$

### Stage 2 기술경제성 분석

| 항목 | 값 |
|------|----|
| Total Capital Cost | USD 5,527,980 |
| Total Operating Cost | USD 138,344,000 / year |
| Payback Period | 9.34861 year |

### 민감도 분석

큐멘 생산량이 최대가 되는 최적 벤젠 공급량: **103.105 kmol/hr**

---

## 주요 기능

### 1. 전환율 계산 (`calc_conversion`, `print_conversion_summary`)

Aspen Plus 문제풀이 수식을 그대로 구현해 Stage 1, 2 전환율을 계산하고 경제성 수치를 함께 출력합니다.

### 2. 재순환 비율 최적화 (`optimize_recycle_ratio`)

재순환 비율 0.00~0.90 구간을 91단계로 분할해 전환율, 큐멘 생산량, 반응기 부하, 경제성 점수를 계산합니다.  
Stage 1(r=0, 61.56%)과 Stage 2(r≈0.10, 64.00%) 실측값을 보간 기준으로 사용합니다.

```python
df_opt = optimize_recycle_ratio(steps=91)
# → recycle_optimization_results.csv 저장
```

### 3. 공정 조건 시간 축 추적 (`track_process_conditions`)

CUMENE Stream 기준(Liquid, 151.807°C, 1 bar)으로 온도·압력·유량을 시간 축으로 추적합니다.

```python
df_proc = track_process_conditions(
    T_in=151.807, P_in=1.0,
    flow_in=93.9971, recycle_ratio=0.10, duration_min=50
)
# → process_conditions_log.csv 저장
```

### 4. 민감도 분석 (`sensitivity_benzene_feed`)

벤젠 공급량 변화에 따른 큐멘 생산량 변화를 분석합니다. 최적점 103.105 kmol/hr를 기준으로 좌우 수확 체감 특성을 반영합니다.

```python
df_sens = sensitivity_benzene_feed(feed_range=(80.0, 130.0), steps=51)
# → sensitivity_analysis.csv 저장
```

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

실행 순서:

```
[ 1단계 ] 전환율 계산 및 경제성 요약
[ 2단계 ] 재순환 비율 최적화 (91회 시뮬레이션)
[ 3단계 ] 공정 조건 시간 축 추적 (Stage 2 기준)
[ 4단계 ] 민감도 분석 (벤젠 공급량 vs 큐멘 생산량)
[ 5단계 ] 시각화 출력
```

### 출력 파일

| 파일명 | 설명 |
|--------|------|
| `recycle_optimization_results.csv` | 재순환 비율별 전체 시뮬레이션 결과 |
| `process_conditions_log.csv` | 시간 축 온도·압력·유량 로그 |
| `sensitivity_analysis.csv` | 벤젠 공급량별 큐멘 생산량 분석 결과 |
| `recycle_optimization.png` | 재순환 비율 최적화 곡선 (Stage 1·2 실측점 표시) |
| `process_conditions.png` | 공정 조건 시간 추적 그래프 |
| `stream_comparison.png` | Stage 1 vs 2 스트림 몰유량 비교 바 차트 |
| `sensitivity_analysis.png` | 벤젠 공급량 vs 큐멘 생산량 민감도 곡선 |

---

## 주요 결과

| 항목 | Stage 1 (기존) | Stage 2 (재순환) | 변화 |
|------|---------------|-----------------|------|
| 전환율 | 61.56% | 64.00% | **+2.44%p** |
| 큐멘 생산량 | 92.1131 kmol/hr | 93.9971 kmol/hr | **+1.884 kmol/hr** |
| 미반응 벤젠 (FT-VAP) | 6.8541 kmol/hr | 7.31583 kmol/hr | 재순환 흐름 반영 |

재순환 비율이 0.45를 초과하면 반응기 부하가 급증해 경제성이 역전되는 것을 시뮬레이션으로 확인했습니다.

---

## 프로젝트 구조

```
.
├── cumene_process_simulation.py     # 메인 시뮬레이션 코드
├── README.md                        # 이 문서
├── recycle_optimization_results.csv
├── process_conditions_log.csv
├── sensitivity_analysis.csv
├── recycle_optimization.png
├── process_conditions.png
├── stream_comparison.png
└── sensitivity_analysis.png
```

---

## 기술 스택

- Python 3.9+
- NumPy — 수치 계산 및 배열 연산
- Pandas — 결과 데이터 관리 및 CSV 입출력
- Matplotlib — 공정 조건 및 최적화 결과 시각화
- Aspen Plus — 기존 공정 P&ID 모사 (별도 라이선스)
