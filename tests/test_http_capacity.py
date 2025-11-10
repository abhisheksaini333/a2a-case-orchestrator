import socket,threading,time,unittest,urllib.request
from supplier_case.transport import server
class Capacity(unittest.TestCase):
 def test_partial_headers_expire_and_excess_connections_are_rejected(self):
  http=server(type('Service',(),{'name':'document'})(),{},max_connections=2,request_deadline=.3)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();clients=[]
  try:
   for _ in range(2):
    client=socket.create_connection(http.server_address);client.sendall(b'GET /health HTTP/1.1\r\nHost: localhost\r\nX-Slow: ');clients.append(client)
   time.sleep(.05)
   third=socket.create_connection(http.server_address);third.settimeout(1);third.sendall(b'GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n');self.assertIn(b'503',third.recv(1024));third.close()
   time.sleep(.4)
   for client in clients:client.settimeout(1);self.assertEqual(client.recv(100),b'')
   with urllib.request.urlopen('http://127.0.0.1:'+str(http.server_port)+'/health') as r:self.assertEqual(r.status,200)
  finally:
   for client in clients:client.close()
   http.shutdown();http.server_close();thread.join()
 def test_incomplete_body_expires_and_duplicate_length_is_rejected(self):
  http=server(type('Service',(),{'name':'document'})(),{'coordinator':'t'*32},request_deadline=.2)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   client=socket.create_connection(http.server_address);client.settimeout(1)
   client.sendall(b'POST /a2a HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nAuthorization: Bearer '+b't'*32+b'\r\nContent-Length: 100\r\n\r\n{')
   time.sleep(.3);self.assertEqual(client.recv(100),b'');client.close()
   client=socket.create_connection(http.server_address);client.settimeout(1)
   client.sendall(b'POST /a2a HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\n{}')
   self.assertIn(b'400',client.recv(1024));client.close()
  finally:http.shutdown();http.server_close();thread.join()
