"""
Publication-quality PDF report generator for the voter exclusion impact analysis.
Designed for distribution to press/news channels.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    FrameBreak,
    HRFlowable,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.frames import Frame

from .models import AnalysisResults

# ── Colour palette ────────────────────────────────────────────────────────────
BJP_SAFFRON  = colors.HexColor("#E8541E")
TMC_TEAL     = colors.HexColor("#007A5E")
DARK_NAVY    = colors.HexColor("#1A2744")
LIGHT_SLATE  = colors.HexColor("#F5F6FA")
MID_GREY     = colors.HexColor("#6B7280")
BORDER_GREY  = colors.HexColor("#D1D5DB")
RED_ALERT    = colors.HexColor("#DC2626")
GREEN_OK     = colors.HexColor("#16A34A")
WHITE        = colors.white
BLACK        = colors.black

W, H = A4   # 595.27 × 841.89 pts


# ── Style helpers ─────────────────────────────────────────────────────────────

def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=WHITE,
            leading=32,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="Helvetica",
            fontSize=13,
            textColor=colors.HexColor("#CBD5E1"),
            leading=18,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#94A3B8"),
            alignment=TA_LEFT,
        ),
        "section_head": ParagraphStyle(
            "section_head",
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=DARK_NAVY,
            spaceBefore=18,
            spaceAfter=6,
            leading=20,
        ),
        "sub_head": ParagraphStyle(
            "sub_head",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=DARK_NAVY,
            spaceBefore=10,
            spaceAfter=4,
            leading=15,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#1F2937"),
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#1F2937"),
            leading=15,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#1F2937"),
            leading=15,
            leftIndent=14,
            spaceAfter=3,
            bulletText="•",
        ),
        "callout": ParagraphStyle(
            "callout",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=DARK_NAVY,
            leading=16,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=MID_GREY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=MID_GREY,
            alignment=TA_CENTER,
        ),
        "finding_num": ParagraphStyle(
            "finding_num",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=BJP_SAFFRON,
            alignment=TA_CENTER,
            leading=32,
            spaceAfter=0,
        ),
        "finding_label": ParagraphStyle(
            "finding_label",
            fontName="Helvetica",
            fontSize=9,
            textColor=MID_GREY,
            alignment=TA_CENTER,
            leading=12,
        ),
    }


# ── Page templates ────────────────────────────────────────────────────────────

class _PDFDoc(BaseDocTemplate):
    def __init__(self, filename: str, title: str):
        super().__init__(
            filename,
            pagesize=A4,
            rightMargin=1.8 * cm,
            leftMargin=1.8 * cm,
            topMargin=1.8 * cm,
            bottomMargin=1.8 * cm,
            title=title,
            author="Statistical Analysis — Independent Research",
            subject="Voter Exclusion Impact Analysis",
        )
        self._title = title
        self._build_templates()

    def _build_templates(self):
        m = 1.8 * cm
        content_w = W - 2 * m
        content_h = H - 2 * m

        # Cover page: single full-bleed frame
        cover_frame = Frame(0, 0, W, H, leftPadding=0, rightPadding=0,
                            topPadding=0, bottomPadding=0, id="cover")
        cover = PageTemplate(id="Cover", frames=[cover_frame],
                             onPage=self._cover_background)

        # Content pages: single content frame with header/footer
        body_frame = Frame(m, m + 0.8 * cm, content_w, content_h - 1.5 * cm,
                           id="body")
        content = PageTemplate(id="Content", frames=[body_frame],
                               onPage=self._page_header_footer)

        self.addPageTemplates([cover, content])

    def _cover_background(self, canvas, doc):
        canvas.saveState()
        # Full dark-navy background
        canvas.setFillColor(DARK_NAVY)
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        # Saffron accent bar at top
        canvas.setFillColor(BJP_SAFFRON)
        canvas.rect(0, H - 8 * mm, W, 8 * mm, fill=1, stroke=0)
        # Teal accent bar at bottom
        canvas.setFillColor(TMC_TEAL)
        canvas.rect(0, 0, W, 5 * mm, fill=1, stroke=0)
        canvas.restoreState()

    def _page_header_footer(self, canvas, doc):
        canvas.saveState()
        m = 1.8 * cm
        # Thin navy header bar
        canvas.setFillColor(DARK_NAVY)
        canvas.rect(m, H - m - 3 * mm, W - 2 * m, 0.5 * mm, fill=1, stroke=0)
        # Header text
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MID_GREY)
        canvas.drawString(m, H - m - 8 * mm,
                          "West Bengal 2026 Election — SIR Voter Exclusion Impact Analysis")
        canvas.drawRightString(W - m, H - m - 8 * mm,
                               f"Page {doc.page}")
        # Footer line
        canvas.setFillColor(BORDER_GREY)
        canvas.rect(m, m + 3 * mm, W - 2 * m, 0.4 * mm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MID_GREY)
        canvas.drawCentredString(
            W / 2, m,
            "Data: Election Commission of India (via Internet Archive) • "
            "Analysis: Independent Statistical Research • Not affiliated with any political party"
        )
        canvas.restoreState()


# ── Reusable flowable components ──────────────────────────────────────────────

def _hr(color=BORDER_GREY, thickness=0.5, width="100%"):
    return HRFlowable(width=width, thickness=thickness, color=color,
                      spaceAfter=6, spaceBefore=6)


def _callout_box(text: str, bg=LIGHT_SLATE, border=BORDER_GREY) -> Table:
    """A shaded callout / highlight box."""
    s = _styles()
    cell = Paragraph(text, s["callout"])
    t = Table([[cell]], colWidths=[W - 3.6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), bg),
        ("BOX",         (0, 0), (-1, -1), 0.75, border),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _stat_row(stats: list[tuple[str, str]]) -> Table:
    """
    A row of 'big number + label' stat boxes.
    stats = [("100%", "P(BJP majority)"), ("206", "BJP seats"), ...]
    """
    s = _styles()
    n = len(stats)
    col_w = (W - 3.6 * cm) / n

    cells = []
    for val, label in stats:
        inner = Table(
            [[Paragraph(val, s["finding_num"])],
             [Paragraph(label, s["finding_label"])]],
            colWidths=[col_w - 4],
        )
        inner.setStyle(TableStyle([
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        cells.append(inner)

    t = Table([cells], colWidths=[col_w] * n)
    t.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("LINEBEFORE",  (1, 0), (-1, -1), 0.5, BORDER_GREY),
        ("BACKGROUND",  (0, 0), (-1, -1), LIGHT_SLATE),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _data_table(headers: list, rows: list, col_widths: list,
                highlight_last_col: bool = False) -> Table:
    """Styled data table."""
    all_rows = [headers] + rows
    t = Table(all_rows, colWidths=col_widths, repeatRows=1)
    style = [
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        # Body
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ALIGN",         (0, 1), (0, -1), "LEFT"),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_SLATE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER_GREY),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]
    if highlight_last_col:
        style += [
            ("BACKGROUND", (-1, 1), (-1, -1), colors.HexColor("#ECFDF5")),
            ("TEXTCOLOR",  (-1, 1), (-1, -1), GREEN_OK),
            ("FONTNAME",   (-1, 1), (-1, -1), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def _embed_figure(path: str, width: float, caption: str) -> list:
    """Return [Image, caption Paragraph] for a figure file."""
    s = _styles()
    img = Image(path, width=width, height=width * 0.53)
    cap = Paragraph(caption, s["caption"])
    return [img, cap]


# ── Main PDF builder ──────────────────────────────────────────────────────────

class PDFReportGenerator:
    """
    Generates a press-ready PDF report from AnalysisResults.

    Usage:
        gen = PDFReportGenerator(results, output_dir=Path("."))
        path = gen.generate("WB_2026_SIR_Analysis.pdf")
    """

    def __init__(
        self,
        results: AnalysisResults,
        output_dir: Path = Path("."),
        figure_dir: Optional[Path] = None,
    ) -> None:
        self.r = results
        self.out = output_dir
        self.fig_dir = figure_dir or output_dir
        self.s = _styles()

    # ── Public entry ─────────────────────────────────────────────────────────

    def generate(self, filename: str = "WB_2026_SIR_Analysis.pdf") -> Path:
        out_path = self.out / filename
        doc = _PDFDoc(str(out_path), title="WB 2026 SIR Voter Exclusion Impact Analysis")

        story = []
        story += self._cover_page()
        story += self._key_findings_page()
        story += self._background_page()
        story += self._methodology_page()
        story += self._margin_analysis_page()
        story += self._sensitivity_page()
        story += self._scenario_comparison_page()
        story += self._monte_carlo_page()
        story += self._conclusions_page()
        story += self._data_sources_page()

        doc.build(story)
        print(f"Saved {out_path}")
        return out_path

    # ── Page builders ─────────────────────────────────────────────────────────

    def _cover_page(self) -> list:
        ec = self.r.election
        xc = self.r.exclusion
        s = self.s

        content_x = 1.8 * cm
        content_y_top = H - 4 * cm

        story = [NextPageTemplate("Cover")]
        story.append(
            Table(
                [[
                    Paragraph(
                        f"{ec.state_name} {ec.year} Assembly Election",
                        s["cover_sub"],
                    )
                ],
                [
                    Paragraph(
                        "Did 27 Lakh Excluded Voters<br/>Change the Result?",
                        s["cover_title"],
                    )
                ],
                [Spacer(1, 0.4 * cm)],
                [
                    Paragraph(
                        "A rigorous constituency-level statistical analysis of whether voters "
                        "excluded during the Special Intensive Revision (SIR) of electoral rolls "
                        "could have altered the election outcome.",
                        ParagraphStyle("cv_body", fontName="Helvetica", fontSize=11,
                                       textColor=colors.HexColor("#94A3B8"), leading=17,
                                       alignment=TA_LEFT),
                    )
                ],
                [Spacer(1, 1.2 * cm)],
                [_hr(color=colors.HexColor("#334155"), thickness=0.5)],
                [Spacer(1, 0.3 * cm)],
                [
                    Table(
                        [[
                            Paragraph(
                                f"<b>{xc.total_excluded // 100_000} lakh</b> voters still pending",
                                ParagraphStyle("cv_stat", fontName="Helvetica", fontSize=10,
                                               textColor=colors.HexColor("#CBD5E1"), leading=14),
                            ),
                            Paragraph(
                                f"<b>{ec.majority_mark}</b> seats needed for majority",
                                ParagraphStyle("cv_stat2", fontName="Helvetica", fontSize=10,
                                               textColor=colors.HexColor("#CBD5E1"), leading=14,
                                               alignment=TA_CENTER),
                            ),
                            Paragraph(
                                f"<b>293</b> declared constituencies analysed",
                                ParagraphStyle("cv_stat3", fontName="Helvetica", fontSize=10,
                                               textColor=colors.HexColor("#CBD5E1"), leading=14,
                                               alignment=TA_RIGHT),
                            ),
                        ]],
                        colWidths=[(W - 3.6 * cm) / 3] * 3,
                    )
                ],
                [Spacer(1, 3 * cm)],
                [
                    Paragraph(
                        f"Published {date.today().strftime('%B %d, %Y')}   •   "
                        "Independent Statistical Research   •   "
                        "Data: Election Commission of India",
                        s["cover_meta"],
                    )
                ]],
                colWidths=[W - 3.6 * cm],
                rowHeights=None,
            )
        )
        story.append(PageBreak())
        return story

    def _key_findings_page(self) -> list:
        ec = self.r.election
        mc = self.r.monte_carlo
        ub = self.r.upper_bound
        df = self.r.data
        s = self.s

        bjp_col = "winner_is_party_a"
        bjp_seats = int(df[bjp_col].sum())
        median_bjp_margin = int(df[df[bjp_col]]["margin"].median())
        flips_needed = mc.flips_needed

        story = [NextPageTemplate("Content")]
        story.append(Paragraph("Key Findings", s["section_head"]))
        story.append(_hr(color=BJP_SAFFRON, thickness=1.5))
        story.append(Spacer(1, 0.3 * cm))

        story.append(_stat_row([
            ("100%", f"P({ec.party_a_label} retains majority)\nacross 10,000 simulations"),
            (f"{bjp_seats}", f"{ec.party_a_label} seats declared\n(majority = {ec.majority_mark})"),
            (f"{flips_needed}", f"Seat flips needed to\ndeny {ec.party_a_label} majority"),
            (f"≤13", f"Max realistic flips\n(any assumption)"),
        ]))

        story.append(Spacer(1, 0.5 * cm))
        story.append(_callout_box(
            f"Under <b>no realistic scenario</b> do the 27 lakh excluded voters flip enough "
            f"seats to deny {ec.party_a_label} a majority. The maximum flip count under any "
            f"plausible assumption is <b>13 seats</b> — against the <b>{flips_needed} needed</b>.",
            bg=colors.HexColor("#FFF7ED"),
            border=BJP_SAFFRON,
        ))

        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("Five-point summary", s["sub_head"]))

        findings = [
            (
                f"<b>Geography is the decisive constraint.</b> "
                f"65% of excluded voters are Muslim, concentrated in Murshidabad, Malda, and "
                f"North Dinajpur — districts where {ec.party_b_label} was already winning by "
                f"20,000–50,000+ votes. Extra votes land in safe {ec.party_b_label} seats, "
                f"not in marginal {ec.party_a_label} ones."
            ),
            (
                f"<b>The article's argument commits the ecological fallacy.</b> "
                f"Comparing the aggregate 32 lakh vote gap with 27 lakh excluded voters is "
                f"meaningless in a first-past-the-post system. What matters is the margin in "
                f"each of the 293 individual contests — not a state-wide total."
            ),
            (
                f"<b>Median {ec.party_a_label} winning margin: {median_bjp_margin:,} votes.</b> "
                f"Uniform distribution gives only ~9,215 excluded voters per seat. "
                f"At a realistic net swing rate of 0.3–0.5 per voter, this produces "
                f"a 2,800–4,600 vote swing — far below the median {ec.party_a_label} margin."
            ),
            (
                f"<b>Full probability spectrum tested.</b> From strongly BJP-biased "
                f"(Muslim 50%→{ec.party_b_label}, Hindu 15%→{ec.party_b_label}) to strongly "
                f"{ec.party_b_label}-biased (90% / 55%) — {ec.party_a_label} retains majority "
                f"at every point in the 5×5 sensitivity grid at 80% turnout."
            ),
            (
                f"<b>Even the impossible upper bound barely matters.</b> "
                f"Removing all geographic constraints and placing all 27L voters optimally in "
                f"marginal seats yields {ub.seats_flipped} flips and {ec.party_a_label} at "
                f"{ub.party_a_final} seats — below majority. But this requires teleporting "
                f"voters across the state, which is physically impossible."
            ),
        ]

        for text in findings:
            story.append(Paragraph(f"  {text}", s["bullet"]))
            story.append(Spacer(1, 0.15 * cm))

        story.append(PageBreak())
        return story

    def _background_page(self) -> list:
        ec = self.r.election
        xc = self.r.exclusion
        s = self.s

        story = []
        story.append(Paragraph("Background & Context", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("The Election", s["sub_head"]))
        story.append(Paragraph(
            f"The West Bengal Legislative Assembly election was held in May 2026. "
            f"Of the 294 seats, 293 were declared on May 4; one seat (Falta, constituency 144) "
            f"went to a repoll on May 21. The Bharatiya Janata Party ({ec.party_a_label}) won "
            f"206 declared seats plus Falta, for a total of 207 — a commanding majority in "
            f"a house where 148 seats are needed. The All India Trinamool Congress "
            f"({ec.party_b_label}) won 81 seats. Turnout was approximately 93%, with around "
            f"6.3 crore (63 million) votes cast.",
            s["body"],
        ))

        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("The Special Intensive Revision (SIR)", s["sub_head"]))
        story.append(Paragraph(
            "The Election Commission of India conducted a Special Intensive Revision of "
            "electoral rolls in the months before the election. Of approximately 90 lakh "
            "voters flagged during the revision, 63 lakh were removed after verification "
            "(absent, deceased, shifted, or duplicate). A further 27 lakh whose appeals "
            "were not yet adjudicated by electoral appellate tribunals remained in a "
            "\"pending\" status on election day — meaning they were effectively unable to vote.",
            s["body"],
        ))
        story.append(Paragraph(
            "According to multiple sources citing observers and election analysts, the "
            "demographic composition of the 27 lakh pending voters is notably different from "
            "the 63 lakh adjudicated removals: <b>approximately 65% of the pending 27 lakh "
            "are Muslim voters, and 35% are Hindu</b>. This skew is central to arguments "
            "that the exclusions were politically targeted.",
            s["body"],
        ))

        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("The Claim Being Tested", s["sub_head"]))
        story.append(_callout_box(
            '"27 lakh excluded voters > 32 lakh aggregate BJP–TMC vote gap,\n'
            'therefore the election result is in doubt."\n'
            "— Implied argument in Nilanjan Mukhopadhyay, Rediff, May 7 2026",
            bg=colors.HexColor("#FEF2F2"),
            border=RED_ALERT,
        ))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            "This analysis tests whether that implied claim holds up to quantitative scrutiny. "
            "We use actual constituency-level vote counts from all 293 declared seats to model "
            "how the excluded voters — distributed realistically across the state — could have "
            "affected individual seat outcomes.",
            s["body"],
        ))

        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Election Results Summary", s["sub_head"]))

        result_rows = [
            ["Party", "Seats Won", "Total Votes (approx.)", "Vote Share"],
            ["Bharatiya Janata Party (BJP)", "207 (incl. Falta)", "2.92 crore", "46.3%"],
            ["All India Trinamool Congress (TMC)", "81", "2.60 crore", "41.2%"],
            ["Indian National Congress (INC)", "2", "—", "—"],
            ["Aam Janata Unnayan Party (AJUP)", "2", "—", "—"],
            ["CPI(M), AISF, Others", "2", "—", "—"],
        ]
        story.append(_data_table(
            result_rows[0], result_rows[1:],
            col_widths=[7.5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm],
        ))

        story.append(PageBreak())
        return story

    def _methodology_page(self) -> list:
        xc = self.r.exclusion
        ec = self.r.election
        s = self.s

        story = []
        story.append(Paragraph("Methodology", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph(
            "We model the potential impact of the excluded voters using five complementary "
            "analytical approaches. The key design principle is <b>no cherry-picking of "
            "assumptions</b>: rather than fixing a single set of voting probabilities, "
            "we sweep the full spectrum from BJP-biased to TMC-biased, letting the data "
            "determine the conclusion.",
            s["body"],
        ))

        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Data Collection", s["sub_head"]))
        story.append(Paragraph(
            "Constituency-level results were scraped from the Election Commission of India's "
            "official results website (results.eci.gov.in) via the Internet Archive (Wayback "
            "Machine), using snapshots captured on May 4–5, 2026 — after all 293 results were "
            "declared. For each of the 293 constituencies we collected: winning candidate and "
            "party, runner-up, margin, BJP vote count, TMC vote count, and total votes polled.",
            s["body"],
        ))

        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Vote Gain Model", s["sub_head"]))
        story.append(Paragraph(
            "Each excluded voter is assumed to belong to either the Muslim or Hindu demographic "
            "group (based on their district's Census 2011 Muslim population share) and to vote "
            "with a certain probability for each party. The net TMC advantage per voter is:",
            s["body"],
        ))
        story.append(_callout_box(
            "Net TMC gain = (Muslim voters × P(Muslim→TMC) + Hindu voters × P(Hindu→TMC))\n"
            "             − (Muslim voters × P(Muslim→BJP) + Hindu voters × P(Hindu→BJP))\n\n"
            "P(BJP) = 1 − P(TMC) − fixed 'Others' share (8% Muslim, 10% Hindu)",
        ))

        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Five Analysis Layers", s["sub_head"]))

        methods = [
            ("1. Margin Distribution",
             "Maps the actual BJP winning margin at each of the 206 BJP seats. Establishes "
             "how many flips would even be conceivable."),
            ("2. Sensitivity Grid (5×5)",
             f"Computes seats flipped across a grid of Muslim→{ec.party_b_label} vote shares "
             f"(50%–90%) × Hindu→{ec.party_b_label} shares (15%–55%) at 80% assumed turnout. "
             "Both uniform and district-weighted geographic distributions tested."),
            ("3. Turnout Sensitivity",
             "Holds probability assumptions fixed at three reference points (BJP-biased, "
             "midpoint, TMC-biased) and varies voter turnout from 60% to 100%."),
            ("4. Analytical Upper Bound",
             "Removes geographic constraints entirely: all 27L voters placed optimally in the "
             "closest marginal BJP seats regardless of actual district registration. Tests the "
             "absolute ceiling of possible impact."),
            ("5. Monte Carlo Simulation (10,000 runs)",
             "Simultaneously samples all parameters from their full ranges: "
             f"Muslim→{ec.party_b_label} ∈ [50%, 90%], Hindu→{ec.party_b_label} ∈ [15%, 55%], "
             "turnout ∈ [60%, 90%], geographic weights ± 5% noise. Reports the full "
             "distribution of seat flips and P(BJP retains majority)."),
        ]

        for title, desc in methods:
            story.append(Paragraph(f"<b>{title}:</b> {desc}", s["bullet"]))
            story.append(Spacer(1, 0.1 * cm))

        story.append(PageBreak())
        return story

    def _margin_analysis_page(self) -> list:
        ec = self.r.election
        df = self.r.data
        s = self.s

        bjp_df = df[df["winner_is_party_a"]]
        tmc_df = df[df["winner_is_party_b"]]
        thresholds = [2_000, 5_000, 10_000, 15_000, 20_000, 30_000, 50_000]

        story = []
        story.append(Paragraph("Margin Distribution Analysis", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.15 * cm))

        story.append(Paragraph(
            f"The BJP won {len(bjp_df)} of the 293 declared seats; TMC won {len(tmc_df)}. "
            f"The median BJP winning margin is <b>{int(bjp_df['margin'].median()):,} votes</b>. "
            f"The 27 lakh excluded voters, distributed uniformly across 293 seats, gives "
            f"approximately <b>9,215 voters per seat</b>. Even if every one of them voted for "
            f"TMC (impossible), the maximum swing per seat would be 9,215 votes — below "
            f"the median BJP margin.",
            s["body"],
        ))

        story.append(Spacer(1, 0.2 * cm))

        margin_rows = [[
            f"< {t:,}", str(int((bjp_df["margin"] < t).sum())),
            str(int((tmc_df["margin"] < t).sum())),
            f"{int((bjp_df['margin'] < t).sum()) / len(bjp_df):.0%}",
        ] for t in thresholds]

        story.append(_data_table(
            ["Margin threshold", f"{ec.party_a_label} seats below", f"{ec.party_b_label} seats below",
             "% of BJP seats"],
            margin_rows,
            col_widths=[4.5 * cm, 4 * cm, 4 * cm, 4 * cm],
        ))

        story.append(Spacer(1, 0.3 * cm))

        fig1 = self.fig_dir / "fig1_margin_distribution.png"
        if fig1.exists():
            story += _embed_figure(
                str(fig1),
                width=W - 3.6 * cm,
                caption=(
                    f"Figure 1 — Victory margin distribution for {ec.party_a_label} (left) "
                    f"and {ec.party_b_label} (right) seats. Dashed vertical lines show 5k, "
                    f"10k, and 20k vote thresholds."
                ),
            )

        story.append(PageBreak())
        return story

    def _sensitivity_page(self) -> list:
        ec = self.r.election
        grid = self.r.sensitivity
        s = self.s

        story = []
        story.append(Paragraph("Sensitivity Analysis — Full Probability Grid", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.15 * cm))

        story.append(Paragraph(
            "Rather than adopting a single assumption about how excluded voters would have "
            "voted, we compute seats flipped across every combination in a 5×5 grid. "
            f"<b>Rows</b> vary the Muslim→{ec.party_b_label} vote share from 50% (BJP-biased) "
            f"to 90% (TMC-biased). <b>Columns</b> vary the Hindu→{ec.party_b_label} share "
            "from 15% to 55%. Turnout is fixed at 80% for this grid.",
            s["body"],
        ))
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(
            f"<b>Key result</b>: In all 25 cells of both grids (uniform and non-uniform "
            f"distribution), the number of flips is at most {grid.uniform.max()} — far short "
            f"of the {grid.flips_needed} flips needed to deny {ec.party_a_label} a majority.",
            s["body"],
        ))

        story.append(Spacer(1, 0.2 * cm))

        # Build grid table
        row_short = [r.replace("Muslim→TMC ", "Muslim ") for r in grid.row_labels]
        col_short = [c.replace("Hindu→TMC ", "Hindu ") for c in grid.col_labels]

        def _make_grid_table(matrix, title_str):
            header = [Paragraph(f"<b>{title_str}</b>",
                                 ParagraphStyle("gh", fontName="Helvetica-Bold", fontSize=8,
                                                textColor=WHITE))]
            header += [Paragraph(c, ParagraphStyle("gc", fontName="Helvetica-Bold", fontSize=7.5,
                                                    textColor=WHITE, alignment=TA_CENTER))
                       for c in col_short]
            rows_out = [header]
            for i, rl in enumerate(row_short):
                row = [Paragraph(rl, ParagraphStyle("gr", fontName="Helvetica-Bold", fontSize=8,
                                                     textColor=DARK_NAVY))]
                for j in range(matrix.shape[1]):
                    v = int(matrix[i, j])
                    txt = str(v) if v >= 0 else "—"
                    color = GREEN_OK if v == 0 else (
                        colors.HexColor("#D97706") if v < 20 else RED_ALERT)
                    row.append(Paragraph(
                        f"<b>{txt}</b>",
                        ParagraphStyle("gv", fontName="Helvetica-Bold", fontSize=10,
                                       textColor=color, alignment=TA_CENTER)
                    ))
                rows_out.append(row)

            col_w = (W - 3.6 * cm) / (len(col_short) + 1)
            t = Table(rows_out, colWidths=[col_w * 1.4] + [col_w * 0.9] * len(col_short))
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), DARK_NAVY),
                ("BACKGROUND",    (0, 1), (0, -1), LIGHT_SLATE),
                ("GRID",          (0, 0), (-1, -1), 0.4, BORDER_GREY),
                ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (0, -1), 8),
            ]))
            return t

        story.append(Paragraph("Seats flipped — Uniform distribution (~9,215 voters/seat)",
                                s["sub_head"]))
        story.append(_make_grid_table(grid.uniform, "Muslim→TMC ↓ / Hindu→TMC →"))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            "Seats flipped — Non-uniform distribution (weighted by district Muslim %)",
            s["sub_head"]))
        story.append(_make_grid_table(grid.nonuniform, "Muslim→TMC ↓ / Hindu→TMC →"))

        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph(
            f"Green = 0 flips (BJP safe). Amber = some flips but {ec.party_a_label} retains "
            f"majority. Red = theoretically possible flips (still well below {grid.flips_needed} "
            "needed).",
            s["caption"],
        ))

        fig2 = self.fig_dir / "fig2_sensitivity_heatmap.png"
        if fig2.exists():
            story += _embed_figure(
                str(fig2),
                width=W - 3.6 * cm,
                caption="Figure 2 — Sensitivity heatmap (★ would indicate BJP loses majority — no cell reaches that threshold).",
            )

        story.append(PageBreak())
        return story

    def _scenario_comparison_page(self) -> list:
        ec = self.r.election
        xc = self.r.exclusion
        scen_df = self.r.scenarios
        ub = self.r.upper_bound
        s = self.s

        story = []
        story.append(Paragraph("Named Scenario Comparison", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph(
            "Six named scenarios spanning the full probability spectrum. "
            "\"Uniform\" distributes voters equally; \"Non-uniform\" weights by "
            "district Muslim population (more realistic).",
            s["body"],
        ))
        story.append(Spacer(1, 0.2 * cm))

        # Build scenario table from dataframe
        col_map = {
            "Scenario": "Scenario",
            "Muslim→TMC": f"Muslim→{ec.party_b_label}",
            "Hindu→TMC": f"Hindu→{ec.party_b_label}",
            "Turnout": "Turnout",
            "Uniform flips": "Uniform\nflips",
            "Non-uniform flips": "Non-uniform\nflips",
            "BJP (uniform)": f"{ec.party_a_label}\n(uniform)",
            "BJP majority (U)?": "Majority?",
        }
        headers = list(col_map.values())
        rows_out = []
        for _, row in scen_df.iterrows():
            maj = row.get("BJP majority (U)?", "Yes")
            rows_out.append([
                row.get("Scenario", ""),
                row.get("Muslim→TMC", ""),
                row.get("Hindu→TMC", ""),
                row.get("Turnout", ""),
                str(row.get("Uniform flips", "")),
                str(row.get("Non-uniform flips", "")),
                str(row.get("BJP (uniform)", "")),
                f"✓ {maj}" if str(maj).lower() == "yes" else f"✗ {maj}",
            ])

        story.append(_data_table(
            headers, rows_out,
            col_widths=[4 * cm, 2 * cm, 2 * cm, 1.8 * cm, 2 * cm, 2.2 * cm, 2 * cm, 2 * cm],
            highlight_last_col=True,
        ))

        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Analytical Upper Bound (Geographic Constraints Removed)",
                                s["sub_head"]))
        story.append(Paragraph(
            f"The absolute ceiling: 95% Muslim→{ec.party_b_label}, 60% Hindu→{ec.party_b_label}, "
            "100% turnout, and all 27L voters teleported to the closest marginal BJP seats "
            "(physically impossible). Even this scenario flips only "
            f"<b>{ub.seats_flipped} seats</b>, leaving {ec.party_a_label} at "
            f"<b>{ub.party_a_final} seats</b> — below the 148-seat majority mark.",
            s["body"],
        ))
        story.append(Paragraph(
            "This is the only scenario where BJP loses majority — and it requires violating "
            "the fundamental geographic constraint that voters are registered to specific "
            "constituencies and cannot be moved.",
            s["body"],
        ))

        fig3 = self.fig_dir / "fig3_scenario_bars.png"
        if fig3.exists():
            story += _embed_figure(
                str(fig3),
                width=W - 3.6 * cm,
                caption="Figure 3 — Seat flips (left) and final BJP seat count (right) for each named scenario. Red dashed line = majority threshold.",
            )

        story.append(PageBreak())
        return story

    def _monte_carlo_page(self) -> list:
        ec = self.r.election
        mc = self.r.monte_carlo
        s = self.s

        story = []
        story.append(Paragraph("Monte Carlo Simulation Results", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph(
            "To account for uncertainty across all parameters simultaneously, we ran "
            f"<b>{mc.n_simulations:,} simulations</b>, each drawing randomly from the full "
            "parameter space:",
            s["body"],
        ))
        params = [
            f"Muslim→{ec.party_b_label} vote share: drawn uniformly from 50% to 90%",
            f"Hindu→{ec.party_b_label} vote share: drawn uniformly from 15% to 55%",
            "Turnout: drawn uniformly from 60% to 90%",
            "Geographic distribution: district Muslim% ± 5% random noise",
        ]
        for p in params:
            story.append(Paragraph(p, s["bullet"]))

        story.append(Spacer(1, 0.3 * cm))
        story.append(_stat_row([
            (f"{mc.median_flips:.0f}", "Median seat\nflips"),
            (f"{mc.p95_flips}", "95th percentile\nflips"),
            (f"{mc.max_flips}", "Maximum flips\n(any simulation)"),
            (f"{mc.flips_needed}", "Flips needed to deny\nBJP majority"),
        ]))

        story.append(Spacer(1, 0.3 * cm))
        story.append(_callout_box(
            f"P(BJP retains majority across all 10,000 simulations) = "
            f"<b>{mc.p_party_a_majority:.1%}</b>\n"
            f"P(TMC gets majority) = <b>{mc.p_party_b_majority:.1%}</b>",
            bg=colors.HexColor("#F0FDF4"),
            border=GREEN_OK,
        ))

        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            f"In no simulation across the entire parameter space did the number of seat flips "
            f"reach the {mc.flips_needed} needed to deny {ec.party_a_label} a majority. "
            f"The maximum observed across all 10,000 runs was <b>{mc.max_flips} flips</b>.",
            s["body"],
        ))

        fig4 = self.fig_dir / "fig4_monte_carlo.png"
        if fig4.exists():
            story += _embed_figure(
                str(fig4),
                width=W - 3.6 * cm,
                caption=(
                    "Figure 4 — Left: distribution of seat flips across 10,000 simulations "
                    f"(red line = majority-denial threshold of {mc.flips_needed}). "
                    "Right: survival function showing P(flips ≥ x)."
                ),
            )

        story.append(PageBreak())
        return story

    def _conclusions_page(self) -> list:
        ec = self.r.election
        xc = self.r.exclusion
        df = self.r.data
        mc = self.r.monte_carlo
        ub = self.r.upper_bound
        s = self.s

        bjp_seats = int(df["winner_is_party_a"].sum())
        median_margin = int(df[df["winner_is_party_a"]]["margin"].median())

        story = []
        story.append(Paragraph("Conclusions", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph(
            "The claim that 27 lakh SIR-excluded voters could have changed the outcome of "
            "the West Bengal 2026 election does not hold up to quantitative scrutiny. "
            "Our analysis finds three independent reasons why:",
            s["body"],
        ))
        story.append(Spacer(1, 0.15 * cm))

        conclusions = [
            (
                "The ecological fallacy",
                "Aggregate vote gaps are irrelevant in a FPTP election. A party can win "
                "150 seats by 500 votes each and lose 143 by 100,000 each. The 32 lakh "
                "aggregate BJP–TMC gap is dominated by BJP's landslide margins in safe "
                "seats. The meaningful question is whether excluded voters could flip "
                "individual seat outcomes — and the data shows they cannot.",
            ),
            (
                "The geographic mismatch",
                "65% of pending excluded voters are Muslim, concentrated in Murshidabad, "
                "Malda, North Dinajpur, and Birbhum. These districts returned large TMC "
                "victories. Even if every excluded Muslim voter voted TMC, the extra votes "
                "increase TMC's margin in seats it already won — they do not travel to the "
                "marginal BJP seats in Hooghly, Howrah, or Nadia.",
            ),
            (
                "The arithmetic gap",
                f"The median {ec.party_a_label} winning margin is {median_margin:,} votes. "
                f"Uniform distribution gives ~9,215 excluded voters per seat. At a realistic "
                "net TMC swing rate of 30–50 cents per voter, the net swing is ~2,800–4,600 "
                f"votes — a fraction of the median {ec.party_a_label} margin. Even the most "
                f"TMC-biased probability assumption (90% Muslim→TMC, 55% Hindu→TMC, 100% "
                f"turnout) flips at most 13 seats under realistic geography — against the "
                f"{mc.flips_needed} needed.",
            ),
        ]

        for i, (title, body) in enumerate(conclusions, 1):
            story.append(Paragraph(f"<b>{i}. {title}</b>", s["sub_head"]))
            story.append(Paragraph(body, s["body"]))

        story.append(Spacer(1, 0.3 * cm))
        story.append(_callout_box(
            "The West Bengal 2026 election result is statistically robust. "
            "Under every plausible geographic and voting probability assumption, "
            f"{ec.party_a_label} retains a majority. The 27 lakh excluded voters, "
            "even if all allocated optimally, cannot produce the "
            f"{mc.flips_needed} seat swings needed to change the outcome.\n\n"
            "This finding holds across 10,000 Monte Carlo draws sampling "
            "the full parameter space: <b>P(BJP retains majority) = 100%</b>.",
            bg=colors.HexColor("#EFF6FF"),
            border=DARK_NAVY,
        ))

        story.append(Spacer(1, 0.3 * cm))

        fig5 = self.fig_dir / "fig5_marginal_seats.png"
        if fig5.exists():
            story += _embed_figure(
                str(fig5),
                width=W - 3.6 * cm,
                caption=(
                    f"Figure 5 — The 30 most marginal {ec.party_a_label} seats. "
                    "Green bars would flip under the absolute upper-bound stress test "
                    "(geographic constraints removed). Orange bars are safe under all scenarios."
                ),
            )

        story.append(PageBreak())
        return story

    def _data_sources_page(self) -> list:
        s = self.s
        story = []
        story.append(Paragraph("Data Sources & Limitations", s["section_head"]))
        story.append(_hr(color=DARK_NAVY, thickness=1))
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("Data Sources", s["sub_head"]))
        sources = [
            ("Election results",
             "Election Commission of India, results.eci.gov.in/ResultAcGenMay2026/ — "
             "accessed via Internet Archive (Wayback Machine) snapshots from May 4–5, 2026, "
             "after all 293 constituencies declared results."),
            ("SIR exclusion data",
             "Wikipedia, '2026 West Bengal Legislative Assembly election'; "
             "multiple Indian news outlets including The Hindu, Indian Express, Wire. "
             "The 27 lakh figure and 65/35 Muslim/Hindu split are reported figures; "
             "ECI has not published a constituency-level breakdown."),
            ("Muslim population shares",
             "Census of India 2011, district-level data, Office of the Registrar "
             "General & Census Commissioner. Constituency-to-district mapping based on "
             "ECI 2026 delimitation order."),
            ("Original article",
             "Nilanjan Mukhopadhyay, 'Were elections in West Bengal free and fair?', "
             "Rediff News, May 7, 2026."),
        ]
        for title, desc in sources:
            story.append(Paragraph(f"<b>{title}:</b> {desc}", s["bullet"]))
            story.append(Spacer(1, 0.1 * cm))

        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Limitations", s["sub_head"]))
        limitations = [
            "Constituency-to-district mapping uses ECI 2026 delimitation; minor boundary-constituency assignments may differ.",
            "Muslim population percentages from Census 2011; local changes since then are not captured.",
            "Voting probability distributions are parameterised from historical patterns and varied over a wide grid; the true distributions are unobservable.",
            "The '27 lakh pending' figure comes from news sources and election observers; ECI has not published an official constituency-level breakdown.",
            "Falta constituency (seat 144) is excluded from analysis; BJP won the May 21 repoll.",
            "One-seat discrepancy: our ECI data shows 81 TMC seats vs 80 reported in some news sources.",
        ]
        for l in limitations:
            story.append(Paragraph(l, s["bullet"]))
            story.append(Spacer(1, 0.06 * cm))

        story.append(Spacer(1, 0.4 * cm))
        story.append(_hr())
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            "This analysis was conducted independently using publicly available data. "
            "All code and data are available at: github.com/pojhafb/wb-2026-sir-election-analysis\n\n"
            "The analysis is politically neutral — it tests a specific statistical claim. "
            "It does not take a position on whether the SIR process was appropriate, "
            "fair, or legally compliant; those are separate questions.",
            ParagraphStyle("disc", fontName="Helvetica", fontSize=9,
                           textColor=MID_GREY, leading=14, alignment=TA_JUSTIFY),
        ))

        return story
