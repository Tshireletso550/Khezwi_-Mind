"""Run with: streamlit run app.py. See README.md before deployment."""
import io
import base64
import json
import os
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from core import SCHEMAS, ROLES, PERMISSIONS, Store, derive, alerts_for, risk_class

st.set_page_config(page_title='Khwezi Mine Monitor', page_icon='⛏️', layout='wide')
NAV_ICONS = {
    'Home': '🏠', 'Dashboard': '📊', 'Workers': '👷', 'Incidents': '🚨',
    'Equipment': '🚜', 'Maintenance': '🔧', 'Risk assessment': '🛡️',
    'Alerts': '🔔', 'Analysis': '📈', 'Reports': '📄',
    'Manage users': '👥', 'Backup and restore': '💾',
}

# SECTION 5: GRAPHICAL USER INTERFACE — navigation and homepage
def navigation_label(page):
    return f"{NAV_ICONS[page]}  {page}"

# The requested homepage photograph is included in the source so no image upload is needed.
from branding import HOME_PHOTO_BASE64

def background_image():
    return HOME_PHOTO_BASE64


def apply_style(home=False):
    background = (
        "linear-gradient(90deg,rgba(10,22,30,.76),rgba(10,22,30,.15)),"
        f"url('data:image/jpeg;base64,{background_image()}')" if home else 'none'
    )
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] {background-color:#f4f6f8;}
    [data-testid="stHeader"] {background:transparent;}
    [data-testid="stSidebar"] {background:#192b36;}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {color:#f5f7fa;}
    [data-testid="stSidebar"] button p {color:#182c3a;}
    [data-testid="stMetric"] {background:white;padding:16px;border-radius:12px;border:1px solid #dde5ef;}
    h1,h2,h3 {color:#15344b;}
    .home-brand {font-size:15px;letter-spacing:3px;font-weight:800;color:white;padding:12px 0 22px;}
    .home-hero {max-width:940px;padding:clamp(10px,4vw,50px) 0 24px;}
    .home-hero h1 {color:white;font-size:clamp(32px,5vw,64px);line-height:1.12;letter-spacing:-1px;margin:0;}
    .home-hero h1 span {color:#ffb51b;}
    .home-hero p {font-size:clamp(17px,2vw,24px);color:#e5e8eb;margin-top:20px;}
    .gold-rule {width:80px;height:5px;background:#ffb51b;margin-top:24px;}
    .home-footer {display:flex;flex-wrap:wrap;justify-content:space-between;gap:24px;
        background:rgba(15,23,29,.93);color:white;border-top:1px solid #56616a;
        border-radius:12px;padding:24px;margin-top:70px;font-size:16px;}
    .home-footer small {color:#d2dbe0;}
    .home-footer strong {color:#ffbf40;}
    @media(max-width:640px){.home-footer{margin-top:30px;gap:16px;} }
    </style>""", unsafe_allow_html=True)
    st.markdown(f"""<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background-image:{background} !important;
        background-color:{'#16232d' if home else '#f4f6f8'} !important;
        background-size:cover !important;
        background-position:center center !important;
        background-repeat:no-repeat !important;
        background-attachment:fixed !important;
    }}
    [data-testid="stMainBlockContainer"] {{background:transparent !important;}}
    </style>""", unsafe_allow_html=True)
    if home:
        st.markdown("""<style>
        [data-testid="stMainBlockContainer"] {max-width:1400px;}
        [data-testid="stForm"] {background:rgba(255,255,255,.96);border-radius:16px;padding:24px;max-width:480px;}
        [data-testid="stForm"] label p {color:#15344b;}
        [data-testid="stMain"] [data-testid="stButton"] button {
            min-height:116px;background:rgba(22,34,43,.94);border:1px solid #566572;
            border-bottom:5px solid #ffb51b;border-radius:12px;color:white;text-align:left;}
        [data-testid="stMain"] [data-testid="stButton"] button:hover {border-color:#ffc14b;background:#273e4e;}
        [data-testid="stMain"] [data-testid="stButton"] button p {font-size:19px;font-weight:650;}
        </style>""", unsafe_allow_html=True)

def home_heading():
    st.markdown("""<div class="home-brand">⛏ KHWEZI MINE MONITOR</div>
    <div class="home-hero"><h1>Mining Safety &amp;<br><span>Risk Assessment</span> System</h1>
    <p>Smart Monitoring. Safer People. Stronger Mines.</p><div class="gold-rule"></div></div>""", unsafe_allow_html=True)

def home_footer():
    st.markdown("""<footer class="home-footer">
      <div>🛡️ <strong>Safety Today.</strong><br>A Better Tomorrow.</div>
      <div><small>People &nbsp; | &nbsp; Safety &nbsp; | &nbsp; Productivity &nbsp; | &nbsp; Sustainability</small></div>
      <div>🌿 Building Safer Mines<br>for Stronger Communities.</div>
    </footer>""", unsafe_allow_html=True)

def go_to(page):
    st.session_state['navigation'] = page


def setting(key, default):
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except FileNotFoundError:
        return os.environ.get(key, default)

# SECTION 4: TECHNICAL STACK — Pandas data preparation
def frame(entity, rows):
    if not rows:
        return pd.DataFrame(columns=list(SCHEMAS[entity]))
    return pd.DataFrame([derive(entity, r) for r in rows])

def csv_bytes(df):
    # Avoid spreadsheet formula execution when exported user text is opened in Excel.
    safe = df.copy()
    for c in safe.select_dtypes(include=['object', 'string']).columns:
        safe[c] = safe[c].map(lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v)
    return safe.to_csv(index=False).encode('utf-8-sig')

def table(df):
    st.dataframe(df, width='stretch', hide_index=True)

def show_chart(df, x, y, title, color=None):
    if df.empty:
        st.info('No records match these filters.')
        return
    fig = px.bar(df, x=x, y=y, color=color, title=title, template='plotly_white')
    fig.update_layout(margin=dict(l=20,r=20,t=55,b=20))
    st.plotly_chart(fig, width='stretch')

def group_count(df, column):
    return df.groupby(column).size().reset_index(name='count')

# SECTIONS 3(b), 3(c), 3(d), 3(g): SHARED DATA-ENTRY FORMS
def record_editor(store, role, entity, rows):
    if role == 'Manager':
        st.caption('Manager access is read-only. Reports and exports are available.')
        return
    with st.expander('Add or edit a record'):
        mode = st.radio('Action', ['Add new record', 'Edit existing record'], horizontal=True, key=f'{entity}_mode')
        current = {}
        editing = mode == 'Edit existing record'
        if editing:
            if not rows:
                st.info('Add a record first.')
                return
            chosen = st.selectbox('Record to edit', [r['id'] for r in rows], key=f'{entity}_chosen')
            current = next(r for r in rows if r['id'] == chosen)
        if entity == 'equipment':
            st.info('Use operating hours and downtime for the SAME reporting period across all equipment. Every save records a new monitoring observation. To complete maintenance, set Operational, enter the next due date and explain the work in maintenance notes.')
        form_key = entity + '_' + str(current.get('id', 'new'))
        with st.form(form_key):
            values = {}
            cols = st.columns(2)
            for i, (name, spec) in enumerate(SCHEMAS[entity].items()):
                with cols[i % 2]:
                    label = name.replace('_', ' ').replace('pct', '%').title()
                    key = form_key + '_' + name
                    default = current.get(name)
                    if spec[0] == 'choice':
                        values[name] = st.selectbox(label, spec[1], index=spec[1].index(default) if default in spec[1] else 0, key=key)
                    elif spec[0] in ('number', 'integer'):
                        cast = int if spec[0] == 'integer' else float
                        values[name] = st.number_input(label, min_value=cast(spec[1]), max_value=cast(spec[2]), value=cast(default if default is not None else spec[3]), step=cast(1), key=key)
                    elif spec[0] == 'date':
                        values[name] = st.date_input(label, value=date.fromisoformat(default) if default else date.today(), key=key).isoformat()
                    elif spec[0] == 'time':
                        values[name] = st.time_input(label, value=datetime.strptime(default or '08:00', '%H:%M').time(), key=key).strftime('%H:%M')
                    else:
                        values[name] = st.text_input(label, value=default or '', disabled=editing and name=='id', key=key)
            submitted = st.form_submit_button('Save record', type='primary')
        if submitted:
            try:
                store.save(role, entity, values, update=editing)
                st.session_state['notice'] = 'Record saved. Dashboard and alerts have been updated.'
                st.rerun()
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))


# SECTION 3(a): ACCESS CONTROL — login, current-role checks and permitted pages
def main():
    demo = str(setting('DEMO_MODE', 'true')).lower() == 'true'
    store = Store(os.environ.get('KHWEZI_DB', str(Path(__file__).parent / 'data' / 'khwezi.sqlite3')))
    try:
        store.bootstrap(demo=demo, admin_password=setting('ADMIN_PASSWORD', None))
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    if 'username' not in st.session_state:
        apply_style(home=True)
        home_heading()
        with st.form('login'):
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            submitted = st.form_submit_button('Sign in', type='primary')
        if submitted:
            if time.time() < st.session_state.get('login_wait_until', 0):
                st.error('Too many attempts. Wait one minute and try again.')
            else:
                role = store.login(username.strip(), password)
                if role:
                    st.session_state['username'] = username.strip()
                    st.session_state['login_failures'] = 0
                    st.rerun()
                else:
                    failures = st.session_state.get('login_failures', 0) + 1
                    st.session_state['login_failures'] = failures
                    if failures % 5 == 0:
                        st.session_state['login_wait_until'] = time.time() + 60
                    st.error('Incorrect username or password.')
        home_footer()
        st.stop()
    # Look up current role on EVERY rerun, including after an administrator changes it.
    role = store.role_for(st.session_state['username'])
    if role not in ROLES:
        st.session_state.clear()
        st.rerun()
    st.sidebar.title('Mine operations')
    st.sidebar.write(f"{st.session_state['username']} · {role}")
    if st.sidebar.button('Sign out'):
        st.session_state.clear()
        st.rerun()
    allowed = PERMISSIONS[role]
    pages = ['Home', 'Dashboard']
    pages += [label for entity,label in [('workers','Workers'),('incidents','Incidents'),('equipment','Equipment'),('equipment','Maintenance'),('risks','Risk assessment')] if entity in allowed]
    pages += ['Alerts', 'Analysis', 'Reports']
    if role == 'Administrator':
        pages += ['Manage users', 'Backup and restore']
    page = st.sidebar.radio('Navigate', pages, format_func=navigation_label, key='navigation')
    apply_style(home=page == 'Home')
    if page == 'Home':
        home_heading()
        shortcuts = [('Workers', '👷 Worker Safety'), ('Risk assessment', '🛡️ Risk Assessment'),
                     ('Analysis', '📈 Safety Analytics'), ('Reports', '📄 Reports'),
                     ('Equipment', '🚜 Equipment'), ('Maintenance', '🔧 Maintenance')]
        shortcuts = [(target, label) for target, label in shortcuts if target in pages]
        for start in range(0, len(shortcuts), 4):
            for col, (target, label) in zip(st.columns(min(4, len(shortcuts)-start)), shortcuts[start:start+4]):
                col.button(label + '  →', key='home_'+target, on_click=go_to, args=(target,), width='stretch')
        home_footer()
        return
    st.title('Khwezi Mine Monitor')
    if st.sidebar.button('Refresh current data'):
        st.rerun()
    if 'notice' in st.session_state:
        st.success(st.session_state.pop('notice'))
    raw = {entity: store.rows(role, entity) for entity in allowed}
    data = {entity: frame(entity, rows) for entity,rows in raw.items()}
    active = [a for entity,rows in raw.items() for r in rows for a in alerts_for(entity,r)]
    history = store.history(role) if 'equipment' in allowed else []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    repeated = {}
    for event in history:
        if datetime.fromisoformat(event['timestamp']) >= cutoff and event['alerts']:
            repeated[event['equipment_id']] = repeated.get(event['equipment_id'],0) + 1
    for equipment_id, count in repeated.items():
        if count >= 3:
            eq = next((r for r in raw['equipment'] if r['id'] == equipment_id), None)
            if eq:
                active.append(dict(source='equipment', record_id=equipment_id, department=eq['department'], level='Warning', parameter='Repeated alert observations (30 days)', value=str(count), recommended_action='Review repeated abnormal observations and maintenance history.'))
    alert_df = pd.DataFrame(active, columns=['source','record_id','department','level','parameter','value','recommended_action'])
    st.subheader(page)

    # SECTION 3(i): MINING MONITORING DASHBOARD
    if page == 'Dashboard':
        st.caption('All current records in your permitted datasets. Incident totals are all-time; use Analysis to select dates.')
        metrics = []
        if 'workers' in data:
            w = data['workers']
            metrics += [('Workers',len(w)),('Fully PPE compliant',f"{(w.ppe_compliance_pct.eq(100).mean()*100 if len(w) else 0):.1f}%")]
        if 'incidents' in data:
            inc = data['incidents']
            metrics += [('Safety incidents',len(inc)),('Near-miss incident records',int(inc.incident_type.eq('Near miss').sum()))]
        if 'risks' in data:
            r = data['risks']
            metrics += [('Open high / critical observations',int(((r.risk_score>=10)&r.status.ne('Closed')).sum()) if len(r) else 0)]
        if 'equipment' in data:
            eq = data['equipment']
            available = int(((eq.maintenance_status=='Operational')&(eq.condition=='Normal')&eq.due_status.ne('Overdue')).sum()) if len(eq) else 0
            avg = eq.availability_pct.mean() if len(eq) else float('nan')
            metrics += [('Equipment',len(eq)),('Equipment available', available),('Under maintenance',int(eq.maintenance_status.eq('Under maintenance').sum())),('Mean availability',f'{avg:.1f}%' if pd.notna(avg) else 'N/A'),('Equipment alerts',int(alert_df.source.eq('equipment').sum())),('Critical equipment alerts',int(((alert_df.source=='equipment')&(alert_df.level=='Critical')).sum()))]
        metrics += [('Active alerts',len(active)),('Critical alerts',int(alert_df.level.eq('Critical').sum()))]
        for start in range(0,len(metrics),4):
            for col,(name,value) in zip(st.columns(4),metrics[start:start+4]):
                col.metric(name,value)
        if 'incidents' in data and not data['incidents'].empty:
            show_chart(group_count(data['incidents'],'department'),'department','count','Incidents by department')
        if 'equipment' in data and not data['equipment'].empty:
            show_chart(data['equipment'],'id','availability_pct','Equipment availability (%)','condition')
        st.markdown('**Conditions requiring attention**')
        table(alert_df)

    # SECTIONS 3(b)-(e), 3(g): WORKERS, INCIDENTS, EQUIPMENT AND RISK ASSESSMENT
    elif page in ['Workers','Incidents','Equipment','Risk assessment']:
        entity = {'Workers':'workers','Incidents':'incidents','Equipment':'equipment','Risk assessment':'risks'}[page]
        if entity == 'risks':
            st.write('Risk score = likelihood × consequence. Low: 1–4; Medium: 5–9; High: 10–16; Critical: 17–25.')
            c1,c2 = st.columns(2)
            likelihood = c1.slider('Try likelihood',1,5,3)
            consequence = c2.slider('Try consequence',1,5,3)
            score = likelihood*consequence
            level = risk_class(score)
            (st.error if score>=10 else st.info)(f'Risk score {score}: {level}. ' + ('Apply and review controls.' if score>=10 else 'Continue monitoring.'))
        record_editor(store, role, entity, raw[entity])
        df = data[entity].copy()
        query = st.text_input('Search records (literal text)')
        if query and len(df):
            df = df[df.astype(str).apply(lambda c:c.str.contains(query,case=False,regex=False)).any(axis=1)]
        department = st.selectbox('Department', ['All']+sorted(set(r['department'] for r in raw[entity])))
        if department != 'All':
            df = df[df.department==department]
        if entity == 'incidents':
            severity = st.multiselect('Severity',SCHEMAS[entity]['severity'][1],default=SCHEMAS[entity]['severity'][1])
            status = st.multiselect('Status',SCHEMAS[entity]['status'][1],default=SCHEMAS[entity]['status'][1])
            df = df[df.severity.isin(severity)&df.status.isin(status)]
        st.write(f'{len(df)} matching records')
        table(df)
        st.download_button('Download filtered CSV', csv_bytes(df), file_name=entity+'_filtered.csv', mime='text/csv')

    # SECTION 3(f): EQUIPMENT MAINTENANCE MONITORING
    elif page == 'Maintenance':
        eq = data['equipment'].copy()
        st.info('Availability = operating hours ÷ (operating hours + downtime hours) × 100. Zero total hours is N/A. Monitoring thresholds: downtime >24 hours, availability <85%, maintenance due within 7 days, and 3+ abnormal saved observations in 30 days.')
        if len(eq):
            eq['abnormal_observations_30d'] = eq.id.map(repeated).fillna(0).astype(int)
            needs = (eq.due_status!='Not due') | (eq.condition!='Normal') | (eq.maintenance_status!='Operational') | (eq.downtime_hours>24) | (eq.availability_pct<85) | (eq.abnormal_observations_30d>=3)
            st.metric('Equipment requiring attention',int(needs.sum()))
            table(eq[needs].sort_values(['maintenance_priority','availability_pct'],ascending=[True,True]))
            show_chart(eq.sort_values('downtime_hours',ascending=False),'id','downtime_hours','Downtime ranking')
        else:
            st.info('No equipment records yet.')
        st.caption('Update status, due date and maintenance notes on the Equipment page. Each equipment save records a timestamped observation.')
        if history:
            table(pd.DataFrame([{'timestamp':h['timestamp'],'equipment_id':h['equipment_id'],'alerts_in_observation':len(h['alerts'])} for h in history]))
        else:
            st.info('No saved monitoring history yet. Seed records are current snapshots; history starts when you save equipment observations.')

    # SECTION 3(h): ALERTS AND NOTIFICATIONS
    elif page == 'Alerts':
        levels = st.multiselect('Alert levels',['Warning','High','Critical'],default=['Warning','High','Critical'])
        selected = alert_df[alert_df.level.isin(levels)]
        st.metric('Matching active alerts',len(selected))
        table(selected)
        st.caption('Counts measure individual conditions, not unique equipment. Repeated-alert counts measure distinct equipment saves with at least one alert. Resolved current conditions disappear after an update; historical observations remain.')

    # SECTION 3(j): INTERACTIVE DATA ANALYSIS — Appendix A business questions
    elif page == 'Analysis':
        if 'incidents' in data:
            inc = data['incidents'].copy()
            c1,c2 = st.columns(2)
            start = c1.date_input('Incident period starts', date.today()-timedelta(days=60))
            end = c2.date_input('Incident period ends',date.today())
            if start>end:
                st.error('Start date must be on or before end date.')
                return
            inc = inc[(inc.date>=start.isoformat())&(inc.date<=end.isoformat())]
            st.metric('Incidents in selected period',len(inc))
            if not inc.empty:
                group = st.selectbox('Compare incident counts by',['department','shift','incident_type','severity','cause'])
                summary = group_count(inc,group).sort_values('count',ascending=False)
                show_chart(summary,group,'count','Incident comparison')
                table(summary)
                trend = group_count(inc,'date').set_index('date')
                trend.index = pd.to_datetime(trend.index)
                trend = trend.reindex(pd.date_range(start,end),fill_value=0)
                st.plotly_chart(px.line(trend,x=trend.index,y='count',title='Daily incidents (including zero-incident days)',markers=True),width='stretch')
                st.write(f"Near misses: {int(inc.incident_type.eq('Near miss').sum())} · High / critical incidents: {int(inc.severity.isin(['High','Critical']).sum())}")
            else:
                st.info('No incidents in this period.')
        if 'workers' in data and len(data['workers']):
            w=data['workers']
            st.write(f"Fully PPE-compliant workers: {w.ppe_compliance_pct.eq(100).mean()*100:.1f}%. Average individual PPE compliance: {w.ppe_compliance_pct.mean():.1f}%.")
            st.caption('Worker-reported historical near misses are not added to incident-register near misses, because that could double count events.')
        if 'equipment' in data and len(data['equipment']):
            eq = data['equipment'].copy()
            metric = st.selectbox('Rank equipment by',['downtime_hours','availability_pct','vibration_mm_s','temperature_c'])
            eq = eq.sort_values(metric,ascending=metric=='availability_pct',na_position='last')
            show_chart(eq,'id',metric,'Equipment ranking','equipment_type')
            by_type = eq.groupby('equipment_type',as_index=False).downtime_hours.sum()
            show_chart(by_type,'equipment_type','downtime_hours','Total downtime by equipment type')
            st.write(f"Equipment with normal monitored condition: {eq.condition.eq('Normal').mean()*100:.1f}%")
            counts = alert_df[alert_df.source=='equipment'].groupby('record_id').size().reindex(eq.id,fill_value=0).reset_index(name='active_alerts')
            counts.columns=['equipment_id','active_alerts']
            show_chart(counts,'equipment_id','active_alerts','Active alerts by equipment')
            if 'risks' in data:
                risks=data['risks']
                high = risks[(risks.risk_score>=10)&(risks.status!='Closed')] if len(risks) else risks
                combined = eq.groupby('department').downtime_hours.sum().to_frame().join(high.groupby('department').size().rename('open_high_critical_risks'),how='outer').fillna(0).reset_index()
                st.markdown('**Departments: current safety risk and equipment downtime**')
                table(combined)
                st.markdown('**Recommendations from current monitoring results**')
        table(alert_df[['department','record_id','level','recommended_action']].drop_duplicates())

    # SECTION 3(a), TABLE 1: GENERATE REPORTS FOR PERMITTED DATA
    elif page == 'Reports':
        st.write('Export permitted datasets, current alerts and a summary. Restricted data are excluded from all report files.')
        summary = {'generated_utc':datetime.now(timezone.utc).isoformat(),'role':role,'dataset_counts':{k:len(v) for k,v in data.items()},'active_alerts':len(active),'critical_alerts':int(alert_df.level.eq('Critical').sum()),'notes':'Educational thresholds; fictional demo data if demo mode enabled. Counts are current/all-time, not date-filtered.'}
        st.json(summary)
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('summary.json',json.dumps(summary,indent=2))
            archive.writestr('current_alerts.csv',csv_bytes(alert_df))
            for entity,df in data.items():
                archive.writestr(entity+'.csv',csv_bytes(df))
            if 'equipment' in allowed:
                archive.writestr('monitoring_history.json',json.dumps(history,indent=2))
        st.download_button('Download report ZIP',buffer.getvalue(),'khwezi_report.zip','application/zip')
        for entity,df in data.items():
            st.download_button(f'Download {entity} CSV',csv_bytes(df),entity+'.csv','text/csv',key='export_'+entity)

    # SECTION 3(a): ADMINISTRATOR USER MANAGEMENT
    elif page == 'Manage users':
        table(pd.DataFrame(store.users(role),columns=['username','role']))
        st.caption('Administrator-only account creation and password/role updates. At least one administrator must remain.')
        with st.form('user_form'):
            action=st.selectbox('Account action',['Create','Update'])
            username=st.text_input('Account username')
            password=st.text_input('New password (at least 12 characters)',type='password')
            new_role=st.selectbox('Account role',ROLES)
            submitted=st.form_submit_button('Save account')
        if submitted:
            try:
                store.set_user(role,username.strip(),password,new_role,replace=action=='Update')
                st.session_state['notice']='Account saved.'
                st.rerun()
            except (ValueError,PermissionError) as exc:
                st.error(str(exc))

    # SECTION 4: DATA STORAGE — JSON BACKUP AND RESTORE
    elif page == 'Backup and restore':
        st.info('This JSON backup contains operational records only. It excludes passwords and monitoring history. Download the report ZIP separately for history. Restore replaces all operational records and clears history; accounts remain unchanged.')
        backup={'version':1,'records':raw}
        st.download_button('Download operational backup',json.dumps(backup,indent=2),'khwezi_backup.json','application/json')
        uploaded=st.file_uploader('Restore operational JSON backup',type=['json'])
        confirmed=st.checkbox('I understand restore replaces all operational records and clears monitoring history.')
        if st.button('Restore backup',disabled=not(uploaded and confirmed)):
            try:
                if uploaded.size>10*1024*1024:
                    raise ValueError('Maximum backup size is 10 MB.')
                store.restore(role,json.loads(uploaded.getvalue()))
                st.session_state['notice']='Operational records restored. Monitoring history starts again from new saves.'
                st.rerun()
            except (ValueError,TypeError,KeyError,AttributeError,PermissionError) as exc:
                st.error('Backup could not be restored: '+str(exc))

if __name__ == '__main__':
    main()
