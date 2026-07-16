"""전체 고객 이탈율 vs 해지관련 부정 VOC 이력 고객 이탈율 비교 막대그래프"""
import os

import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# 색상 (dataviz 스킬 팔레트: 중립 회색 + critical 빨강)
COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"
COLOR_MUTED = "#898781"
COLOR_GRID = "#e1e0d9"
COLOR_TEXT_PRIMARY = "#0b0b0b"
COLOR_TEXT_SECONDARY = "#52514e"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "charts", "output")

voc = pd.read_csv(os.path.join(DATA_DIR, "data_voc.csv"))
customers = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"))

# 해지관련 + 부정 VOC를 남긴 고객(중복 제거)
target_ids = voc.loc[
    (voc["category"] == "해지관련") & (voc["sentiment"] == "부정"), "customer_id"
].unique()

target_customers = customers[customers["customer_id"].isin(target_ids)]
target_rate = (target_customers["churn_yn"] == "Y").mean() * 100

overall_rate = (customers["churn_yn"] == "Y").mean() * 100

labels = ["전체 고객", "해지관련 부정 VOC 이력 있음"]
rates = [overall_rate, target_rate]
colors = [COLOR_NEUTRAL, COLOR_CRITICAL]

fig, ax = plt.subplots(figsize=(6, 5.5))

bar_width = 0.5
x = range(len(labels))
bars = ax.bar(x, rates, width=bar_width, color=colors, zorder=3)

for bar, rate in zip(bars, rates):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.6,
        f"{rate:.1f}%",
        ha="center",
        va="bottom",
        fontsize=14,
        fontweight="bold",
        color=COLOR_TEXT_PRIMARY,
    )

ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontsize=12, color=COLOR_TEXT_PRIMARY)
ax.set_ylabel("이탈율 (%)", fontsize=11, color=COLOR_TEXT_SECONDARY)
ax.set_title("전체 고객 vs 해지관련 부정 VOC 이력 고객 이탈율 비교", fontsize=14, pad=16, color=COLOR_TEXT_PRIMARY)

ax.set_ylim(0, max(rates) * 1.25)
ax.yaxis.grid(True, color=COLOR_GRID, linewidth=1, zorder=0)
ax.set_axisbelow(True)

for spine in ["top", "right", "left"]:
    ax.spines[spine].set_visible(False)
ax.spines["bottom"].set_color(COLOR_MUTED)
ax.tick_params(axis="y", colors=COLOR_TEXT_SECONDARY, labelsize=10)
ax.tick_params(axis="x", length=0)

plt.tight_layout()

os.makedirs(OUTPUT_DIR, exist_ok=True)
output_path = os.path.join(OUTPUT_DIR, "01_matplotlib_voc이탈비교.png")
plt.savefig(output_path, dpi=150)
plt.close()

print(f"전체 고객 이탈율: {overall_rate:.2f}%")
print(f"해지관련 부정 VOC 이력 고객 이탈율: {target_rate:.2f}%")
print(f"저장 완료: {output_path}")
