import os
import glob
import re
import html
import datetime

# --- CONFIGURATION ---
# Set this to the folder containing your logs, or '.' for the current directory
LOG_FOLDER = "." 
REPORT_FILE = "test_report.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Execution Report</title>
    <style>
        :root {
            --bg-color: #f4f7f6;
            --text-color: #333;
            --pass-color: #28a745;
            --fail-color: #dc3545;
            --skip-color: #ffc107;
            --border-color: #dee2e6;
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { border-bottom: 2px solid var(--border-color); padding-bottom: 10px; color: #2c3e50; }
        
        /* Dashboard Summary */
        .summary { display: flex; gap: 20px; margin-bottom: 20px; }
        .card { flex: 1; padding: 20px; border-radius: 8px; text-align: center; color: white; font-weight: bold; font-size: 1.2em; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card.total { background: #6c757d; }
        .card.passed { background: var(--pass-color); }
        .card.failed { background: var(--fail-color); }
        .card.skipped { background: var(--skip-color); color: #333;}
        .card span { display: block; font-size: 2em; margin-top: 10px; }

        /* Filters */
        .filters { margin-bottom: 15px; }
        .btn { padding: 8px 15px; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; margin-right: 5px; transition: opacity 0.2s;}
        .btn:hover { opacity: 0.8; }
        .btn-all { background: #007bff; color: white; }
        .btn-pass { background: var(--pass-color); color: white; }
        .btn-fail { background: var(--fail-color); color: white; }

        /* Table Styles */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border-color); }
        th { background-color: #e9ecef; color: #495057; }
        tr.test-row { cursor: pointer; transition: background-color 0.2s; }
        tr.test-row:hover { background-color: #f1f3f5; }
        
        .badge { padding: 5px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold; color: white; }
        .badge.passed { background-color: var(--pass-color); }
        .badge.failed { background-color: var(--fail-color); }
        .badge.skipped { background-color: var(--skip-color); color: #333; }

        /* Log Details & Tabs */
        .details-row { display: none; background-color: #fafafa; }
        .details-container { padding: 15px; border: 1px solid var(--border-color); border-radius: 4px; margin: 10px 0; }
        
        .tab { overflow: hidden; border-bottom: 1px solid var(--border-color); background-color: #f1f1f1; border-radius: 4px 4px 0 0; }
        .tab button { background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 10px 16px; transition: 0.3s; font-weight: bold; }
        .tab button:hover { background-color: #ddd; }
        .tab button.active { background-color: #fff; border: 1px solid var(--border-color); border-bottom: none; border-radius: 4px 4px 0 0; margin-bottom: -1px; }
        .tab button.fail-tab { color: var(--fail-color); }
        
        .tabcontent { display: none; padding: 15px; background: #fff; border: 1px solid var(--border-color); border-top: none; overflow-x: auto; max-height: 400px; overflow-y: auto; }
        pre { margin: 0; font-family: 'Courier New', Courier, monospace; font-size: 0.9em; color: #2b2b2b; white-space: pre-wrap; word-wrap: break-word; }
        .empty-log { color: #888; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Execution Report</h1>
        <p>Generated on: __DATE__</p>
        
        <div class="summary">
            <div class="card total">Total Tests<span>__TOTAL__</span></div>
            <div class="card passed">Passed<span>__PASSED__</span></div>
            <div class="card failed">Failed<span>__FAILED__</span></div>
            <div class="card skipped">Skipped/Other<span>__SKIPPED__</span></div>
        </div>

        <div class="filters">
            <button class="btn btn-all" onclick="filterTests('all')">Show All</button>
            <button class="btn btn-pass" onclick="filterTests('passed')">Show Passed</button>
            <button class="btn btn-fail" onclick="filterTests('failed')">Show Failed</button>
        </div>

        <table id="testTable">
            <thead>
                <tr>
                    <th>SUT Name</th>
                    <th>Test Name</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                __TABLE_ROWS__
            </tbody>
        </table>
    </div>

    <script>
        function toggleDetails(id) {
            const row = document.getElementById('details-' + id);
            if (row.style.display === 'table-row') {
                row.style.display = 'none';
            } else {
                row.style.display = 'table-row';
            }
        }

        function openTab(evt, tabName, rowId) {
            const container = document.getElementById('details-' + rowId);
            const tabcontent = container.getElementsByClassName("tabcontent");
            for (let i = 0; i < tabcontent.length; i++) {
                tabcontent[i].style.display = "none";
            }
            const tablinks = container.getElementsByClassName("tablinks");
            for (let i = 0; i < tablinks.length; i++) {
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }

        function filterTests(status) {
            const table = document.getElementById("testTable");
            const trs = table.getElementsByTagName("tr");
            
            // Loop through all table rows, starting from index 1 to skip header
            for (let i = 1; i < trs.length; i++) {
                // Ensure we only process main test rows, not detail rows
                if (trs[i].classList.contains('test-row')) {
                    const rowStatus = trs[i].getAttribute("data-status");
                    const detailsRow = document.getElementById('details-' + trs[i].getAttribute("data-id"));
                    
                    if (status === 'all' || rowStatus === status) {
                        trs[i].style.display = "";
                        // Close details when filtering to keep it clean
                        detailsRow.style.display = "none"; 
                    } else {
                        trs[i].style.display = "none";
                        detailsRow.style.display = "none";
                    }
                }
            }
        }
    </script>
</body>
</html>
"""

def parse_log_file(filepath):
    filename = os.path.basename(filepath)
    
    # Expected format: pytest_<outcome>_<sut_name>_<test_name>.log
    match = re.match(r'pytest_(?P<outcome>[^_]+)_(?P<sut_name>[^_]+)_(?P<test_name>.+)\.log$', filename)
    if match:
        outcome = match.group('outcome').lower()
        sut_name = match.group('sut_name')
        test_name = match.group('test_name')
    else:
        # Fallback if filename format is slightly off
        outcome, sut_name, test_name = "unknown", "unknown", filename

    setup_log, call_log, teardown_log, failure_log = [], [], [], []
    current_section = "header" # everything before setup

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return None

    for line in lines:
        line_stripped = line.strip()
        
        # State machine to detect sections
        if "****live log setup***" in line_stripped:
            current_section = "setup"
            continue
        elif "****live log call***" in line_stripped:
            current_section = "call"
            continue
        elif "****live log teardown***" in line_stripped:
            current_section = "teardown"
            continue
        elif "*****Failures****" in line_stripped or "**** Failures ****" in line_stripped:
            current_section = "failures"
            continue

        # Append to the respective list based on current state
        escaped_line = html.escape(line)
        if current_section == "setup":
            setup_log.append(escaped_line)
        elif current_section == "call":
            call_log.append(escaped_line)
        elif current_section == "teardown":
            teardown_log.append(escaped_line)
        elif current_section == "failures":
            failure_log.append(escaped_line)

    return {
        "sut_name": sut_name,
        "test_name": test_name,
        "outcome": outcome,
        "setup": "".join(setup_log) or "<span class='empty-log'>No setup logs found.</span>",
        "call": "".join(call_log) or "<span class='empty-log'>No call logs found.</span>",
        "teardown": "".join(teardown_log) or "<span class='empty-log'>No teardown logs found.</span>",
        "failures": "".join(failure_log) or "<span class='empty-log'>No failure traces found.</span>"
    }

def generate_html_report():
    log_files = glob.glob(os.path.join(LOG_FOLDER, "pytest_*.log"))
    
    if not log_files:
        print(f"No log files found in '{LOG_FOLDER}' matching 'pytest_*.log'")
        return

    results = []
    stats = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

    for file in log_files:
        data = parse_log_file(file)
        if data:
            results.append(data)
            stats["total"] += 1
            if data["outcome"] == "passed":
                stats["passed"] += 1
            elif data["outcome"] == "failed":
                stats["failed"] += 1
            else:
                stats["skipped"] += 1

    # Generate HTML Rows
    rows_html = ""
    for idx, test in enumerate(results):
        row_id = str(idx)
        status = test["outcome"]
        badge_class = status if status in ['passed', 'failed'] else 'skipped'
        
        # Determine the default active tab (If failed, default to failures tab, otherwise call tab)
        default_tab = "failures" if status == "failed" else "call"

        # Main Table Row
        rows_html += f"""
        <tr class="test-row" data-status="{status}" data-id="{row_id}" onclick="toggleDetails('{row_id}')">
            <td>{test['sut_name']}</td>
            <td>{test['test_name']}</td>
            <td><span class="badge {badge_class}">{status.upper()}</span></td>
        </tr>
        """
        
        # Details Dropdown Row (Tabs: Setup, Call, Teardown, Failures)
        rows_html += f"""
        <tr id="details-{row_id}" class="details-row">
            <td colspan="3">
                <div class="details-container">
                    <div class="tab">
                        <button class="tablinks {'active' if default_tab == 'setup' else ''}" onclick="openTab(event, 'setup-{row_id}', '{row_id}')">Setup</button>
                        <button class="tablinks {'active' if default_tab == 'call' else ''}" onclick="openTab(event, 'call-{row_id}', '{row_id}')">Call</button>
                        <button class="tablinks {'active' if default_tab == 'teardown' else ''}" onclick="openTab(event, 'teardown-{row_id}', '{row_id}')">Teardown</button>
                        """
        
        if status == 'failed' or "<span class='empty-log'>" not in test['failures']:
            rows_html += f"""<button class="tablinks fail-tab {'active' if default_tab == 'failures' else ''}" onclick="openTab(event, 'failures-{row_id}', '{row_id}')">Failures</button>"""
            
        rows_html += f"""
                    </div>
                    
                    <div id="setup-{row_id}" class="tabcontent" style="display: {'block' if default_tab == 'setup' else 'none'};">
                        <pre>{test['setup']}</pre>
                    </div>
                    <div id="call-{row_id}" class="tabcontent" style="display: {'block' if default_tab == 'call' else 'none'};">
                        <pre>{test['call']}</pre>
                    </div>
                    <div id="teardown-{row_id}" class="tabcontent" style="display: {'block' if default_tab == 'teardown' else 'none'};">
                        <pre>{test['teardown']}</pre>
                    </div>
                    <div id="failures-{row_id}" class="tabcontent" style="display: {'block' if default_tab == 'failures' else 'none'};">
                        <pre>{test['failures']}</pre>
                    </div>
                </div>
            </td>
        </tr>
        """

    # Inject variables into Template
    final_html = HTML_TEMPLATE \
        .replace("__DATE__", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) \
        .replace("__TOTAL__", str(stats["total"])) \
        .replace("__PASSED__", str(stats["passed"])) \
        .replace("__FAILED__", str(stats["failed"])) \
        .replace("__SKIPPED__", str(stats["skipped"])) \
        .replace("__TABLE_ROWS__", rows_html)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print(f"Success! Report generated with {stats['total']} tests: {os.path.abspath(REPORT_FILE)}")

if __name__ == "__main__":
    generate_html_report()
