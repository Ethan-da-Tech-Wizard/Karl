import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.insert(0, '.')

from core.prompt_templates import get_template, list_templates
from core.workflows import get_workflow, list_workflows
from eval.graders import run_grader

# Template substitution
tpl = get_template('json_extractor', rag_context='test context', schema='{}')
assert 'test context' in tpl, 'template substitution failed'
print('OK  prompt_templates.get_template')

# Workflow lookup
wf = get_workflow('document_extractor')
assert wf['template'] == 'json_extractor', f"wrong template: {wf['template']}"
wf2 = get_workflow('grounded_answer')
assert wf2['eval_grader'] == 'groundedness'
print('OK  workflows.get_workflow')

# List functions
templates = list_templates()
assert 'json_extractor' in templates
workflows = list_workflows()
assert any(n == 'code_review' for n, _ in workflows)
print('OK  list_templates / list_workflows')

# json_valid grader — valid JSON with required key
payload = json.dumps({"invoice_number": "INV-001"})
r = run_grader('json_valid', payload, schema_keys=['invoice_number'])
assert r['passed'], f"json_valid FAIL: {r}"
print('OK  graders.json_valid (pass case)')

# json_valid grader — missing key
r2 = run_grader('json_valid', payload, schema_keys=['invoice_number', 'total'])
assert not r2['passed'], "json_valid should FAIL on missing key"
print('OK  graders.json_valid (fail on missing key)')

# not_in_context grader
r3 = run_grader('not_in_context', 'NOT IN CONTEXT: no evidence found')
assert r3['passed'], f"not_in_context FAIL: {r3}"
r4 = run_grader('not_in_context', 'The answer is 42')
assert not r4['passed'], "not_in_context should FAIL on real answer"
print('OK  graders.not_in_context')

# keyword_hit grader
r5 = run_grader('keyword_hit', 'The price is 25 dollars', keywords=['25', 'price'])
assert r5['passed'], f"keyword_hit FAIL: {r5}"
r6 = run_grader('keyword_hit', 'The price is unknown', keywords=['25', 'price'])
assert not r6['passed'], f"keyword_hit should FAIL: {r6}"
print('OK  graders.keyword_hit')

# groundedness grader — NOT IN CONTEXT refusal
r7 = run_grader('groundedness', 'NOT IN CONTEXT: answer absent', context_chunks=['some doc text'])
assert r7['passed'], f"groundedness refusal FAIL: {r7}"
print('OK  graders.groundedness (refusal detection)')

print()
print('All smoke tests PASSED.')
