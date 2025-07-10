#!/usr/bin/env python3
"""
Code Quality Automation Script

Provides automated code analysis, documentation generation, and quality metrics
for the Cross-Market Arbitrage Tool project.
"""

import subprocess
import sys
import json
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

class CodeQualityAnalyzer:
    """Comprehensive code quality analysis and reporting."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all code quality checks and return comprehensive report."""
        print("🔍 Running comprehensive code quality analysis...")
        
        results = {
            "timestamp": self._get_timestamp(),
            "project_root": str(self.project_root),
            "checks": {}
        }
        
        # Run individual checks
        checks = [
            ("formatting", self._check_formatting),
            ("linting", self._check_linting),
            ("type_checking", self._check_type_checking),
            ("security", self._check_security),
            ("complexity", self._check_complexity),
            ("documentation", self._check_documentation),
            ("test_coverage", self._check_test_coverage),
            ("dependencies", self._check_dependencies),
        ]
        
        for check_name, check_func in checks:
            print(f"  Running {check_name} check...")
            try:
                results["checks"][check_name] = check_func()
                print(f"  ✅ {check_name} check completed")
            except Exception as e:
                print(f"  ❌ {check_name} check failed: {e}")
                results["checks"][check_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Generate overall quality score
        results["quality_score"] = self._calculate_quality_score(results["checks"])
        
        # Save detailed report
        report_file = self.reports_dir / "code_quality_report.json"
        with open(report_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Quality Score: {results['quality_score']:.1f}/100")
        print(f"📋 Detailed report saved to: {report_file}")
        
        return results
    
    def _check_formatting(self) -> Dict[str, Any]:
        """Check code formatting with Black and isort."""
        results = {"tool": "black + isort", "issues": []}
        
        # Check Black formatting
        try:
            result = subprocess.run(
                ["black", "--check", "--diff", str(self.src_dir)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                results["issues"].append({
                    "tool": "black",
                    "message": "Code formatting issues found",
                    "details": result.stdout
                })
        except FileNotFoundError:
            results["issues"].append({"tool": "black", "message": "Black not installed"})
        
        # Check isort formatting
        try:
            result = subprocess.run(
                ["isort", "--check-only", "--diff", str(self.src_dir)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                results["issues"].append({
                    "tool": "isort",
                    "message": "Import sorting issues found",
                    "details": result.stdout
                })
        except FileNotFoundError:
            results["issues"].append({"tool": "isort", "message": "isort not installed"})
        
        results["status"] = "pass" if not results["issues"] else "fail"
        results["issue_count"] = len(results["issues"])
        return results
    
    def _check_linting(self) -> Dict[str, Any]:
        """Check code linting with flake8."""
        results = {"tool": "flake8", "issues": []}
        
        try:
            result = subprocess.run(
                ["flake8", str(self.src_dir), "--format=json"],
                capture_output=True, text=True
            )
            
            if result.stdout:
                # Parse flake8 JSON output
                try:
                    flake8_issues = json.loads(result.stdout)
                    for issue in flake8_issues:
                        results["issues"].append({
                            "file": issue.get("filename", ""),
                            "line": issue.get("line_number", 0),
                            "column": issue.get("column_number", 0),
                            "code": issue.get("code", ""),
                            "message": issue.get("text", "")
                        })
                except json.JSONDecodeError:
                    # Fallback to plain text parsing
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            results["issues"].append({"message": line.strip()})
        
        except FileNotFoundError:
            results["issues"].append({"message": "flake8 not installed"})
        
        results["status"] = "pass" if not results["issues"] else "fail"
        results["issue_count"] = len(results["issues"])
        return results
    
    def _check_type_checking(self) -> Dict[str, Any]:
        """Check type annotations with mypy."""
        results = {"tool": "mypy", "issues": []}
        
        try:
            result = subprocess.run(
                ["mypy", str(self.src_dir), "--json-report", str(self.reports_dir / "mypy")],
                capture_output=True, text=True
            )
            
            # Parse mypy output
            for line in result.stdout.split('\n'):
                if line.strip() and ':' in line:
                    results["issues"].append({"message": line.strip()})
            
            # Try to read JSON report if available
            mypy_report = self.reports_dir / "mypy" / "index.txt"
            if mypy_report.exists():
                with open(mypy_report) as f:
                    mypy_data = f.read()
                    results["detailed_report"] = mypy_data
        
        except FileNotFoundError:
            results["issues"].append({"message": "mypy not installed"})
        
        results["status"] = "pass" if not results["issues"] else "fail"
        results["issue_count"] = len(results["issues"])
        return results
    
    def _check_security(self) -> Dict[str, Any]:
        """Check security issues with bandit."""
        results = {"tool": "bandit", "issues": []}
        
        try:
            result = subprocess.run(
                ["bandit", "-r", str(self.src_dir), "-f", "json"],
                capture_output=True, text=True
            )
            
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    for issue in bandit_data.get("results", []):
                        results["issues"].append({
                            "file": issue.get("filename", ""),
                            "line": issue.get("line_number", 0),
                            "severity": issue.get("issue_severity", ""),
                            "confidence": issue.get("issue_confidence", ""),
                            "code": issue.get("test_id", ""),
                            "message": issue.get("issue_text", "")
                        })
                except json.JSONDecodeError:
                    results["issues"].append({"message": "Failed to parse bandit output"})
        
        except FileNotFoundError:
            results["issues"].append({"message": "bandit not installed"})
        
        results["status"] = "pass" if not results["issues"] else "fail"
        results["issue_count"] = len(results["issues"])
        return results
    
    def _check_complexity(self) -> Dict[str, Any]:
        """Check code complexity with radon."""
        results = {"tool": "radon", "complexity": {}, "issues": []}
        
        try:
            # Cyclomatic complexity
            result = subprocess.run(
                ["radon", "cc", str(self.src_dir), "--json"],
                capture_output=True, text=True
            )
            
            if result.stdout:
                try:
                    complexity_data = json.loads(result.stdout)
                    high_complexity = []
                    
                    for file_path, functions in complexity_data.items():
                        for func in functions:
                            if func.get("complexity", 0) > 10:  # High complexity threshold
                                high_complexity.append({
                                    "file": file_path,
                                    "function": func.get("name", ""),
                                    "complexity": func.get("complexity", 0),
                                    "line": func.get("lineno", 0)
                                })
                    
                    results["complexity"]["high_complexity_functions"] = high_complexity
                    results["complexity"]["total_files"] = len(complexity_data)
                    
                    if high_complexity:
                        results["issues"].extend([
                            f"High complexity in {item['function']} (complexity: {item['complexity']})"
                            for item in high_complexity
                        ])
                
                except json.JSONDecodeError:
                    results["issues"].append({"message": "Failed to parse radon output"})
        
        except FileNotFoundError:
            results["issues"].append({"message": "radon not installed"})
        
        results["status"] = "pass" if not results["issues"] else "fail"
        results["issue_count"] = len(results["issues"])
        return results
    
    def _check_documentation(self) -> Dict[str, Any]:
        """Check documentation coverage with pydocstyle."""
        results = {"tool": "pydocstyle", "issues": []}
        
        try:
            result = subprocess.run(
                ["pydocstyle", str(self.src_dir)],
                capture_output=True, text=True
            )
            
            for line in result.stdout.split('\n'):
                if line.strip():
                    results["issues"].append({"message": line.strip()})
        
        except FileNotFoundError:
            results["issues"].append({"message": "pydocstyle not installed"})
        
        # Count Python files and estimate documentation coverage
        python_files = list(self.src_dir.rglob("*.py"))
        documented_files = 0
        
        for py_file in python_files:
            try:
                with open(py_file) as f:
                    content = f.read()
                    if '"""' in content or "'''" in content:
                        documented_files += 1
            except Exception:
                pass
        
        doc_coverage = (documented_files / len(python_files)) * 100 if python_files else 0
        results["documentation_coverage"] = doc_coverage
        results["total_python_files"] = len(python_files)
        results["documented_files"] = documented_files
        
        results["status"] = "pass" if not results["issues"] else "fail"
        results["issue_count"] = len(results["issues"])
        return results
    
    def _check_test_coverage(self) -> Dict[str, Any]:
        """Check test coverage with pytest-cov."""
        results = {"tool": "pytest-cov", "coverage": 0, "issues": []}
        
        try:
            # Run tests with coverage
            result = subprocess.run(
                ["python", "-m", "pytest", "--cov=src", "--cov-report=xml", "--cov-report=term"],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            # Parse coverage from XML report
            coverage_xml = self.project_root / "coverage.xml"
            if coverage_xml.exists():
                try:
                    tree = ET.parse(coverage_xml)
                    root = tree.getroot()
                    coverage_attr = root.attrib.get('line-rate', '0')
                    results["coverage"] = float(coverage_attr) * 100
                except Exception as e:
                    results["issues"].append({"message": f"Failed to parse coverage: {e}"})
            
            # Parse output for any issues
            if result.returncode != 0:
                results["issues"].append({"message": "Test execution failed"})
                results["test_output"] = result.stdout + result.stderr
        
        except FileNotFoundError:
            results["issues"].append({"message": "pytest not installed"})
        
        results["status"] = "pass" if results["coverage"] >= 85 else "fail"
        results["issue_count"] = len(results["issues"])
        return results
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """Check dependency security and updates."""
        results = {"tool": "pip-audit + pip list", "issues": [], "outdated": []}
        
        try:
            # Check for security vulnerabilities
            result = subprocess.run(
                ["python", "-m", "pip", "audit", "--format=json"],
                capture_output=True, text=True
            )
            
            if result.stdout:
                try:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get("vulnerabilities", []):
                        results["issues"].append({
                            "package": vuln.get("package", ""),
                            "version": vuln.get("installed_version", ""),
                            "vulnerability": vuln.get("id", ""),
                            "description": vuln.get("description", "")
                        })
                except json.JSONDecodeError:
                    pass
        
        except (FileNotFoundError, subprocess.CalledProcessError):
            results["issues"].append({"message": "pip-audit not available"})
        
        try:
            # Check for outdated packages
            result = subprocess.run(
                ["python", "-m", "pip", "list", "--outdated", "--format=json"],
                capture_output=True, text=True
            )
            
            if result.stdout:
                try:
                    outdated_data = json.loads(result.stdout)
                    results["outdated"] = outdated_data
                except json.JSONDecodeError:
                    pass
        
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        results["status"] = "pass" if not results["issues"] else "fail"
        results["issue_count"] = len(results["issues"])
        results["outdated_count"] = len(results["outdated"])
        return results
    
    def _calculate_quality_score(self, checks: Dict[str, Any]) -> float:
        """Calculate overall quality score based on all checks."""
        scores = []
        weights = {
            "formatting": 0.15,
            "linting": 0.20,
            "type_checking": 0.15,
            "security": 0.25,
            "complexity": 0.10,
            "documentation": 0.05,
            "test_coverage": 0.10,
        }
        
        for check_name, weight in weights.items():
            if check_name in checks:
                check_result = checks[check_name]
                
                if check_result.get("status") == "pass":
                    score = 100
                elif check_result.get("status") == "error":
                    score = 0
                else:
                    # Calculate score based on issue count
                    issue_count = check_result.get("issue_count", 0)
                    if check_name == "test_coverage":
                        score = check_result.get("coverage", 0)
                    else:
                        score = max(0, 100 - (issue_count * 5))  # -5 points per issue
                
                scores.append(score * weight)
        
        return sum(scores) if scores else 0
    
    def fix_issues(self, auto_fix: bool = False) -> Dict[str, Any]:
        """Attempt to automatically fix code quality issues."""
        results = {"fixed": [], "failed": []}
        
        print("🔧 Attempting to fix code quality issues...")
        
        # Auto-format with Black
        try:
            result = subprocess.run(
                ["black", str(self.src_dir)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                results["fixed"].append("Code formatted with Black")
            else:
                results["failed"].append(f"Black formatting failed: {result.stderr}")
        except FileNotFoundError:
            results["failed"].append("Black not installed")
        
        # Auto-sort imports with isort
        try:
            result = subprocess.run(
                ["isort", str(self.src_dir)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                results["fixed"].append("Imports sorted with isort")
            else:
                results["failed"].append(f"isort failed: {result.stderr}")
        except FileNotFoundError:
            results["failed"].append("isort not installed")
        
        if auto_fix:
            # Additional auto-fixes could be added here
            # e.g., autopep8, autoflake, etc.
            pass
        
        print(f"  ✅ Fixed: {len(results['fixed'])} issues")
        print(f"  ❌ Failed: {len(results['failed'])} fixes")
        
        return results
    
    def generate_report(self, format_type: str = "html") -> str:
        """Generate a formatted report."""
        # Read the latest report
        report_file = self.reports_dir / "code_quality_report.json"
        if not report_file.exists():
            raise FileNotFoundError("No quality report found. Run analysis first.")
        
        with open(report_file) as f:
            data = json.load(f)
        
        if format_type == "html":
            return self._generate_html_report(data)
        elif format_type == "markdown":
            return self._generate_markdown_report(data)
        else:
            return json.dumps(data, indent=2)
    
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """Generate HTML quality report."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Quality Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .score {{ font-size: 2em; color: #007acc; }}
                .check {{ margin: 20px 0; padding: 15px; border-left: 4px solid #ddd; }}
                .pass {{ border-left-color: #28a745; }}
                .fail {{ border-left-color: #dc3545; }}
                .error {{ border-left-color: #ffc107; }}
                .issue {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Code Quality Report</h1>
                <div class="score">Quality Score: {data['quality_score']:.1f}/100</div>
                <p>Generated: {data['timestamp']}</p>
            </div>
        """
        
        for check_name, check_data in data["checks"].items():
            status_class = check_data.get("status", "error")
            html += f"""
            <div class="check {status_class}">
                <h3>{check_name.replace('_', ' ').title()}</h3>
                <p>Status: {status_class.upper()}</p>
                <p>Issues: {check_data.get('issue_count', 0)}</p>
            """
            
            if check_data.get("issues"):
                html += "<div class='issues'>"
                for issue in check_data["issues"][:10]:  # Limit to 10 issues
                    html += f"<div class='issue'>{issue.get('message', str(issue))}</div>"
                html += "</div>"
            
            html += "</div>"
        
        html += """
        </body>
        </html>
        """
        
        report_path = self.reports_dir / "quality_report.html"
        with open(report_path, "w") as f:
            f.write(html)
        
        return str(report_path)
    
    def _generate_markdown_report(self, data: Dict[str, Any]) -> str:
        """Generate Markdown quality report."""
        md = f"""# Code Quality Report

**Quality Score:** {data['quality_score']:.1f}/100  
**Generated:** {data['timestamp']}  
**Project:** {data['project_root']}

## Summary

"""
        
        for check_name, check_data in data["checks"].items():
            status = check_data.get("status", "error")
            emoji = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
            
            md += f"- {emoji} **{check_name.replace('_', ' ').title()}**: {status.upper()} "
            md += f"({check_data.get('issue_count', 0)} issues)\n"
        
        md += "\n## Detailed Results\n\n"
        
        for check_name, check_data in data["checks"].items():
            md += f"### {check_name.replace('_', ' ').title()}\n\n"
            md += f"- **Status:** {check_data.get('status', 'error').upper()}\n"
            md += f"- **Issues:** {check_data.get('issue_count', 0)}\n"
            
            if check_data.get("coverage") is not None:
                md += f"- **Coverage:** {check_data['coverage']:.1f}%\n"
            
            if check_data.get("issues"):
                md += "\n**Issues:**\n"
                for issue in check_data["issues"][:5]:  # Limit to 5 issues
                    md += f"- {issue.get('message', str(issue))}\n"
            
            md += "\n"
        
        report_path = self.reports_dir / "quality_report.md"
        with open(report_path, "w") as f:
            f.write(md)
        
        return str(report_path)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Code Quality Analysis Tool")
    parser.add_argument("--check", action="store_true", help="Run all quality checks")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--report", choices=["html", "markdown", "json"], 
                       help="Generate report in specified format")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    analyzer = CodeQualityAnalyzer(args.project_root)
    
    if args.check:
        results = analyzer.run_all_checks()
        print(f"\n📊 Analysis complete. Quality score: {results['quality_score']:.1f}/100")
        
        if results['quality_score'] < 80:
            print("⚠️  Quality score below threshold (80). Consider running --fix")
            sys.exit(1)
    
    if args.fix:
        fix_results = analyzer.fix_issues()
        print(f"🔧 Fixed {len(fix_results['fixed'])} issues")
    
    if args.report:
        report_path = analyzer.generate_report(args.report)
        print(f"📋 Report generated: {report_path}")


if __name__ == "__main__":
    main() 