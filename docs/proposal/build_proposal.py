"""Build the EIBIS microdata proposal PDF: a cover/instructions page
followed by the proposal document itself."""

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, ListFlowable, ListItem,
)

INK = HexColor("#111111")
MUTED = HexColor("#595955")
ACCENT = HexColor("#1c5cab")
LINE = HexColor("#d9d8d2")
BOX_BG = HexColor("#eef3fb")
FILL_BG = HexColor("#fff4e5")
FILL_BORDER = HexColor("#c98500")

OUT = "EIBIS_Microdata_Proposal.pdf"

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18,
    leading=22, textColor=INK, spaceAfter=4, alignment=TA_LEFT,
)
doctitle_style = ParagraphStyle(
    "DocTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15,
    leading=19, textColor=INK, spaceAfter=10, alignment=TA_LEFT,
)
subtitle_style = ParagraphStyle(
    "SubtitleX", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5,
    leading=13, textColor=MUTED, spaceAfter=10,
)
h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12,
    leading=14, textColor=INK, spaceBefore=14, spaceAfter=6,
)
body = ParagraphStyle(
    "BodyX", parent=styles["Normal"], fontName="Helvetica", fontSize=9.6,
    leading=13.5, textColor=INK, spaceAfter=7, alignment=TA_LEFT,
)
bullet = ParagraphStyle(
    "BulletX", parent=body, leftIndent=4, spaceAfter=4,
)
fill_label = ParagraphStyle(
    "FillLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.6,
    leading=13, textColor=HexColor("#8a5a00"),
)
caption_style = ParagraphStyle(
    "Caption", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=8,
    leading=11, textColor=MUTED, spaceBefore=2, spaceAfter=6,
)

story = []

# ============================================================ COVER PAGE
story.append(Paragraph("Before you send this", title_style))
story.append(Paragraph(
    "EIBIS Firm-Level Microdata &mdash; Research Proposal &mdash; Draft prepared by TWIN Analytics, September 2026",
    subtitle_style,
))
story.append(HRFlowable(width="100%", thickness=0.8, color=LINE, spaceAfter=10))

box_text = (
    "<b>Where to submit:</b> email the completed proposal (with CV attached) to "
    "<b>EIBIS_data_access@eib.org</b>. This is an email-based process, not an online form &mdash; "
    "EIB does not publish a web submission portal for this. Background on the access process: "
    "https://www.eib.org/en/publications-research/economics/surveys-data/eibis/about/index"
)
box_table = Table([[Paragraph(box_text, body)]], colWidths=[6.9 * inch])
box_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), BOX_BG),
    ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story.append(box_table)
story.append(Spacer(1, 10))

story.append(Paragraph("What still needs your input", h2))
story.append(Paragraph(
    "The document on the following pages is drafted from the analysis already completed in "
    "the TWIN_Analytics repository and can be used close to as-is. Six fields are marked in "
    "orange and need your input before this is ready to send:",
    body,
))
fill_items = [
    "Your name(s), institutional affiliation, role, and contact email (§1).",
    "Collaborators or institutional partners, if any (§1) — EIBIS access is granted "
    "“for collaborative projects aiming at a publication,” so this matters.",
    "A CV, attached separately (§1) — stated as a requirement by EIBIS.",
    "The specific panel years you're requesting and whether your institution has separate "
    "ORBIS access (§5) — the ORBIS question materially strengthens the proposal since "
    "it's the remaining link needed for a complete firm-level chain.",
    "Your intended publication venue or output format (§6) — this appears to be a real "
    "gating criterion for the committee, not boilerplate.",
    "A timeline (§7).",
]
story.append(ListFlowable(
    [ListItem(Paragraph(t, bullet), leftIndent=14, bulletColor=FILL_BORDER) for t in fill_items],
    bulletType="bullet", start="•",
))

story.append(Paragraph("Two things worth doing before you send it", h2))
note_items = [
    "<b>Attach the existing technical report</b> as evidence of research capacity: "
    "<i>TWIN_Analytics_First_Findings.pdf</i> (2-page summary) and/or a link to "
    "https://github.com/FIMPlank/TWIN_Analytics. The aggregate-level work is real, "
    "independently reviewed across five rounds, and directly motivates the access being "
    "requested — don't undersell it.",
    "<b>If your institution does not have ORBIS access</b>, RQ2/H2 (the firm-level verified-"
    "emissions link) will need EIBIS's own guidance on whether their microdata already carries "
    "a usable firm identifier that maps to EU ETS installations, or whether a different linking "
    "strategy is needed. Worth asking directly in the email rather than assuming.",
]
story.append(ListFlowable(
    [ListItem(Paragraph(t, bullet), leftIndent=14, bulletColor=ACCENT) for t in note_items],
    bulletType="bullet", start="•",
))

story.append(PageBreak())

# ============================================================ PROPOSAL DOC


def fill_in(text):
    t = Table([[Paragraph(f"[FILL IN] {text}", fill_label)]], colWidths=[6.9 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FILL_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, FILL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


story.append(Paragraph("EIBIS Firm-Level Microdata", doctitle_style))
story.append(Paragraph("Research Proposal", subtitle_style))
story.append(HRFlowable(width="100%", thickness=0.8, color=LINE, spaceAfter=10))

story.append(Paragraph("1. Applicant(s)", h2))
story.append(fill_in("Name(s)"))
story.append(fill_in("Institutional affiliation"))
story.append(fill_in("Position / role"))
story.append(fill_in("Contact email"))
story.append(Paragraph("<b>CV(s):</b> attached separately, per EIBIS's stated requirement.", body))
story.append(fill_in(
    "Collaborators, if any — EIBIS microdata access is granted “for collaborative "
    "projects aiming at a publication,” so note co-authors or institutional partners here."
))

story.append(Paragraph("2. Project title", h2))
story.append(Paragraph(
    "<b>Twin Transformation: Does Digitalization Predict Verified Emissions Reduction, or "
    "Only Disclosed Climate Ambition? A Firm-Level Test</b>",
    body,
))

story.append(Paragraph("3. Background and motivation", h2))
story.append(Paragraph(
    "The EU's “twin transformation” agenda treats the digital and green transitions as "
    "mutually reinforcing. This is a plausible but largely untested empirical claim at firm "
    "level: does a firm's digital-technology adoption predict a reduction in its <i>actual, "
    "independently verified</i> emissions, or only in its <i>disclosed</i> climate targets and "
    "investment intentions — measures that are self-reported and not independently "
    "audited?",
    body,
))
story.append(Paragraph(
    "We have already completed an extensive country- and sector-level test of this question "
    "using open data (EU ETS verified emissions, EIBIS <i>aggregate</i> survey results, "
    "Eurostat's Digital Intensity Index, and an independent US state/county extension using EPA "
    "facility-level emissions data), summarized in the attached technical report and at "
    "https://github.com/FIMPlank/TWIN_Analytics. That analysis — built and independently "
    "reviewed across multiple rounds of researcher/reviewer scrutiny, with small-cluster-robust "
    "inference, placebo/timing checks, and convergence-economics robustness tests — found "
    "<b>no significant relationship</b> between digitalization intensity and verified-emissions "
    "change, at the country, industrial-sector, or (in a supplementary regional test) sub-"
    "national level, across an 11-year EU panel, two independent digitalization measures, and a "
    "parallel US analysis.",
    body,
))
story.append(Paragraph(
    "This null result is informative but structurally limited: <b>every variable in that "
    "analysis is a country-, sector-, or region-wide average.</b> An aggregate-level "
    "correlation (or its absence) cannot distinguish between two very different underlying "
    "realities — (a) digitalizing firms and emissions-cutting firms are genuinely "
    "unrelated populations, or (b) they are the <i>same</i> firms, but the relationship is "
    "invisible at the aggregate level because it is diluted by averaging across firms that "
    "never digitalized and firms that were never significant emitters in the first place. Only "
    "firm-level microdata that observes <i>the same firms</i> on both a digitalization measure "
    "and a climate/environmental-investment measure can distinguish these.",
    body,
))
story.append(Paragraph(
    "EIBIS is, to our knowledge, the best-positioned dataset to close this gap: a panel since "
    "2016, ~13,000 EU+US firms/year, with <b>both a digitalization module and a climate/"
    "environmental investment module administered to the same respondents in the same survey "
    "wave</b> — precisely the co-observation that no open dataset we have found provides.",
    body,
))

story.append(Paragraph("4. Research objectives and hypotheses", h2))
story.append(Paragraph(
    "<b>RQ1 (primary):</b> At the firm level, does digital-technology adoption intensity "
    "predict a firm's <i>disclosed climate investment or GHG-target-setting behavior</i> "
    "(EIBIS's own climate module — the “disclosure” side)?",
    body,
))
story.append(Paragraph(
    "<b>RQ2 (primary, the gap this proposal is designed to close):</b> Where EIBIS firm "
    "identifiers can be linked to EU ETS installation-level <i>verified</i> emissions data (via "
    "the JRC-EU-ETS-FIRMS crosswalk to ORBIS firm IDs — already inspected in our open-data "
    "work, but not linkable to EIBIS without this access), does digitalization intensity "
    "predict <i>actual verified emissions change</i>, not just disclosed intent?",
    body,
))
story.append(Paragraph(
    "<b>H1:</b> Firm-level digitalization intensity is positively associated with disclosed "
    "climate investment/target-setting (a relatively low bar, testing survey-response "
    "consistency).",
    body,
))
story.append(Paragraph(
    "<b>H2 (the substantive test):</b> Firm-level digitalization intensity is associated with "
    "<i>verified</i> emissions reduction, net of firm size, sector, and country fixed effects.",
    body,
))
story.append(Paragraph(
    "<b>H3 (the disclosure-reality gap, the project's central question):</b> The disclosure-"
    "side association (H1) is stronger/more robust than the verified-outcome association (H2) "
    "— i.e., digitalization predicts what firms <i>say</i> about their climate ambitions "
    "more reliably than what independently audited data shows they <i>do</i>.",
    body,
))
story.append(Paragraph(
    "Our aggregate-level prior (a robust null on the verified-outcome side, replicated across "
    "country, sector, regional, and cross-national US tests, not yet tested against a "
    "disclosure-side benchmark at the same level of aggregation) is directly consistent with H3 "
    "but cannot distinguish it from simple non-existence of any relationship. Firm-level data "
    "is required to test H3 as stated.",
    body,
))

story.append(Paragraph("5. Data and methodology", h2))
story.append(Paragraph("<b>Primary data requested:</b> EIBIS firm-level microdata (digitalization module + climate/environmental investment module), EU+US coverage, panel years:", body))
story.append(fill_in("specify range, e.g. 2018-2025 if available, or match to survey waves overlapping EU ETS phase 4"))
story.append(Paragraph("<b>Linked data (already open-access, already integrated into our pipeline):</b>", body))
linked_items = [
    "EU ETS verified emissions (installation-level, EUTL) — already downloaded and "
    "validated in our repository.",
    "JRC-EU-ETS-FIRMS (EU ETS account holder ↔ ORBIS/Bureau van Dijk firm-ID crosswalk) "
    "— already downloaded; this is the linking key that would let EIBIS firm IDs be "
    "matched to verified ETS emissions, if EIBIS provides (or can be matched to) ORBIS/BvD "
    "firm identifiers.",
]
story.append(ListFlowable(
    [ListItem(Paragraph(t, bullet), leftIndent=14, bulletColor=ACCENT) for t in linked_items],
    bulletType="bullet", start="•",
))
story.append(fill_in(
    "Does your institution have separate ORBIS financial/firmographic access? This materially "
    "strengthens the proposal, since it is the remaining link needed for a complete firm-level "
    "chain."
))
story.append(Paragraph(
    "<b>Methodology:</b> Firm-level panel regression (fixed effects: firm, sector, country, "
    "year), with the same standard of statistical rigor already demonstrated in our open-data "
    "work: cluster-robust standard errors appropriate to the panel's cluster structure (with "
    "small-sample corrections, e.g. wild cluster bootstrap, where the number of clusters is "
    "limited), a placebo/timing check (does future digitalization “predict” past "
    "emissions? — a check for reverse causality), and controls for firm size, sector "
    "composition, and macroeconomic conditions (GDP growth, energy prices) drawn from the same "
    "free public sources already integrated into our pipeline (Eurostat).",
    body,
))
story.append(Paragraph(
    "<b>Reproducibility and transparency:</b> All non-restricted code, data, and documentation "
    "for this project are maintained in a public repository "
    "(https://github.com/FIMPlank/TWIN_Analytics). We would maintain the same standard for any "
    "firm-level extension, publishing all derived/aggregated results and code subject to "
    "EIBIS's microdata confidentiality and disclosure-control requirements, and would follow "
    "EIBIS's stated access modality (on-site/remote secure environment, as required) for any "
    "non-aggregable output.",
    body,
))

story.append(Paragraph("6. Expected outputs / publication plan", h2))
story.append(fill_in(
    "EIBIS microdata access is stated to be granted “for collaborative projects aiming at "
    "a publication.” Specify your intended venue/format: a working paper, a submission to "
    "a specific journal or conference, a policy report, etc. If this is an academic project, "
    "name the target outlet or research program it sits within."
))

story.append(Paragraph("7. Timeline", h2))
story.append(fill_in(
    "e.g. data access requested by [DATE], analysis over [N months], draft results by [DATE]."
))

doc = SimpleDocTemplate(
    OUT, pagesize=LETTER,
    leftMargin=0.7 * inch, rightMargin=0.7 * inch,
    topMargin=0.6 * inch, bottomMargin=0.55 * inch,
    title="EIBIS Firm-Level Microdata Research Proposal",
    author="TWIN Analytics",
)
doc.build(story)
print("done")
