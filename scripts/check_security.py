"""Small explicit source guardrails; complements, does not replace, security review."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
failures = []
paths = list((root / 'backend').glob('*.py')) + list((root / 'src').glob('*.ts*')) + list((root / 'infra').glob('*.tf'))
for path in paths:
    text = path.read_text(encoding='utf-8')
    if re.search(r'AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text): failures.append(str(path) + ': credential-like material')
    if 'dangerouslySetInnerHTML' in text: failures.append(str(path) + ': unsafe HTML sink')
    if path.parent.name == 'backend' and re.search(r'\.((terminate_instances)|(delete_user)|(authorize_security_group_ingress))\(', text): failures.append(str(path) + ': destructive response API')
if failures: raise SystemExit('\n'.join(failures))
print(f'PASS: checked {len(paths)} source files for credential patterns, unsafe HTML and destructive response APIs')
