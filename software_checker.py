"""Simple software detection program.
Performs basic environment and repo checks helpful before development.
"""
import sys
import os
import json
import subprocess


def run_checks(auto_fix=False):
    """Run all environment checks and return the report dictionary.
    
    Args:
        auto_fix (bool): If True, attempt to automatically fix detected issues
    """
    report = {}
    fixes_applied = []

    # Check Python version
    report['python_version'] = sys.version
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        report['python_version_warning'] = 'Python 3.8+ recommended'

    # Check for venv
    report['venv_exists'] = os.path.isdir('.venv')
    
    # Check for requirements.txt and installed packages
    requirements_file = 'requirements.txt'
    report['requirements_exists'] = os.path.exists(requirements_file)
    
    if report['requirements_exists']:
        try:
            # Check if all requirements are installed
            with open(requirements_file, 'r', encoding='utf-8') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            missing_packages = []
            for req in requirements:
                pkg_name = req.split('==')[0].split('>=')[0].split('<=')[0].strip()
                try:
                    __import__(pkg_name.replace('-', '_'))
                except ImportError:
                    missing_packages.append(req)
            
            report['missing_packages'] = missing_packages
            
            # Auto-fix: Install missing packages
            if auto_fix and missing_packages:
                try:
                    cmd = [sys.executable, '-m', 'pip', 'install'] + missing_packages
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    fixes_applied.append(f"Installed packages: {', '.join(missing_packages)}")
                    report['missing_packages'] = []  # Clear after fixing
                except subprocess.CalledProcessError as e:
                    report['pip_install_error'] = str(e)
                    
        except Exception as e:
            report['requirements_check_error'] = str(e)

    # Check for required files in parent project (NeuroMuscleAI-MVP)
    parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NeuroMuscleAI-MVP'))
    report['parent_exists'] = os.path.isdir(parent)
    report['parent_files'] = []
    if report['parent_exists']:
        try:
            report['parent_files'] = os.listdir(parent)[:20]
        except Exception:
            report['parent_files'] = []

    # Check git status
    try:
        out = subprocess.check_output(['git', 'status', '--porcelain'], stderr=subprocess.STDOUT, universal_newlines=True)
        report['git_dirty'] = bool(out.strip())
        
        # Check for unpushed commits
        try:
            unpushed = subprocess.check_output(['git', 'log', '@{u}..HEAD', '--oneline'], 
                                             stderr=subprocess.STDOUT, universal_newlines=True)
            report['unpushed_commits'] = len(unpushed.strip().split('\n')) if unpushed.strip() else 0
        except subprocess.CalledProcessError:
            report['unpushed_commits'] = 'Unable to check (no upstream branch?)'
            
    except Exception as e:
        report['git_dirty'] = f'git error: {e}'

    # Check system resources
    try:
        import psutil
        report['system_resources'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': {path: psutil.disk_usage(path).percent for path in ['C:', 'E:'] if os.path.exists(path)}
        }
    except ImportError:
        report['system_resources'] = 'psutil not available'

    # Record fixes applied
    if fixes_applied:
        report['fixes_applied'] = fixes_applied
        
    return report


# For backward compatibility when run as script
if __name__ == "__main__":
    REPORT = run_checks()
    print(json.dumps(REPORT, indent=2, ensure_ascii=False))
