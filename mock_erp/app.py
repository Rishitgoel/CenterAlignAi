from contextlib import asynccontextmanager
from typing import List, Optional
import aiosqlite
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from mock_erp.database import (
    create_invoice,
    delete_invoice,
    get_all_invoices,
    get_invoice,
    get_vendors,
    init_db,
    search_invoices,
)
from mock_erp.models import InvoiceCreateRequest, InvoiceRecord, VendorRecord


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and tables on startup
    await init_db()
    yield


app = FastAPI(
    title="CentrAlign Mock Enterprise ERP System",
    description="Internal company API simulating ERP/CRM endpoints for autonomous task execution.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    response = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="CentrAlign ERP — API Documentation",
        swagger_favicon_url="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>❖</text></svg>",
    )
    custom_css = """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.cdnfonts.com/css/google-sans" rel="stylesheet">
    <style>
        * {
            font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }
        body, html {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        .swagger-ui {
            color: #000000 !important;
        }
        .swagger-ui .topbar {
            background-color: #f8f8fa !important;
            border-bottom: 1px solid #e2e2e8 !important;
            padding: 12px 0 !important;
        }
        .swagger-ui .topbar a {
            filter: grayscale(100%) contrast(150%) brightness(0.2) !important;
        }
        .swagger-ui .topbar .download-url-wrapper .download-url-button {
            background-color: #000000 !important;
            color: #ffffff !important;
            border: 1px solid #000000 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
        }
        .swagger-ui .info {
            margin: 25px 0 !important;
        }
        .swagger-ui .info .title {
            color: #000000 !important;
            font-weight: 700 !important;
            letter-spacing: -0.03em !important;
        }
        .swagger-ui .info p, .swagger-ui .info li {
            color: #55555c !important;
        }
        .swagger-ui .scheme-container {
            background-color: #f8f8fa !important;
            box-shadow: none !important;
            border-bottom: 1px solid #e2e2e8 !important;
        }
        .swagger-ui .opblock {
            background-color: #ffffff !important;
            border: 1px solid #e2e2e8 !important;
            box-shadow: none !important;
            border-radius: 8px !important;
            margin-bottom: 12px !important;
            transition: border-color 0.2s ease !important;
        }
        .swagger-ui .opblock:hover {
            border-color: #000000 !important;
        }
        .swagger-ui .opblock .opblock-summary {
            border-bottom: 1px solid transparent !important;
            padding: 10px 16px !important;
        }
        .swagger-ui .opblock.is-open .opblock-summary {
            border-bottom: 1px solid #e2e2e8 !important;
        }
        .swagger-ui .opblock .opblock-summary-method {
            background-color: #000000 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 4px !important;
            text-shadow: none !important;
            min-width: 72px !important;
            border: 1px solid #000000 !important;
        }
        .swagger-ui .opblock-get,
        .swagger-ui .opblock-post,
        .swagger-ui .opblock-delete,
        .swagger-ui .opblock-put {
            border-color: #e2e2e8 !important;
            background: #ffffff !important;
        }
        .swagger-ui .opblock .opblock-summary-path {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        .swagger-ui .opblock .opblock-summary-description {
            color: #55555c !important;
        }
        .swagger-ui .opblock-body {
            background-color: #fafafc !important;
            color: #000000 !important;
        }
        .swagger-ui table thead tr th,
        .swagger-ui table thead tr td {
            color: #55555c !important;
            border-bottom: 1px solid #e2e2e8 !important;
        }
        .swagger-ui table tbody tr td {
            color: #000000 !important;
            border-bottom: 1px solid #f0f0f4 !important;
        }
        .swagger-ui .parameter__name,
        .swagger-ui .parameter__type {
            color: #000000 !important;
        }
        .swagger-ui input[type=text],
        .swagger-ui textarea,
        .swagger-ui select {
            background: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #e2e2e8 !important;
            border-radius: 6px !important;
        }
        .swagger-ui input[type=text]:focus,
        .swagger-ui textarea:focus,
        .swagger-ui select:focus {
            border-color: #000000 !important;
            outline: none !important;
        }
        .swagger-ui .btn {
            border-radius: 6px !important;
            background: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #000000 !important;
            box-shadow: none !important;
            transition: all 0.2s ease !important;
        }
        .swagger-ui .btn:hover {
            background: #000000 !important;
            color: #ffffff !important;
        }
        .swagger-ui .btn.execute {
            background-color: #000000 !important;
            color: #ffffff !important;
            border-color: #000000 !important;
            font-weight: 700 !important;
        }
        .swagger-ui .btn.execute:hover {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        .swagger-ui .btn.try-out__btn {
            border-color: #000000 !important;
            color: #000000 !important;
        }
        .swagger-ui .btn.try-out__btn:hover {
            border-color: #000000 !important;
            background: #000000 !important;
            color: #ffffff !important;
        }
        .swagger-ui .responses-inner {
            background: #ffffff !important;
        }
        .swagger-ui .response-col_status {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        .swagger-ui pre,
        .swagger-ui code,
        .swagger-ui .highlight-code {
            background: #f4f4f8 !important;
            color: #000000 !important;
            border: 1px solid #e2e2e8 !important;
            font-family: 'JetBrains Mono', monospace !important;
        }
        .swagger-ui svg,
        .swagger-ui img {
            filter: grayscale(100%) contrast(150%) brightness(0.4) !important;
        }
        .swagger-ui .model-box,
        .swagger-ui section.models {
            background: #fafafc !important;
            border: 1px solid #e2e2e8 !important;
        }
        .swagger-ui section.models h4 {
            color: #000000 !important;
        }
    </style>
    """
    body = response.body.decode().replace("</head>", f"{custom_css}</head>")
    return HTMLResponse(content=body)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>CentrAlign ERP — ReDoc Specification</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.cdnfonts.com/css/google-sans" rel="stylesheet">
    <link rel="shortcut icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>❖</text></svg>">
    <style>
        * {
            font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }
        body {
            margin: 0;
            padding: 0;
            background: #ffffff;
            color: #000000;
        }
        /* Monochrome filters for ReDoc icons/SVGs */
        svg, img {
            filter: grayscale(100%) contrast(140%) !important;
        }
        /* Force Google Sans on all ReDoc rendered elements */
        .redoc-wrap, .menu-content, .api-content,
        h1, h2, h3, h4, h5, h6, p, span, div, a, li, label {
            font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        code, pre, .code-snippet, [class*="code"] {
            font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace !important;
        }
    </style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
    <script>
        Redoc.init('/openapi.json', {
            theme: {
                typography: {
                    fontFamily: "'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif",
                    fontSize: "14px",
                    lineHeight: "1.55em",
                    fontWeightRegular: "400",
                    fontWeightBold: "600",
                    fontWeightLight: "300",
                    headings: {
                        fontFamily: "'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif",
                        fontWeight: "700",
                        lineHeight: "1.35em"
                    },
                    code: {
                        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                        fontSize: "13px"
                    }
                },
                colors: {
                    primary: {
                        main: '#000000'
                    },
                    text: {
                        primary: '#000000',
                        secondary: '#55555c'
                    },
                    border: {
                        dark: '#000000',
                        light: '#e2e2e8'
                    },
                    http: {
                        get: '#000000',
                        post: '#000000',
                        put: '#000000',
                        delete: '#000000'
                    }
                },
                sidebar: {
                    backgroundColor: '#fafafc',
                    textColor: '#111115'
                },
                rightPanel: {
                    backgroundColor: '#111115',
                    textColor: '#ffffff'
                }
            }
        }, document.getElementById('redoc-container'));
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/", include_in_schema=False)
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" not in accept and "application/json" in accept:
        return JSONResponse({
            "service": "CentrAlign Mock Enterprise ERP System",
            "status": "online",
            "docs": "/docs",
            "endpoints": {
                "health": "/health",
                "invoices": "/invoices",
                "search_invoices": "/invoices/search",
                "vendors": "/vendors",
                "docs": "/docs",
                "redoc": "/redoc",
            },
        })

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CentrAlign AI — Enterprise ERP</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.cdnfonts.com/css/google-sans" rel="stylesheet">
    <style>
        :root {
            /* Permanent Minimal High-Contrast Light Theme */
            --bg: #ffffff;
            --dot-color: rgba(0, 0, 0, 0.05);
            --surface: #ffffff;
            --surface-hover: #f7f7fa;
            --surface-elevated: #f2f2f6;
            --surface-input: #ffffff;
            --border: #e2e2e8;
            --border-hover: #000000;
            --border-subtle: #f0f0f4;
            --text-main: #000000;
            --text-sub: #333338;
            --text-muted: #666672;
            --badge-bg: #ffffff;
            --badge-text: #000000;
            --badge-border: #000000;
            --btn-primary-bg: #000000;
            --btn-primary-text: #ffffff;
            --btn-primary-border: #000000;
            --btn-primary-hover-bg: #ffffff;
            --btn-primary-hover-text: #000000;
            --th-bg: #f6f6f9;
            --cmd-bg: #f6f6f9;
            --tab-inactive-bg: #f6f6f9;
            --tab-inactive-text: #666672;
            --tab-active-bg: #000000;
            --tab-active-text: #ffffff;
            --mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            --radius-card: 12px;
            --radius-inner: 8px;
            --radius-control: 6px;
            --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
            --card-shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg);
            background-image: radial-gradient(var(--dot-color) 1px, transparent 1px);
            background-size: 24px 24px;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px 80px 20px;
        }

        /* Black and white monochrome filter for all emojis */
        .bw-emoji, .emoji {
            display: inline-block;
            vertical-align: -0.1em;
            filter: grayscale(100%) contrast(160%) brightness(0.75);
            -webkit-filter: grayscale(100%) contrast(160%) brightness(0.75);
        }

        .container {
            width: 100%;
            max-width: 1040px;
        }

        /* Top Navigation Header */
        .top-nav {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 16px 24px;
            margin-bottom: 24px;
            box-shadow: var(--card-shadow);
        }

        .brand-group {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-glyph {
            font-size: 1.4rem;
            color: var(--text-main);
            line-height: 1;
        }

        .brand-text h1 {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        .brand-text p {
            font-size: 0.72rem;
            color: var(--text-muted);
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-weight: 500;
            margin-top: 1px;
        }

        .nav-controls {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--badge-bg);
            border: 1px solid var(--badge-border);
            color: var(--badge-text);
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            background-color: var(--badge-text);
            border-radius: 50%;
            box-shadow: 0 0 6px var(--badge-text);
        }

        .host-badge {
            font-family: var(--mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            background: var(--surface-elevated);
            padding: 6px 10px;
            border-radius: var(--radius-control);
            border: 1px solid var(--border);
        }

        /* Hero Intro */
        .hero {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 28px 32px;
            margin-bottom: 24px;
            box-shadow: var(--card-shadow);
        }

        .hero h2 {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.03em;
            margin-bottom: 8px;
        }

        .hero p {
            font-size: 0.95rem;
            color: var(--text-sub);
            line-height: 1.6;
            max-width: 840px;
        }

        /* Section Headers */
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
        }

        .section-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            font-weight: 600;
        }

        /* Metrics / KPIs */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }

        @media (max-width: 800px) {
            .kpi-grid { grid-template-columns: repeat(2, 1fr); }
        }

        .kpi-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 18px 20px;
            box-shadow: var(--card-shadow);
            transition: all 0.18s ease;
        }

        .kpi-card:hover {
            border-color: var(--border-hover);
            transform: translateY(-1px);
            box-shadow: var(--card-shadow-hover);
        }

        .kpi-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 8px;
            font-weight: 600;
        }

        .kpi-val {
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        .kpi-sub {
            font-size: 0.72rem;
            color: var(--text-muted);
            margin-top: 4px;
            font-family: var(--mono);
        }

        /* Quick API Endpoints Grid */
        .links-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }

        @media (max-width: 800px) {
            .links-grid { grid-template-columns: 1fr; }
        }

        .link-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 16px 20px;
            text-decoration: none;
            color: var(--text-main);
            box-shadow: var(--card-shadow);
            transition: all 0.18s ease;
        }

        .link-card:hover {
            background: var(--surface-hover);
            border-color: var(--border-hover);
            transform: translateY(-2px);
            box-shadow: var(--card-shadow-hover);
        }

        .link-card-left strong {
            display: block;
            font-size: 0.92rem;
            font-weight: 600;
            color: var(--text-main);
        }

        .link-card-left span {
            font-family: var(--mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 2px;
            display: block;
        }

        .link-arrow {
            font-size: 1.1rem;
            color: var(--text-muted);
            transition: color 0.18s ease, transform 0.18s ease;
        }

        .link-card:hover .link-arrow {
            color: var(--text-main);
            transform: translate(2px, -2px);
        }

        /* Live Database Viewer Card */
        .db-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: var(--card-shadow);
        }

        .db-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .db-title-group h3 {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        .db-title-group p {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .db-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .search-input {
            background: var(--surface-input);
            border: 1px solid var(--border);
            border-radius: var(--radius-control);
            padding: 8px 14px;
            color: var(--text-main);
            font-size: 0.8rem;
            width: 220px;
            outline: none;
            transition: border-color 0.18s ease;
        }

        .search-input:focus {
            border-color: var(--border-hover);
        }

        .btn-action {
            background: var(--btn-primary-bg);
            color: var(--btn-primary-text);
            border: 1px solid var(--btn-primary-border);
            padding: 8px 16px;
            border-radius: var(--radius-control);
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.18s ease;
        }

        .btn-action:hover {
            background: var(--btn-primary-hover-bg);
            color: var(--btn-primary-hover-text);
        }

        .table-wrap {
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: var(--radius-inner);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.83rem;
        }

        th {
            background: var(--th-bg);
            color: var(--text-muted);
            padding: 12px 16px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-size: 0.68rem;
            border-bottom: 1px solid var(--border);
        }

        td {
            padding: 12px 16px;
            color: var(--text-main);
            border-bottom: 1px solid var(--border-subtle);
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: var(--surface-hover);
        }

        .col-id {
            font-family: var(--mono);
            color: var(--text-muted);
        }

        .col-num {
            font-family: var(--mono);
            font-weight: 600;
            color: var(--text-main);
        }

        .col-vendor {
            font-weight: 500;
            color: var(--text-main);
        }

        .col-amount {
            font-family: var(--mono);
            font-weight: 700;
            color: var(--text-main);
        }

        .col-date {
            font-family: var(--mono);
            font-size: 0.78rem;
            color: var(--text-sub);
        }

        .col-created {
            font-family: var(--mono);
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .badge-status {
            display: inline-block;
            padding: 3px 8px;
            border-radius: var(--radius-control);
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            background: var(--badge-bg);
            border: 1px solid var(--badge-border);
            color: var(--badge-text);
            font-family: var(--mono);
        }

        .empty-state {
            padding: 36px 20px;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        /* Terminal Runner Card */
        .terminal-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-card);
            padding: 24px;
            box-shadow: var(--card-shadow);
        }

        .scenario-meta {
            font-size: 0.82rem;
            color: var(--text-sub);
            margin-bottom: 14px;
            line-height: 1.5;
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 14px;
            flex-wrap: wrap;
        }

        .tab-btn {
            background: var(--tab-inactive-bg);
            border: 1px solid var(--border);
            color: var(--tab-inactive-text);
            padding: 7px 14px;
            border-radius: var(--radius-control);
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .tab-btn:hover {
            color: var(--text-main);
            border-color: var(--border-hover);
        }

        .tab-btn.active {
            background: var(--tab-active-bg);
            color: var(--tab-active-text);
            border-color: var(--tab-active-bg);
        }

        .cmd-display {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--cmd-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius-inner);
            padding: 14px 18px;
            gap: 16px;
        }

        .cmd-text {
            font-family: var(--mono);
            font-size: 0.82rem;
            color: var(--text-main);
            word-break: break-all;
            line-height: 1.5;
        }

        .btn-copy {
            background: #ffffff;
            color: var(--text-main);
            border: 1px solid var(--border);
            border-radius: var(--radius-control);
            padding: 8px 14px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.18s ease;
        }

        .btn-copy:hover {
            border-color: var(--border-hover);
            background: var(--btn-primary-bg);
            color: var(--btn-primary-text);
        }

        /* Footer */
        footer {
            margin-top: 40px;
            text-align: center;
            font-size: 0.75rem;
            color: var(--text-muted);
            letter-spacing: 0.04em;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Nav -->
        <nav class="top-nav">
            <div class="brand-group">
                <div class="brand-glyph">❖</div>
                <div class="brand-text">
                    <h1>CentrAlign AI</h1>
                    <p>Mock Enterprise ERP System</p>
                </div>
            </div>
            <div class="nav-controls">
                <div class="status-pill">
                    <span class="status-dot"></span>
                    <span>System Online</span>
                </div>
                <div class="host-badge">127.0.0.1:8000</div>
            </div>
        </nav>

        <!-- Hero Card -->
        <div class="hero">
            <h2>Autonomous Enterprise Task Worker & Mock ERP</h2>
            <p>
                Simulated company system of record powering deterministic execution, closed-loop state verification, and self-correcting error recovery. All operations enforce immutable audit trails.
            </p>
        </div>

        <!-- Section: KPIs -->
        <div class="section-header">
            <div class="section-title">System Status & Performance Metrics</div>
        </div>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">API Health</div>
                <div class="kpi-val">200 OK</div>
                <div class="kpi-sub"><span class="bw-emoji">✓</span> Operational</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Recorded Invoices</div>
                <div class="kpi-val" id="stat-invoices">—</div>
                <div class="kpi-sub">Database rows</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Registered Vendors</div>
                <div class="kpi-val" id="stat-vendors">—</div>
                <div class="kpi-sub">Active counterparts</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Agent Engine</div>
                <div class="kpi-val">Gemini 3.8</div>
                <div class="kpi-sub">Flash / Heuristic</div>
            </div>
        </div>

        <!-- Section: API Endpoints -->
        <div class="section-header">
            <div class="section-title">API Endpoints & Documentation</div>
        </div>
        <div class="links-grid">
            <a href="/docs" class="link-card">
                <div class="link-card-left">
                    <strong><span class="bw-emoji">📄</span> Interactive Swagger Docs</strong>
                    <span>/docs</span>
                </div>
                <div class="link-arrow">↗</div>
            </a>
            <a href="/redoc" class="link-card">
                <div class="link-card-left">
                    <strong><span class="bw-emoji">📋</span> ReDoc Specification</strong>
                    <span>/redoc</span>
                </div>
                <div class="link-arrow">↗</div>
            </a>
            <a href="/invoices" class="link-card">
                <div class="link-card-left">
                    <strong><span class="bw-emoji">🧾</span> Invoices Registry</strong>
                    <span>/invoices</span>
                </div>
                <div class="link-arrow">↗</div>
            </a>
            <a href="/vendors" class="link-card">
                <div class="link-card-left">
                    <strong><span class="bw-emoji">🏢</span> Vendors Directory</strong>
                    <span>/vendors</span>
                </div>
                <div class="link-arrow">↗</div>
            </a>
            <a href="/invoices/search" class="link-card">
                <div class="link-card-left">
                    <strong><span class="bw-emoji">🔍</span> Invoice Search API</strong>
                    <span>/invoices/search</span>
                </div>
                <div class="link-arrow">↗</div>
            </a>
            <a href="/health" class="link-card">
                <div class="link-card-left">
                    <strong><span class="bw-emoji">⚡</span> System Health Check</strong>
                    <span>/health</span>
                </div>
                <div class="link-arrow">↗</div>
            </a>
        </div>

        <!-- Section: Live Database Records -->
        <div class="section-header">
            <div class="section-title">System of Record — Live Invoices</div>
        </div>
        <div class="db-card">
            <div class="db-header">
                <div class="db-title-group">
                    <h3><span class="bw-emoji">🧾</span> Invoices Registry Table</h3>
                    <p>Live read-back data stored in local SQLite ERP database</p>
                </div>
                <div class="db-actions">
                    <input type="text" id="search-input" class="search-input" placeholder="Filter invoices..." oninput="filterInvoices()">
                    <button class="btn-action" onclick="fetchLiveRecords()"><span class="bw-emoji">⟳</span> Refresh</button>
                </div>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Invoice Number</th>
                            <th>Vendor Name</th>
                            <th>Total Amount</th>
                            <th>Status</th>
                            <th>Due Date</th>
                            <th>Created At</th>
                        </tr>
                    </thead>
                    <tbody id="invoices-table-body">
                        <tr>
                            <td colspan="7" class="empty-state">Loading live ERP records...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section: Terminal Runner -->
        <div class="section-header">
            <div class="section-title">Autonomous Task Worker — Terminal Runner</div>
        </div>
        <div class="terminal-card">
            <div class="tabs">
                <button class="tab-btn active" onclick="switchScenario(0)">Scenario 1: Happy Path</button>
                <button class="tab-btn" onclick="switchScenario(1)">Scenario 2: Malformed Recovery</button>
                <button class="tab-btn" onclick="switchScenario(2)">Scenario 3: $75,000 Escalation</button>
            </div>
            <div class="scenario-meta" id="scenario-meta">
                Standard execution: Extracts Acme Corp invoice, registers it in the ERP system, and independently queries the database to verify mutation.
            </div>
            <div class="cmd-display">
                <div class="cmd-text" id="cmd-text">python main.py run --task "Find the latest invoice from Acme Corp in demo/invoices/invoice_acme_001.json, extract the details, enter it into our ERP system, and verify completion."</div>
                <button class="btn-copy" id="btn-copy" onclick="copyCommand()">📋 Copy Command</button>
            </div>
        </div>

        <!-- Footer -->
        <footer>
            CentrAlign AI · Autonomous Enterprise Task Worker Prototype · High-Contrast Minimal System
        </footer>
    </div>

    <script>
        const scenarioConfigs = [
            {
                cmd: 'python main.py run --task "Find the latest invoice from Acme Corp in demo/invoices/invoice_acme_001.json, extract the details, enter it into our ERP system, and verify completion."',
                desc: 'Standard execution: Extracts Acme Corp invoice, registers it in the ERP system, and independently queries the database to verify mutation.'
            },
            {
                cmd: 'python main.py run --task "Process the invoice from demo/invoices/invoice_malformed_003.json and record it into our ERP system."',
                desc: 'Self-correction: Handles unquoted JSON syntax errors, switches to regex text parsing heuristic, and successfully enters Initech invoice.'
            },
            {
                cmd: 'python main.py run --task "Process the high-value vendor invoice from demo/invoices/invoice_highvalue_004.json into our ERP system."',
                desc: 'Governance escalation: Detects $75,000 invoice exceeding the $10,000 policy threshold, enters ESCALATED state, and halts for human approval.'
            }
        ];

        let allInvoices = [];

        function switchScenario(index) {
            document.querySelectorAll('.tab-btn').forEach((btn, i) => {
                btn.classList.toggle('active', i === index);
            });
            document.getElementById('cmd-text').innerText = scenarioConfigs[index].cmd;
            document.getElementById('scenario-meta').innerText = scenarioConfigs[index].desc;
            const copyBtn = document.getElementById('btn-copy');
            copyBtn.innerText = '📋 Copy Command';
        }

        function copyCommand() {
            const text = document.getElementById('cmd-text').innerText;
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.getElementById('btn-copy');
                btn.innerText = '✓ Copied!';
                setTimeout(() => {
                    btn.innerText = '📋 Copy Command';
                }, 2000);
            });
        }

        async function fetchLiveRecords() {
            try {
                // Fetch invoices
                const invRes = await fetch('/invoices');
                if (invRes.ok) {
                    allInvoices = await invRes.json();
                    document.getElementById('stat-invoices').innerText = allInvoices.length;
                    renderInvoicesTable(allInvoices);
                }

                // Fetch vendors
                const venRes = await fetch('/vendors');
                if (venRes.ok) {
                    const vendors = await venRes.json();
                    document.getElementById('stat-vendors').innerText = vendors.length;
                }
            } catch (err) {
                console.error("Failed to fetch live ERP records:", err);
            }
        }

        function renderInvoicesTable(invoices) {
            const tbody = document.getElementById('invoices-table-body');
            if (!invoices || invoices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No invoices recorded in ERP database yet. Run an autonomous task to record an invoice.</td></tr>';
                return;
            }

            tbody.innerHTML = invoices.map(inv => {
                const amountFormatted = '$' + Number(inv.total_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                const createdTime = inv.created_at ? inv.created_at.replace('T', ' ').split('.')[0] : '—';
                return `
                    <tr>
                        <td class="col-id">${inv.id}</td>
                        <td class="col-num">${escapeHtml(inv.invoice_number)}</td>
                        <td class="col-vendor">${escapeHtml(inv.vendor_name)}</td>
                        <td class="col-amount">${amountFormatted}</td>
                        <td><span class="badge-status">${escapeHtml(inv.status)}</span></td>
                        <td class="col-date">${escapeHtml(inv.due_date || '—')}</td>
                        <td class="col-created">${createdTime}</td>
                    </tr>
                `;
            }).join('');
        }

        function filterInvoices() {
            const q = document.getElementById('search-input').value.toLowerCase().trim();
            if (!q) {
                renderInvoicesTable(allInvoices);
                return;
            }
            const filtered = allInvoices.filter(inv => 
                (inv.vendor_name && inv.vendor_name.toLowerCase().includes(q)) ||
                (inv.invoice_number && inv.invoice_number.toLowerCase().includes(q))
            );
            renderInvoicesTable(filtered);
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/[&<>"']/g, function(m) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
            });
        }

        // Initialize on load
        fetchLiveRecords();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)



@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Mock ERP", "version": "1.0.0"}


@app.get("/invoices", response_model=List[InvoiceRecord])
async def list_invoices():
    return await get_all_invoices()


@app.get("/invoices/search", response_model=List[InvoiceRecord])
async def search_invoice_endpoint(
    vendor_name: Optional[str] = Query(None, description="Vendor name or substring"),
    invoice_number: Optional[str] = Query(None, description="Invoice reference code"),
    min_amount: Optional[float] = Query(None, description="Minimum amount threshold"),
    max_amount: Optional[float] = Query(None, description="Maximum amount threshold"),
):
    return await search_invoices(
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        min_amount=min_amount,
        max_amount=max_amount,
    )


@app.get("/invoices/{invoice_id}", response_model=InvoiceRecord)
async def get_invoice_endpoint(invoice_id: int):
    record = await get_invoice(invoice_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )
    return record


@app.post("/invoices", response_model=InvoiceRecord, status_code=status.HTTP_201_CREATED)
async def create_invoice_endpoint(invoice_req: InvoiceCreateRequest):
    try:
        created = await create_invoice(invoice_req)
        return created
    except aiosqlite.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate invoice: Invoice '{invoice_req.invoice_number}' for vendor '{invoice_req.vendor_name}' already exists.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record invoice: {str(e)}",
        )


@app.delete("/invoices/{invoice_id}")
async def delete_invoice_endpoint(invoice_id: int):
    deleted = await delete_invoice(invoice_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )
    return {"status": "deleted", "invoice_id": invoice_id}


@app.get("/vendors", response_model=List[VendorRecord])
async def list_vendors():
    return await get_vendors()


@app.get("/portal", response_class=HTMLResponse)
async def portal_page():
    from pathlib import Path
    portal_file = Path(__file__).parent / "static" / "portal.html"
    if portal_file.exists():
        return HTMLResponse(content=portal_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Portal not found</h1>", status_code=404)

