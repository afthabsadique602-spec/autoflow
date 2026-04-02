from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import pandas as pd
import time
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import PyPDF2
import docx
from collections import Counter
import re
import requests
from bs4 import BeautifulSoup

# Modular Imports
from ai_engine.llm import call_llm
from tools.data_cleaner import clean_data
from tools.data_insight import generate_insights
from tools.data_analyzer import analyze_data
from tools.report_gen import generate_pdf_report
from tools.file_utility import (
    get_file_stats, preview_utility_file, convert_utility_file, 
    optimize_utility_file, split_utility_file, merge_utility_files,
    extract_columns_utility
)

# Setup
app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # Adaptive limit allowed up to 500MB

def safe_load(path, is_excel=False):
    if is_excel:
        return pd.read_excel(path)
    try:
        return pd.read_csv(path, encoding='utf-8', low_memory=False)
    except:
        try:
            return pd.read_csv(path, encoding='latin1', low_memory=False)
        except:
            return pd.read_csv(path, encoding='cp1252', low_memory=False)

def enforce_limits(df, max_rows=5000):
    df = df.dropna(how='all')
    df.columns = df.columns.astype(str).str.strip()
    df = df.head(max_rows).copy()
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            df[col] = df[col].astype(str)
    return df

@app.route("/")
def home():
    print("[GET] Home page requested")
    return render_template("index.html")

@app.before_request
def log_request_info():
    print(f"[REQUEST] {request.method} {request.url}")

@app.route("/analyze", methods=["POST"])
def analyze():
    """Initial data profiling for Inspector."""
    file = request.files.get("file")
    sheet_url = request.form.get("sheet_url")
    
    if not file and not sheet_url:
        return jsonify({"success": False, "error": "No data source"}), 400
        
    try:
        if sheet_url:
            if "docs.google.com/spreadsheets" in sheet_url:
                if "/edit" in sheet_url: sheet_url = sheet_url.split("/edit")[0] + "/export?format=csv"
            df = safe_load(sheet_url)
        else:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            df = safe_load(filepath, is_excel=not file.filename.endswith('.csv'))
            
        df = enforce_limits(df)
            
        analysis = analyze_data(df)
        return jsonify({
            "success": True, 
            "analysis": analysis,
            "temp_file": filepath if not sheet_url else None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

def highlight_diff(df_orig, df_clean):
    """Generate HTML preview with highlighted changes using index alignment."""
    # Take first 10 rows for preview
    preview_clean = df_clean.head(10).copy()
    
    html = '<table class="table" style="width:100%; border-collapse:collapse;">'
    # Header
    html += '<thead><tr style="background:var(--bg-dark);">' + ''.join(f'<th style="padding:10px; border:1px solid var(--border);">{c}</th>' for c in preview_clean.columns) + '</tr></thead>'
    # Body
    html += '<tbody>'
    for idx, row in preview_clean.iterrows():
        html += '<tr>'
        for col in preview_clean.columns:
            val = row[col]
            is_changed = False
            reason = "MODIFIED"
            
            # Check if index exists in orig and is different
            if idx in df_orig.index and col in df_orig.columns:
                orig_val = df_orig.at[idx, col]
                if str(val) != str(orig_val):
                    is_changed = True
                    # Determine reason
                    if (pd.isna(orig_val) or str(orig_val).lower() == 'nan') and not pd.isna(val):
                        reason = f"Filled using Mean/Mode (was NaN)"
                    elif str(orig_val).strip() != str(orig_val) and str(val) == str(orig_val).strip():
                        reason = "Trimmed whitespace"
                    else:
                        reason = f"Repaired (was {orig_val})"
            elif idx not in df_orig.index:
                is_changed = False
            
            if is_changed:
                html += f'<td style="padding:10px; border:1px solid var(--border); background-color:rgba(16, 185, 129, 0.2); color:white; font-weight:bold;" title="{reason}">{val} <i class="fas fa-info-circle" style="color:#10b981; margin-left:5px; font-size:0.8rem;"></i></td>'
            else:
                html += f'<td style="padding:10px; border:1px solid var(--border); color:var(--text-dim);">{val}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html

@app.route("/process", methods=["POST"])
def process_file():
    """Advanced data cleaning with granular control."""
    print("[PROCESS] Request received at /process")
    temp_file = request.form.get("temp_file")
    file = request.files.get("file")
    sheet_url = request.form.get("sheet_url")
    
    if not file and not sheet_url and not temp_file:
        return jsonify({"success": False, "error": "No data source"}), 400

    try:
        # Load Data
        temp_file = request.form.get("temp_file")
        if temp_file and os.path.exists(temp_file):
            print(f"[PROCESS] Using existing temp file: {temp_file}")
            df_orig = safe_load(temp_file, is_excel=not temp_file.endswith('.csv'))
            base_name = os.path.splitext(os.path.basename(temp_file))[0]
        elif sheet_url:
            if "docs.google.com/spreadsheets" in sheet_url:
                if "/edit" in sheet_url: sheet_url = sheet_url.split("/edit")[0] + "/export?format=csv"
            df_orig = safe_load(sheet_url)
            base_name = "google_sheet"
        elif file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            df_orig = safe_load(filepath, is_excel=not file.filename.endswith('.csv'))
            base_name = os.path.splitext(file.filename)[0]
        else:
            return jsonify({"success": False, "error": "No data source available"}), 400
            
        df_orig = enforce_limits(df_orig)

        # Parse Settings
        import json
        settings_raw = request.form.get("settings", "{}")
        settings = json.loads(settings_raw)
        
        print(f"[PROCESS] User settings: {settings_raw}")
        global_settings = settings.get("global", {})
        column_settings = settings.get("columns", {})

        # Execute Cleaning
        print(f"[PROCESS] Cleaning starting for {base_name}...")
        df_clean, report = clean_data(df_orig, global_settings, column_settings)
        print(f"[PROCESS] Cleaning complete. {len(report)} changes logged.")

        # Save Result
        import re
        safe_base = re.sub(r'[^\w\s-]', '', base_name).strip().replace(' ', '_')
        clean_name = f"cleaned_{safe_base}.csv"
        xlsx_name = f"cleaned_{safe_base}.xlsx"
        json_name = f"cleaned_{safe_base}.json"
        
        out_path = os.path.join(OUTPUT_FOLDER, clean_name)
        df_clean.to_csv(out_path, index=False)
        try:
            df_clean.to_excel(os.path.join(OUTPUT_FOLDER, xlsx_name), index=False)
            df_clean.to_json(os.path.join(OUTPUT_FOLDER, json_name), orient="records")
        except Exception as e:
            print(f"[PROCESS] Failed saving alternate formats: {e}")
            
        print(f"[PROCESS] Saved to {out_path}")
        # PDF Audit generation removed per user request
        analysis = analyze_data(df_clean)
        # Store analysis for frontend issue filtering
        global currentAnalysis
        currentAnalysis = analysis
        return jsonify({
            "success": True,
            "report": report,
            "preview_before": df_orig.head(10).to_html(classes="table", index=False),
            "preview_after": highlight_diff(df_orig, df_clean),
            "download_url": f"/outputs/{clean_name}",
            "excel_url": f"/outputs/{xlsx_name}",
            "json_url": f"/outputs/{json_name}",
            "analysis": analysis  # send full analysis including cell_issues
        })
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"[ERROR] Process failed: {err_msg}")
        return jsonify({"success": False, "error": str(e), "traceback": err_msg}), 400

LATEST_INSIGHT = {}

@app.route("/data_insight", methods=["POST"])
def data_insight():
    """Strategic analysis."""
    file = request.files.get('file')
    sheet_url = request.form.get('sheet_url')
    temp_file = request.form.get('temp_file')
    
    try:
        print(f"[INSIGHT] SMART_HYBRID_AUTO_SCALE | Triggered")
        processing_mode = "Standard"
        
        filepath = None
        df = None
        if temp_file and os.path.exists(temp_file):
            filepath = temp_file
            df = safe_load(filepath, is_excel=not filepath.endswith('.csv'))
        elif sheet_url and sheet_url.strip():
             print(f"[INSIGHT] Using Cloud URL: {sheet_url}")
             if not (sheet_url.startswith('http')):
                 return jsonify({"success": False, "error": "Invalid URL. Must start with http://"}), 400
             if "docs.google.com/spreadsheets" in sheet_url:
                if "/edit" in sheet_url: sheet_url = sheet_url.split("/edit")[0] + "/export?format=csv"
             # For URLs, we load then sample
             df = safe_load(sheet_url)
             if len(df) > 5000: df = df.sample(5000)
             processing_mode = "Cloud Sync (Optimized)"
        elif file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
        
        if df is None and not filepath:
            print("[INSIGHT] ERROR: No valid data source")
            return jsonify({"success": False, "error": "No valid data source provided."}), 400

        # ADAPTIVE LOADING STRATEGY for local files
        if df is None:
            file_size = os.path.getsize(filepath) / (1024 * 1024) # MB
            print(f"[INSIGHT] File Size: {file_size:.2f} MB")
            
            processing_mode = "Standard"
            if filepath.endswith('.csv'):
                if file_size < 10:
                    print("[INSIGHT] Strategy: Full Load")
                    df = safe_load(filepath)
                elif file_size < 100:
                    print("[INSIGHT] Strategy: Proximity Sampled Load")
                    df = safe_load(filepath).sample(5000)
                    processing_mode = "Optimized (Proximity Sampled)"
                else:
                    print("[INSIGHT] Strategy: Deep Chunk Streaming")
                    chunks = pd.read_csv(filepath, chunksize=5000, encoding='latin1', low_memory=True)
                    df = next(chunks) # Use first chunk for deep insight
                    processing_mode = "Performance (Chunk Streamed)"
            else: # Excel
                 df = safe_load(filepath, is_excel=True)

        print(f"[INSIGHT] Stage: Start Data Analysis | Mode: {processing_mode}")
        res = generate_insights(df)
        res["processing_mode"] = processing_mode # Pass to UI
        print(f"[INSIGHT] Stage: Analysis Complete | Rows used: {len(df)}")
        
        preview = res.get("preview", [])
        print("DEBUG PREVIEW:", preview[:2] if len(preview) >= 2 else preview)
        print("DEBUG COLUMNS:", df.columns.tolist())
        
        red_flags = []
        if df.isnull().sum().sum() > 0:
            red_flags.append(f"Missing values: {int(df.isnull().sum().sum())}")
        if df.duplicated().sum() > 0:
            red_flags.append(f"Duplicate rows: {int(df.duplicated().sum())}")
        if len(df) >= 3000:
            red_flags.append("Large dataset — performance optimized mode enabled")
            
        response_data = res.copy()
        
        global LATEST_INSIGHT
        LATEST_INSIGHT = response_data
        
        return jsonify(response_data)
    except Exception as e:
        import traceback
        print(f"[INSIGHT ERROR] {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/custom_chart", methods=["POST"])
def custom_chart():
    """Generate specific chart on demand."""
    from tools.data_insight import generate_custom_chart
    temp_file = request.form.get('temp_file')
    col = request.form.get('column')
    chart_type = request.form.get('type', 'bar')
    
    if not temp_file or not os.path.exists(temp_file):
        return jsonify({"success": False, "error": "No data source"}), 400
    
    try:
        df = pd.read_csv(temp_file) if temp_file.endswith('.csv') else pd.read_excel(temp_file)
        chart_url = generate_custom_chart(df, col, chart_type)
        return jsonify({"success": True, "chart_url": chart_url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


global LATEST_SUMMARY_DOC
global LATEST_GENERATED_SUMMARY
LATEST_SUMMARY_DOC = ""
@app.route("/summarize", methods=["POST"])
def summarize():
    global LATEST_SUMMARY_DOC
    global LATEST_GENERATED_SUMMARY
    try:
        text = request.form.get("text", "")
        url = request.form.get("url", "")
        file = request.files.get("file")
        extracted_text = ""

        if url:
             try:
                 resp = requests.get(url, timeout=10)
                 if resp.status_code == 200:
                     soup = BeautifulSoup(resp.text, 'html.parser')
                     # Remove script and style elements
                     for script in soup(["script", "style"]):
                         script.extract()
                     extracted_text = soup.get_text(separator=' ', strip=True)
             except Exception as e:
                 print(f"URL extraction failed: {e}")
                 return jsonify({"success": False, "error": f"Could not extract content from URL: {str(e)}"})

        elif file:
            filename = file.filename.lower()
            if filename.endswith('.txt'):
                extracted_text = file.read().decode('utf-8', errors='ignore')
            elif filename.endswith('.csv'):
                df = safe_load(file)
                extracted_text = df.head(100).to_string()
            elif filename.endswith('.xlsx'):
                df = safe_load(file, is_excel=True)
                extracted_text = df.head(100).to_string()
            elif filename.endswith('.pdf'):
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    extracted_text += page.extract_text() or ""
            elif filename.endswith('.docx'):
                doc = docx.Document(file)
                for para in doc.paragraphs:
                    extracted_text += para.text + "\n"

        final_text = text if (text and text.strip()) else extracted_text
        if not final_text or len(final_text.strip()) == 0:
            return jsonify({"success": False, "error": "No readable content found"})

        # Advanced Structured Prompting
        system_prompt = (
            "You are a Senior Strategic Analyst. "
            "Your goal is to produce a Premium Executive Briefing that is visually stunning and highly readable. "
            "Never use the word 'AI' or reference your own identity. "
            "NEVER use emojis. "
            "You must use a multi-level structure: "
            "1. Start with '### EXECUTIVE STRATEGY' (A high-level summary of the entire content). "
            "2. Use '#### Section Titles' for sub-topics. "
            "3. Use detailed bullet points starting with '-' for key insights under each subheader. "
            "4. ALWAYS end with a section literally titled 'CORE TAKEAWAYS:' followed by the 3-5 most critical, high-impact facts from the document. "
            "STRICT RULE: Do not use bolding (**) or hashes (#) other than the ### and #### markers prescribed. "
            "NEVER place stray hashes (#) or asterisks (*) at the end of lists or sections. "
            "All bullet points should start with '-' only."
        )
        user_prompt = f"""
Produce a PREMIUM ANALYTICAL BRIEFING for the following content.

STRICT VISUAL ARCHITECTURE:
- MAIN HEADING: '### EXECUTIVE STRATEGY'
- SUBHEADERS: '#### [Topic Name]'
- INSIGHTS: Concise bullet points (-)
- FINAL SECTION: 'CORE TAKEAWAYS:' (The absolute essence of the document)

Make the language professional, authoritative, and deeply informative.

CONTENT:
{final_text}
"""
        response = call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        summary = response if response else "Summary not available."

        # CLEANUP: Remove bolding markers but KEEP hashes (#) for structural parsing
        summary = re.sub(r'[*]', '', summary)
        
        # Ensure the structural markers exist if the AI used plain text labels
        if "EXECUTIVE STRATEGY" in summary and "###" not in summary:
             summary = summary.replace("EXECUTIVE STRATEGY", "### EXECUTIVE STRATEGY")
        if "CORE TAKEAWAYS" in summary and "###" not in summary:
             summary = summary.replace("CORE TAKEAWAYS", "### CORE TAKEAWAYS")

        summary = summary.strip()
        LATEST_GENERATED_SUMMARY = summary 
        LATEST_SUMMARY_DOC = final_text

        return jsonify({
            "success": True,
            "summary": summary
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)})

@app.route("/chat_summary", methods=["POST"])
def chat_summary():
    try:
        data = request.json
        query = data.get("query", "")
        
        if not LATEST_SUMMARY_DOC:
            return jsonify({"success": False, "error": "No document uploaded for context."})
        if not query:
            return jsonify({"success": False, "error": "Missing query."})

        system_prompt = (
            "You are a professional assistant helping a user understand a document. "
            "Use the document context to answer questions accurately and deeply. "
            "STRICT RULE: Do NOT use any Markdown formatting like asterisks (**) or hashes (#). "
            "Your output must be clear, standard text with normal line breaks. "
            "NEVER use emojis or AI-related self-branding."
        )
        
        user_prompt = f"DOCUMENT CONTEXT:\n{LATEST_SUMMARY_DOC[:5000]}\n\nUSER QUESTION: {query}"
        
        response = call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        # Strip any accidental markdown the model might still produce
        clean_response = re.sub(r'[*#]', '', response)
        
        return jsonify({"success": True, "answer": clean_response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/outputs/<path:filename>')
def serve_outputs(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    """Generate high-fidelity strategic PDF report."""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        filename = f"Strategic_Report_{int(time.time())}.pdf"
        
        sections = []
        
        # 1. Executive Summary
        sections.append({
            "title": "Executive Summary",
            "content": data.get("insights_md", "Detailed dataset strategy and visual blueprint.").replace("### ", "").replace("#### ", ""),
            "type": "text"
        })
        
        # 2. Key Insights
        insights_list = data.get("insights_list", [])
        if insights_list:
            sections.append({
                "title": "Actionable Data Insights",
                "content": insights_list,
                "type": "list"
            })
            
        # 3. Quality & Red Flags
        flags = [f["msg"] for f in data.get("red_flags", [])]
        if flags:
            sections.append({
                "title": "Data Health & Red Flags",
                "content": flags,
                "type": "list"
            })
            
        # 4. Charts (If path exists)
        charts = data.get("charts", [])
        for chart_url in charts[:2]: # Max 2 for space
             full_path = chart_url.lstrip('/')
             if os.path.exists(full_path):
                 sections.append({
                     "title": "Visual Pattern Analysis",
                     "content": full_path,
                     "type": "image"
                 })

        stats = data.get("stats", {})
        path = generate_pdf_report(filename, sections, stats=stats)
        
        return jsonify({"success": True, "download_url": f"/outputs/{filename}"})
    except Exception as e:
        print(f"[PDF ERROR] {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/download_summary_pdf", methods=['POST'])
def download_summary_pdf():
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        data = request.json
        summary = data.get("summary", "")
        keywords = data.get("keywords", [])
        
        filename = f"summary_report_{int(time.time())}.pdf"
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        doc = SimpleDocTemplate(file_path)
        styles = getSampleStyleSheet()
        
        content = []
        content.append(Paragraph("AUTOFLOW - AI ANALYTICAL REPORT", styles['Title']))
        content.append(Spacer(1, 15))
        
        content.append(Paragraph("Comprehensive Analysis:", styles['Heading2']))
        content.append(Paragraph(summary, styles['BodyText']))
        content.append(Spacer(1, 15))
        
        content.append(Paragraph("Keywords & Strategic Tags:", styles['Heading2']))
        content.append(Paragraph(", ".join(keywords), styles['BodyText']))
        
        doc.build(content)
        return send_file(file_path, as_attachment=True, download_name="AutoFlow_Final_Summary.pdf")
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download_insight_pdf')
def download_insight_pdf():
    global LATEST_INSIGHT
    if not LATEST_INSIGHT:
        return jsonify({"success": False, "error": "No insights generated yet."}), 400
        
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        report_file = os.path.join(OUTPUT_FOLDER, f"report_{int(time.time())}.pdf")
        doc = SimpleDocTemplate(report_file)
        styles = getSampleStyleSheet()
        style = styles['Normal']
        
        content = []

        content.append(Paragraph("AutoFlow Data Insight Report", styles['Title']))
        content.append(Spacer(1, 10))

        # Insights
        insights_text = LATEST_INSIGHT.get('insights_md', '')
        if insights_text:
            content.append(Paragraph(insights_text.replace('\n', '<br/>'), style))
            content.append(Spacer(1, 10))

        # Stats
        stats = LATEST_INSIGHT.get('stats', {})
        content.append(Paragraph(f"Rows: {stats.get('rows', 0)}", style))
        content.append(Paragraph(f"Columns: {stats.get('cols', 0)}", style))
        content.append(Spacer(1, 10))

        # Red Flags
        red_flags = LATEST_INSIGHT.get('red_flags', [])
        if red_flags:
            content.append(Paragraph("Red Flags:", styles['Heading3']))
            for flag in red_flags:
                content.append(Paragraph(f"• {flag}", style))
            content.append(Spacer(1, 10))

        # Charts
        charts = LATEST_INSIGHT.get('charts', [])
        if charts:
            chart_path = "." + charts[0] if charts[0].startswith("/") else charts[0]
            if os.path.exists(chart_path):
                content.append(Paragraph("Data Distribution:", styles['Heading3']))
                content.append(Spacer(1, 10))
                # Resize image proportionally
                content.append(Image(chart_path, width=400, height=240))

        doc.build(content)
        return send_file(report_file, as_attachment=True, download_name="Data_Insight_Report.pdf")
    except Exception as e:
        import traceback
        print(f"[ERROR] PDF generation failed: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

# --- FILE UTILITY ROUTES ---

@app.route("/file_utility/preview", methods=["POST"])
def utility_preview():
    file = request.files.get("file")
    if not file: return jsonify({"success": False, "error": "No file uploaded"}), 400
    try:
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        stats = get_file_stats(path)
        preview = preview_utility_file(path)
        return jsonify({"success": True, "stats": stats, "preview": preview, "temp_file": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/file_utility/convert", methods=["POST"])
def utility_convert():
    temp_file = request.form.get("temp_file")
    target = request.form.get("target_format")
    if not temp_file or not target: return jsonify({"success": False, "error": "Missing parameters"}), 400
    try:
        out_path = convert_utility_file(temp_file, target, OUTPUT_FOLDER)
        return jsonify({"success": True, "download_url": f"/download/{os.path.basename(out_path)}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/file_utility/optimize", methods=["POST"])
def utility_optimize():
    temp_file = request.form.get("temp_file")
    options = {
        'remove_empty': request.form.get("remove_empty") == 'true',
        'remove_dupes': request.form.get("remove_dupes") == 'true'
    }
    if not temp_file: return jsonify({"success": False, "error": "No file to optimize"}), 400
    try:
        out_path = optimize_utility_file(temp_file, options, OUTPUT_FOLDER)
        return jsonify({"success": True, "download_url": f"/download/{os.path.basename(out_path)}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/file_utility/split", methods=["POST"])
def utility_split():
    temp_file = request.form.get("temp_file")
    rows = int(request.form.get("rows", 1000))
    if not temp_file: return jsonify({"success": False, "error": "No file to split"}), 400
    try:
        files = split_utility_file(temp_file, rows, OUTPUT_FOLDER)
        links = [{"name": f, "url": f"/download/{f}"} for f in files]
        return jsonify({"success": True, "files": links})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/file_utility/extract_columns", methods=["POST"])
def utility_extract():
    temp_file = request.form.get("temp_file")
    cols = request.form.getlist("columns[]")
    if not temp_file or not cols: 
        return jsonify({"success": False, "error": "Missing parameters or no columns selected"}), 400
    try:
        out_path = extract_columns_utility(temp_file, cols, OUTPUT_FOLDER)
        return jsonify({"success": True, "download_url": f"/download/{os.path.basename(out_path)}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/file_utility/merge", methods=["POST"])
def utility_merge():
    # Placeholder for multi-file upload merge
    return jsonify({"success": False, "error": "Merge requires multiple files. Implementation pending UI multi-upload."}), 400

@app.route("/download/<filename>")
def download_output(filename):
    path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    print("[SERVER] Starting AutoFlow on http://0.0.0.0:5002")
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5002)
