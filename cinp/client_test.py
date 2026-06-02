import pytest

from cinp.client import CInP, ResponseError, InvalidRequest, DetailedInvalidRequest, InvalidSession, NotAuthorized, NotFound, ServerError

# TODO: test timeout value  passthrough
# TODO: test setting proxy, also make sure the environment proxy settings are handdled correctly


class MockResponse():
  def __init__( self, code, header_map, data ):
    super().__init__()
    self.status = code
    self.headers = [ ( k.encode( 'ascii' ), v.encode( 'ascii' ) ) for k, v in header_map.items() ]
    self.content = data.encode( 'utf-8' )

  async def aclose( self ):
    pass


def test_constructor():
  CInP( 'http://localhost:8080', '/api/v1/', None )
  CInP( 'http://localhost', '/api/v1/', None )

  with pytest.raises( ValueError ):
    CInP( 'localhost', '/api/v1/', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost', '/api/v1', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost', 'api/v1', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost', 'api/v1/', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost/', '/api/v1/', None )

  with pytest.raises( ValueError ):
    CInP( 'localhost:8080', '/api/v1/', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost:8080', '/api/v1', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost:8080', 'api/v1', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost:8080', 'api/v1/', None )

  with pytest.raises( ValueError ):
    CInP( 'http://localhost:8080/', '/api/v1/', None )


def test_checkRequest():
  cinp = CInP( 'http://localhost', '/api/v1/', None )

  # describe
  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DESCRIBE', '/api/v/', None )

  cinp._checkRequest( 'DESCRIBE', '/api/v1/', None )
  cinp._checkRequest( 'DESCRIBE', '/api/v1/model', None )
  cinp._checkRequest( 'DESCRIBE', '/api/v1/ns/model', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DESCRIBE', '/api/v1/model:sadf:', None )

  cinp._checkRequest( 'DESCRIBE', '/api/v1/model(action)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DESCRIBE', '/api/v1/model:sadf:(action)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DESCRIBE', '/api/v1/model', 'sdf' )

  # get
  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/ns/', None )

  cinp._checkRequest( 'GET', '/api/v1/model:asdf:', None )
  cinp._checkRequest( 'GET', '/api/v1/model:adsf:ert:', None )
  cinp._checkRequest( 'GET', '/api/v1/ns/model:asdf:', None )
  cinp._checkRequest( 'GET', '/api/v1/ns/model:adsf:ert:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/:asdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/model:adsf', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/model:adsf:ert', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/model(sdf)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/model:ad:', {'sdf': 'sdf'} )

  # create
  cinp._checkRequest( 'CREATE', '/api/v1/model', { 'asdf': 'asdf' } )
  cinp._checkRequest( 'CREATE', '/api/v1/ns/model', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/ns/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/ns/model', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/ns/model:sdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/ns/model:sdf:234', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/model:sdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/model:sdf:234', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CREATE', '/api/v1/model(sdf)', None )

  # update
  cinp._checkRequest( 'UPDATE', '/api/v1/model:123:', { 'asdf': 'asdf' } )
  cinp._checkRequest( 'UPDATE', '/api/v1/ns/model:123:', { 'asdf': 'asdf' } )

  cinp._checkRequest( 'UPDATE', '/api/v1/model:asd:234:', { 'asdf': 'asdf' } )
  cinp._checkRequest( 'UPDATE', '/api/v1/ns/model:asd:123:', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/model:123:asd', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/ns/model:434:fsd', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/model:123:asd:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/ns/model:434:fsd:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/model', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/ns/model', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/ns/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/ns/model', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'UPDATE', '/api/v1/ns/model(sdf)', None )

  # delete
  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v1/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v1/ns/', None )

  cinp._checkRequest( 'DELETE', '/api/v1/model:asdf:', None )
  cinp._checkRequest( 'DELETE', '/api/v1/model:adsf:ert:', None )
  cinp._checkRequest( 'DELETE', '/api/v1/ns/model:asdf:', None )
  cinp._checkRequest( 'DELETE', '/api/v1/ns/model:adsf:ert:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v1/:asdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v1/model:adsf', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v1/model:adsf:ert', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v1/model(dsf)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'DELETE', '/api/v1/model:sdf:', {'sdf': 2} )

  # list
  cinp._checkRequest( 'LIST', '/api/v1/model', { 'asdf': 'asdf' } )
  cinp._checkRequest( 'LIST', '/api/v1/ns/model', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v1/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v1/ns/', None )

  cinp._checkRequest( 'LIST', '/api/v1/model', None )
  cinp._checkRequest( 'LIST', '/api/v1/ns/model', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v1/ns/model:sdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v1/ns/model:sdf:234', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v1/model:sdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v1/model:sdf:234', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'LIST', '/api/v1/model(sdf)', None )

  # call
  cinp._checkRequest( 'CALL', '/api/v1/model(act)', { 'asdf': 'asdf' } )
  cinp._checkRequest( 'CALL', '/api/v1/ns/model(act)', { 'asdf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/ns/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v/(act)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/(act)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/ns/(act)', None )

  cinp._checkRequest( 'CALL', '/api/v1/model(act)', None )
  cinp._checkRequest( 'CALL', '/api/v1/ns/model(act)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/ns/model:sdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/ns/model:sdf:234', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/model:sdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/model:sdf:234', None )

  cinp._checkRequest( 'CALL', '/api/v1/model:sdf:(act)', None )
  cinp._checkRequest( 'CALL', '/api/v1/ns/model:wer:(act)', None )
  cinp._checkRequest( 'CALL', '/api/v1/model:sdf:234:(act)', None )
  cinp._checkRequest( 'CALL', '/api/v1/ns/model:wer:erf:(act)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'CALL', '/api/v1/ns/model:sdf:234(act)', None )

  # bogus
  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/ns/', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/ns/model', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/ns/model', { 'adsf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/ns/model:sdf:', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/ns/model:sdf:asdf', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/ns/model(sdf)', None )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'ASDF', '/api/v1/ns/model', { 'adsf': 'asdf' } )

  with pytest.raises( InvalidRequest ):
    cinp._checkRequest( 'GET', '/api/v1/ns/model:sdf:asdf', 'stuff' )


@pytest.mark.asyncio
async def test_request( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, {}, '' )

    with pytest.raises( InvalidRequest ):
      await cinp._request( 'GET', '//api/v1/model')

    mocked_open.reset_mock()
    ( code, data, header_map ) = await cinp._request( 'GET', '/api/v1/model:123:' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert code == 200
    assert data is None
    assert header_map == {}

    mocked_open.reset_mock()
    ( code, data, header_map ) = await cinp._request( 'UPDATE', '/api/v1/model:123:', data={ 'myval': 234 } )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{"myval": 234}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'UPDATE'
    assert code == 200
    assert data is None
    assert header_map == {}

    mocked_open.reset_mock()
    ( code, data, header_map ) = await cinp._request( 'LIST', '/api/v1/model', data={ 'myval': 'me' }, header_map={ 'Pos': '123' } )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{"myval": "me"}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Pos', b'123'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'LIST'
    assert code == 200
    assert data is None
    assert header_map == {}

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, 'not JSON' )
    with pytest.raises( ResponseError ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 400, {}, '{}' )
    with pytest.raises( InvalidRequest ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 400, {}, 'not JSON' )
    with pytest.raises( InvalidRequest ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 400, {}, '{ "message": "this is a test" }' )
    with pytest.raises( DetailedInvalidRequest ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 401, {}, '{}' )
    with pytest.raises( InvalidSession ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 403, {}, '{}' )
    with pytest.raises( NotAuthorized ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 404, {}, '{}' )
    with pytest.raises( NotFound ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 500, {}, '{}' )
    with pytest.raises( ServerError ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 500, {}, 'not JSON' )
    with pytest.raises( ServerError ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 402, {}, 'not JSON' )
    with pytest.raises( ResponseError ):
      await cinp._request( 'GET', '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '{"My thing": "the value"}' )
    ( code, data, header_map ) = await cinp._request( 'GET', '/api/v1/model:123:' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert code == 200
    assert data == { 'My thing': 'the value' }
    assert header_map == {}

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {"Type": "model"}, '' )
    ( code, data, header_map ) = await cinp._request( 'GET', '/api/v1/model:123:' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert code == 200
    assert data is None
    assert header_map == { "Type": "model" }

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {"other": "model"}, '' )
    ( code, data, header_map ) = await cinp._request( 'GET', '/api/v1/model:123:' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert code == 200
    assert data is None
    assert header_map == {}

  async with CInP( 'http://bob.com:70', '/theapi/', 'http://proxy:3128/' ) as cinp2:
    mocked_open2 = mocker.patch.object( cinp2.connection_pool, 'request' )
    mocked_open2.return_value = MockResponse( 200, {}, '' )
    ( code, data, header_map ) = await cinp2._request( 'GET', '/theapi/model:123:' )
    ( method, full_url ) = mocked_open2.call_args.args
    assert full_url == 'http://bob.com:70/theapi/model:123:'
    assert mocked_open2.call_args.kwargs[ 'content' ] == b''
    assert mocked_open2.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert code == 200
    assert data is None
    assert header_map == {}

  async with CInP( 'http://asdf.com', '/theapi/', 'http://proxy:3128/' ) as cinp3:
    mocked_open3 = mocker.patch.object( cinp3.connection_pool, 'request' )
    mocked_open3.return_value = MockResponse( 200, {}, '' )
    ( code, data, header_map ) = await cinp3._request( 'GET', '/theapi/model:123:' )
    ( method, full_url ) = mocked_open3.call_args.args
    assert full_url == 'http://asdf.com/theapi/model:123:'
    assert mocked_open3.call_args.kwargs[ 'content' ] == b''
    assert mocked_open3.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert code == 200
    assert data is None
    assert header_map == {}


@pytest.mark.asyncio
async def test_get( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, {}, '{"key": "value", "thing": "stuff"}' )

    with pytest.raises( InvalidRequest ):
      await cinp.get( '/api/v1/' )

    with pytest.raises( InvalidRequest ):
      await cinp.get( '/api/v1/model' )

    mocked_open.reset_mock()
    rec_values = await cinp.get( '/api/v1/model:123:' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert rec_values == { 'key': 'value', 'thing': 'stuff' }

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 201, {}, '{"key": "value", "thing": "stuff"}' )
    with pytest.raises( ResponseError ):
      await cinp.get( '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '"hi mom"' )
    with pytest.raises( ResponseError ):
      await cinp.get( '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 404, {}, '{"key": "value", "thing": "stuff"}' )
    with pytest.raises( NotFound ):
      await cinp.get( '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '{"key": "value", "thing": "stuff"}' )
    rec_values = await cinp.get( '/api/v1/model:123:', force_multi_mode=True )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Multi-Object', b'True'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    assert rec_values == { 'key': 'value', 'thing': 'stuff' }


@pytest.mark.asyncio
async def test_list( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, { 'Position': '0', 'Count': '2', 'Total': '20' }, '["/api/v1/model:123:","/api/v1/model:124:"]' )

    with pytest.raises( InvalidRequest ):
      await cinp.list( '/api/v1/' )

    with pytest.raises( InvalidRequest ):
      await cinp.list( '/api/v1/model:asdf:' )

    mocked_open.reset_mock()
    ( items, count_map ) = await cinp.list( '/api/v1/model' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Position', b'0'), (b'Count', b'10'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'LIST'
    assert items == [ '/api/v1/model:123:', '/api/v1/model:124:' ]
    assert count_map == { 'position': 0, 'count': 2, 'total': 20 }

    mocked_open.reset_mock()
    ( items, count_map ) = await cinp.list( '/api/v1/model', count=5, position=20 )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Position', b'20'), (b'Count', b'5'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'LIST'
    assert items == [ '/api/v1/model:123:', '/api/v1/model:124:' ]
    assert count_map == { 'position': 0, 'count': 2, 'total': 20 }

    mocked_open.reset_mock()
    ( items, count_map ) = await cinp.list( '/api/v1/model', filter_name='alpha', filter_value_map={ 'sort_by': 'age' } )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{"sort_by": "age"}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Position', b'0'), (b'Count', b'10'), (b'Filter', b'alpha'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'LIST'
    assert items == [ '/api/v1/model:123:', '/api/v1/model:124:' ]
    assert count_map == { 'position': 0, 'count': 2, 'total': 20 }

    with pytest.raises( InvalidRequest ):
      await cinp.list( '/api/v1/', filter_value_map='asdf' )

    with pytest.raises( InvalidRequest ):
      await cinp.list( '/api/v1/', position=-1 )

    with pytest.raises( InvalidRequest ):
      await cinp.list( '/api/v1/', count=-1 )

    with pytest.raises( InvalidRequest ):
      await cinp.list( '/api/v1/', position='adf' )

    with pytest.raises( InvalidRequest ):
      await cinp.list( '/api/v1/', count='asdf' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 201, { 'Position': '0', 'Count': '2', 'Total': '20' }, '["/api/v1/model:123:","/api/v1/model:124:"]' )
    with pytest.raises( ResponseError ):
      await cinp.list( '/api/v1/model' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, { 'Position': '0', 'Count': '2', 'Total': '20' }, '"adsf"' )
    with pytest.raises( ResponseError ):
      await cinp.list( '/api/v1/model' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, { 'Position': '0', 'Count': '2', 'Total': '20' }, '{"adsf":"sdf"}' )
    with pytest.raises( ResponseError ):
      await cinp.list( '/api/v1/model' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '["/api/v1/model:123:","/api/v1/model:124:"]' )
    ( items, count_map ) = await cinp.list( '/api/v1/model' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Position', b'0'), (b'Count', b'10'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'LIST'
    assert items == [ '/api/v1/model:123:', '/api/v1/model:124:' ]
    assert count_map == { 'position': 0, 'count': 0, 'total': 0 }

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, { 'Position': 'a', 'Count': 'b', 'Total': 'c' }, '["/api/v1/model:123:","/api/v1/model:124:"]' )
    ( items, count_map ) = await cinp.list( '/api/v1/model' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Position', b'0'), (b'Count', b'10'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'LIST'
    assert items == [ '/api/v1/model:123:', '/api/v1/model:124:' ]
    assert count_map == { 'position': 0, 'count': 0, 'total': 0 }


@pytest.mark.asyncio
async def test_create( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 201, { 'Object-Id': 'test' }, '{"asdf": "erere"}' )

    with pytest.raises( InvalidRequest ):
      await cinp.create( '/api/v1/', { 'asdf': 'xcv' } )

    with pytest.raises( InvalidRequest ):
      await cinp.create( '/api/v1/model:adsf:', { 'asdf': 'xcv' } )

    with pytest.raises( InvalidRequest ):
      await cinp.create( '/api/v1/model', 'adsf' )

    mocked_open.reset_mock()
    rec_values = await cinp.create( '/api/v1/model', {} )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CREATE'
    assert rec_values == ( 'test', { 'asdf': 'erere' } )

    mocked_open.reset_mock()
    rec_values = await cinp.create( '/api/v1/model', { 'asdf': 'xcv' } )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{"asdf": "xcv"}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CREATE'
    assert rec_values == ( 'test', { 'asdf': 'erere' } )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '"/api/v1/model:123:"' )
    with pytest.raises( ResponseError ):
      await cinp.create( '/api/v1/model', { 'asdf': 'xcv' } )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 201, {}, '["/api/v1/model:123:"]' )
    with pytest.raises( ResponseError ):
      await cinp.create( '/api/v1/model', { 'asdf': 'xcv' } )

    mocked_open.return_value = MockResponse( 200, {}, '{ "hi": "there"}' )
    with pytest.raises( ResponseError ):
      await cinp.create( '/api/v1/model', { 'asdf': 'xcv' } )


@pytest.mark.asyncio
async def test_update( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, {}, '{"hi": "there"}' )

    with pytest.raises( InvalidRequest ):
      await cinp.update( '/api/v1/', { 'asdf': 'xcv' } )

    with pytest.raises( InvalidRequest ):
      await cinp.update( '/api/v1/model', 'adsf' )

    with pytest.raises( InvalidRequest ):
      await cinp.update( '/api/v1/model', { 'asdf': 'xcv' } )

    mocked_open.reset_mock()
    rec_values = await cinp.update( '/api/v1/model:asdf:', { 'asdf': 'xcv' } )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:asdf:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{"asdf": "xcv"}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'UPDATE'
    assert rec_values == { 'hi': 'there' }

    mocked_open.reset_mock()
    rec_values = await cinp.update( '/api/v1/model:asdf:123:', { 'asdf': 'xcv' } )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:asdf:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{"asdf": "xcv"}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'UPDATE'
    assert rec_values == { 'hi': 'there' }

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '"/api/v1/model:123:"' )
    with pytest.raises( ResponseError ):
      await cinp.update( '/api/v1/model:123:', { 'asdf': 'xcv' } )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '["/api/v1/model:123:"]' )
    with pytest.raises( ResponseError ):
      await cinp.update( '/api/v1/model:123:', { 'asdf': 'xcv' } )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 201, {}, '{ "hi": "there"}' )
    with pytest.raises( ResponseError ):
      await cinp.update( '/api/v1/model:123:', { 'asdf': 'xcv' } )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 404, {}, '{"hi": "there"}' )
    with pytest.raises( NotFound ):
      await cinp.update( '/api/v1/model:123:', { 'asdf': 'xcv' } )


@pytest.mark.asyncio
async def test_delete( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, {}, '{}' )

    with pytest.raises( InvalidRequest ):
      await cinp.delete( '/api/v1/' )

    with pytest.raises( InvalidRequest ):
      await cinp.delete( '/api/v1/model' )

    mocked_open.reset_mock()
    result = await cinp.delete( '/api/v1/model:123:' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'DELETE'
    assert result is True

    mocked_open.reset_mock()
    result = await cinp.delete( '/api/v1/model:123:asdf:' )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:123:asdf:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'DELETE'
    assert result is True

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 201, {}, '{}' )
    with pytest.raises( ResponseError ):
      await cinp.delete( '/api/v1/model:123:' )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 404, {}, '{}' )
    with pytest.raises( NotFound ):
      await cinp.delete( '/api/v1/model:123:' )


@pytest.mark.asyncio
async def test_call( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, {}, '{}' )

    with pytest.raises( InvalidRequest ):
      await cinp.call( '/api/v1/', {} )

    with pytest.raises( InvalidRequest ):
      await cinp.call( '/api/v1/model', {} )

    with pytest.raises( InvalidRequest ):
      await cinp.call( '/api/v1/model:dfs:', {} )

    with pytest.raises( InvalidRequest ):
      await cinp.call( '/api/v1/model(adsf)', 'sdf' )

    mocked_open.reset_mock()
    return_value = await cinp.call( '/api/v1/model(myfunc)', {} )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model(myfunc)'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CALL'
    assert return_value == {}

    mocked_open.reset_mock()
    return_value = await cinp.call( '/api/v1/model:234:(myfunc)', {} )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:234:(myfunc)'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CALL'
    assert return_value == {}

    mocked_open.reset_mock()
    return_value = await cinp.call( '/api/v1/model:234:sdf:(myfunc)', {} )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model:234:sdf:(myfunc)'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CALL'
    assert return_value == {}

    mocked_open.reset_mock()
    return_value = await cinp.call( '/api/v1/model(myfunc)', { 'arg1': 12 } )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model(myfunc)'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{"arg1": 12}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CALL'
    assert return_value == {}

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '"The Value"' )
    return_value = await cinp.call( '/api/v1/model(myfunc)', {} )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model(myfunc)'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CALL'
    assert return_value == 'The Value'

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 200, {}, '{ "stuff": "nice"}' )
    return_value = await cinp.call( '/api/v1/model(myfunc)', {} )
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model(myfunc)'
    assert mocked_open.call_args.kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'CALL'
    assert return_value == { 'stuff': 'nice' }

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 404, {}, '' )
    with pytest.raises( NotFound ):
      await cinp.call( '/api/v1/model:123:(myfunc)', {} )

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 201, {}, '' )
    with pytest.raises( ResponseError ):
      await cinp.call( '/api/v1/model(myfunc)', {} )


@pytest.mark.asyncio
async def test_describe( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, {}, '' )

    with pytest.raises( InvalidRequest ):
      await cinp.describe( '/api/v1/model:sdf:' )

    mocked_open.return_value = MockResponse( 200, {'Type': 'Namespace'}, '' )
    mocked_open.reset_mock()
    data, type = await cinp.describe( '/api/v1/' )
    assert type == 'Namespace'
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'DESCRIBE'
    assert data is None

    mocked_open.return_value = MockResponse( 200, {'Type': 'Model'}, '' )
    mocked_open.reset_mock()
    data, type = await cinp.describe( '/api/v1/model' )
    assert type == 'Model'
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'DESCRIBE'
    assert data is None

    mocked_open.return_value = MockResponse( 200, {'Type': 'Action'}, '' )
    mocked_open.reset_mock()
    data, type = await cinp.describe( '/api/v1/model(sdf)' )
    assert type == 'Action'
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/model(sdf)'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'DESCRIBE'
    assert data is None

    mocked_open.reset_mock()
    mocked_open.return_value = MockResponse( 201, {}, '' )
    with pytest.raises( ResponseError ):
      await cinp.describe( '/api/v1/model' )


@pytest.mark.asyncio
async def test_setauth():
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    cinp.setAuth( 'user', 'token' )
    cinp.setAuth()


@pytest.mark.asyncio
async def test_get_multi( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.return_value = MockResponse( 200, {}, '{"/api/v1/ns/model:asd:":{"key1":"value1"},"/api/v1/ns/model:efe:":{"key2":"value2"}}' )

    mocked_open.reset_mock()
    gen = cinp.getMulti( '/api/v1/ns/model:asd:efe:' )
    assert mocked_open.call_args is None
    assert sorted( [ item async for item in gen ] ) == sorted( [ ( '/api/v1/ns/model:asd:', { 'key1': 'value1' } ), ( '/api/v1/ns/model:efe:', { 'key2': 'value2' } ) ] )
    assert mocked_open.call_count == 1
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/ns/model:asd:efe:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Multi-Object', b'True'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'

    mocked_open.reset_mock()
    gen = cinp.getMulti( '/api/v1/ns/model', [ 'asd', 'efe' ] )
    assert mocked_open.call_args is None
    assert sorted( [ item async for item in gen ] ) == sorted( [ ( '/api/v1/ns/model:asd:', { 'key1': 'value1' } ), ( '/api/v1/ns/model:efe:', { 'key2': 'value2' } ) ] )
    assert mocked_open.call_count == 1
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/ns/model:asd:efe:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Multi-Object', b'True'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'

    mocked_open.reset_mock()
    gen = cinp.getMulti( '/api/v1/ns/model:123:', [ 'asd', 'efe' ] )
    assert mocked_open.call_args is None
    assert sorted( [ item async for item in gen ] ) == sorted( [ ( '/api/v1/ns/model:asd:', { 'key1': 'value1' } ), ( '/api/v1/ns/model:efe:', { 'key2': 'value2' } ) ] )
    assert mocked_open.call_count == 1
    ( method, full_url ) = mocked_open.call_args.args
    assert full_url == 'http://localhost:8080/api/v1/ns/model:asd:efe:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Multi-Object', b'True'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'

    mocked_open.reset_mock()
    gen = cinp.getMulti( '/api/v1/ns/model', [ 'asd', 'efe', 'qwe', '123' ], chunk_size=2 )
    assert mocked_open.call_args is None
    assert sorted( [ item async for item in gen ] ) == sorted( [ ( '/api/v1/ns/model:asd:', { 'key1': 'value1' } ), ( '/api/v1/ns/model:efe:', { 'key2': 'value2' } ), ( '/api/v1/ns/model:asd:', { 'key1': 'value1' } ), ( '/api/v1/ns/model:efe:', { 'key2': 'value2' } ) ] )
    assert mocked_open.call_count == 2
    ( method, full_url ) = mocked_open.call_args_list[0].args
    assert full_url == 'http://localhost:8080/api/v1/ns/model:asd:efe:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Multi-Object', b'True'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'
    ( method, full_url ) = mocked_open.call_args_list[1].args
    assert full_url == 'http://localhost:8080/api/v1/ns/model:qwe:123:'
    assert mocked_open.call_args.kwargs[ 'content' ] == b''
    assert mocked_open.call_args.kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Multi-Object', b'True'), (b'Content-Type', b'application/json;charset=utf-8')]
    assert method == 'GET'


@pytest.mark.asyncio
async def test_get_filtered_objects( mocker ):
  async with CInP( 'http://localhost:8080', '/api/v1/', None ) as cinp:
    mocked_open = mocker.patch.object( cinp.connection_pool, 'request' )
    mocked_open.side_effect = [
      MockResponse( 200, { 'Position': '0', 'Count': '2', 'Total': '2' }, '["/api/v1/ns/model:asd:","/api/v1/ns/model:efe:"]' ),
      MockResponse( 200, {}, '{"/api/v1/ns/model:asd:":{"key1":"value1"},"/api/v1/ns/model:efe:":{"key2":"value2"}}' ),
    ]

    result = sorted( [ item async for item in cinp.getFilteredObjects( '/api/v1/ns/model' ) ] )

    assert result == sorted( [ ( '/api/v1/ns/model:asd:', { 'key1': 'value1' } ), ( '/api/v1/ns/model:efe:', { 'key2': 'value2' } ) ] )
    assert mocked_open.call_count == 2

    ( method, full_url ) = mocked_open.call_args_list[0].args
    assert method == 'LIST'
    assert full_url == 'http://localhost:8080/api/v1/ns/model'
    assert mocked_open.call_args_list[0].kwargs[ 'content' ] == b'{}'
    assert mocked_open.call_args_list[0].kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Position', b'0'), (b'Count', b'100'), (b'Content-Type', b'application/json;charset=utf-8')]

    ( method, full_url ) = mocked_open.call_args_list[1].args
    assert method == 'GET'
    assert full_url == 'http://localhost:8080/api/v1/ns/model:asd:efe:'
    assert mocked_open.call_args_list[1].kwargs[ 'content' ] == b''
    assert mocked_open.call_args_list[1].kwargs[ 'headers' ] == [(b'User-Agent', b'python CInP client 2.0.0'), (b'Accepts', b'application/json'), (b'Accept-Charset', b'utf-8'), (b'CInP-Version', b'2.0'), (b'Multi-Object', b'True'), (b'Content-Type', b'application/json;charset=utf-8')]
