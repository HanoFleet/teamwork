"""Execute the repository's unchanged 18-case acceptance suite in an owned project."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'support'))
from isolated_project import Project, arguments

def main():
    options = arguments(__doc__)
    with Project('acceptance', options) as project:
        a = project.a
        result = 1
        try:
            result = a.main()
        except Exception as error:
            a.CHECKS.append(dict(id='ENV', name='Archive validation environment',
                criterion='Build and start the tested source', status='failed', elapsed_ms=0,
                detail=type(error).__name__))
        finally:
            a.write_report()
        passed = bool(a.CHECKS) and all(c['status'] == 'passed' for c in a.CHECKS)
        print('Output:', project.output)
        return 0 if result == 0 and passed else 1

if __name__ == '__main__':
    sys.exit(main())
