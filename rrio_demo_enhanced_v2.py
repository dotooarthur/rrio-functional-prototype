import time
import textwrap
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="RRIO Functional Prototype",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem;}
.main-title {font-size: 2.1rem; font-weight: 700; color: #12355B; margin-bottom: 0.15rem;}
.subtle {color: #5b6573; font-size: 1rem; margin-bottom: 0.8rem;}
.section-box {
    background: #ffffff;
    border: 1px solid #d9e2f0;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 18px;
}
.insight-box {
    background: #eef6ff;
    border-left: 6px solid #2563eb;
    padding: 14px 16px;
    border-radius: 10px;
    margin-bottom: 10px;
}
.trace-box {
    background: #f8fafc;
    border: 1px solid #d9e2f0;
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.lesson-box {
    background: #fcfdff;
    border: 1px solid #d9e2f0;
    border-radius: 14px;
    padding: 18px;
    margin-top: 10px;
}
.small-note {font-size: 0.9rem; color: #667085;}
.stMetric {
    background: #f7f9fc;
    border: 1px solid #d9e2f0;
    padding: 10px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Constants
# -----------------------------
REQUIRED_COLS = {"student_id", "standard", "item", "skill", "correct"}
THRESHOLD_SUPPORT = 0.70

# -----------------------------
# Helpers
# -----------------------------
def load_data(uploaded_file):
    if uploaded_file is None:
        try:
            return pd.read_csv("rrio_demo_sample_v2.csv")
        except FileNotFoundError:
            st.error("Sample data file not found. Please upload a CSV.")
            st.stop()
    return pd.read_csv(uploaded_file)

def normalize(df):
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    return out

def validate(df):
    missing = REQUIRED_COLS - set(df.columns)
    return sorted(missing)

def compute_results(df):
    if df.empty:
        raise ValueError("Uploaded file contains no rows.")

    df = df.copy()
    df["correct"] = pd.to_numeric(df["correct"], errors="coerce").fillna(0).astype(float)

    standards = (
        df.groupby("standard", as_index=False)["correct"]
        .mean()
        .rename(columns={"correct": "accuracy"})
        .sort_values("accuracy")
    )

    skills = (
        df.groupby(["standard", "skill"], as_index=False)["correct"]
        .mean()
        .rename(columns={"correct": "accuracy"})
        .sort_values(["standard", "accuracy"])
    )

    if standards.empty or skills.empty:
        raise ValueError("Unable to compute standard or skill summaries from the uploaded data.")

    weakest_standard = standards.iloc[0]["standard"]
    weakest_skill_candidates = skills[skills["standard"] == weakest_standard].sort_values("accuracy")

    if weakest_skill_candidates.empty:
        raise ValueError("Unable to identify a weakest skill for the selected standard.")

    weakest_skill_row = weakest_skill_candidates.iloc[0]
    weakest_skill = weakest_skill_row["skill"]

    student_perf = df.groupby("student_id", as_index=False)["correct"].mean()
    support_count = int((student_perf["correct"] < THRESHOLD_SUPPORT).sum())
    mastery_pct = round(df["correct"].mean() * 100, 1)

    return {
        "mastery_pct": mastery_pct,
        "students": int(df["student_id"].nunique()),
        "responses": int(len(df)),
        "support_count": support_count,
        "weakest_standard": weakest_standard,
        "weakest_skill": weakest_skill,
        "weakest_skill_pct": round(float(weakest_skill_row["accuracy"]) * 100, 1),
        "standards": standards,
        "skills": skills,
        "student_perf": student_perf,
    }

def build_evidence_trace(df, results, threshold=THRESHOLD_SUPPORT):
    skill_mask = (
        (df["standard"] == results["weakest_standard"]) &
        (df["skill"] == results["weakest_skill"])
    )
    skill_accuracy = round(df.loc[skill_mask, "correct"].mean() * 100, 1)

    below_threshold = int((results["student_perf"]["correct"] < threshold).sum())

    return {
        "selected_standard": results["weakest_standard"],
        "selected_skill": results["weakest_skill"],
        "skill_accuracy": skill_accuracy,
        "students_below_threshold": below_threshold,
        "threshold_pct": int(threshold * 100),
    }

def group_students(df):
    student_perf = df.groupby("student_id", as_index=False)["correct"].mean()
    student_perf["group"] = student_perf["correct"].apply(
        lambda x: "Reteach Group" if x < 0.50 else
                  "Near Mastery" if x < 0.80 else
                  "On Track"
    )
    student_perf["accuracy_pct"] = (student_perf["correct"] * 100).round(1)
    return student_perf

def misconception_text(skill):
    s = str(skill).lower()
    bank = {
        "inverse operations": "Students are selecting the wrong inverse operation when trying to isolate the variable.",
        "two-step equations": "Students are undoing only one step or are not preserving equality across both sides.",
        "division equations": "Students confuse dividing by the coefficient with subtracting the coefficient.",
        "fraction equations": "Students are avoiding fraction-clearing strategies and losing equation balance.",
        "graph interpretation": "Students can read points but struggle to connect slope or change to meaning in context.",
    }
    return bank.get(s, "Students show inconsistent understanding and need explicit modeling plus guided practice.")

def lesson_text(standard, skill, ell=False, ese=False, coteach=False):
    skill_lower = str(skill).lower()

    if skill_lower == "inverse operations":
        warmup = "Review 2 worked examples and identify which inverse operation was applied incorrectly."
        ido = "Teacher models solving equations step-by-step, emphasizing how to choose the correct inverse operation."
        wedo = "Students solve 2 equations together and explain why the same operation must be applied to both sides."
        youdo = "Students complete 3 one-step and 2 two-step equations independently."
        exit_ticket = "Solve 2 equations and explain which inverse operation you used."
    elif skill_lower == "division equations":
        warmup = "Compare two equations and decide whether to divide, subtract, or multiply to isolate the variable."
        ido = "Teacher uses visual coefficient models to show why division isolates the variable."
        wedo = "Students work through coefficient-based equations with guided questioning."
        youdo = "Students complete 4 division equations with increasing complexity."
        exit_ticket = "Solve 2 division equations and justify each step."
    elif skill_lower == "graph interpretation":
        warmup = "Look at two graphs and describe how slope changes the situation."
        ido = "Teacher models how to connect graph features to real-world meaning."
        wedo = "Students compare two graphs and explain differences in rate of change."
        youdo = "Students answer 3 graph interpretation questions independently."
        exit_ticket = "Interpret one graph and explain what the slope means in context."
    elif skill_lower == "two-step equations":
        warmup = "Spot the step that was skipped in two worked two-step equation examples."
        ido = "Teacher models undoing operations in the correct order while preserving equality."
        wedo = "Students solve 2 two-step equations together with verbal reasoning."
        youdo = "Students complete 4 two-step equations independently."
        exit_ticket = "Solve 2 two-step equations and explain the order of operations used."
    else:
        warmup = "Review one solved example and identify the mistake."
        ido = "Teacher models 2 problems with think-aloud reasoning."
        wedo = "Guided practice with partner discussion and quick checks."
        youdo = "3 independent practice items aligned to the weak skill."
        exit_ticket = "2 short items plus 1 explanation prompt."

    overlays = []
    if ell:
        overlays.append("ELL support: pre-teach vocabulary with sentence stems and visual examples.")
    if ese:
        overlays.append("ESE support: chunk the process, model each step, and provide one worked example.")
    if coteach:
        overlays.append("Co-teach support: one teacher models while the other runs a targeted small-group check.")
    if not overlays:
        overlays.append("No additional support overlays selected.")

    overlay_lines = "\n".join([f"- {x}" for x in overlays])

    return textwrap.dedent(f"""
    **Lesson Focus:** {standard}

    **Targeted Skill:** {skill}

    **Likely Misconception**  
    {misconception_text(skill)}

    **Next-Day Lesson**
    - **Warm-Up (5 min):** {warmup}
    - **I Do (10 min):** {ido}
    - **We Do (12 min):** {wedo}
    - **You Do (10 min):** {youdo}
    - **Exit Ticket (5 min):** {exit_ticket}

    **Recommended Supports**
    {overlay_lines}

    **Teacher Review Reminder**  
    This is a prototype-generated instructional draft. Teacher approval is required before classroom use.
    """).strip()

def materials_df(skill):
    return pd.DataFrame([
        {"Material": "Guided Notes", "Purpose": f"Step-by-step scaffold for {skill}"},
        {"Material": "Mini Practice Set", "Purpose": f"3 reteach problems focused on {skill}"},
        {"Material": "Checks for Understanding", "Purpose": "Whole-group or whiteboard quick checks"},
        {"Material": "Exit Ticket", "Purpose": f"Measure improvement after reteach of {skill}"},
        {"Material": "Answer Key", "Purpose": "Teacher-only answers and suggested explanations"},
    ])

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("RRIO Functional Prototype")
st.sidebar.caption("Rapid Response Instruction Optimizer")
st.sidebar.selectbox("Grade Band", ["6-8", "9-12", "K-5"], index=0)
st.sidebar.selectbox("Subject", ["Mathematics", "Science", "ELA", "Social Studies"], index=0)
st.sidebar.selectbox("Assessment Type", ["Exit Ticket", "Quiz", "Checkpoint"], index=0)
ell = st.sidebar.toggle("ELL Support", value=True)
ese = st.sidebar.toggle("ESE Support", value=True)
coteach = st.sidebar.toggle("Co-Teach Planning", value=False)

# -----------------------------
# Data load
# -----------------------------
uploaded = st.file_uploader("Upload classroom assessment data (.csv)", type=["csv"])
df = normalize(load_data(uploaded))
missing = validate(df)

if missing:
    st.error("Missing required columns: " + ", ".join(missing))
    st.stop()

try:
    results = compute_results(df)
except ValueError as e:
    st.error(str(e))
    st.stop()

current_signature = (
    len(df),
    df["student_id"].nunique(),
    ell,
    ese,
    coteach
)

if "generated" not in st.session_state:
    st.session_state.generated = False

if "input_signature" not in st.session_state:
    st.session_state.input_signature = current_signature

if st.session_state.input_signature != current_signature:
    st.session_state.generated = False
    st.session_state.input_signature = current_signature

evidence = build_evidence_trace(df, results)
student_groups = group_students(df)
lesson = lesson_text(
    results["weakest_standard"],
    results["weakest_skill"],
    ell=ell,
    ese=ese,
    coteach=coteach
)
materials = materials_df(results["weakest_skill"])

# -----------------------------
# Header
# -----------------------------
st.markdown('<div class="main-title">RRIO: From Data to Instruction — Instantly</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtle">A functional prototype showing how RRIO converts classroom evidence into a grounded, reviewable next-day instructional response.</div>',
    unsafe_allow_html=True
)
st.caption("This prototype uses performance thresholds and skill-based instructional templates to simulate RRIO’s evidence-to-instruction logic.")

# -----------------------------
# Section 1: Upload
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("1. Upload Classroom Data")
st.success(f"Loaded {len(df)} response rows from {df['student_id'].nunique()} students.")
st.dataframe(df.head(12), use_container_width=True)
with open("rrio_demo_sample_v2.csv", "rb") as f:
    st.download_button(
        "Download sample CSV",
        data=f.read(),
        file_name="rrio_demo_sample_v2.csv",
        mime="text/csv"
    )
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Section 2: Analysis summary
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("2. RRIO Analysis Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Class Mastery", f"{results['mastery_pct']}%")
c2.metric("Students Needing Support", results["support_count"])
c3.metric("Priority Standard", "Linear Equations" if "equation" in results["weakest_standard"].lower() else results["weakest_standard"])
c4.metric("Top Skill Accuracy", f"{results['weakest_skill_pct']}%")

st.markdown(
    f'<div class="insight-box"><strong>Likely Skill Gap:</strong> {results["weakest_skill"]}<br><span class="small-note">Full priority standard: {results["weakest_standard"]}</span></div>',
    unsafe_allow_html=True
)

skill_df = results["skills"].copy()
skill_df["accuracy_pct"] = (skill_df["accuracy"] * 100).round(1)
st.dataframe(
    skill_df[["standard", "skill", "accuracy_pct"]].sort_values(["standard", "accuracy_pct"]),
    use_container_width=True
)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Section 3: Student groups
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("3. Student Support Groups")
group_counts = student_groups["group"].value_counts().rename_axis("Group").reset_index(name="Students")
st.dataframe(group_counts, use_container_width=True)
st.bar_chart(group_counts.set_index("Group")["Students"], use_container_width=True)
st.caption("Prototype grouping thresholds: Reteach < 50%, Near Mastery 50–79%, On Track ≥ 80%.")
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Section 4: Generate plan
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("4. Generate RRIO Plan")
st.caption("This instructional response is grounded in the lowest-performing standard and skill in the uploaded data.")

st.markdown(
    f"""
<div class="trace-box">
<strong>Selected Standard:</strong> {evidence["selected_standard"]}<br>
<strong>Selected Skill:</strong> {evidence["selected_skill"]}<br>
<strong>Class Accuracy for Selected Skill:</strong> {evidence["skill_accuracy"]}%<br>
<strong>Students Below Threshold ({evidence["threshold_pct"]}%):</strong> {evidence["students_below_threshold"]}
</div>
""",
    unsafe_allow_html=True
)

if st.button("Generate Instructional Response", type="primary"):
    feed = st.empty()
    steps = [
        f"Loaded {results['responses']} response rows for {results['students']} students.",
        f"Computed overall class mastery: {results['mastery_pct']}%.",
        f"Priority standard selected: {results['weakest_standard']}.",
        f"Detected lowest skill accuracy in {results['weakest_skill']}: {results['weakest_skill_pct']}%.",
        f"Flagged {results['support_count']} students below the support threshold of {evidence['threshold_pct']}%.",
        "Generated a skill-sensitive next-day lesson draft with supports and review workflow."
    ]
    shown = ""
    for step in steps:
        shown += f"• {step}\n"
        feed.info(shown)
        time.sleep(0.45)
    st.session_state.generated = True

if st.session_state.generated:
    st.markdown('<div class="lesson-box">', unsafe_allow_html=True)
    st.markdown(lesson)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Section 5: Materials preview
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("5. Materials Preview & Export")
st.dataframe(materials, use_container_width=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Guided Notes")
    st.info(f"""
Step 1: Identify the target skill: {results["weakest_skill"]}  
Step 2: Review the likely misconception  
Step 3: Apply the modeled strategy  
Step 4: Check your answer and explain your reasoning
""")

with col2:
    st.markdown("### Exit Ticket")
    st.success(f"""
1. Complete one problem targeting **{results["weakest_skill"]}**  
2. Explain the reasoning you used  
3. Identify one mistake a student might make and correct it
""")

with col3:
    st.markdown("### Answer Key")
    st.warning("""
- Correct answer should show the correct operation sequence  
- Reasoning should match the modeled process  
- Student explanation should justify why the step preserves equivalence
""")

lesson_export = lesson.replace("**", "")
st.download_button(
    "Download lesson draft (.txt)",
    data=lesson_export,
    file_name="rrio_lesson_draft.txt",
    mime="text/plain"
)
st.download_button(
    "Download materials pack (.csv)",
    data=materials.to_csv(index=False).encode("utf-8"),
    file_name="rrio_materials_pack.csv",
    mime="text/csv"
)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Section 6: Teacher review
# -----------------------------
st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.subheader("6. Teacher Review, Edit and Approval")
st.info("RRIO is a teacher-support prototype. All outputs require teacher review before classroom use.")

notes = st.text_area(
    "Teacher edits / notes",
    value="Adjust pacing for small-group reteach and add one extra worked example.",
    height=130
)
approved = st.checkbox("I have reviewed this instructional draft.")

if approved:
    st.success("Draft approved for export.")
else:
    st.warning("Draft not yet approved.")

review_df = pd.DataFrame([
    {"Field": "Priority Standard", "Value": evidence["selected_standard"]},
    {"Field": "Target Skill", "Value": evidence["selected_skill"]},
    {"Field": "Students Below Threshold", "Value": evidence["students_below_threshold"]},
    {"Field": "Approval Status", "Value": "Approved" if approved else "Pending"},
])

st.markdown("### Review Snapshot")
st.dataframe(review_df, use_container_width=True)
st.write("**Saved note:**")
st.write(notes)
st.markdown('</div>', unsafe_allow_html=True)
