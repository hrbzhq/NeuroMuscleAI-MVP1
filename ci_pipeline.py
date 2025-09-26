"""Automated CI/CD Integration Script.

This script integrates environment checking, testing, and development analysis
into an automated workflow suitable for CI/CD pipelines.
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from typing import Dict, List, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

import software_checker
import dev_analyzer


class CIPipeline:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'pipeline_version': '1.0.0',
            'steps': {}
        }
        
    def run_environment_checks(self, auto_fix: bool = False) -> Dict[str, Any]:
        """Run comprehensive environment checks."""
        print("🔍 Running environment checks...")
        
        try:
            report = software_checker.run_checks(auto_fix=auto_fix)
            
            # Determine status
            issues = []
            if 'missing_packages' in report and report['missing_packages']:
                issues.append(f"Missing packages: {report['missing_packages']}")
            if 'git_dirty' in report and report['git_dirty'] is True:
                issues.append("Uncommitted changes detected")
            if 'system_resources' in report and isinstance(report['system_resources'], dict):
                resources = report['system_resources']
                if resources.get('cpu_percent', 0) > 90:
                    issues.append("High CPU usage")
                if resources.get('memory_percent', 0) > 90:
                    issues.append("High memory usage")
            
            status = 'failed' if issues else 'passed'
            
            result = {
                'status': status,
                'report': report,
                'issues': issues,
                'auto_fixes_applied': report.get('fixes_applied', [])
            }
            
            print(f"✅ Environment check: {status}")
            if issues:
                for issue in issues:
                    print(f"  ⚠️  {issue}")
            if result['auto_fixes_applied']:
                for fix in result['auto_fixes_applied']:
                    print(f"  🔧 {fix}")
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def run_tests(self, test_path: str = "tests/") -> Dict[str, Any]:
        """Run the test suite."""
        print(f"🧪 Running tests from {test_path}...")
        
        try:
            # Run pytest (do not require pytest-json-report plugin in CI)
            cmd = [
                sys.executable, '-m', 'pytest',
                test_path, '-v', '--tb=short'
            ]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=os.getcwd()
            )
            
            # Parse test results
            test_output = result.stdout
            test_errors = result.stderr
            exit_code = result.returncode
            
            # No JSON plugin required; keep test_data empty unless present
            test_data = {}
            
            # Extract test statistics from output
            passed = test_output.count(' PASSED')
            failed = test_output.count(' FAILED')
            errors = test_output.count(' ERROR')
            
            # Parse summary line like "3 passed in 2.53s"
            import re
            summary_match = re.search(r"(\d+) passed", test_output)
            if summary_match:
                try:
                    passed = int(summary_match.group(1))
                except Exception:
                    pass

            failed_match = re.search(r"(\d+) failed", test_output)
            if failed_match:
                try:
                    failed = int(failed_match.group(1))
                except Exception:
                    pass

            error_match = re.search(r"(\d+) error", test_output)
            if error_match:
                try:
                    errors = int(error_match.group(1))
                except Exception:
                    pass

            status = 'passed' if exit_code == 0 else 'failed'
            
            result = {
                'status': status,
                'exit_code': exit_code,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'output': test_output,
                'stderr': test_errors,
                'json_report': test_data
            }
            
            print(f"✅ Tests: {status} ({passed} passed, {failed} failed, {errors} errors)")
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def run_development_analysis(self) -> Dict[str, Any]:
        """Run development session analysis."""
        print("📊 Running development analysis...")
        
        try:
            analyzer = dev_analyzer.DevAnalyzer()
            analysis = analyzer.analyze_session_patterns()
            insights = analyzer.generate_insights()
            
            # Generate reports
            json_report = analyzer.export_report('json', 'ci_dev_analysis.json')
            
            result = {
                'status': 'passed',
                'analysis': analysis,
                'insights': insights,
                'report_file': json_report
            }
            
            print(f"✅ Analysis complete: {len(insights)} insights generated")
            for insight in insights[:3]:  # Show first 3 insights
                print(f"  💡 {insight}")
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_code_quality(self) -> Dict[str, Any]:
        """Run code quality checks."""
        print("🔍 Running code quality checks...")
        
        quality_issues = []
        
        # Check for common Python issues
        python_files = []
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        # Basic code quality checks
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Check for very long lines
                    for i, line in enumerate(lines):
                        if len(line) > 120:
                            quality_issues.append(f"{file_path}:{i+1} - Line too long ({len(line)} chars)")
                    
                    # Check for TODO/FIXME comments
                    todo_count = content.lower().count('todo')
                    fixme_count = content.lower().count('fixme')
                    if todo_count > 0:
                        quality_issues.append(f"{file_path} - {todo_count} TODO comments")
                    if fixme_count > 0:
                        quality_issues.append(f"{file_path} - {fixme_count} FIXME comments")
                        
            except Exception:
                continue
        
        status = 'passed' if len(quality_issues) < 10 else 'warning'
        
        result = {
            'status': status,
            'issues_count': len(quality_issues),
            'issues': quality_issues[:10],  # Limit output
            'files_checked': len(python_files)
        }
        
        print(f"✅ Code quality: {status} ({len(quality_issues)} issues in {len(python_files)} files)")
        
        return result
    
    def run_full_pipeline(self, auto_fix: bool = False) -> Dict[str, Any]:
        """Run the complete CI/CD pipeline."""
        print("🚀 Starting CI/CD Pipeline")
        print("=" * 50)
        
        # Step 1: Environment checks
        self.results['steps']['environment'] = self.run_environment_checks(auto_fix)
        
        # Step 2: Code quality
        self.results['steps']['code_quality'] = self.check_code_quality()
        
        # Step 3: Tests
        self.results['steps']['tests'] = self.run_tests()
        
        # Step 4: Development analysis (if log exists)
        if os.path.exists('dev_session.log'):
            self.results['steps']['dev_analysis'] = self.run_development_analysis()
        
        # Determine overall status
        failed_steps = [
            step for step, result in self.results['steps'].items() 
            if result.get('status') == 'failed'
        ]
        
        self.results['overall_status'] = 'failed' if failed_steps else 'passed'
        self.results['failed_steps'] = failed_steps
        
        print("\n" + "=" * 50)
        print(f"🎯 Pipeline Result: {self.results['overall_status'].upper()}")
        
        if failed_steps:
            print("❌ Failed steps:")
            for step in failed_steps:
                print(f"  - {step}")
        else:
            print("✅ All steps passed!")
        
        return self.results
    
    def save_results(self, output_file: str = 'ci_results.json'):
        """Save pipeline results to file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        return output_file


def main():
    parser = argparse.ArgumentParser(description='Run CI/CD Pipeline')
    parser.add_argument('--auto-fix', action='store_true', 
                      help='Automatically fix detected issues')
    parser.add_argument('--output', default='ci_results.json',
                      help='Output file for results')
    parser.add_argument('--step', choices=['env', 'tests', 'quality', 'analysis'],
                      help='Run only specific step')
    
    args = parser.parse_args()
    
    pipeline = CIPipeline()
    
    if args.step:
        # Run specific step
        if args.step == 'env':
            result = pipeline.run_environment_checks(args.auto_fix)
        elif args.step == 'tests':
            result = pipeline.run_tests()
        elif args.step == 'quality':
            result = pipeline.check_code_quality()
        elif args.step == 'analysis':
            result = pipeline.run_development_analysis()
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Run full pipeline; default to auto-fix when no flags provided
        auto_fix = args.auto_fix or True
        results = pipeline.run_full_pipeline(auto_fix)
        output_file = pipeline.save_results(args.output)
        
        print(f"\n📄 Results saved to: {output_file}")
        
        # Exit with appropriate code
        sys.exit(0 if results['overall_status'] == 'passed' else 1)


if __name__ == "__main__":
    main()