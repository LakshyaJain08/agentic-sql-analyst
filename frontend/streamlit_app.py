"""Agentic AI Data Analyst - Modern Executive Streamlit Dashboard.

Features:
- Dual Modes:
  1. 💬 Ask in Plain English (Natural Language to SQL with LangGraph)
  2. ⚡ Custom SQL Workbench (Execute, validate, visualize, and ask questions on user SQL)
- Follow-Up Data Q&A (Ask conversational questions about returned query results)
- Strict SQL AST security and read-only policy enforcement
- Evidence-grounded executive answers
- Interactive Plotly visualizations (Line, Bar, Scatter, KPI metrics)
- Data dictionary and relational schema explorer
- Live audit trail and telemetry
- Dual backend support: REST API or local embedded LangGraph engine
"""

import json
import time
from typing import Dict, Any, Optional, List
import pandas as pd
import plotly.io as pio
import streamlit as st

# Configure Streamlit Page
st.set_page_config(
    page_title="Agentic AI Data Analyst | NL to SQL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Modern Styling (Glassmorphic Dark Theme)
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    .main {
        background-color: #0B0F19;
    }

    /* Top Hero Header */
    .hero-container {
        padding: 1.5rem 2rem;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        backdrop-filter: blur(12px);
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60A5FA 0%, #A78BFA 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .hero-subtitle {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-top: 0.4rem;
    }

    /* Badges */
    .badge-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-right: 0.5rem;
    }
    .badge-blue { background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-green { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-purple { background: rgba(168, 85, 247, 0.15); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.3); }
    .badge-amber { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }

    /* Executive Answer Card */
    .answer-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px -2px rgba(99, 102, 241, 0.15);
    }

    .followup-card {
        background: rgba(30, 41, 59, 0.65);
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 12px;
        padding: 1.25rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    .answer-header {
        display: flex;
        align-items: center;
        font-size: 1.1rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.75rem;
    }

    /* Metric Tiles */
    .metric-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        color: #38BDF8;
        font-size: 1.8rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Code block styling */
    pre, code {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* St tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 8px 16px;
        font-weight: 600;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize Session State
if "current_result" not in st.session_state:
    st.session_state["current_result"] = None
if "followup_answers" not in st.session_state:
    st.session_state["followup_answers"] = []
if "query_history" not in st.session_state:
    st.session_state["query_history"] = []


# Helper: Execute Question via REST API or local embedded graph
def execute_query_pipeline(question: Optional[str] = None, sql: Optional[str] = None, provider: str = "gemini", api_key: Optional[str] = None) -> Dict[str, Any]:
    """Execute question or custom SQL via API if running, else directly via embedded LangGraph."""
    import httpx
    api_url = "http://localhost:8000/api/v1/ask"

    # Try REST API first
    try:
        payload = {
            "question": question,
            "sql": sql,
            "provider": provider,
            "api_key": api_key if api_key else None
        }
        resp = httpx.post(api_url, json=payload, timeout=25.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass  # Fallback to local embedded pipeline

    # Local Embedded Execution
    import os
    if api_key:
        if provider.lower() == "gemini":
            os.environ["GEMINI_API_KEY"] = api_key
        elif provider.lower() == "openai":
            os.environ["OPENAI_API_KEY"] = api_key

    # If user provided raw SQL directly
    if sql and sql.strip():
        from app.security.sql_validator import validate_and_sanitize_sql
        from app.database.executor import execute_query
        from app.analytics.chart_builder import build_chart_specification
        from app.analytics.metrics import compute_summary_statistics
        from app.agent.prompts import GROUNDED_ANSWER_PROMPT
        from app.agent.llm_factory import get_llm
        from langchain_core.messages import SystemMessage, HumanMessage

        val_res = validate_and_sanitize_sql(sql)
        if not val_res.is_valid:
            return {
                "status": "validation_failed",
                "question": question or "Custom SQL Query",
                "answer": f"**Security Policy Violation**: {val_res.error_message}",
                "sql": sql,
                "audit_trail": [{"step": "validate_user_sql", "error": val_res.error_message}]
            }

        exec_res = execute_query(val_res.sanitized_sql)
        if exec_res.status != "success":
            return {
                "status": "execution_error",
                "question": question or "Custom SQL Query",
                "answer": f"**Database Error ({exec_res.error_category})**: {exec_res.error_message}",
                "sql": val_res.sanitized_sql,
                "execution_ms": exec_res.execution_time_ms,
                "audit_trail": [{"step": "execute_user_sql", "error": exec_res.error_message}]
            }

        chart_spec = build_chart_specification(exec_res.columns, exec_res.column_types, exec_res.rows)
        stats = compute_summary_statistics(exec_res.columns, exec_res.rows)

        user_prompt_q = question if question else "Analyze the key insights and findings from this query result."
        prompt = GROUNDED_ANSWER_PROMPT.format(
            question=user_prompt_q,
            sql=val_res.sanitized_sql,
            columns=exec_res.columns,
            row_count=exec_res.row_count,
            rows_json=json.dumps(exec_res.rows[:25], default=str)
        )
        llm = get_llm(provider=provider, api_key=api_key)
        resp = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=user_prompt_q)])

        return {
            "status": "success",
            "question": user_prompt_q,
            "answer": resp.content,
            "sql": val_res.sanitized_sql,
            "columns": exec_res.columns,
            "rows": exec_res.rows,
            "row_count": exec_res.row_count,
            "execution_ms": exec_res.execution_time_ms,
            "chart": chart_spec,
            "summary_stats": stats,
            "audit_trail": [{"step": "custom_sql_executed"}]
        }

    # Standard Natural Language to SQL
    from app.agent.graph import agent_app
    state = {
        "question": question,
        "session_id": "streamlit-session",
        "conversation_history": [],
        "retry_count": 0,
        "audit_trail": []
    }
    final = agent_app.invoke(state)
    exec_data = final.get("execution_result") or {}

    return {
        "status": final.get("status", "success"),
        "question": question,
        "answer": final.get("final_answer", "Analysis finished."),
        "sql": final.get("candidate_sql"),
        "columns": exec_data.get("columns", []),
        "rows": exec_data.get("rows", []),
        "row_count": len(exec_data.get("rows", [])),
        "execution_ms": exec_data.get("execution_time_ms", 0.0),
        "chart": final.get("chart_spec"),
        "summary_stats": final.get("summary_stats"),
        "clarification_question": final.get("clarification_question"),
        "unsupported_reason": final.get("unsupported_reason"),
        "audit_trail": final.get("audit_trail", [])
    }


def execute_followup_question(question: str, sql: Optional[str], columns: List[str], rows: List[Dict[str, Any]], provider: str, api_key: Optional[str]) -> str:
    """Execute a follow-up inquiry strictly grounded in previous query rows."""
    import httpx
    api_url = "http://localhost:8000/api/v1/follow-up"
    try:
        payload = {
            "question": question,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "provider": provider,
            "api_key": api_key if api_key else None
        }
        resp = httpx.post(api_url, json=payload, timeout=20.0)
        if resp.status_code == 200:
            return resp.json().get("answer", "")
    except Exception:
        pass

    # Local Fallback
    from app.agent.prompts import GROUNDED_ANSWER_PROMPT
    from app.agent.llm_factory import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    prompt = GROUNDED_ANSWER_PROMPT.format(
        question=question,
        sql=sql or "N/A",
        columns=columns,
        row_count=len(rows),
        rows_json=json.dumps(rows[:30], default=str)
    )
    llm = get_llm(provider=provider, api_key=api_key)
    res = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"Answer this specific question regarding the data: {question}")
    ])
    return res.content


# ==========================================
# SIDEBAR: Engine Controls & Schema Browser
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")

    provider_choice = st.selectbox(
        "LLM Provider",
        ["Google Gemini", "OpenAI (GPT-4o)", "Mock / Offline Analyst"],
        index=0,
        help="Choose the model provider. 'Mock / Offline Analyst' requires no API key and runs locally."
    )
    provider_map = {
        "Google Gemini": "gemini",
        "OpenAI (GPT-4o)": "openai",
        "Mock / Offline Analyst": "mock"
    }
    selected_provider = provider_map[provider_choice]

    api_key_input = ""
    if selected_provider != "mock":
        key_label = "Gemini API Key" if selected_provider == "gemini" else "OpenAI API Key"
        api_key_input = st.text_input(key_label, type="password", help="Optional if set in your local .env file")

    st.markdown("---")
    st.markdown("### 🛡️ Safety & Policies")
    st.markdown("""
    - **Read-Only Enforced**: Only `SELECT` statements permitted
    - **Defense in Depth**: SQLGlot AST validation + DB isolation
    - **Max Rows Cap**: 500 rows
    - **Statement Timeout**: 10 seconds
    - **Bounded Retries**: Max 2 repair attempts
    """)

    st.markdown("---")
    st.markdown("### 📚 Data Dictionary & Schema")
    with st.expander("🔍 Explore Database Tables", expanded=False):
        st.markdown("**customers**")
        st.caption("customer_id (PK), name, city, region, signup_date, segment")

        st.markdown("**products**")
        st.caption("product_id (PK), product_name, category, cost_price")

        st.markdown("**orders**")
        st.caption("order_id (PK), customer_id (FK), order_date, status, payment_method")

        st.markdown("**order_items**")
        st.caption("order_item_id (PK), order_id (FK), product_id (FK), quantity, unit_price, discount")

    with st.expander("📐 Core Business Metric Formulas", expanded=False):
        st.markdown("""
        - **Net Sales**: `SUM(qty * unit_price * (1 - discount))`
        - **Gross Sales**: `SUM(qty * unit_price)`
        - **Eligible Orders**: `orders.status = 'Completed'`
        - **AOV**: `Net Sales / COUNT(DISTINCT order_id)`
        - **MoM Growth**: `(Current - Prior) / Prior * 100`
        """)

    st.markdown("---")
    st.caption("Agentic AI Data Analyst v1.0 • Built with LangGraph & FastAPI")


# ==========================================
# MAIN INTERFACE
# ==========================================

# Hero Banner
st.markdown("""
<div class="hero-container">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
            <h1 class="hero-title">AI Data Analyst</h1>
            <p class="hero-subtitle">Ask questions in plain English or provide your own SQL • Validated execution • Grounded insights & charts</p>
        </div>
        <div>
            <span class="badge-pill badge-green">● Database Connected</span>
            <span class="badge-pill badge-purple">LangGraph Active</span>
            <span class="badge-pill badge-blue">SQLGlot Guardrail</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Select Workspace Mode
mode_tab_nl, mode_tab_sql = st.tabs([
    "💬 Ask in Plain English (NL-to-SQL)",
    "⚡ Direct SQL Workbench (Custom Query + Questions)"
])

# ------------------------------------------
# MODE 1: Natural Language Question
# ------------------------------------------
with mode_tab_nl:
    st.markdown("##### 💡 Suggested Questions")
    col1, col2, col3, col4, col5 = st.columns(5)

    selected_prompt = None
    with col1:
        if st.button("📈 2025 MoM Growth", use_container_width=True):
            selected_prompt = "Which months had the highest month-over-month revenue growth in 2025?"
    with col2:
        if st.button("📊 Sales by Category", use_container_width=True):
            selected_prompt = "What was the total net sales by product category in 2025?"
    with col3:
        if st.button("🏆 Top 10 Products", use_container_width=True):
            selected_prompt = "List the top 10 products by net revenue."
    with col4:
        if st.button("🌍 Regional Performance", use_container_width=True):
            selected_prompt = "What is the customer count and total net sales by region?"
    with col5:
        if st.button("❓ Test Ambiguity", use_container_width=True):
            selected_prompt = "Which product is best?"

    nl_query_input = st.text_input(
        "Ask a business question in plain English",
        value=selected_prompt or "",
        placeholder="e.g. Which product categories had the highest month-over-month revenue growth in 2025?",
        key="nl_query_input"
    )

    nl_search_col, nl_clear_col = st.columns([6, 1])
    with nl_search_col:
        run_nl_btn = st.button("⚡ Run Agent Analysis", type="primary", use_container_width=True, key="btn_run_nl")
    with nl_clear_col:
        if st.button("Clear", use_container_width=True, key="btn_clear_nl"):
            st.session_state["current_result"] = None
            st.session_state["followup_answers"] = []
            st.rerun()

    if run_nl_btn and nl_query_input:
        with st.status("🧠 Agent Orchestrating Analysis...", expanded=True) as status_box:
            st.write("🔍 **Step 1/6**: Interpreting business question & ambiguity checks...")
            time.sleep(0.2)
            st.write("📖 **Step 2/6**: Retrieving relational schema & metric formulas...")
            time.sleep(0.2)
            st.write("⚙️ **Step 3/6**: Generating candidate SQL query...")

            res = execute_query_pipeline(
                question=nl_query_input,
                provider=selected_provider,
                api_key=api_key_input
            )

            st.write("🛡️ **Step 4/6**: Enforcing SQLGlot AST read-only security checks...")
            time.sleep(0.2)
            st.write(f"⚡ **Step 5/6**: Executed query safely in {res.get('execution_ms', 0)}ms...")
            st.write("📊 **Step 6/6**: Synthesizing evidence-grounded answer & chart...")
            status_box.update(label="✅ Analysis Complete!", state="complete", expanded=False)

        st.session_state["current_result"] = res
        st.session_state["followup_answers"] = []
        st.session_state["query_history"].append({"type": "NL", "input": nl_query_input, "answer": res.get("answer")})

# ------------------------------------------
# MODE 2: Custom SQL Workbench
# ------------------------------------------
with mode_tab_sql:
    st.markdown("##### 💻 Execute & Analyze Custom SQL Query")
    st.caption("Provide your own SQL query. The system validates it through SQLGlot AST guardrails, executes it safely, and generates an evidence-grounded analysis answering your questions about the query results.")

    sample_sql = """SELECT p.category, 
       ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales,
       COUNT(DISTINCT o.order_id) AS order_count
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.status = 'Completed'
GROUP BY p.category
ORDER BY net_sales DESC;"""

    user_sql_input = st.text_area(
        "Enter SQL Query (Read-Only SELECT):",
        value=sample_sql,
        height=140,
        key="custom_sql_input"
    )

    user_question_about_sql = st.text_input(
        "Optional Question or Focus for the AI:",
        placeholder="e.g. Which category is performing best, and what is its contribution to overall sales?",
        key="question_about_sql"
    )

    sql_run_col, sql_clear_col = st.columns([6, 1])
    with sql_run_col:
        run_sql_btn = st.button("⚡ Execute & Analyze SQL", type="primary", use_container_width=True, key="btn_run_sql")
    with sql_clear_col:
        if st.button("Clear SQL", use_container_width=True, key="btn_clear_sql"):
            st.session_state["current_result"] = None
            st.session_state["followup_answers"] = []
            st.rerun()

    if run_sql_btn and user_sql_input:
        with st.status("🛡️ Validating & Executing Custom SQL...", expanded=True) as status_box:
            st.write("🔍 **Step 1/4**: Checking AST syntax and read-only policies...")
            time.sleep(0.2)
            st.write("⚡ **Step 2/4**: Executing query against database with row limits...")

            res = execute_query_pipeline(
                question=user_question_about_sql if user_question_about_sql else "Analyze the key insights and trends from this query result.",
                sql=user_sql_input,
                provider=selected_provider,
                api_key=api_key_input
            )

            st.write(f"📊 **Step 3/4**: Query returned {res.get('row_count', 0)} rows in {res.get('execution_ms', 0)}ms...")
            st.write("📋 **Step 4/4**: Synthesizing grounded explanation & visualization...")
            status_box.update(label="✅ Query & Analysis Complete!", state="complete", expanded=False)

        st.session_state["current_result"] = res
        st.session_state["followup_answers"] = []
        st.session_state["query_history"].append({"type": "SQL", "input": user_sql_input, "answer": res.get("answer")})


# ==========================================
# RESULT PRESENTATION & FOLLOW-UP Q&A
# ==========================================
active_result = st.session_state.get("current_result")

if active_result:
    st.markdown("---")
    status = active_result.get("status")

    if status == "clarification_required":
        st.warning(f"⚠️ **Clarification Required**: {active_result.get('clarification_question')}")
        st.info("The agent avoided guessing and asked for clarification to ensure accurate business results.")
    elif status == "unsupported":
        st.error(f"🚫 **Unsupported Request**: {active_result.get('unsupported_reason')}")
    elif status in ("validation_failed", "execution_error"):
        st.error(active_result.get("answer", "Query execution failed."))
    else:
        # 1. Executive Answer
        st.markdown(f"""
        <div class="answer-card">
            <div class="answer-header">
                <span style="font-size: 1.3rem; margin-right: 0.5rem;">📋</span> Executive Answer & Analysis
            </div>
            <div>{active_result.get('answer', '')}</div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Main Content Tabs
        tab_chart, tab_data, tab_sql, tab_audit = st.tabs([
            "📊 Visualization",
            f"📋 Query Results ({active_result.get('row_count', 0)} rows)",
            "🛡️ Executed SQL & Security",
            "🕵️ Audit Trail & Telemetry"
        ])

        with tab_chart:
            chart_info = active_result.get("chart")
            if chart_info:
                c_type = chart_info.get("type")
                if c_type == "metric":
                    st.markdown(f"""
                    <div class="metric-card" style="max-width: 320px; margin: 1.5rem auto;">
                        <div class="metric-title">{chart_info.get('title', 'Metric')}</div>
                        <div class="metric-value">{chart_info.get('value', '0')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                elif chart_info.get("plotly_json"):
                    fig = pio.from_json(chart_info["plotly_json"])
                    st.plotly_chart(fig, use_container_width=True)
                    if chart_info.get("truncation_note"):
                        st.caption(f"ℹ️ {chart_info['truncation_note']}")
                else:
                    st.info(chart_info.get("message", "No visualization available for this tabular result."))
            else:
                st.info("No visualization available for this query result.")

        with tab_data:
            rows = active_result.get("rows", [])
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv,
                    file_name="query_results.csv",
                    mime="text/csv",
                    use_container_width=False
                )
            else:
                st.info("Query returned 0 rows.")

        with tab_sql:
            st.markdown(f"""
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                <span class="badge-pill badge-green">✓ AST Read-Only Approved</span>
                <span class="badge-pill badge-blue">Dialect: PostgreSQL / SQLite</span>
                <span class="badge-pill badge-purple">Execution: {active_result.get('execution_ms', 0)} ms</span>
            </div>
            """, unsafe_allow_html=True)

            sql_code = active_result.get("sql", "-- No SQL generated")
            st.code(sql_code, language="sql")

        with tab_audit:
            audit = active_result.get("audit_trail", [])
            st.json(audit)

        # ------------------------------------------
        # 3. INTERACTIVE FOLLOW-UP QUESTIONS ON QUERY RESULTS
        # ------------------------------------------
        st.markdown("---")
        st.markdown("#### 💬 Ask a Follow-Up Question About This Data")
        st.caption("Ask specific follow-up questions about the active query results above. The AI analyst answers strictly grounded in these numbers.")

        # Quick Suggested Follow-Up Chips
        fu_col1, fu_col2, fu_col3 = st.columns(3)
        suggested_fu = None
        with fu_col1:
            if st.button("🔍 What is the top performer and by how much?", use_container_width=True):
                suggested_fu = "What is the top performing item in this data and by what margin does it lead?"
        with fu_col2:
            if st.button("📊 Calculate the total & average of this data", use_container_width=True):
                suggested_fu = "What is the total sum and average across the numeric columns in this result set?"
        with fu_col3:
            if st.button("📉 Identify anomalies or lowest performers", use_container_width=True):
                suggested_fu = "Which items are the lowest performers or represent significant anomalies in this data?"

        followup_input = st.text_input(
            "Ask a question about the returned data above:",
            value=suggested_fu or "",
            placeholder="e.g. Which category represents the highest percentage of the total?",
            key="followup_query_input"
        )

        if st.button("💡 Ask About This Data", type="secondary", key="btn_ask_followup"):
            if followup_input:
                with st.spinner("Analyzing data rows..."):
                    fu_answer = execute_followup_question(
                        question=followup_input,
                        sql=active_result.get("sql"),
                        columns=active_result.get("columns", []),
                        rows=active_result.get("rows", []),
                        provider=selected_provider,
                        api_key=api_key_input
                    )
                    st.session_state["followup_answers"].append({
                        "question": followup_input,
                        "answer": fu_answer
                    })

        # Display Follow-Up Answers
        if st.session_state["followup_answers"]:
            for item in reversed(st.session_state["followup_answers"]):
                st.markdown(f"""
                <div class="followup-card">
                    <div style="font-weight: 700; color: #34D399; margin-bottom: 0.4rem;">
                        Q: {item['question']}
                    </div>
                    <div>{item['answer']}</div>
                </div>
                """, unsafe_allow_html=True)
