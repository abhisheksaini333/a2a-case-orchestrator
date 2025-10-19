import json,unittest
from pathlib import Path
from jsonschema import Draft7Validator
from supplier_case.protocol import agent_card,task,stream_frames
class Profiles(unittest.TestCase):
 def test_cards_and_events_conform_to_pinned_v02_and_v03_schemas(self):
  for profile in ['0.2.0','0.3.0']:
   schema=json.loads((Path(__file__).parents[1]/'contracts'/('v'+profile+'.json')).read_text())
   def validate(name,value):Draft7Validator({**schema,'$ref':'#/definitions/'+name}).validate(value)
   card=agent_card('document','http://localhost/a2a','document-check',profile);validate('AgentCard',card)
   result=task('t1','c1','completed',artifacts=[{'artifactId':'a1','parts':[{'kind':'data','data':{'valid':True}}]}]);validate('Task',result)
   frames=[json.loads(s.split('data: ',1)[1])['result'] for s in stream_frames(1,result)]
   validate('TaskArtifactUpdateEvent',frames[1]);validate('TaskStatusUpdateEvent',frames[-1])
