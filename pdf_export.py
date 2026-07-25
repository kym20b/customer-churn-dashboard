"""개선 제안 리포트를 PDF로 변환한다.

차트(Plotly)는 kaleido로 정적 이미지화하면 로컬 테스트에서 크롬 프로세스가 여럿
떠서 멈추는 현상이 있어(배포 환경에서는 훨씬 더 위험), 이 PDF는 차트 이미지 없이
텍스트·표 중심으로만 구성한다. 한글 렌더링을 위해 fonts/ 폴더에 번들된
Noto Sans KR(OFL 라이선스, 흔히 쓰이는 한글 서브셋으로 축소) 서브셋 폰트를 쓴다.
"""
import os
import re

from fpdf import FPDF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR = os.path.join(BASE_DIR, "fonts", "NotoSansKR-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "fonts", "NotoSansKR-Bold.ttf")

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
TABLE_RE = re.compile(r"(\|.+\|(?:\n\|.+\|)+)")
SECTION_RE = re.compile(r"^## (\d+)\.\s+(.+)$", re.MULTILINE)
SUBSECTION_RE = re.compile(r"^### (4-\d)\.\s+(.+?)\s*\(confidence:\s*(.+?)\)\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)

INK = (15, 23, 42)
MUTED = (100, 116, 139)
ACCENT = (59, 130, 246)
RULE = (226, 232, 240)


SUBHEADING_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)


def _clean(text: str) -> str:
    """PDF 본문용: 위키링크는 괄호 없는 일반 텍스트로, **볼드**는 그대로 남겨
    fpdf2의 markdown=True가 처리하도록 한다. fpdf2의 markdown 지원은 굵게/기울임뿐이라
    '### 소제목'류는 그대로 두면 문자 그대로 노출되므로 굵게 처리로 대체한다."""
    text = SUBHEADING_RE.sub(r"**\1**", text)
    return WIKILINK_RE.sub(r"\1", text).strip()


def _split_sections(body: str) -> dict:
    matches = list(SECTION_RE.finditer(body))
    sections = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[m.group(1)] = (m.group(2).strip(), body[start:end].strip())
    return sections


def _parse_table(md_text: str) -> list[list[str]]:
    lines = [l for l in md_text.strip().split("\n") if l.strip().startswith("|")]
    header = [_clean(cell.strip()).replace("**", "") for cell in lines[0].strip("|").split("|")]
    rows = [header]
    for line in lines[2:]:
        cells = [_clean(cell.strip()).replace("**", "") for cell in line.strip("|").split("|")]
        if len(cells) == len(header):
            rows.append(cells)
    return rows


class ReportPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("NotoKR", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f"{self.page_no()}", align="C")


def _add_heading(pdf: ReportPDF, text: str, size: int = 15, space_before: int = 6):
    pdf.ln(space_before)
    pdf.set_font("NotoKR", "B", size)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, size * 0.6, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.6)
    y = pdf.get_y() + 1
    pdf.line(pdf.l_margin, y, pdf.l_margin + 30, y)
    pdf.set_draw_color(*INK)  # 표 테두리 등 이후 그려지는 선은 다시 검은색으로
    pdf.set_line_width(0.2)
    pdf.ln(4)


def _add_body(pdf: ReportPDF, text: str, size: int = 10.5):
    pdf.set_font("NotoKR", "", size)
    pdf.set_text_color(*INK)
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        pdf.multi_cell(0, size * 0.62, _clean(para), markdown=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)


def _add_table(pdf: ReportPDF, rows: list[list[str]], center_cols: set[int] = frozenset(), col_widths=None):
    pdf.set_font("NotoKR", "", 9)
    pdf.set_draw_color(*INK)  # 표 테두리는 항상 검은색
    align_map = {i: "CENTER" for i in center_cols}
    with pdf.table(
        rows,
        text_align=[align_map.get(i, "LEFT") for i in range(len(rows[0]))],
        col_widths=col_widths,
        line_height=5,
    ):
        pass
    pdf.ln(2)


def build_report_pdf(raw_markdown: str) -> bytes:
    """리포트 마크다운 전체를 받아 PDF 바이트를 반환한다."""
    fm = FRONTMATTER_RE.match(raw_markdown)
    body = raw_markdown[fm.end():] if fm else raw_markdown

    title_match = re.search(r"^# (.+)$", body, re.MULTILINE)
    title = title_match.group(1) if title_match else "리포트"
    body = body[title_match.end():] if title_match else body

    sections = _split_sections(body)

    pdf = ReportPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("NotoKR", "", FONT_REGULAR)
    pdf.add_font("NotoKR", "B", FONT_BOLD)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()

    # ── 표지 ──
    pdf.set_font("NotoKR", "B", 22)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 12, _clean(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("NotoKR", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 7, "2026-07-24 작성 · confidence 높음 4건 · 중간 1건 · 낮음 1건", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    # ── 1. Executive Summary ──
    _add_heading(pdf, f"1. {sections['1'][0]}")
    items = re.split(r"^\d+\.\s+", sections["1"][1], flags=re.MULTILINE)
    items = [it.strip() for it in items if it.strip()]
    for i, item in enumerate(items, start=1):
        conf_match = re.search(r"\*\*confidence\s+(\S+?)\*\*", item)
        level = conf_match.group(1) if conf_match else ""
        text_only = re.sub(r"\(\*\*confidence\s+\S+?\*\*\)", "", item).strip()
        pdf.set_font("NotoKR", "B", 10.5)
        pdf.set_text_color(*ACCENT)
        pdf.multi_cell(0, 6, f"{i}. (confidence: {level})", new_x="LMARGIN", new_y="NEXT")
        _add_body(pdf, text_only)

    # ── 2. 배경·목적 ──
    _add_heading(pdf, f"2. {sections['2'][0]}")
    _add_body(pdf, sections["2"][1])

    # ── 3. 데이터·방법론 ──
    _add_heading(pdf, f"3. {sections['3'][0]}")
    text3 = sections["3"][1]
    tables3 = TABLE_RE.findall(text3)
    prose3 = TABLE_RE.sub("", text3)
    _add_body(pdf, prose3)
    for tbl in tables3:
        _add_table(pdf, _parse_table(tbl))

    # ── 4. 현황 ──
    _add_heading(pdf, f"4. {sections['4'][0]}")
    section4 = sections["4"][1]
    sub_matches = list(SUBSECTION_RE.finditer(section4))
    for i, m in enumerate(sub_matches):
        sub_id, sub_title, sub_conf = m.group(1), m.group(2), m.group(3)
        start = m.end()
        end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(section4)
        sub_body = section4[start:end].strip()
        pdf.set_font("NotoKR", "B", 12)
        pdf.set_text_color(*INK)
        pdf.multi_cell(0, 7, f"{sub_id}. {sub_title}  ·  confidence: {sub_conf}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        _add_body(pdf, sub_body)

    # ── 5. 원인 분석 ──
    _add_heading(pdf, f"5. {sections['5'][0]}")
    section5 = sections["5"][1]
    for para in [p.strip() for p in section5.split("\n\n") if p.strip()]:
        _add_body(pdf, para)

    # ── 6. 개선 제안 우선순위 ──
    _add_heading(pdf, f"6. {sections['6'][0]}")
    section6 = sections["6"][1]
    tables6 = TABLE_RE.findall(section6)
    prose6 = TABLE_RE.sub("\n[[TABLE]]\n", section6, count=2)
    prose_parts = prose6.split("[[TABLE]]")
    _add_body(pdf, prose_parts[0])
    if tables6:
        rows = _parse_table(tables6[0])
        header = rows[0]
        impact_idx = header.index("이탈 감소 임팩트")
        difficulty_idx = header.index("실행 난이도")
        note_idx = header.index("비고") if "비고" in header else None
        new_header = ["순위", "후보", "임팩트", "임팩트 근거", "난이도", "난이도 근거"]
        new_rows = [new_header]
        for row in rows[1:]:
            impact_level = re.match(r"(상|중|하)", row[impact_idx])
            difficulty_level = re.match(r"(상|중|하)", row[difficulty_idx])
            new_rows.append(
                [
                    row[0],
                    row[1],
                    impact_level.group(1) if impact_level else "",
                    row[impact_idx],
                    difficulty_level.group(1) if difficulty_level else "",
                    row[difficulty_idx],
                ]
            )
        _add_table(pdf, new_rows, center_cols={0, 2, 4}, col_widths=(8, 24, 8, 26, 8, 26))
        pdf.set_font("NotoKR", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(
            0,
            5,
            "※ 비고 요약: 1번은 임팩트·난이도 조합이 가장 좋은 퀵윈이다. 2번은 표 안에서 유일하게 채널 "
            "문제가 아니면서도 실측 이탈률에 근거한다. 3번은 근본 해결이 아니라 우회책이라 효과가 제한적일 "
            "수 있고, 4번(이메일 채널 개선)과 병행할 수 있다. 5번은 confidence가 중간 수준이라 파일럿으로 "
            "먼저 효과를 확인하는 것을 권장한다. 6·7번은 임팩트가 가장 크지만 각각 엔지니어링 부담과 외부"
            "(통신사 간 프로세스) 의존성 때문에 난이도가 높아 우선순위가 뒤로 밀렸다.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(2)
    if len(prose_parts) > 1:
        _add_body(pdf, prose_parts[1])
    if len(tables6) > 1:
        _add_table(pdf, _parse_table(tables6[1]), center_cols={0})
    if len(prose_parts) > 2:
        _add_body(pdf, prose_parts[2])

    # ── 7. 한계 ──
    _add_heading(pdf, f"7. {sections['7'][0]}")
    _add_body(pdf, sections["7"][1])

    # ── 8. 부록 ──
    _add_heading(pdf, f"8. {sections['8'][0]}")
    text8 = sections["8"][1]
    tables8 = TABLE_RE.findall(text8)
    prose8 = TABLE_RE.sub("", text8)
    _add_body(pdf, prose8)
    for tbl in tables8:
        _add_table(pdf, _parse_table(tbl))

    return bytes(pdf.output())
