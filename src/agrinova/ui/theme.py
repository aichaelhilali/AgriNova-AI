"""AgriNova presentation system. No scientific transformations."""

TEXT = "#11190F"
GREEN = "#186105"
MUTED = "#545D49"
GRID = "#E8E8E8"

CSS = """<style>
.stApp{--ag-ivory:#E8E8E8;--ag-green:#11190F;--ag-secondary:#A3A3A3;--ag-text:#11190F;--ag-muted:#545D49;--ag-border:#E8E8E8;background:var(--ag-ivory);color:var(--ag-text);color-scheme:light;font-family:Inter,'Segoe UI',sans-serif;}
.stApp [data-testid=stHeader]{background:#E8E8E8ED;backdrop-filter:blur(12px);}
.stApp [data-testid=stMainBlockContainer]{max-width:1520px;width:100%;padding:1.3rem clamp(1.2rem,3vw,3.2rem) 3rem;}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:#11190F;letter-spacing:-.6px;}
.stApp h1{font-size:30px;font-weight:750;}.stApp h2{font-size:27px;font-weight:700;}.stApp h3{font-size:21px;font-weight:650;}
.stApp p,.stApp li{font-size:15px;line-height:1.65;}
.stApp [data-testid=stMarkdownContainer],.stApp [data-testid=stWidgetLabel],.stApp [data-testid=stWidgetLabel] p{color:#11190F;}
.stApp [data-testid=stCaptionContainer],.stApp [data-testid=stCaptionContainer] p{color:#545D49;font-size:14px;line-height:1.6;}
.stApp a{color:#545D49;text-underline-offset:4px;}
.stApp [data-testid=stSidebar]{background:#11190F;color:#E8E8E8;border-right:none;}
.stApp [data-testid=stSidebar] [data-testid=stSidebarContent]{padding-top:1.2rem;}
.stApp [data-testid=stSidebar] [data-testid=stMarkdownContainer],.stApp [data-testid=stSidebar] [data-testid=stWidgetLabel] p,.stApp [data-testid=stSidebar] h1,.stApp [data-testid=stSidebar] h2,.stApp [data-testid=stSidebar] h3{color:#E8E8E8;}
.stApp [data-testid=stSidebar] [data-testid=stCaptionContainer] p{color:#C1D7A6;font-size:13px;}
.stApp [data-testid=stSidebar] h1{font-size:19px;letter-spacing:-.3px;}
.stApp [data-testid=stSidebar] a{color:#C1D7A6;}
.sidebar-brand{display:flex;align-items:center;gap:11px;font-size:22px;font-weight:750;letter-spacing:-.7px;padding:0 0 22px;}
.sidebar-brand span{display:grid;place-items:center;width:35px;height:35px;border:1px solid #A3A3A3;border-radius:12px;color:#C1D7A6;font-size:24px;}
.sidebar-label{font-size:11px;letter-spacing:1.8px;font-weight:650;color:#C1D7A6;margin:10px 0 12px;}
.stApp .st-key-dashboard_page [role=radiogroup]{gap:7px;}
.stApp .st-key-dashboard_page label{padding:11px 14px;border-radius:11px;border:1px solid transparent;cursor:pointer;min-height:46px;transition:background .15s;}
.stApp .st-key-dashboard_page label [data-testid=stMarkdownContainer] p{font-size:15px;font-weight:550;color:#E8E8E8;}
.stApp .st-key-dashboard_page label:has(input:checked){background:#E8E8E8;border-color:#E8E8E8;box-shadow:0 5px 15px #11190F20;}
.stApp .st-key-dashboard_page label:has(input:checked) [data-testid=stMarkdownContainer] p{color:#11190F;font-weight:700;}
.stApp .st-key-dashboard_page label:hover{background:#FFFFFF12;}
.stApp .st-key-dashboard_page label:has(input:checked):hover{background:#FFFFFF;}
.stApp .st-key-dashboard_page label>div:first-child{display:none;}
.stApp .st-key-dashboard_page label:focus-within{outline:2px solid #C1D7A6;outline-offset:2px;}
.stApp [data-testid=stSidebar] [data-testid=stForm]{background:#545D49;padding:15px;border-radius:16px;border:1px solid #545D49;}
.stApp [data-testid=stSidebar] [data-testid=stExpander]{background:#545D49;border-color:#545D49;}
.stApp [data-testid=stSidebar] [data-testid=stExpander] summary{color:#E8E8E8;}
.stApp [data-testid=stSidebar] [data-testid=stDateInput] button{color:#11190F;}
.stApp [data-testid=stSidebar] button[kind^=primary]{background:#C1D7A6;border-color:#C1D7A6;}
.stApp [data-testid=stSidebar] button[kind^=primary] p{color:#11190F!important;}
.stApp [data-testid=stSidebar] [data-testid=stSelectbox] [data-testid=stMarkdownContainer]{color:#11190F;}
.hero{display:flex;align-items:center;justify-content:space-between;gap:25px;border-bottom:1px solid #E8E8E8;padding:4px 0 23px;margin-bottom:14px;}
.brand-lockup{display:flex;gap:14px;align-items:center;}.brand-icon{height:45px;width:45px;flex-shrink:0;display:grid;place-items:center;border-radius:14px;background:#E8E8E8;}.brand-icon svg{width:30px;height:30px;}
.stApp .hero h1{font-size:27px;line-height:1.2;margin:0;padding:0;}.stApp .hero p{font-size:14px;margin:5px 0 0;color:#545D49;}
.brand-meta{display:flex;flex-direction:column;align-items:flex-end;gap:7px;font-size:12px;color:#545D49;white-space:nowrap;}
.location-pill{display:inline-flex;align-items:center;gap:7px;font-weight:600;font-size:12px;padding:6px 10px;border-radius:999px;border:1px solid #E8E8E8;background:#E8E8E8;color:#11190F;}
.location-pill:before{content:'';width:6px;height:6px;border-radius:50%;background:#A3A3A3;}
.overview-hero{position:relative;overflow:hidden;display:flex;justify-content:space-between;min-height:285px;padding:36px 40px;border-radius:24px;background:linear-gradient(120deg,#11190F,#545D49);box-shadow:0 12px 30px #11190F12;margin:8px 0 24px;}
.hero-copy{position:relative;z-index:1;max-width:600px;}.hero-eyebrow{color:#C1D7A6;font-size:11px;font-weight:650;letter-spacing:1.9px;margin-bottom:14px;}
.stApp .overview-hero h2{color:#E8E8E8;font-size:clamp(27px,3vw,41px);line-height:1.18;font-weight:650;padding:0;margin:0 0 17px;letter-spacing:-1.2px;}
.stApp .overview-hero p{color:#E8E8E8;font-size:15px;max-width:470px;line-height:1.7;margin:0;}
.hero-tags{display:flex;gap:9px;flex-wrap:wrap;margin-top:24px;}.hero-tags span{border:1px solid #A3A3A350;border-radius:7px;color:#E8E8E8;background:#FFFFFF08;font-size:11px;font-weight:550;padding:5px 10px;}
.field-art{position:absolute;right:0;bottom:0;width:40%;height:100%;opacity:.9;}.illustration-label{position:absolute;bottom:15px;right:21px;font-size:9px;letter-spacing:1.4px;color:#C1D7A6;}
.overview-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:17px;margin:0 0 27px;}
.overview-kpi{border:1px solid #E8E8E8;background:white;border-radius:18px;box-shadow:0 5px 16px #11190F04;padding:20px 21px;min-width:0;}
.kpi-top{display:flex;align-items:center;justify-content:space-between;gap:8px;color:#545D49;font-size:13px;font-weight:550;}
.kpi-icon{font-size:10px;color:#545D49;background:#E8E8E8;border-radius:9px;padding:7px;}
.overview-kpi strong{display:block;color:#11190F;font-weight:650;font-size:clamp(21px,2vw,30px);letter-spacing:-1px;line-height:1.5;margin:12px 0 8px;overflow-wrap:anywhere;}
.stApp .overview-kpi p{font-size:11px;color:#545D49;line-height:1.5;margin:0;}
.stApp .st-key-overview_context,.stApp .st-key-overview_workflow{background:#FFFFFF;border-radius:20px;box-shadow:0 5px 18px #11190F04;height:100%;padding:10px;}
.section-heading{display:flex;gap:13px;align-items:center;margin:4px 0 18px;}.section-index{display:grid;place-items:center;border-radius:10px;width:36px;height:36px;flex-shrink:0;background:#E8E8E8;color:#545D49;font-size:12px;font-weight:650;}
.section-eyebrow{font-size:12px;font-weight:700;color:#11190F;letter-spacing:.9px;text-transform:uppercase;}.stApp .section-heading p{margin:2px 0 0;color:#545D49;font-size:12px;}
.context-list{margin:0;}.context-list>div{padding:14px 0;border-top:1px solid #E8E8E8;display:flex;justify-content:space-between;align-items:center;gap:15px;}.context-list dt{color:#545D49;font-size:13px;}.context-list dd{margin:0;font-size:14px;color:#11190F;font-weight:550;text-align:right;}.data-status{background:#E8E8E8;color:#545D49;border-radius:6px;padding:5px 8px;font-size:12px;}
.workflow-list>div{display:flex;align-items:flex-start;gap:12px;margin:17px 0;}.workflow-dot{height:9px;width:9px;flex-shrink:0;margin-top:6px;border-radius:50%;background:#A3A3A3;box-shadow:0 0 0 4px #E8E8E8;}.workflow-list strong{color:#11190F;font-size:14px;font-weight:600;}.stApp .workflow-list p{margin:1px 0 0;font-size:12px;color:#545D49;}
.science-strip{margin:24px 0;padding:20px 23px;border:1px solid #E8E8E8;border-radius:15px;display:flex;align-items:center;justify-content:space-between;gap:15px;background:#E8E8E8;}.science-strip strong{color:#545D49;font-size:14px;font-weight:600;}.science-strip span{color:#545D49;font-size:12px;}
.stApp [role=tablist]{display:flex;gap:22px;margin:3px 0 18px;padding:0 0 6px;background:transparent;border-bottom:1px solid #E8E8E8;height:auto;}
.stApp button[role=tab]{min-height:47px;padding:8px 3px;background:transparent;color:#545D49;border-radius:0;font-weight:550;}
.stApp button[role=tab] p{color:inherit;font-size:14px;}.stApp button[role=tab][aria-selected=true]{color:#11190F;}.stApp button[role=tab][aria-selected=true] p{color:#11190F;font-weight:700;}
.stApp [data-baseweb=tab-highlight]{background:#11190F;height:3px;border-radius:3px;}.stApp [data-baseweb=tab-border]{background:transparent;}
.stApp [data-testid=stMetric]{background:#FFFFFF;padding:23px 24px;height:100%;border:1px solid #E8E8E8;border-radius:18px;box-shadow:0 4px 18px #11190F04;}
.stApp [data-testid=stMetricLabel],.stApp [data-testid=stMetricLabel] p{color:#545D49;font-size:13px;font-weight:550;}
.stApp [data-testid=stMetricValue]{color:#11190F;font-size:clamp(24px,2.1vw,33px);font-weight:650;letter-spacing:-.9px;}.stApp [data-testid=stMetricValue]>div{white-space:normal;overflow-wrap:anywhere;}
.stApp [data-testid=stPlotlyChart]{background:#FFFFFF;border:1px solid #E8E8E8;border-radius:21px;padding:14px 10px;overflow:hidden;box-shadow:0 6px 22px #11190F05;}
.stApp [data-testid=stExpander]{border:1px solid #E8E8E8;border-radius:14px;background:#FFFFFF;}.stApp [data-testid=stExpander] summary{min-height:51px;padding:12px 16px;color:#11190F;font-size:14px;font-weight:550;}
.stApp [data-testid=stForm]{border-color:#E8E8E8;border-radius:18px;}.stApp input,.stApp textarea,.stApp [data-baseweb=input],.stApp [data-baseweb=base-input],.stApp [data-baseweb=select]>div{color:#11190F;background:#FFFFFF;caret-color:#11190F;font-size:14px;}
.stApp [data-baseweb=tag]{background:#E8E8E8;color:#11190F;}.stApp input::placeholder,.stApp textarea::placeholder{color:#545D49;opacity:1;}
.stApp [data-testid=stWidgetLabel] p{font-size:14px;font-weight:550;}
.stApp [data-testid=stButton] button,.stApp [data-testid=stFormSubmitButton] button,.stApp [data-testid=stDownloadButton] button{min-height:44px;border-radius:10px;padding:10px 17px;font-weight:600;}
.stApp button[kind^=primary]{background:#11190F;border-color:#11190F;}.stApp button[kind^=primary] p,.stApp button[kind^=primary] [data-testid=stMarkdownContainer]{color:#FFFFFF;}
.stApp button[kind^=secondary],.stApp button[kind^=tertiary]{background:#FFFFFF;border-color:#C1D7A6;color:#11190F;}.stApp button[kind^=secondary] p,.stApp button[kind^=tertiary] p{color:#11190F;}
.stApp button[kind^=secondary]:hover{background:#E8E8E8;border-color:#A3A3A3;}.stApp button[kind^=primary]:hover{background:#545D49;border-color:#545D49;}.stApp button:disabled{opacity:.6;}
.stApp button:focus-visible,.stApp input:focus-visible,.stApp textarea:focus-visible{outline:3px solid #A3A3A3;outline-offset:3px;}
.stApp [data-testid=stAlertContainer]{border-radius:13px;font-size:14px;}.stApp [data-testid=stAlertContainer][kind=warning]{background:#E8E8E8;color:#545D49;border:1px solid #C1D7A6;}.stApp [data-testid=stAlertContainer][kind=error]{background:#E8E8E8;color:#545D49;border:1px solid #C1D7A6;}
.stApp .st-key-rotation_grid,.stApp .st-key-climate_metrics{container-type:inline-size;width:100%;}.stApp .st-key-rotation_grid [data-testid=stHorizontalBlock],.stApp .st-key-climate_metrics [data-testid=stHorizontalBlock]{gap:18px;align-items:stretch;}
.stApp .st-key-rotation_grid [data-testid=stColumn],.stApp .st-key-climate_metrics [data-testid=stColumn]{min-width:0;flex:1 1 0;}
.stApp [class*=st-key-rotation_card_]{background:#FFFFFF;border-radius:20px;padding:7px;height:100%;box-shadow:0 6px 22px #11190F06;}
.stApp .st-key-rotation_card_0{border-top:4px solid #11190F;}.stApp .st-key-rotation_card_1{border-top:4px solid #A3A3A3;}.stApp .st-key-rotation_card_2{border-top:4px solid #C1D7A6;}
.stApp [class*=st-key-rotation_card_] h3{font-size:22px;padding:10px 0;}.scenario-badge{display:inline-flex;padding:5px 9px;font-size:10px;font-weight:750;letter-spacing:1px;border-radius:6px;color:#545D49;background:#E8E8E8;}.scenario-badge.reference{background:#11190F;color:#FFFFFF;}.scenario-badge.demo{background:#E8E8E8;color:#545D49;}
.input-guide{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px;}.input-guide span{font-size:10px;font-weight:650;color:#545D49;padding:4px 7px;background:#E8E8E8;border-radius:5px;letter-spacing:.4px;}
.stApp .st-key-comparison_results{background:#FFFFFF;border-radius:20px;box-shadow:0 6px 22px #11190F05;padding:8px;}
.stApp [data-testid=stDataFrame]{border-radius:12px;border:1px solid #E8E8E8;overflow:hidden;}
.stApp .st-key-dashboard_exports [data-testid=stDownloadButton] button{width:100%;justify-content:space-between;text-align:left;box-shadow:0 3px 10px #11190F03;}
.stApp .st-key-dashboard_exports [data-testid=stVerticalBlockBorderWrapper]{border-radius:18px;background:#FFFFFF;}
.empty-state{padding:42px 30px;border:1px dashed #C1D7A6;border-radius:22px;background:linear-gradient(140deg,#FFFFFF,#E8E8E8);text-align:center;margin:12px 0 25px;}.empty-symbol{margin:0 auto 18px;display:grid;place-items:center;width:58px;height:58px;border-radius:18px;background:#E8E8E8;color:#11190F;font-size:28px;}.stApp .empty-state h3{font-size:23px;margin:0 0 9px;}.stApp .empty-state p{max-width:610px;margin:0 auto;color:#545D49;}
@media(min-width:901px){.stApp [data-testid=stSidebar][aria-expanded=true]{width:282px!important;min-width:282px;}}
@container(max-width:1000px){.st-key-rotation_grid [data-testid=stHorizontalBlock],.st-key-climate_metrics [data-testid=stHorizontalBlock]{flex-wrap:wrap;}.st-key-rotation_grid [data-testid=stColumn],.st-key-climate_metrics [data-testid=stColumn]{flex:0 0 calc((100% - 18px)/2)!important;width:calc((100% - 18px)/2)!important;}}
@container(max-width:620px){.st-key-rotation_grid [data-testid=stColumn],.st-key-climate_metrics [data-testid=stColumn]{flex:1 1 100%!important;width:100%!important;}}
@media(max-width:1150px){.overview-kpis{grid-template-columns:repeat(2,minmax(0,1fr));}.field-art{opacity:.45;}.hero-copy{max-width:80%;}.science-strip{align-items:flex-start;flex-direction:column;}}
@media(max-width:760px){.stApp [data-testid=stMainBlockContainer]{padding:1rem 1rem 2rem;}.hero{align-items:flex-start;gap:14px;flex-wrap:wrap;}.brand-meta{flex-direction:row;align-items:center;flex-wrap:wrap;}.brand-lockup{gap:10px;}.stApp .hero p{font-size:12px;}.overview-hero{padding:25px;min-height:290px;border-radius:19px;}.hero-copy{max-width:100%;}.field-art{opacity:.13;width:80%;}.overview-kpis{gap:10px;}.overview-kpi{padding:16px;}.kpi-top{font-size:12px;}.kpi-icon{display:none;}.context-list>div{align-items:flex-start;flex-direction:column;gap:6px;}.context-list dd{text-align:left;}.stApp [data-testid=stHorizontalBlock]{flex-wrap:wrap;}.stApp [data-testid=stColumn]{min-width:0;}.stApp [role=tablist]{gap:15px;overflow-x:auto;}.stApp button[role=tab]{white-space:nowrap;}.empty-state{padding:28px 20px;}}
@media(max-width:420px){.overview-kpis{grid-template-columns:1fr;}.stApp .hero h1{font-size:24px;}}
@media(prefers-reduced-motion:no-preference){.stApp button{transition:background-color .18s,border-color .18s,box-shadow .18s;}}
/* Original shell inspired by the reference's light icon rail and rounded cards. */
.stApp{background:#F5F5F5;}
.stApp [data-testid="stHeader"]{background:#F5F5F5ED;}
.stApp [data-testid="stSidebar"]{background:#F5F5F5;border-right:1px solid #E8E8E8;}
.stApp [data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding:12px 9px;}
.sidebar-brand{justify-content:center;padding:8px 0 22px;}
.sidebar-brand span{width:44px;height:44px;background:#186105;color:#FFFFFF;border:0;border-radius:15px;font-size:16px;letter-spacing:-1px;}
.stApp .st-key-dashboard_page label{display:flex;flex-direction:column;align-items:center;gap:6px;padding:12px 5px;border:0;background:#FFFFFF;box-shadow:0 2px 5px #11190F04;border-radius:13px;min-height:74px;}
.stApp .st-key-dashboard_page label [data-testid="stMarkdownContainer"] p{font-size:14px;line-height:1.3;text-align:center;color:#545D49;font-weight:550;}
.stApp .st-key-dashboard_page label:before{content:'⌂';font-family:'Segoe UI Symbol',sans-serif;font-size:24px;line-height:1;color:#11190F;}
.stApp .st-key-dashboard_page label:nth-of-type(2):before{content:'☀';}
.stApp .st-key-dashboard_page label:nth-of-type(3):before{content:'▧';}
.stApp .st-key-dashboard_page label:nth-of-type(4):before{content:'♧';}
.stApp .st-key-dashboard_page label:nth-of-type(5):before{content:'⇄';}
.stApp .st-key-dashboard_page label:nth-of-type(6):before{content:'▤';}
.stApp .st-key-dashboard_page label:nth-of-type(7):before{content:'⚙';}
.stApp .st-key-dashboard_page label:nth-of-type(8):before{content:'↗';}
.stApp .st-key-dashboard_page label:has(input:checked){background:linear-gradient(#545D49,#11190F);box-shadow:0 4px 8px #11190F20;}
.stApp .st-key-dashboard_page label:has(input:checked) [data-testid="stMarkdownContainer"] p,.stApp .st-key-dashboard_page label:has(input:checked):before{color:#FFFFFF;}
.stApp .st-key-dashboard_page label:hover{background:#C1D7A640;}
.stApp .st-key-dashboard_page label:has(input:checked):hover{background:#11190F;}
.stApp .st-key-dashboard_page label:nth-of-type(7){margin-top:25px;}
.stApp [data-testid="stMainBlockContainer"]{max-width:1800px;padding:1.1rem clamp(18px,2.2vw,35px) 2.5rem;}
.hero{border:0;padding:3px 0 10px;margin-bottom:0;}
.brand-icon{background:#C1D7A6;}.brand-meta{font-size:14px;}
.stApp .hero h1{color:#11190F;font-size:27px;}.stApp .hero p{font-size:14px;}
.toolbar-context{display:flex;align-items:center;gap:14px;flex-wrap:wrap;font-size:14px;color:#545D49;padding-bottom:8px;}
.toolbar-status{font-size:13px;color:#186105;}.toolbar-status:before{content:'●';font-size:9px;margin-right:6px;}
.stApp .st-key-dashboard_toolbar{margin-bottom:15px;}
.stApp .st-key-dashboard_toolbar button{background:#11190F;border-color:#11190F;}
.stApp .st-key-dashboard_toolbar button p{color:#FFFFFF;}
.overview-hero{background:#FFFFFF;border:0;min-height:350px;box-shadow:0 4px 20px #11190F03;border-radius:24px;padding:30px;margin:0 0 20px;}
.hero-eyebrow{color:#545D49;font-size:12px;letter-spacing:1.3px;}
.stApp .overview-hero h2{color:#11190F;font-size:clamp(27px,2.5vw,38px);font-weight:600;letter-spacing:-1.2px;}
.stApp .overview-hero p{color:#545D49;font-size:15px;max-width:400px;}
.hero-copy{max-width:65%;}.field-art{height:78%;width:48%;right:0;bottom:0;opacity:1;}
.illustration-label{color:#545D49;font-size:10px;}.hero-tags{max-width:350px;}
.hero-tags span{background:#C1D7A630;border-color:#E8E8E8;color:#186105;font-size:12px;}
.overview-kpis{gap:13px;margin-bottom:18px;}.overview-kpi{padding:18px;background:#FFFFFF;border:0;border-radius:19px;}
.overview-kpi:first-child{background:#186105;}
.overview-kpi:first-child .kpi-top,.overview-kpi:first-child strong,.stApp .overview-kpi:first-child p{color:#FFFFFF;}
.kpi-top{font-size:14px;line-height:1.45;}
.overview-kpi strong{font-size:clamp(23px,2vw,31px);color:#11190F;font-weight:550;margin:14px 0;}
.stApp .overview-kpi p{font-size:13px;color:#545D49;}
.stApp [class*="st-key-overview_"]{border:0!important;border-radius:23px;background:#FFFFFF;}
.stApp .st-key-overview_context,.stApp .st-key-overview_workflow{padding:10px;}
.stApp .st-key-overview_quality,.stApp .st-key-overview_evidence,.stApp .st-key-overview_scope{padding:9px;}
.stApp .st-key-overview_evidence{background:linear-gradient(150deg,#C1D7A6,#FFFFFF);}
.evidence-badge{font-size:12px;letter-spacing:.8px;display:inline-block;color:#186105;background:#FFFFFF;border-radius:8px;padding:7px 10px;margin:6px 0 12px;font-weight:650;}
.coverage-heading{display:flex;justify-content:space-between;gap:8px;font-size:14px;color:#545D49;margin:18px 0 9px;}
.coverage-heading strong{font-weight:600;color:#11190F;}
.coverage-track{height:10px;background:#E8E8E8;border-radius:5px;overflow:hidden;margin-bottom:15px;}
.coverage-track span{display:block;height:100%;background:#57A735;border-radius:5px;}
.stApp .section-heading p{font-size:14px;}.section-eyebrow{font-size:13px;color:#11190F;}
.section-index{background:#C1D7A650;color:#186105;}.context-list dt,.context-list dd{font-size:14px;}
.stApp [data-testid="stPlotlyChart"]{border:0;border-radius:24px;padding:16px 12px;}
.stApp [data-testid="stMetric"]{border:0;border-radius:20px;}
.stApp [data-testid="stMetricValue"]{color:#11190F;}.stApp [data-testid="stMetricLabel"] p{font-size:14px;}
.stApp [data-testid="stAlertContainer"][kind="warning"]{background:#ADAF4D20;border:1px solid #ADAF4D70;color:#545D49;}
.stApp [data-testid="stAlertContainer"][kind="error"]{background:#E8E8E8;border:1px solid #A3A3A3;color:#11190F;}
.stApp [data-testid="stExpander"]{border:1px solid #E8E8E8;background:#FFFFFF;}
.stApp [data-testid="stDataFrame"]{border-color:#E8E8E8;}
.scenario-badge{font-size:12px;letter-spacing:.4px;}.scenario-badge.demo{background:#ADAF4D30;color:#545D49;}
.input-guide span{font-size:12px;}.stApp [class*="st-key-rotation_card_"]{border-left:0;border-right:0;border-bottom:0;padding:10px;}
.stApp .st-key-rotation_card_0{border-top-color:#186105;}.stApp .st-key-rotation_card_1{border-top-color:#57A735;}.stApp .st-key-rotation_card_2{border-top-color:#ADAF4D;}
.stApp .st-key-dashboard_settings [data-testid="stForm"]{background:#FFFFFF;padding:24px;}
.stApp .st-key-dashboard_exports [data-testid="stVerticalBlockBorderWrapper"]{border:0!important;}
@media(min-width:901px){.stApp [data-testid="stSidebar"][aria-expanded="true"]{width:152px!important;min-width:152px;}}
@media(max-width:1200px){.overview-kpis{grid-template-columns:repeat(2,minmax(0,1fr));}.hero-copy{max-width:80%;}.field-art{opacity:.5;}.stApp .overview-hero h2{font-size:29px;}}
@media(max-width:900px){.hero-copy{max-width:100%;}.field-art{opacity:.15;width:65%;}.overview-hero{min-height:300px;}.brand-meta{display:none;}}
.stApp .st-key-dashboard_page label>div:first-child{display:block;position:absolute;width:1px;height:1px;opacity:0;overflow:hidden;}
.stApp{--ag-green:#186105;--ag-secondary:#57A735;--ag-text:#11190F;--ag-muted:#545D49;}
.stApp .overview-kpi strong{overflow-wrap:anywhere;}
.stApp,.stApp [data-testid="stSidebar"]{background:color-mix(in srgb,#E8E8E8 42%,#FFFFFF);}
.stApp [data-testid="stHeader"]{background:color-mix(in srgb,#E8E8E8 42%,#FFFFFF);}
.stApp .st-key-comparison_grid{container-type:inline-size;width:100%;}
.comparison-summary{background:#FFFFFF;border-radius:22px;padding:24px;height:100%;border-top:3px solid #57A735;}
.stApp .comparison-summary h3{font-size:22px;margin:16px 0 8px;line-height:1.4;}
.comparison-origin{font-size:12px;letter-spacing:.6px;color:#545D49;}
.stApp .comparison-summary p{font-size:14px;color:#545D49;}
.comparison-total{border-top:1px solid #E8E8E8;padding-top:15px;display:flex;flex-direction:column;gap:7px;}
.comparison-total span,.comparison-coverage{font-size:14px;color:#545D49;}
.comparison-total strong{font-size:20px;color:#11190F;font-weight:600;}
.comparison-coverage{margin-top:13px;}.stApp .comparison-caution{font-size:13px;background:#C1D7A630;border-radius:9px;padding:9px;}
@container(max-width:1000px){.st-key-comparison_grid [data-testid="stHorizontalBlock"]{flex-wrap:wrap;}.st-key-comparison_grid [data-testid="stColumn"]{flex:0 0 calc((100% - 16px)/2)!important;width:calc((100% - 16px)/2)!important;}}
@container(max-width:620px){.st-key-comparison_grid [data-testid="stColumn"]{flex:1 1 100%!important;width:100%!important;}}
</style>"""


def style_climate_chart(figure, title):
    """Apply chart typography and surfaces without changing trace values."""
    figure.update_layout(
        template="plotly_white", autosize=True,
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font={"color": TEXT, "family": "Inter, Segoe UI, sans-serif", "size": 14},
        title={"text": title, "font": {"color": GREEN, "size": 20}, "x": 0.02, "xanchor": "left", "automargin": True},
        legend={"orientation": "h", "y": 1.08, "x": 0, "font": {"color": TEXT, "size": 12}, "bgcolor": "#FFFFFF"},
        hovermode="x unified",
        hoverlabel={"bgcolor": "#FFFFFF", "font": {"color": TEXT, "size": 14}},
        margin={"l": 50, "r": 25, "t": 105, "b": 55}, height=440,
    )
    figure.update_xaxes(color=MUTED, showgrid=False, zerolinecolor=GRID, automargin=True)
    figure.update_yaxes(color=TEXT, gridcolor=GRID, zerolinecolor=GRID, automargin=True)
    return figure
