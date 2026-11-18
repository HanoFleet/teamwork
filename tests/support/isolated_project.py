"""Portable adaptation of the executed acceptance/run_online session wrappers.
Only generated test resources are removed. Existing credentials are never replaced.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]

def arguments(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--subnet', help='Optional unused Docker subnet; omitted uses daemon default')
    p.add_argument('--build-proxy', help='Optional download proxy for build args only')
    return p.parse_args()

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Project:
    def __init__(self, purpose, options):
        self.name = 'teamwork-tests-' + purpose + '-' + uuid.uuid4().hex[:8]
        self.options = options
        self.output = ROOT / 'tests' / 'output' / self.name
        self.runtime = ROOT / 'tests' / '.runtime' / self.name
        self.a = load('archive_acceptance', ROOT / 'scripts/acceptance.py')
        self.a.PROJECT = self.name
        self.a.ENV_FILE = self.runtime / 'generated.env'
        self.a.REPORT_DIR = self.output
        self.previous = {k: os.environ.get(k) for k in ['COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'COMPOSE_ENV_FILES']}

    def __enter__(self):
        existing = subprocess.check_output(['docker', 'ps', '-a', '--filter',
                    'label=com.docker.compose.project=' + self.name, '--format', '{{.ID}}'])
        if existing.strip():
            raise RuntimeError('Refusing to reuse an existing Compose project')
        self.runtime.mkdir(parents=True)
        self.output.mkdir(parents=True)
        os.environ['COMPOSE_PROJECT_NAME'] = self.name
        files = [str(ROOT / 'docker-compose.yml')]
        if self.options.subnet:
            import ipaddress
            ipaddress.ip_network(self.options.subnet, strict=True)
            overlay = self.runtime / 'network.yml'
            overlay.write_text('networks:\n  default:\n    ipam:\n      config:\n'
                               '        - subnet: ' + self.options.subnet + '\n', encoding='utf-8')
            files.append(str(overlay))
        os.environ['COMPOSE_FILE'] = os.pathsep.join(files)
        original = self.a.compose
        def compose(*args, **kwargs):
            if args and args[0] == 'build' and self.options.build_proxy:
                args = (*args, '--build-arg', 'HTTP_PROXY=' + self.options.build_proxy,
                        '--build-arg', 'HTTPS_PROXY=' + self.options.build_proxy)
            return original(*args, **kwargs)
        self.a.compose = compose
        self.a.write_env()
        os.environ['COMPOSE_ENV_FILES'] = str(self.a.ENV_FILE)
        self.env = dict(line.split('=', 1) for line in self.a.ENV_FILE.read_text().splitlines() if '=' in line)
        return self

    def start(self):
        self.a.compose('build', timeout=600)
        self.a.compose('up', '-d', '--wait', timeout=300)

    def verifier(self):
        path = ROOT / 'scripts/verify.py'
        source = path.read_text(encoding='utf-8')
        if source.count('ENV = load_env()') != 1:
            raise RuntimeError('verify.py loader changed; review the adapter')
        v = types.ModuleType('archive_verifier')
        v.__dict__.update(__file__=str(path), _ARCHIVE_ENV=self.env)
        exec(compile(source.replace('ENV = load_env()', 'ENV = _ARCHIVE_ENV'), str(path), 'exec'), v.__dict__)
        v.write_doc = lambda: (self.output / 'verification.md').write_text('\n'.join(v.LINES)+'\n', encoding='utf-8')
        original = v.compose
        def compose(*args, **kwargs):
            if args and args[0] == 'exec' and 'rabbitmq' in args:
                for _ in range(60):
                    ready = original('exec', '-T', 'rabbitmq', 'rabbitmq-diagnostics', '-q', 'check_running', check=False)
                    if ready.returncode == 0:
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError('RabbitMQ app did not become ready within 60 probes')
            return original(*args, **kwargs)
        v.compose = compose
        return v

    def __exit__(self, *exc):
        try:
            self.a.cleanup()
        finally:
            self.a.ENV_FILE.unlink(missing_ok=True)
            for key, value in self.previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
