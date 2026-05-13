import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import base64
from fpdf import FPDF
import io
import tempfile
import os

st.set_page_config(
    page_title="DEC | Data Quality Dashboard",
    page_icon="📊",
    layout="wide"
)

# ── BACKGROUND IMAGE ──
def get_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

img = get_base64("bg.jpg")

st.markdown(f"""
<style>
.stApp {{
    background-image: url("data:image/png;base64,{img}");
    background-size: 60%;
    background-repeat: no-repeat;
    background-position: center center;
    background-attachment: fixed;
    background-blend-mode: overlay;
    background-color: rgba(255, 255, 255, 0.50);
}}

/* ── COLORED DOWNLOAD BUTTONS ── */
div.stDownloadButton > button {{
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
    font-weight: 600 !important;
    width: 100% !important;
    transition: opacity 0.2s ease !important;
}}
div.stDownloadButton > button:hover {{
    opacity: 0.85 !important;
    transform: scale(1.02) !important;
}}
div.stDownloadButton:nth-of-type(1) > button {{
    background-color: #1E8449 !important;
}}
div.stDownloadButton:nth-of-type(2) > button {{
    background-color: #E67E22 !important;
}}
div.stDownloadButton:nth-of-type(3) > button {{
    background-color: #2E75B6 !important;
}}
</style>
""", unsafe_allow_html=True)

# ── DB CONFIG — SUPABASE ──
DB_CONFIG = {
    "host":     "db.qrftlbjubdinkolkwavi.supabase.co",
    "port":     6543,
    "database": "postgres",
    "user":     "postgres",
    "password": "Adityasingh2026",  # ← yahan apna pssword daalo
}

@st.cache_data(ttl=300)
def load_data():
    cfg = DB_CONFIG
    url = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    engine = create_engine(url)
    return pd.read_sql("SELECT * FROM exhibitors_raw", engine)

df = load_data()
total = len(df)

status_fields = {
    "Mobile1":  "phone_mobile1_status",
    "Email1":   "email1_status",
    "Website1": "website1_status",
    "Company":  "company_status",
    "City":     "city_status",
    "Country":  "country_status",
    "Category": "category_status",
}
status_fields = {k: v for k, v in status_fields.items() if v in df.columns}

clean   = (df["row_quality"] == "clean").sum()
partial = (df["row_quality"] == "partial").sum()
poor    = (df["row_quality"] == "poor").sum()
health  = round(clean / total * 100, 1)

# ── DUPLICATE DETECTION ──
dup_phone   = df["Mobile1"].dropna().duplicated().sum()
dup_email   = df["Email1"].dropna().duplicated().sum()
dup_company = df["CompanyName"].dropna().duplicated().sum()

# ── ACTIONABLE INSIGHTS ──
def get_insights(df, status_fields, total, clean, partial, poor, health,
                 dup_phone, dup_email, dup_company):
    insights = []
    for label, scol in status_fields.items():
        c = df[scol].value_counts()
        missing = int(c.get("missing", 0))
        invalid = int(c.get("invalid", 0))
        if missing > 0:
            insights.append(("⚠️", f"{missing:,} records have missing **{label}** - fill before outreach"))
        if invalid > 0:
            insights.append(("❌", f"{invalid:,} records have **{label}** in invalid format - needs cleaning"))
    if dup_phone > 0:
        insights.append(("🔁", f"{dup_phone:,} duplicate **phone numbers** found - merge or remove"))
    if dup_email > 0:
        insights.append(("🔁", f"{dup_email:,} duplicate **emails** found - deduplicate before campaign"))
    if dup_company > 0:
        insights.append(("🏢", f"{dup_company:,} duplicate **company names** found - consolidate records"))
    if health >= 80:
        insights.append(("🎉", f"Data health **{health}%** - excellent! This data is ready for campaign use"))
    elif health >= 50:
        insights.append(("💡", f"Data health **{health}%** - moderate. Use clean records, fix remaining"))
    else:
        insights.append(("🚨", f"Data health is only **{health}%** - major cleaning required before use"))
    return insights

insights = get_insights(df, status_fields, total, clean, partial, poor,
                        health, dup_phone, dup_email, dup_company)

# ── PDF EXPORT ──
def generate_pdf(total, clean, partial, poor, health,
                 dup_phone, dup_email, dup_company,
                 status_fields, df, insights):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_fill_color(31, 56, 100)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 10)
    pdf.cell(190, 12, "DIC 2026 - Data Quality Report", align="C")

    pdf.set_xy(10, 20)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(181, 212, 244)
    pdf.cell(190, 8, "Dairy Conference & Exhibition | Exhibitor Data Efficiency Report", align="C")

    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(46, 117, 182)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 8, "  SUMMARY", fill=True)
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)

    summary = [
        ("Total Records",   f"{total:,}"),
        ("Clean Records",   f"{clean:,}  ({health}%)"),
        ("Partial Records", f"{partial:,}"),
        ("Poor Records",    f"{poor:,}"),
        ("Overall Health",  f"{health}%"),
    ]
    for label, val in summary:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(80, 7, f"  {label}:", border="B")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(110, 7, val, border="B")
        pdf.ln()

    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(46, 117, 182)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 8, "  FIELD QUALITY SCORECARD", fill=True)
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(214, 228, 240)
    for h, w in [("Field",50),("Valid",35),("Invalid",35),("Missing",35),("Valid %",35)]:
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for label, scol in status_fields.items():
        c = df[scol].value_counts()
        v   = int(c.get("valid",   0))
        inv = int(c.get("invalid", 0))
        mis = int(c.get("missing", 0))
        pct = round(v / total * 100, 1)
        pdf.cell(50, 6, f"  {label}", border=1)
        pdf.cell(35, 6, f"{v:,}",   border=1, align="C")
        pdf.cell(35, 6, f"{inv:,}", border=1, align="C")
        pdf.cell(35, 6, f"{mis:,}", border=1, align="C")
        pdf.cell(35, 6, f"{pct}%",  border=1, align="C")
        pdf.ln()

    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(46, 117, 182)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 8, "  DUPLICATE DETECTION", fill=True)
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)

    for label, val in [
        ("Duplicate Phone Numbers", f"{dup_phone:,}"),
        ("Duplicate Emails",        f"{dup_email:,}"),
        ("Duplicate Company Names", f"{dup_company:,}"),
    ]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(100, 7, f"  {label}:", border="B")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(90, 7, val, border="B")
        pdf.ln()

    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(46, 117, 182)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 8, "  ACTIONABLE INSIGHTS", fill=True)
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)

    icon_map = {
        "⚠️": "[WARNING]",
        "❌": "[INVALID]",
        "🔁": "[DUPLICATE]",
        "🏢": "[COMPANY]",
        "🎉": "[GOOD]",
        "💡": "[INFO]",
        "🚨": "[ALERT]",
    }
    for icon, insight in insights:
        clean_text = insight.replace("**", "").replace("—", "-").replace("–", "-")
        clean_icon = icon_map.get(icon, "[*]")
        pdf.multi_cell(190, 6, f"  {clean_icon}  {clean_text}", border="B")
        pdf.ln(1)

    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(190, 10,
             "Dairy Conference & Exhibition 2026 | Data Quality Report | Built by Aditya Singh",
             align="C")

    return pdf.output()

# ── HEADER ──
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("cow.png", width=130, output_format="PNG")
with col_title:
    st.markdown("""
    <div style='background:linear-gradient(90deg,#1F3864,#2E75B6);
    padding:22px 28px;border-radius:12px;margin-bottom:20px;'>
    <h2 style='color:white;margin:0;font-size:1.6rem'>
    DCE 2026 - Data Quality Dashboard</h2>
    <p style='color:#B5D4F4;margin:6px 0 0;font-size:0.95rem'>
    Dairy Conference & Exhibition | Exhibitor Data Efficiency Report</p>
    </div>
    """, unsafe_allow_html=True)

# ── KPI CARDS ──
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("📦 Total Records", f"{total:,}")
k2.metric("✅ Clean",         f"{clean:,}")
k3.metric("⚠️ Partial",       f"{partial:,}")
k4.metric("❌ Poor",          f"{poor:,}")
k5.metric("🎯 Health Score",  f"{health}%")

st.markdown("---")

# ── ROW 1 — Gauge + Field Breakdown ──
g1, g2 = st.columns([1, 2])

with g1:
    st.markdown("### 🎯 Overall Health")
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health,
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar":  {"color": "#2E75B6"},
            "steps": [
                {"range": [0,  50], "color": "#FADBD8"},
                {"range": [50, 80], "color": "#FDEBD0"},
                {"range": [80,100], "color": "#D5F5E3"},
            ],
            "threshold": {
                "line": {"color": "#1E8449", "width": 3},
                "thickness": 0.75, "value": 80
            }
        }
    ))
    gauge.update_layout(height=250, margin=dict(t=20,b=0,l=20,r=20))
    st.plotly_chart(gauge, use_container_width=True)

with g2:
    st.markdown("### 📋 Field-wise Breakdown")
    rows = []
    for label, scol in status_fields.items():
        c = df[scol].value_counts()
        rows.append({
            "Field":   label,
            "Valid":   int(c.get("valid",   0)),
            "Invalid": int(c.get("invalid", 0)),
            "Missing": int(c.get("missing", 0)),
        })
    fdf = pd.DataFrame(rows)
    fig = px.bar(
        fdf.melt(id_vars="Field", value_vars=["Valid","Invalid","Missing"],
                 var_name="Status", value_name="Count"),
        x="Field", y="Count", color="Status", barmode="stack",
        color_discrete_map={"Valid":"#1E8449","Invalid":"#C0392B","Missing":"#E67E22"},
        height=250
    )
    fig.update_layout(margin=dict(t=10,b=10),
                      plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── ROW 2 — Country + Category ──
c1, c2 = st.columns(2)

with c1:
    st.markdown("### 🌍 Top Countries")
    if "Country" in df.columns:
        cdf = df["Country"].value_counts().head(10).reset_index()
        cdf.columns = ["Country","Count"]
        fig2 = px.bar(cdf, x="Count", y="Country", orientation="h",
                      color="Count",
                      color_continuous_scale=["#B5D4F4","#1F3864"],
                      height=320)
        fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                           coloraxis_showscale=False,
                           yaxis=dict(autorange="reversed"),
                           margin=dict(t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)

with c2:
    st.markdown("### 🏷️ Top Categories")
    if "Product Category" in df.columns:
        catdf = df["Product Category"].value_counts().head(10).reset_index()
        catdf.columns = ["Category","Count"]
        fig3 = px.pie(catdf, values="Count", names="Category",
                      hole=0.4, height=320,
                      color_discrete_sequence=px.colors.sequential.Blues_r)
        fig3.update_layout(margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ── ROW 3 — Sector + Business Type ──
s1, s2 = st.columns(2)

with s1:
    st.markdown("### 🏭 Top Sectors")
    if "Sector" in df.columns:
        secdf = df["Sector"].value_counts().head(8).reset_index()
        secdf.columns = ["Sector","Count"]
        fig5 = px.bar(secdf, x="Count", y="Sector", orientation="h",
                      color="Count",
                      color_continuous_scale=["#D5F5E3","#1E8449"],
                      height=300)
        fig5.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                           coloraxis_showscale=False,
                           yaxis=dict(autorange="reversed"),
                           margin=dict(t=10,b=10))
        st.plotly_chart(fig5, use_container_width=True)

with s2:
    st.markdown("### 💼 Business Type")
    if "Business TYpe" in df.columns:
        btdf = df["Business TYpe"].value_counts().head(8).reset_index()
        btdf.columns = ["Type","Count"]
        fig6 = px.pie(btdf, values="Count", names="Type",
                      hole=0.4, height=300,
                      color_discrete_sequence=px.colors.sequential.Purples_r)
        fig6.update_layout(margin=dict(t=10,b=10))
        st.plotly_chart(fig6, use_container_width=True)

st.markdown("---")

# ── ROW 4 — Field Health Scorecards ──
st.markdown("### 🏅 Field Health Scorecards")
cols = st.columns(len(status_fields))
for i, (label, scol) in enumerate(status_fields.items()):
    c = df[scol].value_counts()
    pct = round(c.get("valid", 0) / total * 100, 1)
    icon = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")
    cols[i].metric(
        f"{icon} {label}",
        f"{pct}%",
        f"✅{c.get('valid',0):,} ❌{c.get('invalid',0):,} ⚠️{c.get('missing',0):,}"
    )

st.markdown("---")

# ── DATA COMPLETENESS SCORECARD ──
st.markdown("### 📊 Data Completeness Scorecard")
comp_data = []
for label, scol in status_fields.items():
    c = df[scol].value_counts()
    v   = int(c.get("valid",   0))
    inv = int(c.get("invalid", 0))
    mis = int(c.get("missing", 0))
    pct = round(v / total * 100, 1)
    bar = "🟩" * int(pct // 10) + "⬜" * (10 - int(pct // 10))
    comp_data.append({
        "Field":    label,
        "Valid":    f"{v:,}",
        "Invalid":  f"{inv:,}",
        "Missing":  f"{mis:,}",
        "Valid %":  f"{pct}%",
        "Progress": bar,
        "Status":   "Good" if pct >= 80 else ("Fair" if pct >= 50 else "Poor")
    })
comp_df = pd.DataFrame(comp_data)
st.dataframe(comp_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ── DUPLICATE DETECTION ──
st.markdown("### 🔁 Duplicate Detection")
dp1, dp2, dp3 = st.columns(3)
dp1.metric("Duplicate Phones",    f"{dup_phone:,}")
dp2.metric("Duplicate Emails",    f"{dup_email:,}")
dp3.metric("Duplicate Companies", f"{dup_company:,}")

with st.expander("View Duplicate Phone Records"):
    dup_phone_df = df[df["Mobile1"].duplicated(keep=False) & df["Mobile1"].notna()]
    show = ["CompanyName","Mobile1","Email1","City","row_quality"]
    show = [c for c in show if c in dup_phone_df.columns]
    st.dataframe(dup_phone_df[show].sort_values("Mobile1").head(100),
                 use_container_width=True, height=200)

with st.expander("View Duplicate Email Records"):
    dup_email_df = df[df["Email1"].duplicated(keep=False) & df["Email1"].notna()]
    show = ["CompanyName","Email1","Mobile1","City","row_quality"]
    show = [c for c in show if c in dup_email_df.columns]
    st.dataframe(dup_email_df[show].sort_values("Email1").head(100),
                 use_container_width=True, height=200)

st.markdown("---")

# ── ROW 5 — Row Quality Donut + Data Preview ──
d1, d2 = st.columns([1, 2])

with d1:
    st.markdown("### Row Quality Split")
    rq = df["row_quality"].value_counts().reset_index()
    rq.columns = ["Quality","Count"]
    fig4 = px.pie(rq, values="Count", names="Quality", hole=0.5,
                  color="Quality",
                  color_discrete_map={
                      "clean":   "#1E8449",
                      "partial": "#E67E22",
                      "poor":    "#C0392B"
                  }, height=280)
    fig4.update_layout(margin=dict(t=10,b=10))
    st.plotly_chart(fig4, use_container_width=True)

with d2:
    st.markdown("### Data Preview")
    quality_filter = st.selectbox(
        "Filter by Quality",
        ["All", "clean", "partial", "poor"]
    )
    filtered = df if quality_filter == "All" else df[df["row_quality"] == quality_filter]
    show_cols = ["CompanyName","City","Country","Product Category",
                 "Mobile1","Email1","Website1","row_quality"]
    show_cols = [c for c in show_cols if c in df.columns]
    st.dataframe(filtered[show_cols].head(100),
                 use_container_width=True, height=250)
    st.caption(f"Showing {min(100, len(filtered)):,} of {len(filtered):,} records")

st.markdown("---")

# ── ACTIONABLE INSIGHTS ──
st.markdown("### Actionable Insights")
for icon, insight in insights:
    color = "#FADBD8" if icon == "❌" else ("#FDEBD0" if icon in ["⚠️","🔁","🏢"] else "#D5F5E3")
    st.markdown(f"""
    <div style='background:{color};padding:10px 16px;border-radius:8px;
    margin-bottom:8px;font-size:0.95rem'>
    {icon} {insight}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── SIDEBAR ──
with st.sidebar:
    st.image("cow.png", width=180, output_format="PNG")
    st.markdown("## Filters")

    if "Country" in df.columns:
        countries = ["All"] + sorted(df["Country"].dropna().unique().tolist())
        sel_country = st.selectbox("Country", countries)
        if sel_country != "All":
            df = df[df["Country"] == sel_country]

    if "Sector" in df.columns:
        sectors = ["All"] + sorted(df["Sector"].dropna().unique().tolist())
        sel_sector = st.selectbox("Sector", sectors)
        if sel_sector != "All":
            df = df[df["Sector"] == sel_sector]

    if "Product Category" in df.columns:
        cats = ["All"] + sorted(df["Product Category"].dropna().unique().tolist())
        sel_cat = st.selectbox("Category", cats)
        if sel_cat != "All":
            df = df[df["Product Category"] == sel_cat]

    st.markdown("---")
    st.markdown(f"**Total:** {total:,} records")
    st.markdown(f"**Clean:** {clean:,} ({health}%)")
    st.markdown(f"**DB:** `Supabase`")

st.markdown("---")

# ── DOWNLOAD BUTTONS ──
st.markdown("### Download Data")
dl1, dl2, dl3, dl4 = st.columns(4)

dl1.download_button(
    "✅ Clean Records",
    df[df["row_quality"]=="clean"].to_csv(index=False).encode(),
    "clean_exhibitors.csv", "text/csv",
    use_container_width=True
)
dl2.download_button(
    "⚠️ Issues Records",
    df[df["row_quality"]!="clean"].to_csv(index=False).encode(),
    "issues_exhibitors.csv", "text/csv",
    use_container_width=True
)
dl3.download_button(
    "📦 Full Data",
    df.to_csv(index=False).encode(),
    "full_exhibitors.csv", "text/csv",
    use_container_width=True
)

# ── PDF — HTML colored button ──
pdf_bytes = generate_pdf(total, clean, partial, poor, health,
                         dup_phone, dup_email, dup_company,
                         status_fields, df, insights)
pdf_b64 = base64.b64encode(bytes(pdf_bytes)).decode()
with dl4:
    st.markdown(f"""
    <a href="data:application/pdf;base64,{pdf_b64}"
       download="DIC_2026_Data_Quality_Report.pdf"
       style="
           display: block;
           background-color: #C0392B;
           color: white;
           text-align: center;
           padding: 10px 16px;
           border-radius: 8px;
           font-weight: 600;
           text-decoration: none;
           margin-top: 4px;
           font-size: 0.9rem;
       ">
       📄 Export PDF Report
    </a>
    """, unsafe_allow_html=True)

st.markdown("<br><center><small>Dairy Conference & Exhibition 2026 | Data Quality Report | Built by Aditya Singh</small></center>",
            unsafe_allow_html=True)