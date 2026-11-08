import httpx
from argilla._api._http._client import create_http_client

def test_default_transport_still_constructs_client():
 with create_http_client('http://localhost:6900','fixture-key',2,0) as client:
  assert client.headers['X-Argilla-Api-Key']=='fixture-key'
  assert str(client.base_url)=='http://localhost:6900'

def test_custom_transport_receives_auth_and_response():
 seen=[]
 def handle(request):
  seen.append((request.url.path,request.headers['X-Argilla-Api-Key']))
  return httpx.Response(200,json={'ok':True})
 transport=httpx.MockTransport(handle)
 with create_http_client('http://offline.invalid','fixture-key',2,0,transport=transport) as client:
  assert client.get('/contract').json()=={'ok':True}
 assert seen==[('/contract','fixture-key')]
