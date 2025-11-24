import os,sys,time,uuid,unittest,tempfile,subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tests.database import DatabaseCase
from supplier_case.store import Store
from supplier_case.domain import digest
@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires PostgreSQL')
class WorkerCrash(DatabaseCase):
 def setUp(self):
  self.store=Store(os.environ['DATABASE_URL']);self.store.migrate()
  self.case=self.store.create_case({'name':'Crash Tested','tax_id':'T-'+uuid.uuid4().hex[:8]},'operator',uuid.uuid4().hex)
  self.record={**self.case['input'],'category':'office','risk':'low'}
  self.store.update_case(self.case['id'],1,state='review',proposal=self.record,proposal_digest=digest(self.record));self.store.approve(self.case['id'],digest(self.record),'reviewer')
 def test_sigkill_between_supplier_insert_and_commit_recovers_one_record(self):
  with tempfile.TemporaryDirectory() as directory:
   marker=Path(directory)/'transaction-ready'
   code="import os,time;from pathlib import Path;from supplier_case.store import Store;Store(os.environ['DATABASE_URL']).deliver(before_commit=lambda:(Path(os.environ['MARKER']).touch(),time.sleep(30)))"
   child=subprocess.Popen([sys.executable,'-c',code],env={**os.environ,'MARKER':str(marker)},cwd=Path(__file__).resolve().parents[1])
   try:
    deadline=time.monotonic()+5
    while not marker.exists() and time.monotonic()<deadline:time.sleep(.02)
    self.assertTrue(marker.exists());child.kill();child.wait(timeout=3)
   finally:
    if child.poll() is None:child.kill();child.wait()
   self.assertFalse(any(x['case_id']==self.case['id'] for x in self.store.suppliers()))
   self.store.deliver();self.store.deliver()
   self.assertEqual(sum(x['case_id']==self.case['id'] for x in self.store.suppliers()),1)
 def test_parallel_workers_deliver_an_approved_command_once(self):
  with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(lambda _:self.store.deliver(),range(6)))
  self.assertEqual(sum(x['case_id']==self.case['id'] for x in self.store.suppliers()),1)
