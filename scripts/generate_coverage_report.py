#!/usr/bin/env python3
"""
Script to generate and analyze test coverage for the lexigram project.
This script runs pytest with coverage using the uv package manager and generates a detailed report.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

from bs4 import BeautifulSoup


def extract_coverage_from_html():
    """Extract coverage data from the HTML report if JSON is not available."""
    try:
        # Parse the index.html file
        with open("htmlcov/index.html", "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Extract overall coverage percentage
        coverage_text = soup.select_one(".pc_cov")
        overall_percent = float(coverage_text.text.strip("%")) if coverage_text else 0

        # Extract file data from the table
        files_data = {}
        for row in soup.select("table.index tbody tr.region"):
            try:
                file_path = row.select_one("td.name a").text
                statements = int(row.select("td")[1].text)
                missing = int(row.select("td")[2].text)
                excluded = int(row.select("td")[3].text)

                # Calculate covered statements
                covered = statements - missing

                # Calculate percentage
                percent = (covered / statements * 100) if statements > 0 else 0

                files_data[file_path] = {
                    "statements_total": statements,
                    "statements_covered": covered,
                    "statements_percent": percent,
                    "excluded": excluded,
                }
            except (AttributeError, IndexError, ValueError) as e:
                print(f"Error parsing row: {e}")
                continue

        # Extract totals from the footer
        try:
            total_row = soup.select_one("table.index tfoot tr.total")
            total_statements = int(total_row.select("td")[1].text)
            total_missing = int(total_row.select("td")[2].text)
            total_excluded = int(total_row.select("td")[3].text)
            total_covered = total_statements - total_missing
        except (AttributeError, IndexError, ValueError):
            # Calculate totals from file data if footer parsing fails
            total_statements = sum(
                data["statements_total"] for data in files_data.values()
            )
            total_covered = sum(
                data["statements_covered"] for data in files_data.values()
            )
            total_excluded = sum(
                data.get("excluded", 0) for data in files_data.values()
            )

        # Create a coverage data structure similar to what we'd expect from JSON
        coverage_data = {
            "files": files_data,
            "totals": {
                "statements_total": total_statements,
                "statements_covered": total_covered,
                "statements_percent": overall_percent,
                "excluded": total_excluded,
            },
        }

        return coverage_data

    except Exception as e:
        print(f"Error extracting coverage from HTML: {e}")
        # Return a minimal structure
        return {
            "files": {},
            "totals": {
                "statements_total": 0,
                "statements_covered": 0,
                "statements_percent": 0,
                "excluded": 0,
            },
        }


def run_tests_with_coverage():
    """Run pytest with coverage using uv and return the exit code."""
    print("Running tests with coverage using uv...")
    result = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/",
            "--cov=app",
            "--cov-report=term",
            "--cov-report=html",
            "--cov-report=json",
            "--cov-config=.coveragerc",
        ],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("Errors:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    return result.returncode


def analyze_coverage_report():
    """Analyze the coverage report and print statistics."""
    if not os.path.exists(".coverage"):
        print(
            "Coverage file '.coverage' not found. Make sure tests were run with coverage."
        )
        return

    # Check if we have an HTML report
    if not os.path.exists("htmlcov/index.html"):
        print(
            "HTML coverage report not found. Make sure tests were run with --cov-report=html."
        )
        return

    # Try to read the coverage data from the JSON report
    try:
        if os.path.exists("htmlcov/status.json"):
            with open("htmlcov/status.json", "r") as f:
                coverage_data = json.load(f)
        else:
            print(
                "JSON coverage report not found. Falling back to HTML report analysis."
            )
            coverage_data = extract_coverage_from_html()

        # Extract totals - handle different possible JSON structures
        if "totals" in coverage_data:
            totals = coverage_data["totals"]
            total_statements = totals.get("statements_total", 0)
            covered_statements = totals.get("statements_covered", 0)
            coverage_percent = totals.get("statements_percent", 0)
        elif "summary" in coverage_data:
            totals = coverage_data["summary"]
            total_statements = totals.get("total_statements", 0)
            covered_statements = totals.get("covered_statements", 0)
            coverage_percent = (
                (covered_statements / total_statements * 100)
                if total_statements > 0
                else 0
            )
        else:
            # If we can't find the totals in the expected format, calculate them from files
            files_data = coverage_data.get("files", {})
            total_statements = 0
            covered_statements = 0

            for file_data in files_data.values():
                if isinstance(file_data, dict):
                    total_statements += file_data.get("statements_total", 0)
                    covered_statements += file_data.get("statements_covered", 0)

            coverage_percent = (
                (covered_statements / total_statements * 100)
                if total_statements > 0
                else 0
            )
    except Exception as e:
        print(f"Error analyzing coverage data: {e}")
        print("Falling back to basic coverage report.")
        # Provide default values
        total_statements = 0
        covered_statements = 0
        coverage_percent = 0
        coverage_data = {"files": {}}

    # Print summary
    print("\n" + "=" * 80)
    print(
        f"COVERAGE SUMMARY (Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
    )
    print("=" * 80)
    print(f"Total statements: {total_statements}")
    print(f"Covered statements: {covered_statements}")
    print(f"Coverage percentage: {coverage_percent:.2f}%")
    print("=" * 80)

    # Process file data to ensure consistent structure
    processed_files = {}
    files_data = coverage_data.get("files", {})

    for file_path, data in files_data.items():
        if not isinstance(data, dict):
            continue

        # Extract or calculate key metrics with fallbacks
        total = data.get("statements_total", 0)
        if total == 0:
            total = data.get("total_statements", 0)

        covered = data.get("statements_covered", 0)
        if covered == 0:
            covered = data.get("covered_statements", 0)

        percent = data.get("statements_percent", 0)
        if percent == 0 and total > 0:
            percent = (covered / total) * 100

        # Store processed data
        processed_files[file_path] = {
            "statements_total": total,
            "statements_covered": covered,
            "statements_percent": percent,
        }

    # Print files with low coverage
    print("\nFILES WITH LOW COVERAGE (< 50%):")
    print("-" * 80)

    low_coverage_files = []
    for file_path, data in processed_files.items():
        total = data["statements_total"]
        percent = data["statements_percent"]
        covered = data["statements_covered"]

        if percent < 50 and total > 0:
            low_coverage_files.append((file_path, percent, covered, total))

    # Sort by coverage percentage (ascending)
    low_coverage_files.sort(key=lambda x: x[1])

    for file_path, percent, covered, total in low_coverage_files:
        print(f"{file_path:<50} {percent:>6.2f}% ({covered}/{total})")

    # Print files with no coverage
    print("\nFILES WITH NO COVERAGE (0%):")
    print("-" * 80)

    no_coverage_files = [f for f, p, _, _ in low_coverage_files if p == 0]
    for file_path in no_coverage_files:
        print(file_path)

    # Print files with high coverage
    print("\nFILES WITH HIGH COVERAGE (≥ 90%):")
    print("-" * 80)

    high_coverage_files = []
    for file_path, data in processed_files.items():
        total = data["statements_total"]
        percent = data["statements_percent"]
        covered = data["statements_covered"]

        if percent >= 90 and total > 0:
            high_coverage_files.append((file_path, percent, covered, total))

    # Sort by coverage percentage (descending)
    high_coverage_files.sort(key=lambda x: x[1], reverse=True)

    for file_path, percent, covered, total in high_coverage_files:
        print(f"{file_path:<50} {percent:>6.2f}% ({covered}/{total})")

    # Print coverage by module
    print("\nCOVERAGE BY MODULE:")
    print("-" * 80)

    modules = {}
    for file_path, data in processed_files.items():
        parts = file_path.split("/")
        if len(parts) > 1:
            module = parts[0]
            if module not in modules:
                modules[module] = {"statements_total": 0, "statements_covered": 0}
            modules[module]["statements_total"] += data["statements_total"]
            modules[module]["statements_covered"] += data["statements_covered"]

    for module, data in modules.items():
        if data["statements_total"] > 0:
            percent = (data["statements_covered"] / data["statements_total"]) * 100
            print(
                f"{module:<20} {percent:>6.2f}% ({data['statements_covered']}/{data['statements_total']})"
            )

    print("\nHTML report generated in: htmlcov/index.html")


def main():
    """Main function to run tests and analyze coverage."""
    exit_code = run_tests_with_coverage()
    if exit_code != 0:
        print(f"Tests failed with exit code {exit_code}")

    analyze_coverage_report()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
