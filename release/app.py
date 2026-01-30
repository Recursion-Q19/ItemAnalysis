#Import libraries and tools

from flask import Flask, request, render_template, abort
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import io
import sys
import base64
import time
import os
import threading
import webbrowser


#Function - create app
def create_app():
    def resource_path(relative_path):
        try:
            base_path = sys._MEIPASS  # PyInstaller temp folder
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    app = Flask(
        __name__,
        template_folder=resource_path("templates")
    )

    last_ping = {"t": time.time()}
    had_client = {"v": False}
    @app.route("/ping", methods=["POST"])
    def ping():
        # Only allow local shutdown control
        ###if request.remote_addr not in ("127.0.0.1", "::1"):
            ###abort(403)
        if not request.remote_addr.startswith("127.") and request.remote_addr != "::1":
          abort(403)
        last_ping["t"] = time.time()
        had_client["v"] = True
        return ("", 204)

    def watchdog():
      #wait until someone actually opens the page once
      while not had_client["v"]:
        time.sleep(0.5)

      #If no pings for N seconds => exit the whole process
      TIMEOUT_SECONDS = 5
      while True:
        time.sleep(1)
        if time.time() - last_ping["t"] > TIMEOUT_SECONDS: 
          os._exit(0) #force-terminate (works reliably for PyInstaller exe)
      
    threading.Thread(target=watchdog, daemon=True).start()

    @app.route('/', methods=['GET', 'POST'])
    def home():

      #Initializing the variables (Not initializing results in errors)
      hist_plot_url = None
      error_hist = None
      stats = None
      difficulty_index_table = None
      discrimination_index_table = None
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

            difficulty_index_table, discrimination_index_table = calculate_dif_Disc_indices(df)

            #Combining errors separated by a new line
            if error_messages:
              error = " <br> ".join(error_messages)

          except Exception as e:
            error = f"Error processing file: {e}"

      return render_template('home.html', stats=stats, plot_url=hist_plot_url, difficulty_index_table=difficulty_index_table, discrimination_index_table=discrimination_index_table , error=error)



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




    #helper functions
    def interpret_difficulty_index(value):
      if value >= 0.91:
          return 'Very Easy'
      elif 0.76 <= value < 0.91:
          return 'Easy'
      elif 0.26 <= value < 0.76:
          return 'Moderate(Average)'
      elif 0.11 <= value < 0.26:
          return 'difficult'
      else:
          return 'Very Difficult'

    def interpret_discrimination_index(value):
      if value >= 0.40:
          return 'Very Good'
      elif 0.30 <= value < 0.40:
          return 'Reasonably Good'
      elif 0.20 <= value < 0.30:
          return 'Marginal Item'
      else:
          return 'Poor item'


    def calculate_dif_Disc_indices(df: pd.DataFrame, round_to: int = 2):
      #Sort the dataframe
      df_sorted_des = df.sort_values(by=df.columns[-1], ascending=False)
      #Calculate 27 precent top and bottom
      n = len(df)
      _27percent = math.ceil(n * 0.27)
      top_27 = df_sorted_des.head(_27percent)
      bottom_27 = df_sorted_des.tail(_27percent)

      #Get the column names of the numeric type
      numeric_cols = df.select_dtypes(include='number').columns

      #Computing Difficulty Index
      difficulty_index = (top_27[numeric_cols].sum() + bottom_27[numeric_cols].sum()) / (2 * _27percent)

      difficulty_index = difficulty_index.round(round_to).to_frame(name='Difficulty Index').iloc[:-1, :]

      difficulty_index['Interpretation'] = difficulty_index['Difficulty Index'].apply(interpret_difficulty_index)

      #computing Discrimination Index

      discrimination_index = (top_27[numeric_cols].sum() - bottom_27[numeric_cols].sum()) / _27percent

      discrimination_index = discrimination_index.round(round_to).to_frame(name='Discrimination Index').iloc[:-1, :]
      
      discrimination_index['Interpretation'] = discrimination_index['Discrimination Index'].apply(interpret_discrimination_index)

      diff_index_table = difficulty_index.to_html(classes='table table-bordered', index=True)
      disc_index_table = discrimination_index.to_html(classes='table table-bordered', index=True)

      return diff_index_table, disc_index_table


    return app

    

if __name__ == '__main__':
    app = create_app()
    def open_browser():
        webbrowser.open("http://127.0.0.1:5000")

    t = threading.Timer(1.0, open_browser)
    t.daemon = True
    t.start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)