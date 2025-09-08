from tests.database import DatabaseCase
import unittest, os, uuid
from supplier_case.store import Store
from supplier_case.domain import DomainError
@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires isolated PostgreSQL')
class TaskStore(DatabaseCase):
 def setUp(self):
  self.s=Store(os.environ['DATABASE_URL']);self.s.migrate();self.message=uuid.uuid4().hex
 def test_tasks_remain_available_after_store_reconstruction(self):
  task=self.s.create_task('document','coordinator',self.message,'ctx',{'x':1})
  new=Store(os.environ['DATABASE_URL'])
  self.assertEqual(new.get_task(task['id'],'document')['id'],task['id'])
  with self.assertRaises(DomainError):new.get_task(task['id'],'catalog')
