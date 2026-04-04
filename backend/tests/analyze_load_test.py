"""
Analyze Locust load test results and generate HTML report.

Usage:
    python analyze_load_test.py --input=load_test_results/ --output=report.html
"""

import argparse
import pandas as pd
import os
from datetime import datetime
from pathlib import Path


def load_results(input_dir: str):
    """Load CSV results from Locust."""
    results_path = Path(input_dir)
    
    # Load requests CSV
    requests_file = results_path / "requests.csv"
    if requests_file.exists():
        requests_df = pd.read_csv(requests_file)
    else:
        requests_df = pd.DataFrame()
    
    # Load stats CSV
    stats_file = results_path / "stats.csv"
    if stats_file.exists():
        stats_df = pd.read_csv(stats_file)
    else:
        stats_df = pd.DataFrame()
    
    # Load failures CSV
    failures_file = results_path / "failures.csv"
    if failures_file.exists():
        failures_df = pd.read_csv(failures_file)
    else:
        failures_df = pd.DataFrame()
    
    return requests_df, stats_df, failures_df


def generate_report(requests_df, stats_df, failures_df, output_file: str):
    """Generate HTML report from results."""
    
    # Calculate summary statistics
    total_requests = len(requests_df) if not requests_df.empty else 0
    total_failures = len(failures_df) if not failures_df.empty else 0
    success_rate = ((total_requests - total_failures) / total_requests * 100) if total_requests > 0 else 0
    
    # Get P95 and P99 from stats
    if not stats_df.empty:
        total_row = stats_df[stats_df['Method'] == 'Total']
        if not total_row.empty:
            p95 = total_row['response_time_95_percentile'].values[0]
            p99 = total_row['response_time_99_percentile'].values[0]
            avg_response_time = total_row['avg_response_time'].values[0]
        else:
            p95 = p99 = avg_response_time = 0
    else:
        p95 = p99 = avg_response_time = 0
    
    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>24-Hour Load Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
        .metric {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric.pass {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .metric.fail {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .metric-value {{ font-size: 36px; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ font-size: 14px; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        tr:hover {{ background: #f8f9fa; }}
        .status-pass {{ color: #28a745; font-weight: bold; }}
        .status-fail {{ color: #dc3545; font-weight: bold; }}
        .timestamp {{ color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 24-Hour Load Test Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <h2>Executive Summary</h2>
        <div class="summary">
            <div class="metric {'pass' if success_rate > 99 else 'fail'}">
                <div class="metric-value">{success_rate:.2f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric {'pass' if p95 < 3000 else 'fail'}">
                <div class="metric-value">{p95:.0f}ms</div>
                <div class="metric-label">P95 Response Time</div>
            </div>
            <div class="metric {'pass' if p99 < 5000 else 'fail'}">
                <div class="metric-value">{p99:.0f}ms</div>
                <div class="metric-label">P99 Response Time</div>
            </div>
            <div class="metric">
                <div class="metric-value">{total_requests:,}</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric {'pass' if total_failures < 100 else 'fail'}">
                <div class="metric-value">{total_failures:,}</div>
                <div class="metric-label">Total Failures</div>
            </div>
        </div>
        
        <h2>Performance Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Target</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Success Rate</td>
                <td>{success_rate:.2f}%</td>
                <td>>99%</td>
                <td class="{'status-pass' if success_rate > 99 else 'status-fail'}">{'✅ PASS' if success_rate > 99 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>P95 Response Time</td>
                <td>{p95:.0f}ms</td>
                <td><3000ms</td>
                <td class="{'status-pass' if p95 < 3000 else 'status-fail'}">{'✅ PASS' if p95 < 3000 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>P99 Response Time</td>
                <td>{p99:.0f}ms</td>
                <td><5000ms</td>
                <td class="{'status-pass' if p99 < 5000 else 'status-fail'}">{'✅ PASS' if p99 < 5000 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>Average Response Time</td>
                <td>{avg_response_time:.0f}ms</td>
                <td><2000ms</td>
                <td class="{'status-pass' if avg_response_time < 2000 else 'status-fail'}">{'✅ PASS' if avg_response_time < 2000 else '❌ FAIL'}</td>
            </tr>
        </table>
        
        <h2>Request Statistics by Endpoint</h2>
        {stats_df.to_html(index=False, classes='stats-table', border=0) if not stats_df.empty else '<p>No statistics available</p>'}
        
        <h2>Failure Analysis</h2>
        {failures_df.to_html(index=False, classes='failures-table', border=0) if not failures_df.empty else '<p>No failures recorded - Excellent! ✅</p>'}
        
        <h2>Recommendations</h2>
        <ul>
            {'<li>✅ System performed well under load - Ready for production!</li>' if success_rate > 99 and p95 < 3000 else '<li>⚠️ Review failing endpoints and optimize response times</li>'}
            {'<li>✅ Response times within acceptable range</li>' if p95 < 3000 else '<li>⚠️ Consider optimizing slow endpoints or scaling resources</li>'}
            {'<li>✅ No significant failures detected</li>' if total_failures < 100 else '<li>⚠️ Investigate root cause of failures</li>'}
        </ul>
        
        <h2>Next Steps</h2>
        <ol>
            <li>Review this report with the team</li>
            <li>Address any failing metrics</li>
            <li>Update TEST_RESULTS.md with findings</li>
            <li>Schedule production deployment if all tests pass</li>
        </ol>
    </div>
</body>
</html>
"""
    
    # Write HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Report generated: {output_file}")
    
    # Print summary to console
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Requests:    {total_requests:,}")
    print(f"Total Failures:    {total_failures:,}")
    print(f"Success Rate:      {success_rate:.2f}%")
    print(f"P95 Response Time: {p95:.0f}ms")
    print(f"P99 Response Time: {p99:.0f}ms")
    print(f"Avg Response Time: {avg_response_time:.0f}ms")
    print("="*60)
    
    if success_rate > 99 and p95 < 3000:
        print("✅ TEST PASSED - System ready for production!")
    else:
        print("❌ TEST FAILED - Review metrics and optimize")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Analyze load test results')
    parser.add_argument('--input', required=True, help='Input directory with CSV files')
    parser.add_argument('--output', default='load_test_report.html', help='Output HTML file')
    
    args = parser.parse_args()
    
    print(f"Loading results from: {args.input}")
    requests_df, stats_df, failures_df = load_results(args.input)
    
    print(f"Generating report: {args.output}")
    generate_report(requests_df, stats_df, failures_df, args.output)


if __name__ == '__main__':
    main()
