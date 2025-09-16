#Import libraries and tools

from flask import Flask, request, render_template
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import base64


#Function - create app
def create_app():
    app = Flask(__name__)


    @app.route('/', methods=['GET', 'POST'])
    def home():

      #Initializing the variables (Not initializing results in errors)
      hist_plot_url = None
      error_hist = None
      stats = None
      error = None

      #This block runs only if the form is submitted (i.e., a POST request).
      if request.method == 'POST':
        #Retrieving the uploaded file from the form field named 'file'.
        uploaded_file = request.files.get('file')

        #Error handling and file processing
        if not uploaded_file or uploaded_file.filename == '':
          error = "Please choose a file to upload."
        elif not uploaded_file.filename.lower().endswith(('.xlsx', '.xls')):
          error = "Please upload an Excel file (.xlsx or .xls)."
        else:
          try:
            error_messages = []
            # Read Excel; if your file has no header, use header=None
            df = pd.read_excel(uploaded_file)

            # Computing stats
            stats, stats_err = compute_total_stats(df)
            if stats_err:
              error_messages.append(stats_err)

            #Ploting the histogram
            hist_plot_url, error_hist = generate_total_histogram(df)
            if error_hist:
                error_messages.append(error_hist)

            #Combining errors separated by a new line
            if error_messages:
              error = " <br> ".join(error_messages)

          except Exception as e:
            error = f"Error processing file: {e}"

      return render_template('home.html', plot_url=hist_plot_url, error=error, stats=stats)



    def generate_total_histogram(df: pd.DataFrame):
      # 1) Find columns that look like "total" grades
      total_cols = [c for c in df.columns if 'total' in str(c).lower()]

      if not total_cols:
        return None, "No columns containing 'total' found in the uploaded file."
      elif len(total_cols) > 1:
        return None, "There are more than one column containing 'total'."
      
      all_grades = pd.to_numeric(df[total_cols[0]], errors='coerce').dropna().reset_index(drop=True)

      # 3) Auto-detect scale and choose bins/ticks
      max_val = all_grades.max()
      min_val = all_grades.min()


      
      # Custom scaling: from (min - 1) to (max + 5)
      xlim = (min_val - 1, max_val + 1)
      bins = np.arange(xlim[0] + 0.5, xlim[1] + 0.5, 1) 
      xticks = np.arange(xlim[0], xlim[1] + 1, 1)
      xlabel = "Grade"
      title_suffix = f" (range: {xlim[0]}–{xlim[1]})"

      

      # 4) Plot a single combined histogram across all matching "total" columns
      fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
      ax.hist(all_grades, bins=bins, edgecolor='black', color='#4C78A8')
      if xlim is not None:
        ax.set_xlim(*xlim)
      if xticks is not None:
        ax.set_xticks(xticks)
      ax.set_title(f"Grade Distribution from 'Total' Columns{title_suffix}")
      ax.set_xlabel(xlabel)
      ax.set_ylabel("Frequency")
      ax.grid(axis='y', alpha=0.25)

      # Small caption listing which columns were used (trim if too many)
      used_cols = "".join(map(str, total_cols[0]))
      
      ax.text(
        0.99, -0.22,
        f"Column used: {used_cols}",
        ha='right', va='top',
        transform=ax.transAxes,
        fontsize=8, color="#555555"
      )

      # 5) Encode to base64
      img = io.BytesIO()
      plt.tight_layout()
      fig.savefig(img, format='png')
      plt.close(fig)
      img.seek(0)
      plot_url = base64.b64encode(img.getvalue()).decode('utf-8')

      return plot_url, None



    def compute_total_stats(df: pd.DataFrame, round_to: int = 3):
      """
      Returns (stats: dict, error_message: str|None)
      Computes stats for the single column whose name contains 'total' (case-insensitive).
      """
      # Find the total column
      col = next((c for c in df.columns if 'total' in str(c).lower()), None)
      
      if col is None:
        return {}, "No columns containing 'total' found."

      # To numeric
      s = pd.to_numeric(df[col], errors='coerce')

      if s.count() == 0:
        return {
          "column": str(col),
          "count": 0, "mean": None, "median": None,
          "min": None, "max": None, "range": None, "mode": None
        }, None

      mode_vals = s.mode(dropna=True).tolist()
      stats = {
        "column": str(col),
        "count": int(s.count()),
        "mean": round(float(s.mean()), round_to),
        "median": round(float(s.median()), round_to),
        "min": round(float(s.min()), round_to),
        "max": round(float(s.max()), round_to),
        "range": round(float(s.max() - s.min()), round_to),
        "mode": ", ".join(map(str, mode_vals)) if mode_vals else None,
      }
      return stats, None


    return app

    

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)