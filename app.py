"""OpsMind — The AI Brain for Your Factory."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import APP_NAME, APP_TAGLINE, VERSION
from modules.sql_agent import run_query
from modules.doc_search import search as doc_search, ingest_pdf, ingest_text, get_doc_count
from modules.excel_agent import analyse_file
from modules.waste_predictor import (
    get_yield_trends, get_waste_summary, get_yield_by_product,
    predict_waste, get_ai_waste_analysis
)
from modules.compliance import (
    trace_batch, get_temperature_excursions, get_allergen_matrix,
    get_compliance_score, generate_audit_summary
)
from modules.alerts import check_all_alerts
from modules.llm import get_response, get_streaming_response, FACTORY_SYSTEM_PROMPT

# === PAGE CONFIG ===
st.set_page_config(
    page_title=f"{APP_NAME} — Factory AI",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === SESSION STATE ===
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'chat'


# === SIDEBAR ===
with st.sidebar:
    st.markdown(f"## 🏭 {APP_NAME}")
    st.caption(f"{APP_TAGLINE} | v{VERSION}")
    st.divider()

    # Navigation
    tab = st.radio(
        "Navigate",
        ['💬 Chat', '📊 Dashboard', '📈 Yield & Waste', '🔍 Documents',
         '📋 Compliance', '🔔 Alerts', '📁 Upload'],
        label_visibility='collapsed'
    )
    st.session_state.active_tab = tab

    st.divider()

    # Quick stats
    try:
        from modules.database import query as db_q, scalar
        from modules.sql_dialect import days_ago
        q_count = scalar(f"SELECT COUNT(*) FROM production WHERE date >= {days_ago(7)}")
        w_total = scalar(f"SELECT COALESCE(SUM(waste_kg), 0) FROM production WHERE date >= {days_ago(7)}")
        w_cost = scalar(f"SELECT COALESCE(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) FROM production p JOIN products pr ON p.product_id = pr.id WHERE p.date >= {days_ago(7)}")
        o_pending = scalar("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        st.metric("Production runs (7d)", q_count or 0)
        st.metric("Waste (7d)", f"{(w_total or 0):,.0f} kg")
        st.metric("💷 Waste cost (7d)", f"GBP {(w_cost or 0):,.0f}")
        st.metric("Pending orders", o_pending or 0)
    except Exception:
        st.caption("Connect database to see stats")

    st.divider()
    st.caption(f"📚 {get_doc_count()} document chunks indexed")


# === MAIN CONTENT ===

# ─── CHAT TAB ───
if '💬 Chat' in tab:
    st.title("💬 Ask OpsMind")
    st.caption("Ask anything about your factory data, documents, or operations")

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
            if 'data' in msg and msg['data'] is not None:
                st.dataframe(msg['data'], use_container_width=True)
            if 'sql' in msg:
                with st.expander("🔍 SQL Query"):
                    st.code(msg['sql'], language='sql')

    # Chat input
    if prompt := st.chat_input("Ask about production, waste, orders, compliance..."):
        # Add user message
        st.session_state.chat_history.append({'role': 'user', 'content': prompt})
        with st.chat_message('user'):
            st.markdown(prompt)

        with st.chat_message('assistant'):
            with st.spinner('Thinking...'):
                # Decide: SQL query, document search, or general chat
                prompt_lower = prompt.lower()
                sql_keywords = ['how much', 'how many', 'show me', 'total', 'average', 'count',
                               'list', 'top', 'worst', 'best', 'compare', 'trend', 'waste',
                               'yield', 'production', 'order', 'customer', 'staff', 'temperature',
                               'cost', 'profit', 'margin', 'revenue', 'kg', 'today', 'week', 'month',
                               'yesterday', 'last', 'this', 'supplier', 'batch', 'salary', 'hours']
                doc_keywords = ['procedure', 'sop', 'haccp', 'brc', 'policy', 'handbook',
                               'specification', 'spec', 'cleaning', 'allergen procedure',
                               'how to', 'what is the process', 'document', 'guideline']

                is_sql = any(kw in prompt_lower for kw in sql_keywords)
                is_doc = any(kw in prompt_lower for kw in doc_keywords)

                if is_sql and not is_doc:
                    # SQL Query mode
                    result = run_query(prompt)
                    st.markdown(result['explanation'])
                    if result['data'] is not None and not result['data'].empty:
                        st.dataframe(result['data'], use_container_width=True)
                        # Auto-chart if numeric data
                        numeric_cols = result['data'].select_dtypes(include='number').columns
                        if len(numeric_cols) >= 1 and len(result['data']) > 1:
                            try:
                                fig = px.bar(result['data'].head(20),
                                           x=result['data'].columns[0],
                                           y=numeric_cols[0],
                                           title=prompt[:80])
                                st.plotly_chart(fig, use_container_width=True)
                            except Exception:
                                pass
                    with st.expander("🔍 SQL Query"):
                        st.code(result['sql'], language='sql')
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': result['explanation'],
                        'data': result['data'],
                        'sql': result['sql']
                    })

                elif is_doc:
                    # Document search mode
                    results = doc_search(prompt, n_results=3)
                    if results:
                        context = '\n\n'.join([f"[{r['metadata'].get('source', 'doc')}]: {r['text']}" for r in results])
                        answer = get_response(
                            f"Question: {prompt}\n\nRelevant documents:\n{context}\n\nAnswer based on these documents:",
                            system_prompt=FACTORY_SYSTEM_PROMPT
                        )
                        st.markdown(answer)
                        with st.expander("📚 Source documents"):
                            for r in results:
                                st.caption(f"📄 {r['metadata'].get('source', 'Unknown')} (relevance: {1 - r['distance']:.0%})")
                                st.text(r['text'][:300] + '...')
                        st.session_state.chat_history.append({
                            'role': 'assistant', 'content': answer
                        })
                    else:
                        st.warning("No documents found. Upload documents in the Upload tab first.")
                        st.session_state.chat_history.append({
                            'role': 'assistant',
                            'content': 'No documents found. Please upload relevant documents first.'
                        })
                else:
                    # General chat with factory context
                    context = [{'role': m['role'], 'content': m['content']}
                              for m in st.session_state.chat_history[-6:]]
                    answer = get_response(prompt, system_prompt=FACTORY_SYSTEM_PROMPT, context=context)
                    st.markdown(answer)
                    st.session_state.chat_history.append({
                        'role': 'assistant', 'content': answer
                    })

    # Quick action buttons
    st.divider()
    st.caption("Quick queries:")
    cols = st.columns(4)
    quick_queries = [
        "Show today's production summary",
        "Top 5 products by waste this week",
        "Any temperature excursions today?",
        "Pending orders for this week"
    ]
    for i, q in enumerate(quick_queries):
        if cols[i].button(q, key=f"quick_{i}", use_container_width=True):
            st.session_state.chat_history.append({'role': 'user', 'content': q})
            st.rerun()


# ─── DASHBOARD TAB ───
elif '📊 Dashboard' in tab:
    st.title("📊 Factory Dashboard")

    try:
        from modules.database import query as db_q, scalar
        from modules.sql_dialect import days_ago

        # KPI cards
        c1, c2, c3, c4, c5 = st.columns(5)
        today_prod = db_q(f"SELECT COALESCE(SUM(finished_output_kg), 0) as output, COALESCE(SUM(waste_kg), 0) as waste, COALESCE(AVG(yield_pct), 0) as yield_avg FROM production WHERE date >= {days_ago(1)}")
        today_cost = db_q(f"SELECT COALESCE(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) as cost FROM production p JOIN products pr ON p.product_id = pr.id WHERE p.date >= {days_ago(1)}")
        pending = scalar("SELECT COUNT(*) FROM orders WHERE status='pending'") or 0

        c1.metric("Today's Output", f"{today_prod.iloc[0]['output']:,.0f} kg")
        c2.metric("Today's Waste", f"{today_prod.iloc[0]['waste']:,.0f} kg")
        c3.metric("💷 Waste Cost", f"GBP {today_cost.iloc[0]['cost']:,.0f}")
        c4.metric("Avg Yield", f"{today_prod.iloc[0]['yield_avg']:.1f}%")
        c5.metric("Pending Orders", pending)

        # Monthly money lost
        monthly_cost = scalar(f"SELECT COALESCE(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) FROM production p JOIN products pr ON p.product_id = pr.id WHERE p.date >= {days_ago(30)}") or 0
        annual_projected = monthly_cost * 12
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#fef2f2,#fee2e2);border:1px solid #fca5a5;border-radius:12px;padding:1.2rem;margin-bottom:1.5rem;display:flex;justify-content:space-between;align-items:center;">
            <div><strong style="color:#991b1b;">💷 Money Lost to Waste</strong></div>
            <div style="display:flex;gap:2rem;">
                <div><span style="color:#991b1b;font-size:1.3rem;font-weight:800;">GBP {monthly_cost:,.0f}</span><br><span style="color:#b91c1c;font-size:0.8rem;">This Month</span></div>
                <div><span style="color:#991b1b;font-size:1.3rem;font-weight:800;">GBP {annual_projected:,.0f}</span><br><span style="color:#b91c1c;font-size:0.8rem;">Projected Annual</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Production trend
        st.subheader("Production Trend (30 days)")
        trend = db_q(f"""
            SELECT date, SUM(finished_output_kg) as output_kg, SUM(waste_kg) as waste_kg,
                   ROUND(AVG(yield_pct), 1) as avg_yield
            FROM production WHERE date >= {days_ago(30)}
            GROUP BY date ORDER BY date
        """)
        if not trend.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=trend['date'], y=trend['output_kg'], name='Output (kg)', marker_color='#005eb8'))
            fig.add_trace(go.Bar(x=trend['date'], y=trend['waste_kg'], name='Waste (kg)', marker_color='#dc2626'))
            fig.update_layout(barmode='stack', height=350)
            st.plotly_chart(fig, use_container_width=True)

        # Orders by customer
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Orders by Customer (30d)")
            cust = db_q(f"""
                SELECT customer, SUM(quantity_kg) as total_kg, COUNT(*) as order_count
                FROM orders WHERE order_date >= {days_ago(30)}
                GROUP BY customer ORDER BY total_kg DESC
            """)
            if not cust.empty:
                fig = px.pie(cust, values='total_kg', names='customer', hole=0.4)
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Yield by Product")
            yield_df = get_yield_by_product(30)
            if not yield_df.empty:
                fig = px.bar(yield_df, x='product', y='avg_yield',
                           color='avg_yield', color_continuous_scale=['#dc2626', '#f59e0b', '#059669'],
                           range_color=[50, 75])
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Database error: {e}. Run `python scripts/seed_demo_db.py` to create the demo database.")


# ─── YIELD & WASTE TAB ───
elif '📈 Yield & Waste' in tab:
    st.title("📈 Yield & Waste Analysis")

    col1, col2 = st.columns([1, 3])
    with col1:
        days = st.selectbox("Period", [7, 14, 30, 60], index=2)
        product_filter = st.text_input("Filter product", placeholder="e.g. Salmon")

    # Yield trends
    df = get_yield_trends(days, product_filter if product_filter else None)
    if not df.empty:
        st.subheader(f"Yield Trends ({days} days)")
        daily = df.groupby('date').agg({'yield_pct': 'mean', 'waste_kg': 'sum'}).reset_index()
        fig = px.line(daily, x='date', y='yield_pct', title='Average Daily Yield %',
                     markers=True, color_discrete_sequence=['#005eb8'])
        fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="Target: 60%")
        st.plotly_chart(fig, use_container_width=True)

    # Yield by product table with money
    st.subheader("Yield by Product")
    yield_df = get_yield_by_product(days)
    if not yield_df.empty:
        total_waste_cost = yield_df['waste_cost_gbp'].sum() if 'waste_cost_gbp' in yield_df.columns else 0
        st.markdown(f"**Total waste cost ({days}d): GBP {total_waste_cost:,.0f}**")
        st.dataframe(yield_df, use_container_width=True)

    # Waste breakdown
    st.subheader("Waste Breakdown")
    waste_df = get_waste_summary(days)
    if not waste_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            by_type = waste_df.groupby('waste_type')['total_kg'].sum().reset_index()
            fig = px.pie(by_type, values='total_kg', names='waste_type', title='Waste by Type')
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            by_reason = waste_df.groupby('reason')['total_kg'].sum().reset_index().sort_values('total_kg', ascending=False)
            fig = px.bar(by_reason.head(8), x='total_kg', y='reason', orientation='h', title='Waste by Reason')
            st.plotly_chart(fig, use_container_width=True)

    # Waste predictor
    st.subheader("🔮 Waste Predictor")
    col1, col2, col3 = st.columns(3)
    with col1:
        pred_product = st.text_input("Product name", value="Salmon Fillet")
    with col2:
        pred_input = st.number_input("Input quantity (kg)", value=500.0, step=50.0)
    with col3:
        if st.button("Predict", use_container_width=True):
            prediction = predict_waste(pred_product, pred_input)
            if prediction:
                # Estimate waste cost (use avg unit cost of 7.50)
                est_cost = prediction['expected_waste_kg'] * 7.50
                st.success(f"Expected output: **{prediction['expected_output_kg']} kg** | "
                          f"Expected waste: **{prediction['expected_waste_kg']} kg** "
                          f"(**GBP {est_cost:,.0f}**) | "
                          f"Yield: **{prediction['expected_yield_pct']}%**")
            else:
                st.warning("No historical data found for this product.")

    # AI analysis
    st.subheader("🤖 AI Waste Analysis")
    if st.button("Generate AI Recommendations", use_container_width=True):
        with st.spinner("Analysing waste patterns..."):
            analysis = get_ai_waste_analysis(days)
            st.markdown(analysis)


# ─── DOCUMENTS TAB ───
elif '🔍 Documents' in tab:
    st.title("🔍 Document Search")
    st.caption("Search your factory SOPs, HACCP plans, and specifications")

    query = st.text_input("Search documents", placeholder="e.g. allergen procedure for cod")
    if query:
        results = doc_search(query, n_results=5)
        if results:
            for r in results:
                relevance = 1 - r['distance']
                with st.expander(f"📄 {r['metadata'].get('source', 'Unknown')} — {relevance:.0%} match"):
                    st.markdown(r['text'])
                    st.caption(f"Category: {r['metadata'].get('category', 'N/A')} | Page: {r['metadata'].get('page', 'N/A')}")
        else:
            st.info("No matching documents found. Upload documents in the Upload tab.")

    st.divider()
    st.caption(f"Total document chunks indexed: {get_doc_count()}")


# ─── COMPLIANCE TAB ───
elif '📋 Compliance' in tab:
    st.title("📋 Compliance & Audit")

    # Compliance scores
    scores = get_compliance_score()
    cols = st.columns(len(scores))
    for i, (key, val) in enumerate(scores.items()):
        color = "normal" if val >= 95 else ("off" if val >= 85 else "inverse")
        cols[i].metric(key, f"{val}%", delta=None)

    # Batch traceability
    st.subheader("🔗 Batch Traceability")
    batch = st.text_input("Enter batch code", placeholder="e.g. PR-260329-1")
    if batch:
        trace = trace_batch(batch)
        if not trace['raw_materials'].empty:
            st.markdown("**Raw Materials:**")
            st.dataframe(trace['raw_materials'], use_container_width=True)
        if not trace['production'].empty:
            st.markdown("**Production:**")
            st.dataframe(trace['production'], use_container_width=True)
        if not trace['orders'].empty:
            st.markdown("**Related Orders:**")
            st.dataframe(trace['orders'], use_container_width=True)
        if trace['raw_materials'].empty and trace['production'].empty:
            st.warning("No records found for this batch code.")

    # Temperature excursions
    st.subheader("🌡️ Temperature Excursions (7 days)")
    excursions = get_temperature_excursions(7)
    if not excursions.empty:
        st.warning(f"⚠️ {len(excursions)} temperature excursions detected!")
        st.dataframe(excursions, use_container_width=True)
    else:
        st.success("✅ No temperature excursions in the last 7 days")

    # Allergen matrix
    st.subheader("⚠️ Allergen Matrix")
    allergens = get_allergen_matrix()
    st.dataframe(allergens, use_container_width=True)

    # Audit report
    st.subheader("📝 Generate Audit Report")
    if st.button("Generate BRC/HACCP Audit Summary", use_container_width=True):
        with st.spinner("Generating audit report..."):
            report = generate_audit_summary(30)
            st.json({
                'generated_at': report['generated_at'],
                'period_days': report['period_days'],
                'compliance_scores': report['compliance_scores'],
                'temperature_excursions_count': len(report['temperature_excursions']),
                'products_tracked': len(report['production_summary'])
            })
            st.dataframe(report['production_summary'], use_container_width=True)


# ─── ALERTS TAB ───
elif '🔔 Alerts' in tab:
    st.title("🔔 Smart Alerts")

    alerts = check_all_alerts()
    if not alerts:
        st.success("✅ All clear! No active alerts.")
    else:
        st.warning(f"⚠️ {len(alerts)} active alerts")
        for alert in alerts:
            icon_map = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}
            icon = icon_map.get(alert['level'], '⚪')
            with st.expander(f"{icon} {alert['title']}", expanded=alert['level'] == 'critical'):
                st.markdown(alert['message'])
                st.caption(f"Category: {alert['category']}")


# ─── UPLOAD TAB ───
elif '📁 Upload' in tab:
    st.title("📁 Upload Documents & Data")

    upload_type = st.radio("What are you uploading?", ['PDF Document', 'Excel/CSV Report'], horizontal=True)

    if upload_type == 'PDF Document':
        st.caption("Upload SOPs, HACCP plans, customer specs, audit reports")
        uploaded = st.file_uploader("Choose a PDF", type=['pdf'])
        if uploaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
                f.write(uploaded.read())
                temp_path = f.name
            with st.spinner(f"Ingesting {uploaded.name}..."):
                chunks = ingest_pdf(temp_path)
            os.unlink(temp_path)
            st.success(f"✅ Ingested {uploaded.name} — {chunks} chunks indexed")

    else:
        st.caption("Upload production reports, waste logs, yield data")
        uploaded = st.file_uploader("Choose an Excel or CSV file", type=['csv', 'xlsx', 'xls'])
        if uploaded:
            question = st.text_input("What would you like to know about this data?",
                                    placeholder="e.g. What's the average yield? Show waste trends.")
            if question:
                ext = uploaded.name.split('.')[-1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as f:
                    f.write(uploaded.read())
                    temp_path = f.name
                with st.spinner("Analysing..."):
                    result = analyse_file(temp_path, question, ext)
                os.unlink(temp_path)
                st.markdown(result['answer'])
                if result['data'] is not None:
                    st.dataframe(result['data'].head(50), use_container_width=True)
