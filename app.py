import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
import json
import time
import csv
import io
import datetime
from pydantic import BaseModel, ValidationError
from typing import Literal, List

# ─────────────────────────────────────────────────────────────────────────────
# 1. PAGE CONFIG & GLOBAL STYLES
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Vertex Triage Test",
    layout="wide",
    page_icon=":material/science:",
)

# Inject Google Material Symbols for use in markdown/HTML
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap" rel="stylesheet" />
<style>
    .material-symbols-outlined {
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        vertical-align: middle;
        margin-right: 6px;
    }
    .material-symbols-outlined.filled {
        font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }
    .icon-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.25rem;
    }
    .icon-header .material-symbols-outlined {
        font-size: 36px;
        margin-right: 0;
    }
    .section-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .section-label .material-symbols-outlined {
        font-size: 20px;
        margin-right: 0;
    }
    .demo-banner {
        background: linear-gradient(90deg, #4285F4 0%, #34A853 50%, #FBBC04 75%, #EA4335 100%);
        color: white;
        padding: 6px 16px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 1rem;
    }
    .demo-banner .material-symbols-outlined {
        font-size: 18px;
        margin-right: 0;
    }
    /* Hide Streamlit Cloud chrome */
    .stAppDeployButton { display: none !important; }
    [data-testid="manage-app-button"] { display: none !important; }
    ._profileContainer_gzau3_53 { display: none !important; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Demo banner ──────────────────────────────────────────────────────────────
st.markdown(
    '<div class="demo-banner">'
    '<span class="material-symbols-outlined">science</span>'
    'DEMONSTRATION — This app is a proof-of-concept showing Gemini as a deterministic, '
    'schema-locked logic engine for enterprise triage. All data is synthetic.'
    '</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;margin-top:-2rem;">'
        '<span class="material-symbols-outlined filled" style="font-size:28px;color:#4285F4;">cloud</span>'
        '<span style="font-size:1.4rem;font-weight:700;">Vertex Triage</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("Gemini as a Deterministic Logic Engine")

    # Load API key silently from secrets
    api_key = st.secrets.get("GEMINI_API_KEY", "")

    sector = st.selectbox(
        ":material/domain: Domain Sector",
        options=[
            "Healthcare (HCLS)",
            "Industrial (Manufacturing)",
            "Cybersecurity (SecOps)",
            "Financial Services (FinOps)",
            "Energy & Utilities",
        ],
        help="Switch domains instantly — each has its own Pydantic schema and output layout.",
    )

    # ── What is this? ─────────────────────────────────────────────────────
    with st.expander(":material/help: What is this?", expanded=False):
        st.markdown(
            "**Vertex Triage Test** demonstrates how Gemini 3.0 can function as a "
            "**deterministic logic engine** for enterprise systems.\n\n"
            "- Unstructured text goes in (notes, logs, alerts)\n"
            "- A strict **Pydantic schema** constrains the output\n"
            "- Gemini returns **machine-readable JSON** — no hallucinated format, every time\n\n"
            "Switch the domain selector above to see the schema change instantly."
        )

    # ── How it works ──────────────────────────────────────────────────────
    with st.expander(":material/architecture: How it works", expanded=False):
        st.markdown(
            "**1. Schema definition** — Each domain has a Pydantic `BaseModel` "
            "defining exact fields, types, and allowed enum values.\n\n"
            "**2. API constraint** — The schema is passed to Gemini via "
            "`response_schema` + `response_mime_type='application/json'`, "
            "forcing structured output at the API level.\n\n"
            "**3. Validation** — The SDK auto-parses the response into "
            "a typed Pydantic object. If the JSON doesn't match, it fails loudly.\n\n"
            "**Stack:** Streamlit · Google GenAI SDK · Gemini 3.0 Pro · Pydantic v2"
        )

    # ── Why build this? ───────────────────────────────────────────────────
    with st.expander(":material/lightbulb: Why build this?", expanded=False):
        st.markdown(
            "Enterprise teams drown in **unstructured data** — nurse handoff notes, "
            "sensor logs, SOC alerts, wire-transfer narratives. Today that data gets "
            "triaged manually, slowly, and inconsistently.\n\n"
            "This pattern — **LLM + locked schema** — turns free text into "
            "**structured, actionable records** in seconds. Real-world applications:\n\n"
            "- **Healthcare** — Auto-classify ER intake notes by acuity so "
            "the sickest patients are seen first, reducing wait-to-treatment.\n"
            "- **Manufacturing** — Convert sensor anomalies into prioritized "
            "work orders before an unplanned shutdown costs millions.\n"
            "- **Cybersecurity** — Instantly triage a flood of SIEM alerts into "
            "severity tiers so analysts focus on real threats, not noise.\n"
            "- **Financial Services** — Flag suspicious transactions with "
            "structured risk scores for compliance teams and SAR filings.\n"
            "- **Energy & Utilities** — Classify grid fault reports in "
            "real time to accelerate restoration and protect critical infrastructure.\n\n"
            "The ROI is **speed, consistency, and auditability** — "
            "every output conforms to a contract, is machine-readable, "
            "and can flow directly into downstream systems (EHR, CMMS, SOAR, "
            "case management) with zero manual re-keying."
        )

    # ── Credit system ──────────────────────────────────────────────────────
    STARTING_CREDITS = 10

    if "credits" not in st.session_state:
        st.session_state.credits = STARTING_CREDITS

    credits_left = st.session_state.credits

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        f'<span class="material-symbols-outlined filled" style="font-size:20px;'
        f'color:{"#34A853" if credits_left > 3 else "#EA4335"};">toll</span>'
        f'<span style="font-size:0.95rem;font-weight:600;">{credits_left} / {STARTING_CREDITS} credits remaining</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.progress(credits_left / STARTING_CREDITS)
    if credits_left <= 3 and credits_left > 0:
        st.caption(":material/warning: Running low on demo credits.")
    elif credits_left == 0:
        st.caption(":material/block: Demo credits exhausted.")

    st.markdown(
        '<div style="font-size:0.82rem;opacity:0.7;display:flex;align-items:center;gap:6px;">'
        '<span class="material-symbols-outlined" style="font-size:16px;">person</span>'
        'Made by <a href="https://www.linkedin.com/in/zacharypolio/" '
        'target="_blank" style="color:inherit;text-decoration:underline;">'
        'Zack Polio</a>'
        '</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA MODELS — The "Brain"
#    Each domain has a strict Pydantic schema. Gemini is constrained to
#    return ONLY valid JSON matching the active schema (response_schema).
# ─────────────────────────────────────────────────────────────────────────────

class ClinicalSchema(BaseModel):
    triage_priority: Literal["Critical", "Urgent", "Routine"]
    esi_acuity_level: Literal["1", "2", "3", "4", "5"]
    diagnosis_impression: str
    specialist_referral: str
    vitals_extracted: List[str]
    risk_factors: List[str]
    medications_administered: List[str]
    allergies_noted: List[str]
    suggested_action: str
    disposition: Literal["Admit ICU", "Admit Floor", "Observation", "Discharge"]


class IndustrialSchema(BaseModel):
    severity_level: Literal["Critical", "Warning", "Info"]
    affected_component: str
    failure_probability_percent: float
    sensor_readings: List[str]
    maintenance_action: Literal["Immediate Shutdown", "Schedule Service", "Monitor"]
    safety_risk: Literal["High", "Medium", "Low"]
    estimated_downtime_hours: float
    parts_required: List[str]
    root_cause_hypothesis: str


class CybersecuritySchema(BaseModel):
    threat_level: Literal["Critical", "High", "Medium", "Low"]
    attack_vector: str
    mitre_attack_techniques: List[str]
    affected_assets: List[str]
    indicators_of_compromise: List[str]
    data_at_risk: str
    urgency_window: Literal["Minutes", "Hours", "Days"]
    containment_steps: List[str]
    recommended_response: Literal["Isolate & Investigate", "Block & Monitor", "Log & Review"]
    threat_hypothesis: str


class FinancialSchema(BaseModel):
    risk_rating: Literal["Critical", "Elevated", "Normal"]
    transaction_type: str
    entities_involved: List[str]
    flagged_anomalies: List[str]
    amount_at_risk_usd: float
    jurisdiction_risk: str
    regulatory_flags: List[str]
    escalation_path: str
    recommended_action: Literal["Freeze Account", "Enhanced Review", "Clear Transaction"]
    fraud_hypothesis: str


class EnergySchema(BaseModel):
    alert_priority: Literal["Emergency", "Warning", "Advisory"]
    affected_system: str
    grid_impact_mw: float
    customers_affected: int
    fault_indicators: List[str]
    weather_factor: str
    safety_hazards: List[str]
    estimated_restoration_hours: float
    recommended_action: Literal["Emergency Dispatch", "Schedule Inspection", "Continue Monitoring"]
    root_cause_hypothesis: str


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHETIC DATA — Realistic but entirely fictional examples (Feb 2026)
# ─────────────────────────────────────────────────────────────────────────────

HEALTHCARE_EXAMPLE = """\
TRIAGE NOTE — ER Intake  |  Timestamp: 2026-02-07 02:47 UTC
Patient: 68 y/o male, arrived via EMS, chief complaint of crushing substernal \
chest pain radiating to left arm and jaw, onset ~45 min ago while sleeping.
Vitals on arrival:  BP 88/54 mmHg  |  HR 112 bpm (irregular)  |  SpO2 91% RA  \
|  RR 24  |  Temp 37.1°C
History: Type-2 DM (A1c 9.2), HTN (non-compliant w/ lisinopril), prior MI \
(2021, LAD stent), current smoker (40 pack-year), BMI 34.
ECG: ST-elevation leads II, III, aVF — consistent with inferior STEMI.
Labs pending: troponin, BMP, CBC, PT/INR.
Nurse note: Patient diaphoretic, anxious, nausea x2 episodes. IV access x2 \
(18g AC bilateral). 324 mg ASA administered PO. Nitro SL x1 given — minimal \
relief. Morphine 2 mg IV ordered. Cardiology page initiated.
Allergies: Sulfa (rash), Codeine (GI upset).
Code Status: Full code.\
"""

INDUSTRIAL_EXAMPLE = """\
=== SENSOR TELEMETRY LOG — Line 7, Compressor Unit C-401 ===
Timestamp: 2026-02-07T03:12:08Z  |  Source: SCADA Gateway / PLC-7-041

[VIBRATION]  Bearing DE — X-axis: 11.4 mm/s RMS (baseline 3.2) ▲ 256%
[VIBRATION]  Bearing NDE — X-axis: 7.8 mm/s RMS (baseline 2.9) ▲ 169%
[TEMPERATURE] Bearing DE — 94.3°C (alarm threshold: 85°C) ⚠ EXCEEDED
[TEMPERATURE] Oil sump — 78.1°C (warning threshold: 75°C) ⚠ EXCEEDED
[PRESSURE]   Discharge — 12.1 bar (nominal 11.5 ± 0.3) — within range
[CURRENT]    Motor draw — 142 A (rated 130 A) ▲ 9.2% above nameplate

Error codes active:
  ERR-4012: High vibration — Loss of dynamic balance
  ERR-4087: Thermal exceedance — Bearing lubrication degradation suspected
  WARN-3001: Predictive model flag — RUL estimate < 72 hrs

Maintenance log: Last PM completed 2025-11-18 (81 days ago, interval = 90 days).
Oil analysis (2026-01-12): Fe particulate 48 ppm (limit 25 ppm), water 0.08%.
Unit runtime since last start: 1,247 hrs.
Downstream dependency: Line 7 feeds Assembly Cell 7A/7B — full production stop \
if C-401 trips.\
"""

CYBERSECURITY_EXAMPLE = """\
=== SIEM ALERT CORRELATION — Incident #SEC-2026-02841 ===
Timestamp: 2026-02-07T04:18:32Z  |  Source: Sentinel / XDR Fusion Engine
Severity Override: Analyst L1 escalated to L3

[ALERT-1] 04:14:07Z  Credential stuffing burst detected — 3,842 failed \
login attempts against Azure AD tenant (threshold: 200/5min). Source IPs: \
185.220.101.0/24 (Tor exit nodes), geolocation: multiple.
[ALERT-2] 04:15:44Z  Successful auth: svc-backup@corp.contoso.com from \
IP 185.220.101.34 — MFA bypassed via legacy IMAP protocol. Account is a \
service principal with Mail.ReadWrite and Files.ReadAll Graph API scopes.
[ALERT-3] 04:16:59Z  Anomalous mailbox rule created: "Auto-Forward All" → \
external address j.smith8827@proton.me. 412 emails exfiltrated in 73 seconds.
[ALERT-4] 04:17:48Z  Lateral movement: svc-backup authenticated to \
SharePoint admin site via stolen session token. 2.1 GB download initiated \
from /sites/finance/Shared Documents/Q4-2025-Earnings/.

Threat intel match: IP 185.220.101.34 flagged in CrowdStrike Falcon feed \
(APT-41 infrastructure, confidence: HIGH). Hash of forwarding rule payload \
matches known BEC toolkit "MailSnake v3.2".
EDR status: No endpoint agent on svc-backup (service account, headless).
Conditional Access gap: Legacy auth protocols not blocked for service accounts.\
"""

FINANCIAL_EXAMPLE = """\
=== TRANSACTION MONITORING ALERT — Case #FIN-2026-09173 ===
Timestamp: 2026-02-07T01:33:17Z  |  Source: AML Engine v4.2 / Wire Desk

Flagged wire transfer:
  Originator: Meridian Capital Holdings LLC (Acct: ****4782, New York)
  Beneficiary: Oceanic Trade Partners Ltd (Acct: ****6190, Cayman Islands)
  Amount: USD 4,750,000.00  |  Reference: "Advisory fee — Project Atlas"
  Routing: JPM NY → Correspondent (Deutsche Frankfurt) → Cayman National Bank

Risk indicators triggered:
  [R-1] Structuring pattern: 5 wires in 14 days totaling $23.4M, each just \
below $5M reporting threshold. Previous 12-month avg: $1.2M/quarter.
  [R-2] Jurisdiction risk: Beneficiary domiciled in FATF grey-list jurisdiction. \
Shell company — incorporated 2025-12-02, no web presence, nominee directors.
  [R-3] Behavioral anomaly: Originator changed beneficiary bank details 3x in \
48 hrs. New authorized signer added to account on 2026-02-04 (KYC refresh pending).
  [R-4] PEP proximity: Originator's UBO (35% stake) is a politically exposed \
person — former deputy minister of trade (Country: undisclosed).

Sanctions screening: No OFAC/EU/UN hits. Adverse media: 2 articles (2025) \
linking UBO to procurement irregularities. SAR history: 1 prior filing (2024).\
"""

ENERGY_EXAMPLE = """\
=== GRID EVENT LOG — Substation Bravo-7, Feeder 12kV-F03 ===
Timestamp: 2026-02-07T05:42:19Z  |  Source: ADMS / SCADA Relay IED

[FAULT] 05:41:58Z  Phase-to-ground fault detected on Feeder F03, Zone 2. \
Relay 51G tripped in 0.12s. Fault current: 8,420 A (nominal load: 340 A).
[RECLOSE] 05:42:03Z  Auto-reclose attempt #1 — FAILED. Fault persists.
[RECLOSE] 05:42:18Z  Auto-reclose attempt #2 — FAILED. Lockout engaged.
[IMPACT] Feeder F03 de-energized. 2,847 customers without power. \
Estimated load lost: 14.3 MW.

Weather: Freezing rain advisory active. Wind: 38 km/h gusting 56 km/h.
Vegetation mgmt: Last trim cycle completed 2025-09-14 (Span 7-12 flagged \
as high-risk corridor — heritage oak canopy, trimming restricted by county).
Asset condition: Recloser R-7 firmware v2.3 (current: v3.1, update deferred). \
Insulator inspection (2025-11-02): Span 9 — hairline crack noted, replacement \
scheduled Q1-2026 but not yet completed.
DER status: 4.2 MW solar + 1.8 MW BESS on Feeder F03. Islanding not enabled.
Adjacent feeders: F02 at 87% capacity, F04 at 91% capacity. Load transfer \
limited — tie switch TS-12 manual-only (motorized upgrade in CIP backlog).\
"""

# Map sector labels → config
SECTOR_CONFIG = {
    "Healthcare (HCLS)": {
        "schema": ClinicalSchema,
        "domain_label": "healthcare clinical",
        "icon": "local_hospital",
        "icon_color": "#E8710A",
        "title": "HCLS Intake Portal",
        "subtitle": "**Schema-locked clinical triage** — paste a nurse's note and let Gemini extract structured output.",
        "example": HEALTHCARE_EXAMPLE,
        "manual_minutes": 12,
        "manual_label": "Avg nurse intake triage",
    },
    "Industrial (Manufacturing)": {
        "schema": IndustrialSchema,
        "domain_label": "industrial IoT",
        "icon": "precision_manufacturing",
        "icon_color": "#F9AB00",
        "title": "IoT Telemetry Dashboard",
        "subtitle": "**Schema-locked industrial triage** — paste a sensor log and let Gemini extract structured output.",
        "example": INDUSTRIAL_EXAMPLE,
        "manual_minutes": 25,
        "manual_label": "Avg manual log review",
    },
    "Cybersecurity (SecOps)": {
        "schema": CybersecuritySchema,
        "domain_label": "cybersecurity threat",
        "icon": "shield_lock",
        "icon_color": "#EA4335",
        "title": "SecOps Threat Console",
        "subtitle": "**Schema-locked threat triage** — paste a SIEM alert and let Gemini extract structured output.",
        "example": CYBERSECURITY_EXAMPLE,
        "manual_minutes": 18,
        "manual_label": "Avg analyst alert triage",
    },
    "Financial Services (FinOps)": {
        "schema": FinancialSchema,
        "domain_label": "financial AML/fraud",
        "icon": "account_balance",
        "icon_color": "#34A853",
        "title": "FinOps Risk Console",
        "subtitle": "**Schema-locked financial triage** — paste a transaction alert and let Gemini extract structured output.",
        "example": FINANCIAL_EXAMPLE,
        "manual_minutes": 35,
        "manual_label": "Avg compliance review",
    },
    "Energy & Utilities": {
        "schema": EnergySchema,
        "domain_label": "energy grid operations",
        "icon": "bolt",
        "icon_color": "#FBBC04",
        "title": "Grid Operations Console",
        "subtitle": "**Schema-locked grid triage** — paste a fault event log and let Gemini extract structured output.",
        "example": ENERGY_EXAMPLE,
        "manual_minutes": 15,
        "manual_label": "Avg dispatcher fault review",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _mi(icon: str, text: str = "", size: int = 20, filled: bool = False) -> str:
    """Render a Material Symbols icon inline in HTML."""
    fill_cls = " filled" if filled else ""
    icon_html = f'<span class="material-symbols-outlined{fill_cls}" style="font-size:{size}px;">{icon}</span>'
    if text:
        return f'{icon_html} {text}'
    return icon_html


MODEL_ID = "gemini-3-pro-preview"
MODEL_LABEL = "Gemini 3.0 Pro"


def _build_system_instruction(domain: str) -> str:
    """Build the system instruction for the triage engine."""
    return (
        f"You are a deterministic {domain} triage engine. "
        "Your ONLY job is to analyze the unstructured event data provided by the user "
        "and return a SINGLE, valid JSON object that conforms to the required schema. "
        "Be precise, clinical, and evidence-based. Extract all relevant data points."
    )


# Domain-specific keyword signals for input validation
_DOMAIN_SIGNALS = {
    "Healthcare (HCLS)": {
        "keywords": [
            "patient", "vitals", "bp ", "hr ", "spo2", "triage", "diagnosis",
            "ecg", "nurse", "allergies", "medications", "symptoms", "chief complaint",
            "history of present", "labs", "ems", "er ", "icu", "mg ", "stemi",
            "cardiac", "pulse", "respiratory", "auscultation", "prognosis",
            "discharge", "admission", "radiology", "ct scan", "mri", "cbc",
            "troponin", "bmp", "creatinine", "hemoglobin", "o2 sat", "intubat",
            "clinical", "physician", "medical record", "icd-10", "cpt code",
        ],
        "label": "clinical / healthcare",
    },
    "Industrial (Manufacturing)": {
        "keywords": [
            "vibration", "bearing", "temperature", "sensor", "compressor",
            "motor", "pressure", "rpm", "scada", "plc", "maintenance",
            "calibration", "pump", "spindle", "err-", "warn-", "telemetry",
            "machine", "conveyor", "hydraulic", "actuator", "downtime",
            "oee", "torque", "overload", "coolant", "cnc", "feed rate",
        ],
        "label": "industrial / manufacturing",
    },
    "Cybersecurity (SecOps)": {
        "keywords": [
            "siem", "alert", "login", "ssh", "credential", "malware", "ip ",
            "firewall", "endpoint", "lateral movement", "exfiltrat", "cve-",
            "mitre", "threat", "ioc", "phishing", "brute force", "xdr", "edr",
            "ransomware", "payload", "c2 ", "command and control", "privilege escalation",
            "hash", "dns", "port scan", "intrusion", "signature", "zero day",
            "exploit", "trojan", "backdoor", "beacon", "cobalt strike",
        ],
        "label": "cybersecurity / SecOps",
    },
    "Financial Services (FinOps)": {
        "keywords": [
            "transaction", "wire", "aml", "fraud", "sar", "kyc", "beneficiary",
            "originator", "ofac", "sanctions", "structuring", "pep",
            "account", "suspicious", "usd", "bank", "compliance",
            "settlement", "clearing", "counterparty", "custody", "trade",
            "equit", "derivative", "portfolio", "dividend", "coupon",
            "reconcil", "ledger", "swift", "iban", "bic", "nostro", "vostro",
            "collateral", "margin call", "exposure", "netting", "exception",
            "payment", "remittance", "forex", "fx ", "basis point", "t+1", "t+2",
            "broker", "dealer", "finra", "sec ", "regulatory", "fiduciary",
        ],
        "label": "financial / AML",
    },
    "Energy & Utilities": {
        "keywords": [
            "fault", "feeder", "substation", "relay", "transformer", "grid",
            "voltage", "frequency", "outage", "customers", "mw ", "kv ",
            "recloser", "breaker", "load shedding", "der", "scada",
            "solar", "wind", "turbine", "inverter", "battery storage",
            "dispatch", "generation", "transmission", "distribution",
            "peak demand", "power factor", "amps", "watt", "kilowatt",
        ],
        "label": "energy / utility",
    },
}


def _detect_domain_mismatch(text: str, selected_sector: str) -> str | None:
    """Check if input text appears to belong to a different domain.
    Returns a warning message if mismatch detected, None if OK."""
    text_lower = text.lower()

    # Score each domain by keyword hits
    scores: dict[str, int] = {}
    for domain, info in _DOMAIN_SIGNALS.items():
        hits = sum(1 for kw in info["keywords"] if kw in text_lower)
        scores[domain] = hits

    best_match = max(scores, key=scores.get)
    best_hits = scores[best_match]

    # If no domain got even 1 hit, we can't determine anything — let it through
    if best_hits < 1:
        return None

    selected_hits = scores.get(selected_sector, 0)

    # Block if: another domain clearly dominates AND the selected domain is weak.
    # Condition: best match is different, AND (best ≥ 2 hits AND either the
    # selected domain has 0 hits or best has at least 1.5× more hits).
    if (
        best_match != selected_sector
        and best_hits >= 2
        and (selected_hits == 0 or best_hits >= selected_hits * 1.5)
    ):
        suggested_sector = best_match
        return (
            f"This input looks like **{_DOMAIN_SIGNALS[best_match]['label']}** data, "
            f"but you have **{_DOMAIN_SIGNALS[selected_sector]['label']}** selected.\n\n"
            f"**Suggested action →** Switch the **Domain Sector** in the sidebar to "
            f"**{suggested_sector}**, or load the correct synthetic example."
        )

    return None


def _severity_color(level: str) -> str:
    mapping = {
        "Critical": "red",
        "Urgent": "orange",
        "High": "orange",
        "Elevated": "orange",
        "Warning": "orange",
        "Emergency": "red",
        "Routine": "green",
        "Info": "green",
        "Normal": "green",
        "Medium": "blue",
        "Low": "green",
        "Advisory": "blue",
    }
    return mapping.get(level, "gray")


# ─────────────────────────────────────────────────────────────────────────────
# 3. MAIN UI
# ─────────────────────────────────────────────────────────────────────────────

cfg = SECTOR_CONFIG[sector]
schema_cls = cfg["schema"]

st.markdown(
    '<div class="icon-header">'
    f'<span class="material-symbols-outlined filled" style="color:{cfg["icon_color"]};">{cfg["icon"]}</span>'
    f'<h1 style="margin:0;">{cfg["title"]}</h1>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(cfg["subtitle"])

# Safety gate
if not api_key:
    st.error("Application not configured. The API key is missing from Streamlit secrets.", icon=":material/error:")
    st.stop()

@st.cache_resource(show_spinner=False)
def _get_genai_client(key: str) -> genai.Client:
    """Cache the GenAI client so it persists across reruns."""
    return genai.Client(api_key=key)

client = _get_genai_client(api_key)

# ── Input section ────────────────────────────────────────────────────────────

col_input, col_actions = st.columns([4, 1])

with col_input:
    if "input_area" not in st.session_state:
        st.session_state.input_area = ""

    raw_input = st.text_area(
        ":material/content_paste: Paste unstructured event data",
        height=260,
        placeholder="Paste event data here, or click 'Load Synthetic Data' →",
        key="input_area",
    )

def _load_synthetic():
    st.session_state.input_area = cfg["example"]


def _clipboard_button(text: str, label: str, icon_name: str, key: str):
    """Render an HTML button that copies *text* to the clipboard on click."""
    escaped = json.dumps(text)
    components.html(f"""
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ background: transparent; }}
            #btn-{key} {{
                width: 100%; padding: 0.45rem 0.75rem;
                border: 1px solid rgba(49,51,63,0.2); border-radius: 0.5rem;
                background: #fff; cursor: pointer;
                font-family: "Source Sans Pro", sans-serif;
                font-size: 14px; font-weight: 400;
                color: rgb(49,51,63);
                display: inline-flex; align-items: center;
                justify-content: center; gap: 0.5rem;
                transition: border-color .2s, color .2s;
            }}
            #btn-{key}:hover {{ border-color: rgb(255,75,75); color: rgb(255,75,75); }}
            .mi {{ font-family: 'Material Symbols Outlined'; font-size: 18px; vertical-align: middle; }}
        </style>
        <button id="btn-{key}" onclick="doCopy_{key}()">
            <span class="mi">{icon_name}</span>{label}
        </button>
        <script>
        async function doCopy_{key}() {{
            var text = {escaped};
            var btn  = document.getElementById('btn-{key}');
            try {{ await navigator.clipboard.writeText(text); }}
            catch(e) {{
                var ta = document.createElement('textarea');
                ta.value = text; ta.style.position='fixed'; ta.style.opacity='0';
                document.body.appendChild(ta); ta.select();
                document.execCommand('copy'); document.body.removeChild(ta);
            }}
            btn.innerHTML = '<span class="mi">check_circle</span>Copied to clipboard!';
            btn.style.borderColor = '#21c354'; btn.style.color = '#21c354';
            setTimeout(function() {{
                btn.innerHTML = '<span class="mi">{icon_name}</span>{label}';
                btn.style.borderColor = ''; btn.style.color = '';
            }}, 2500);
        }}
        </script>
    """, height=46)


with col_actions:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("Load Synthetic Data", use_container_width=True, icon=":material/folder_open:", on_click=_load_synthetic)

    analyze_clicked = st.button(
        "Analyze Event",
        type="primary",
        use_container_width=True,
        icon=":material/rocket_launch:",
    )

# ── Guided walkthrough (shown when input is empty) ───────────────────────

QUICK_EXAMPLES = {
    "Healthcare (HCLS)": [
        "72 y/o female, SOB, SpO2 88%, hx of CHF, bilateral crackles on auscultation, BNP 1840 pg/mL",
        "14 y/o male, right forearm deformity after fall, NV intact distally, pain 7/10, no open wound",
    ],
    "Industrial (Manufacturing)": [
        "Pump P-201 discharge pressure dropped from 6.2 bar to 3.1 bar over 15 min, cavitation noise audible, motor current normal",
        "CNC Mill #4 spindle vibration 8.2 mm/s RMS (baseline 2.1), tool wear sensor flagging, last calibration 120 days ago",
    ],
    "Cybersecurity (SecOps)": [
        "Multiple failed SSH logins from 45.155.205.0/24 against jump host, followed by successful root login at 03:14 UTC, new cron job created",
        "DLP alert: 14,000 customer records exported to USB by user jdoe@corp, outside business hours, 2 weeks before termination date",
    ],
    "Financial Services (FinOps)": [
        "3 wire transfers totaling $890K to newly opened accounts in 48 hrs, originator is a dormant LLC reactivated last week",
        "Credit card: 47 transactions across 6 countries in 2 hours, chip-not-present, average ticket $320, cardholder reports no travel",
    ],
    "Energy & Utilities": [
        "Transformer T-4 oil temp 92°C (alarm 85°C), dissolved gas analysis shows acetylene 180 ppm, load at 94% of rating",
        "Frequency deviation -0.3 Hz sustained 8 seconds, automatic load shedding stage 1 activated, 340 MW generation shortfall",
    ],
}

if not raw_input.strip():
    st.markdown(
        '<div style="background:rgba(66,133,244,0.06);border-radius:8px;padding:16px 20px;margin-top:4px;">'
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;font-weight:600;font-size:0.9rem;">'
        '<span class="material-symbols-outlined" style="font-size:20px;color:#4285F4;">route</span>'
        'How to use this demo'
        '</div>'
        '<div style="font-size:0.85rem;line-height:1.6;opacity:0.85;">'
        '<strong>1.</strong> Select a domain sector in the sidebar<br>'
        '<strong>2.</strong> Click <strong>Load Synthetic Data</strong> for a pre-built scenario, or paste your own text below<br>'
        '<strong>3.</strong> Click <strong>Analyze Event</strong> — Gemini returns structured JSON locked to the domain schema'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    examples = QUICK_EXAMPLES.get(sector, [])
    if examples:
        with st.expander(":material/edit_note: Or try a quick snippet", expanded=False):
            st.caption("Click to copy, then paste into the text area above.")
            for ex in examples:
                st.code(ex, language=None)

# ─────────────────────────────────────────────────────────────────────────────
# 4. GEMINI INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

if analyze_clicked:
    if not raw_input or not raw_input.strip():
        st.warning("Paste or type event data first, or click **Load Synthetic Data** to try an example.", icon=":material/edit_note:")
        st.stop()

    if st.session_state.credits <= 0:
        st.error("**Demo credits exhausted.** You've used all available analysis credits for this session. "
                 "Reload the page to reset.", icon=":material/toll:")
        st.stop()

    # Check for domain mismatch before spending a credit
    mismatch = _detect_domain_mismatch(raw_input, sector)
    if mismatch:
        st.warning(mismatch, icon=":material/swap_horiz:")
        st.stop()

    system_instruction = _build_system_instruction(cfg["domain_label"])
    with st.status(f"Calling **{MODEL_LABEL}** (`{MODEL_ID}`)…", expanded=True) as status:
        st.write("Connecting to Gemini API…")
        response = None
        try:
            st.write("Running structured inference…")
            t0 = time.perf_counter()
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=raw_input,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=schema_cls,
                ),
            )
            latency = time.perf_counter() - t0

            st.write("Response received — validating schema…")

            # The SDK parses JSON and validates against the Pydantic schema
            if response.parsed:
                result = response.parsed.model_dump()
            else:
                parsed = json.loads(response.text)
                validated = schema_cls(**parsed)
                result = validated.model_dump()

            # Deduct a credit on successful analysis
            st.session_state.credits -= 1

            # Persist results so exports survive reruns
            st.session_state.last_result = result
            st.session_state.last_latency = latency
            st.session_state.last_sector = sector

            # Track session history for analytics
            if "triage_history" not in st.session_state:
                st.session_state.triage_history = []
            top_key = list(result.keys())[0]
            st.session_state.triage_history.append({
                "run": len(st.session_state.triage_history) + 1,
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "domain": sector.split("(")[0].strip(),
                "latency": round(latency, 2),
                "manual_min": cfg.get("manual_minutes", 15),
                "top_field": top_key.replace("_", " ").title(),
                "top_value": str(result[top_key]),
            })

            status.update(label="Analysis complete", state="complete", expanded=False)

        except json.JSONDecodeError as e:
            status.update(label="JSON parse error", state="error")
            st.error(f"**JSON Decode Error** — The model returned malformed JSON.\n\n`{e}`", icon=":material/error:")
            with st.expander("Raw model response"):
                st.code(response.text if response else "No response captured", language="json")
            st.stop()
        except ValidationError as e:
            status.update(label="Schema validation error", state="error")
            st.error(f"**Schema Validation Error** — The JSON did not match the expected Pydantic model.\n\n```\n{e}\n```", icon=":material/error:")
            st.stop()
        except Exception as e:
            status.update(label="API Error", state="error")
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
                st.error("**Invalid API Key** — Please double-check the key you pasted in the sidebar.", icon=":material/vpn_key_alert:")
            else:
                st.error(f"**Error:** {error_msg}", icon=":material/error:")
            st.stop()

    # Results stored — fall through to display below

# ─────────────────────────────────────────────────────────────────────────────
# 5. OUTPUT DISPLAY — The "Architect's View"
#    Reads from session state so results persist across reruns (e.g. exports).
# ─────────────────────────────────────────────────────────────────────────────

if "last_result" in st.session_state and st.session_state.get("last_sector") == sector:
    result = st.session_state.last_result
    latency = st.session_state.last_latency

    st.divider()
    st.markdown(
        '<div class="icon-header">'
        '<span class="material-symbols-outlined filled" style="color:#4285F4;font-size:28px;">analytics</span>'
        '<h3 style="margin:0;">Triage Result</h3>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Top row: Key metrics (adaptive to sector) ────────────────────────────

    if sector == "Healthcare (HCLS)":
        m1, m2, m3, m4 = st.columns(4)
        priority = result["triage_priority"]
        with m1:
            st.markdown(f"### :{_severity_color(priority)}[{priority}]")
            st.caption("Triage Priority")
        with m2:
            st.metric("ESI Acuity", f"Level {result['esi_acuity_level']}")
        with m3:
            st.metric("Disposition", result["disposition"])
        with m4:
            st.metric("Latency", f"{latency:.2f} s")

    elif sector == "Industrial (Manufacturing)":
        m1, m2, m3, m4 = st.columns(4)
        severity = result["severity_level"]
        with m1:
            st.markdown(f"### :{_severity_color(severity)}[{severity}]")
            st.caption("Severity Level")
        with m2:
            st.metric("Safety Risk", result["safety_risk"])
        with m3:
            st.metric("Est. Downtime", f"{result['estimated_downtime_hours']:.1f} hrs")
        with m4:
            st.metric("Latency", f"{latency:.2f} s")

    elif sector == "Cybersecurity (SecOps)":
        m1, m2, m3, m4 = st.columns(4)
        threat = result["threat_level"]
        with m1:
            st.markdown(f"### :{_severity_color(threat)}[{threat}]")
            st.caption("Threat Level")
        with m2:
            st.metric("Response", result["recommended_response"])
        with m3:
            st.metric("Urgency Window", result["urgency_window"])
        with m4:
            st.metric("Latency", f"{latency:.2f} s")

    elif sector == "Financial Services (FinOps)":
        m1, m2, m3, m4 = st.columns(4)
        risk = result["risk_rating"]
        with m1:
            st.markdown(f"### :{_severity_color(risk)}[{risk}]")
            st.caption("Risk Rating")
        with m2:
            st.metric("Amount at Risk", f"${result['amount_at_risk_usd']:,.0f}")
        with m3:
            st.metric("Action", result["recommended_action"])
        with m4:
            st.metric("Latency", f"{latency:.2f} s")

    elif sector == "Energy & Utilities":
        m1, m2, m3, m4 = st.columns(4)
        alert = result["alert_priority"]
        with m1:
            st.markdown(f"### :{_severity_color(alert)}[{alert}]")
            st.caption("Alert Priority")
        with m2:
            st.metric("Customers Out", f"{result['customers_affected']:,}")
        with m3:
            st.metric("Est. Restoration", f"{result['estimated_restoration_hours']:.1f} hrs")
        with m4:
            st.metric("Latency", f"{latency:.2f} s")

    # ── Detail cards (adaptive to sector) ────────────────────────────────────
    st.markdown("---")

    if sector == "Healthcare (HCLS)":
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(f'<div class="section-label">{_mi("diagnosis", "Diagnosis Impression", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["diagnosis_impression"], icon=":material/ecg_heart:")
            st.markdown(f'<div class="section-label">{_mi("medical_services", "Specialist Referral", filled=True)}</div>', unsafe_allow_html=True)
            st.success(result["specialist_referral"], icon=":material/person:")
            st.markdown(f'<div class="section-label">{_mi("clinical_notes", "Suggested Action", filled=True)}</div>', unsafe_allow_html=True)
            st.warning(result["suggested_action"], icon=":material/assignment:")
        with d2:
            st.markdown(f'<div class="section-label">{_mi("monitor_heart", "Vitals Extracted", filled=True)}</div>', unsafe_allow_html=True)
            for v in result["vitals_extracted"]:
                st.markdown(f"- {v}")
            st.markdown(f'<div class="section-label">{_mi("medication", "Medications Administered", filled=True)}</div>', unsafe_allow_html=True)
            for med in result["medications_administered"]:
                st.markdown(f"- {med}")
        with d3:
            st.markdown(f'<div class="section-label">{_mi("warning", "Risk Factors", filled=True)}</div>', unsafe_allow_html=True)
            for rf in result["risk_factors"]:
                st.markdown(f"- {rf}")
            st.markdown(f'<div class="section-label">{_mi("allergy", "Allergies Noted", filled=True)}</div>', unsafe_allow_html=True)
            for a in result["allergies_noted"]:
                st.markdown(f"- {a}")

    elif sector == "Industrial (Manufacturing)":
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(f'<div class="section-label">{_mi("settings", "Affected Component", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["affected_component"], icon=":material/memory:")
            st.markdown(f'<div class="section-label">{_mi("build", "Maintenance Action", filled=True)}</div>', unsafe_allow_html=True)
            st.warning(result["maintenance_action"], icon=":material/handyman:")
            st.markdown(f'<div class="section-label">{_mi("trending_down", "Failure Probability", filled=True)}</div>', unsafe_allow_html=True)
            prob = result["failure_probability_percent"]
            st.progress(min(prob / 100, 1.0), text=f"{prob:.1f}%")
        with d2:
            st.markdown(f'<div class="section-label">{_mi("sensors", "Sensor Readings", filled=True)}</div>', unsafe_allow_html=True)
            for sr in result["sensor_readings"]:
                st.markdown(f"- {sr}")
            st.markdown(f'<div class="section-label">{_mi("shopping_cart", "Parts Required", filled=True)}</div>', unsafe_allow_html=True)
            for p in result["parts_required"]:
                st.markdown(f"- {p}")
        with d3:
            st.markdown(f'<div class="section-label">{_mi("search", "Root Cause Hypothesis", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["root_cause_hypothesis"], icon=":material/lightbulb:")

    elif sector == "Cybersecurity (SecOps)":
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(f'<div class="section-label">{_mi("target", "Attack Vector", filled=True)}</div>', unsafe_allow_html=True)
            st.error(result["attack_vector"], icon=":material/gpp_maybe:")
            st.markdown(f'<div class="section-label">{_mi("shield", "MITRE ATT&CK Techniques", filled=True)}</div>', unsafe_allow_html=True)
            for t in result["mitre_attack_techniques"]:
                st.markdown(f"- `{t}`")
        with d2:
            st.markdown(f'<div class="section-label">{_mi("devices", "Affected Assets", filled=True)}</div>', unsafe_allow_html=True)
            for asset in result["affected_assets"]:
                st.markdown(f"- {asset}")
            st.markdown(f'<div class="section-label">{_mi("fingerprint", "Indicators of Compromise", filled=True)}</div>', unsafe_allow_html=True)
            for ioc in result["indicators_of_compromise"]:
                st.markdown(f"- `{ioc}`")
            st.markdown(f'<div class="section-label">{_mi("database", "Data at Risk", filled=True)}</div>', unsafe_allow_html=True)
            st.warning(result["data_at_risk"], icon=":material/folder_off:")
        with d3:
            st.markdown(f'<div class="section-label">{_mi("checklist", "Containment Steps", filled=True)}</div>', unsafe_allow_html=True)
            for i, step in enumerate(result["containment_steps"], 1):
                st.markdown(f"**{i}.** {step}")
            st.markdown(f'<div class="section-label">{_mi("psychology", "Threat Hypothesis", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["threat_hypothesis"], icon=":material/lightbulb:")

    elif sector == "Financial Services (FinOps)":
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(f'<div class="section-label">{_mi("swap_horiz", "Transaction Type", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["transaction_type"], icon=":material/receipt_long:")
            st.markdown(f'<div class="section-label">{_mi("public", "Jurisdiction Risk", filled=True)}</div>', unsafe_allow_html=True)
            st.warning(result["jurisdiction_risk"], icon=":material/travel_explore:")
            st.markdown(f'<div class="section-label">{_mi("escalator_warning", "Escalation Path", filled=True)}</div>', unsafe_allow_html=True)
            st.success(result["escalation_path"], icon=":material/arrow_upward:")
        with d2:
            st.markdown(f'<div class="section-label">{_mi("group", "Entities Involved", filled=True)}</div>', unsafe_allow_html=True)
            for e in result["entities_involved"]:
                st.markdown(f"- {e}")
            st.markdown(f'<div class="section-label">{_mi("flag", "Flagged Anomalies", filled=True)}</div>', unsafe_allow_html=True)
            for a in result["flagged_anomalies"]:
                st.markdown(f"- {a}")
        with d3:
            st.markdown(f'<div class="section-label">{_mi("gavel", "Regulatory Flags", filled=True)}</div>', unsafe_allow_html=True)
            for r in result["regulatory_flags"]:
                st.markdown(f"- {r}")
            st.markdown(f'<div class="section-label">{_mi("policy", "Fraud Hypothesis", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["fraud_hypothesis"], icon=":material/lightbulb:")

    elif sector == "Energy & Utilities":
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(f'<div class="section-label">{_mi("electrical_services", "Affected System", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["affected_system"], icon=":material/power:")
            st.markdown(f'<div class="section-label">{_mi("speed", "Grid Impact", filled=True)}</div>', unsafe_allow_html=True)
            st.metric("Load Lost", f"{result['grid_impact_mw']:.1f} MW")
            st.markdown(f'<div class="section-label">{_mi("cloud", "Weather Factor", filled=True)}</div>', unsafe_allow_html=True)
            st.warning(result["weather_factor"], icon=":material/thunderstorm:")
        with d2:
            st.markdown(f'<div class="section-label">{_mi("error", "Fault Indicators", filled=True)}</div>', unsafe_allow_html=True)
            for fi in result["fault_indicators"]:
                st.markdown(f"- {fi}")
            st.markdown(f'<div class="section-label">{_mi("dangerous", "Safety Hazards", filled=True)}</div>', unsafe_allow_html=True)
            for sh in result["safety_hazards"]:
                st.markdown(f"- {sh}")
        with d3:
            st.markdown(f'<div class="section-label">{_mi("engineering", "Recommended Action", filled=True)}</div>', unsafe_allow_html=True)
            st.success(result["recommended_action"], icon=":material/task_alt:")
            st.markdown(f'<div class="section-label">{_mi("search", "Root Cause Hypothesis", filled=True)}</div>', unsafe_allow_html=True)
            st.info(result["root_cause_hypothesis"], icon=":material/lightbulb:")

    # ── Actions bar ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div class="section-label">'
        '<span class="material-symbols-outlined filled" style="font-size:20px;">share</span>'
        ' Export &amp; Share Results'
        '</div>',
        unsafe_allow_html=True,
    )

    # Build formatted summary for sharing
    _top_key = list(result.keys())[0]
    _top_val = result[_top_key]
    _summary_lines = [f"*Vertex Triage — {cfg['title']}*"]
    _summary_lines.append(f"Model: {MODEL_LABEL} | Latency: {latency:.2f}s")
    _summary_lines.append("─" * 36)
    for k, v in result.items():
        label = k.replace("_", " ").title()
        if isinstance(v, list):
            _summary_lines.append(f"*{label}:*")
            for item in v:
                _summary_lines.append(f"  • {item}")
        elif isinstance(v, float):
            _summary_lines.append(f"*{label}:* {v:,.2f}")
        else:
            _summary_lines.append(f"*{label}:* {v}")
    slack_text = "\n".join(_summary_lines)

    # Build CSV content
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["Field", "Value"])
    for k, v in result.items():
        label = k.replace("_", " ").title()
        if isinstance(v, list):
            writer.writerow([label, "; ".join(str(i) for i in v)])
        else:
            writer.writerow([label, str(v)])
    csv_data = csv_buf.getvalue()

    json_str = json.dumps(result, indent=2)

    a1, a2, a3, a4 = st.columns(4)

    with a1:
        st.download_button(
            "Download JSON",
            data=json_str,
            file_name=f"triage_{sector.split('(')[0].strip().lower().replace(' ', '_')}_{int(time.time())}.json",
            mime="application/json",
            use_container_width=True,
            icon=":material/download:",
        )

    with a2:
        st.download_button(
            "Download CSV",
            data=csv_data,
            file_name=f"triage_{sector.split('(')[0].strip().lower().replace(' ', '_')}_{int(time.time())}.csv",
            mime="text/csv",
            use_container_width=True,
            icon=":material/table_view:",
        )

    with a3:
        _clipboard_button(slack_text, "Copy for Slack", "content_copy", "slack")

    with a4:
        jira_text = slack_text.replace("*", "**")
        _clipboard_button(jira_text, "Copy for Jira / Email", "mail", "jira")

    # ── Raw JSON payload ─────────────────────────────────────────────────────
    with st.expander(":material/code: View Raw JSON Payload", expanded=False):
        st.json(result)

    # ── Speed comparison ──────────────────────────────────────────────────────
    manual_min = cfg.get("manual_minutes", 15)
    manual_label = cfg.get("manual_label", "Avg manual review")
    manual_sec = manual_min * 60
    speedup = manual_sec / latency if latency > 0 else 0

    st.markdown("---")
    st.markdown(
        '<div class="section-label">'
        '<span class="material-symbols-outlined filled" style="font-size:20px;">speed</span>'
        ' Speed Comparison'
        '</div>',
        unsafe_allow_html=True,
    )

    gemini_pct = min(latency / manual_sec * 100, 100)

    st.markdown(
        f"""
        <div style="background:#f8f9fa;border-radius:10px;padding:20px 24px;margin-top:8px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;">
                <span style="font-weight:600;font-size:0.95rem;">
                    <span class="material-symbols-outlined filled" style="font-size:18px;color:#4285F4;">bolt</span>
                    Gemini 3.0 Pro
                </span>
                <span style="font-weight:700;font-size:1.1rem;color:#4285F4;">{latency:.1f}s</span>
            </div>
            <div style="background:#e8eaed;border-radius:6px;height:14px;overflow:hidden;margin-bottom:20px;">
                <div style="background:linear-gradient(90deg,#4285F4,#34A853);height:100%;
                            border-radius:6px;width:{max(gemini_pct, 1.5):.1f}%;
                            transition:width 0.6s ease;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;">
                <span style="font-weight:600;font-size:0.95rem;">
                    <span class="material-symbols-outlined" style="font-size:18px;color:#999;">person</span>
                    {manual_label}
                </span>
                <span style="font-weight:700;font-size:1.1rem;color:#999;">{manual_min} min</span>
            </div>
            <div style="background:#e8eaed;border-radius:6px;height:14px;overflow:hidden;margin-bottom:16px;">
                <div style="background:#bdc1c6;height:100%;border-radius:6px;width:100%;"></div>
            </div>
            <div style="text-align:center;padding-top:4px;border-top:1px solid #e8eaed;">
                <span style="font-size:1.5rem;font-weight:800;color:#34A853;">{speedup:,.0f}×</span>
                <span style="font-size:0.9rem;color:#5f6368;"> faster than manual triage</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Session Analytics ─────────────────────────────────────────────────────
    history = st.session_state.get("triage_history", [])

    if len(history) >= 1:
        st.markdown("---")
        st.markdown(
            '<div class="section-label">'
            '<span class="material-symbols-outlined filled" style="font-size:20px;">monitoring</span>'
            ' Session Analytics'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Cumulative metrics row ────────────────────────────────────────
        total_runs = len(history)
        avg_latency = sum(h["latency"] for h in history) / total_runs
        total_manual_saved_sec = sum(h["manual_min"] * 60 - h["latency"] for h in history)
        total_manual_saved_min = total_manual_saved_sec / 60
        domains_used = len(set(h["domain"] for h in history))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(":material/counter_1: Triages Run", total_runs)
        m2.metric(":material/avg_pace: Avg Latency", f"{avg_latency:.1f}s")
        m3.metric(":material/timer: Time Saved", f"{total_manual_saved_min:.0f} min")
        m4.metric(":material/domain: Domains Used", domains_used)

    # ── ROI Projector ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div class="section-label">'
        '<span class="material-symbols-outlined filled" style="font-size:20px;">calculate</span>'
        ' ROI Projector'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("Estimate annual savings if this triage pattern were deployed at scale.")

    roi1, roi2 = st.columns(2)
    with roi1:
        daily_volume = st.slider(
            "Daily triage events",
            min_value=10, max_value=5000, value=200, step=10,
            help="How many events your team triages per day.",
        )
    with roi2:
        hourly_cost = st.slider(
            "Analyst hourly cost ($)",
            min_value=25, max_value=250, value=75, step=5,
            help="Fully loaded cost per analyst hour.",
        )

    manual_hrs_per_event = manual_min / 60
    gemini_hrs_per_event = avg_latency / 3600 if len(history) >= 1 else latency / 3600
    annual_events = daily_volume * 260  # business days

    manual_annual_hrs = annual_events * manual_hrs_per_event
    gemini_annual_hrs = annual_events * gemini_hrs_per_event
    saved_hrs = manual_annual_hrs - gemini_annual_hrs
    saved_cost = saved_hrs * hourly_cost

    r1, r2, r3 = st.columns(3)
    r1.metric(":material/schedule: Annual Hours Saved", f"{saved_hrs:,.0f} hrs")
    r2.metric(":material/payments: Annual Cost Savings", f"${saved_cost:,.0f}")
    r3.metric(":material/groups: FTE Equivalent Freed", f"{saved_hrs / 2080:.1f}")

    # Visual savings breakdown
    st.markdown(
        f"""
        <div style="background:#f8f9fa;border-radius:10px;padding:16px 24px;margin-top:8px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="font-size:0.85rem;color:#5f6368;">Manual cost @ {daily_volume} events/day</span>
                <span style="font-weight:700;color:#EA4335;">${manual_annual_hrs * hourly_cost:,.0f}/yr</span>
            </div>
            <div style="background:#e8eaed;border-radius:6px;height:12px;overflow:hidden;margin-bottom:16px;">
                <div style="background:#EA4335;height:100%;border-radius:6px;width:100%;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <span style="font-size:0.85rem;color:#5f6368;">With Gemini automation</span>
                <span style="font-weight:700;color:#34A853;">${gemini_annual_hrs * hourly_cost:,.0f}/yr</span>
            </div>
            <div style="background:#e8eaed;border-radius:6px;height:12px;overflow:hidden;margin-bottom:12px;">
                <div style="background:#34A853;height:100%;border-radius:6px;
                            width:{max(gemini_annual_hrs / manual_annual_hrs * 100, 0.5):.2f}%;"></div>
            </div>
            <div style="text-align:center;padding-top:8px;border-top:1px solid #e8eaed;">
                <span style="font-size:0.8rem;color:#5f6368;">
                    Based on <strong>{annual_events:,}</strong> events/yr ·
                    <strong>{manual_min} min</strong> manual avg ·
                    <strong>${hourly_cost}/hr</strong> analyst cost
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
