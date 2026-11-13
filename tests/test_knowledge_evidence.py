import copy,json,sys,tempfile
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from knowledge import load_catalog,search
from knowledge_evidence import snapshot,receipt_state

class ReceiptTests(unittest.TestCase):
    def test_freshness_binds_content_metadata_dependencies_tools_and_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'example';folder.mkdir()
            for name,text in [('guide.md','# Main'),('dep.md','# Dependency'),('suite.json','{}'),('tool.py','pass')]: (folder/name).write_text(text)
            def entry(ident,path):return dict(id=ident,title=ident,entry=path,kind='knowledge',tasks=['repair'],subjects=[],aliases=['repair'],applies_when=['test'],exclude_when=[],required_facts=[],requires=[],verification=[],conditions={},status='experimental')
            main=entry('example.main','guide.md');main['requires']=['example.dep'];main['tool_dependencies']=['tool.py']
            manifest={'schema_version':1,'entries':[main,entry('example.dep','dep.md')]}
            def save(): (folder/'knowledge.json').write_text(json.dumps(manifest))
            save();entries=load_catalog(Path(tmp));report=snapshot(entries,'example.main','suite.json',['tool.py'])
            report.update(verdict='passed',scope={'test':'unit'},checks={'fixture':True},reviewer='test-only')
            (folder/'receipt.json').write_text(json.dumps(report))
            main.update(status='validated',validated_for={'test':'unit'},evidence=['receipt.json']);save()
            self.assertEqual(load_catalog(Path(tmp))['example.main']['validation_state'],'fresh')
            for name in ('guide.md','dep.md','tool.py','suite.json'):
                path=folder/name;old=path.read_text();path.write_text(old+'\nchanged')
                entries=load_catalog(Path(tmp));self.assertTrue(entries['example.main']['validation_state'].startswith('stale'))
                self.assertEqual(search(entries,'example.main')[0]['status'],'experimental')
                path.write_text(old)
            main['aliases'].append('changed decision boundary');save()
            self.assertTrue(load_catalog(Path(tmp))['example.main']['validation_state'].startswith('stale'))
    def test_draft_receipt_cannot_validate(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'x';folder.mkdir();(folder/'guide.md').write_text('guide');(folder/'draft.json').write_text('{}')
            entry=dict(id='example.main',title='main',entry='guide.md',kind='knowledge',tasks=['repair'],subjects=[],aliases=[],applies_when=['test'],exclude_when=[],required_facts=[],requires=[],verification=[],status='validated',validated_for={'scope':'test'},evidence=['draft.json'])
            (folder/'knowledge.json').write_text(json.dumps({'schema_version':1,'entries':[entry]}))
            self.assertTrue(load_catalog(Path(tmp))['example.main']['validation_state'].startswith('stale'))

if __name__=='__main__':unittest.main()
