"""Run unchanged verify.py: business, failure recovery, async and security cases."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'support'))
from isolated_project import Project, arguments

def main():
    with Project('business', arguments(__doc__)) as project:
        project.start()
        v = project.verifier()
        try:
            v.main()
        finally:
            v.write_doc()
        print('Output:', project.output)
    return 0

if __name__ == '__main__':
    sys.exit(main())
