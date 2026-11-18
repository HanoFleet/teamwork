"""Verify sensitive response fields are removed without running historical network code."""
import ast
from pathlib import Path
import unittest

class RedactionContract(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('read_only_class_review.py')
        node = next(n for n in ast.parse(path.read_text(encoding='utf-8')).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'redact_response')
        namespace = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        self.redact = namespace['redact_response']

    def test_nested_secrets_removed(self):
        value = {'csrf_token':'synthetic-token','nested':[{'password':'synthetic-password','token':'synthetic-jwt'}]}
        output = self.redact(value)
        self.assertNotIn('synthetic', str(output))
        self.assertEqual(value['csrf_token'], 'synthetic-token')

    def test_nonsensitive_assertion_fields_preserved(self):
        value = {'status':404, 'class_id':2, 'logs':[{'result_status':'denied'}]}
        self.assertEqual(self.redact(value), value)

if __name__ == '__main__':
    unittest.main()
