"""Explicit Linux namespace integration; no model calls or credential copying."""
import json
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from agent_benchmark import execute,sandbox_command,clean_environment

class IsolationTests(unittest.TestCase):
    def test_hidden_grader_readonly_inputs_and_skills(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as tmp:
            root=Path(tmp);task=root/'run/base/1/task';(task/'inputs').mkdir(parents=True);(task/'.agents/skills').mkdir(parents=True)
            (task/'inputs/source.txt').write_text('original');(task/'.agents/skills/SKILL.md').write_text('guidance')
            auth=root/'private';auth.mkdir();(root/'grader-secret.txt').write_text('hidden')
            code="""import json,pathlib
p=pathlib.Path('/workspace/task');result={}
for name in ('inputs/source.txt','.agents/skills/SKILL.md'):
    try:(p/name).write_text('tampered');result[name]=False
    except OSError as exc:
        assert exc.errno in (13,30),exc
        result[name]=True
result['repo_hidden']=not pathlib.Path(REPO).exists()
result['grader_hidden']=not pathlib.Path(GRADER).exists()
(p/'result.json').write_text(json.dumps(result))
assert all(result.values()),result
""".replace('REPO',repr(str(ROOT/'skills.json'))).replace('GRADER',repr(str(root/'grader-secret.txt')))
            result=execute(sandbox_command(task,auth,[sys.executable,'-c',code],[root]),ROOT,root/'isolation',15,environment=clean_environment())
            self.assertEqual(result['returncode'],0,(root/'isolation.stderr').read_text())
            self.assertTrue(all(json.loads((task/'result.json').read_text()).values()))
            self.assertEqual((task/'inputs/source.txt').read_text(),'original')
            print('ISOLATION_OK',json.loads((task/'result.json').read_text()))
if __name__=='__main__':unittest.main()
