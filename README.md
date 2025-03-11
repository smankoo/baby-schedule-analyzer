# Baby Schedule Analyzer

Baby Schedule Analyzer is a Streamlit app that parses baby schedule logs in a standard format and generates interactive visualizations. It categorizes events into “regular” (occurring at least 3 times overall) and “other” events while also providing an option to hide stale events (i.e. events absent for 3 consecutive days). The app displays the results as a formatted table and an interactive grouped bar chart.

## Features

- **Log Parsing:** Reads baby schedule logs in the format:

Mar 11, 2025 - 5:48 AM: Breastfeeding

- **Event Classification:**
- Separates events into **regular** events (overall count ≥ 3) and **other** events.
- Aligns "other" events by time for better readability.
- Optionally hides regular events that haven’t occurred for three consecutive days.
- **Interactive Visualization:**
- Displays the daily event counts in a data table.
- Provides an interactive grouped bar chart (using Altair) to visualize regular event counts across days.
- **Dual Interface:**
- A **Streamlit** based UI (in `app.py`) for web deployment.
- A **command-line** version (in `main.py`) that prints summary tables using Tabulate.

## Installation

1. **Clone the repository:**

```bash
git clone https://github.com/smankoo/baby-schedule-analyzer.git
cd baby-schedule-analyzer
```

2. Create and activate a virtual environment (optional but recommended):

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows use: venv\Scripts\activate
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Running on Streamlit Community Cloud

1. Push your repository to GitHub.
2. Connect your GitHub repository to Streamlit Community Cloud.
3. Set the main file to app.py and deploy the app.
4. In the deployed app, paste your baby schedule data into the provided text area and click Analyze to view the results.

## Running Locally

- Streamlit App:
  To run the Streamlit interface locally, use:

```bash
streamlit run app.py
```

- Command-Line Version:
  To run the command-line version that prints tables to the console, execute:

```bash
python main.py
```

## Code Structure

- app.py:
  Contains the BabyStatsAnalyzer class and the Streamlit UI components. It processes the baby schedule logs, builds a data table, and creates an interactive Altair bar chart.
- main.py:
  A command-line interface version of the analyzer that prints formatted tables using the Tabulate library. This can be used for testing or non-UI use cases.
- requirements.txt:
  Lists all dependencies required to run the app (including Streamlit, Altair, Pandas, and Tabulate).

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## License

Distributed under the MIT License. See LICENSE for more information.

## Notes

- Sensitive Information:
  Ensure that any personal or sensitive information (e.g., local file system paths or names) is removed before sharing or deploying to GitHub.
- Customization:
  You can modify the default baby schedule data in the app or adapt the input methods as needed.

Happy analyzing!
