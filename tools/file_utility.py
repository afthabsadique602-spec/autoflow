import os
import pandas as pd
import json
import time
from fpdf import FPDF
import PyPDF2

def get_file_stats(filepath):
    """Get basic file metadata."""
    stats = os.stat(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    return {
        "name": os.path.basename(filepath),
        "size_mb": round(stats.st_size / (1024 * 1024), 2),
        "extension": ext
    }

def preview_utility_file(filepath):
    """Safe preview logic for multiple formats."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.csv':
            df = pd.read_csv(filepath, nrows=50, low_memory=False, encoding_errors='ignore')
            df.columns = df.columns.astype(str).str.strip()
            df = df.fillna("")
            return {"type": "table", "columns": df.columns.tolist(), "data": df.to_dict(orient="records")}
        elif ext in ['.xls', '.xlsx']:
            xls = pd.ExcelFile(filepath)
            df = pd.read_excel(filepath, nrows=50, sheet_name=0)
            df.columns = df.columns.astype(str).str.strip()
            df = df.fillna("")
            return {"type": "table", "columns": df.columns.tolist(), "data": df.to_dict(orient="records"), "sheet_names": xls.sheet_names}
        elif ext == '.json':
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    df = pd.DataFrame(data[:50])
                    df = df.fillna("")
                    return {"type": "table", "columns": df.columns.tolist(), "data": df.to_dict(orient="records")}
                else:
                    return {"type": "text", "content": json.dumps(data, indent=2)[:2000]}
        elif ext == '.txt':
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return {"type": "text", "content": f.read(3000)}
        elif ext == '.pdf':
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages[:3]:
                    text += page.extract_text() + "\n"
                return {"type": "text", "content": text[:3000]}
        else:
            return {"type": "unsupported", "content": "Dynamic preview currently optimized for CSV, Excel, JSON, TXT, and PDF."}
    except Exception as e:
        return {"type": "error", "content": f"Preview failed: {str(e)}"}

def convert_utility_file(filepath, target_format, output_folder):
    """Convert between supported formats."""
    ext = os.path.splitext(filepath)[1].lower()
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    out_path = os.path.join(output_folder, f"{base_name}_converted.{target_format}")
    
    try:
        # 1. Load Data
        df = None
        if ext == '.csv':
            df = pd.read_csv(filepath)
        elif ext in ['.xls', '.xlsx']:
            df = pd.read_excel(filepath)
        elif ext == '.json':
            df = pd.read_json(filepath)
        elif ext == '.txt' and target_format == 'pdf':
            # Direct TXT to PDF using FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    pdf.cell(200, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=1)
            pdf.output(out_path)
            return out_path
        
        # 2. Export to Target
        if df is not None:
            if target_format == 'csv':
                df.to_csv(out_path, index=False)
            elif target_format == 'xlsx':
                df.to_excel(out_path, index=False)
            elif target_format == 'json':
                df.to_json(out_path, orient="records", indent=2)
            return out_path
        
        raise Exception(f"Conversion from {ext} to {target_format} not supported.")
    except Exception as e:
        raise Exception(f"Conversion Error: {str(e)}")

def optimize_utility_file(filepath, options, output_folder):
    """Lightweight file optimization."""
    ext = os.path.splitext(filepath)[1].lower()
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    out_path = os.path.join(output_folder, f"{base_name}_optimized{ext}")
    
    try:
        if ext in ['.csv', '.xls', '.xlsx', '.json']:
            if ext == '.csv': df = pd.read_csv(filepath)
            elif ext in ['.xls', '.xlsx']: df = pd.read_excel(filepath)
            else: df = pd.read_json(filepath)
            
            if options.get('remove_empty'):
                df = df.dropna(how='all')
            if options.get('remove_dupes'):
                df = df.drop_duplicates()
            
            if ext == '.csv': df.to_csv(out_path, index=False)
            elif ext in ['.xls', '.xlsx']: df.to_excel(out_path, index=False)
            else: df.to_json(out_path, orient="records", indent=2)
            
            return out_path
        else:
            raise Exception("Optimization only supported for tabular data (CSV/Excel/JSON).")
    except Exception as e:
        raise Exception(f"Optimization Error: {str(e)}")

def split_utility_file(filepath, rows_per_split, output_folder):
    """Split large files into chunks."""
    ext = os.path.splitext(filepath)[1].lower()
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    
    if ext not in ['.csv', '.xls', '.xlsx']:
        raise Exception("Split operation only supported for CSV/Excel.")
        
    try:
        df = pd.read_csv(filepath) if ext == '.csv' else pd.read_excel(filepath)
        chunks = [df[i:i + rows_per_split] for i in range(0, df.shape[0], rows_per_split)]
        
        saved_paths = []
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(output_folder, f"{base_name}_part{i+1}{ext}")
            if ext == '.csv': chunk.to_csv(chunk_path, index=False)
            else: chunk.to_excel(chunk_path, index=False)
            saved_paths.append(os.path.basename(chunk_path))
            
        return saved_paths
    except Exception as e:
        raise Exception(f"Split Error: {str(e)}")

def merge_utility_files(filepaths, output_folder):
    """Combine multiple files of the same type."""
    if not filepaths: return None
    
    ext = os.path.splitext(filepaths[0])[1].lower()
    out_path = os.path.join(output_folder, f"merged_result_{int(time.time())}{ext}")
    
    try:
        all_dfs = []
        for fp in filepaths:
            if ext == '.csv': all_dfs.append(pd.read_csv(fp))
            elif ext in ['.xls', '.xlsx']: all_dfs.append(pd.read_excel(fp))
            
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            if ext == '.csv': combined.to_csv(out_path, index=False)
            else: combined.to_excel(out_path, index=False)
            return out_path
        return None
    except Exception as e:
        raise Exception(f"Merge Error: {str(e)}")

def extract_columns_utility(filepath, columns, output_folder):
    """Extract specific columns into a new file."""
    ext = os.path.splitext(filepath)[1].lower()
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    out_path = os.path.join(output_folder, f"{base_name}_extracted{ext}")
    
    try:
        df = None
        if ext == '.csv': df = pd.read_csv(filepath)
        elif ext in ['.xls', '.xlsx']: df = pd.read_excel(filepath)
        elif ext == '.json': df = pd.read_json(filepath)
        
        if df is not None:
            # Filter only existing columns
            valid_cols = [c for c in columns if c in df.columns]
            if not valid_cols:
                raise Exception("No valid columns selected for extraction.")
            
            df_new = df[valid_cols]
            
            if ext == '.csv': df_new.to_csv(out_path, index=False)
            elif ext in ['.xls', '.xlsx']: df_new.to_excel(out_path, index=False)
            else: df_new.to_json(out_path, orient="records", indent=2)
            
            return out_path
        raise Exception("Column extraction only supported for tabular data.")
    except Exception as e:
        raise Exception(f"Extraction Error: {str(e)}")
