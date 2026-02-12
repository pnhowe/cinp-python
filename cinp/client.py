import os
import json
import logging
import ssl
import math
import random
import asyncio
import httpcore
from datetime import datetime
from tempfile import NamedTemporaryFile

from cinp.common import URI

__CLIENT_VERSION__ = '1.4.0'
__CINP_VERSION__ = '1.0'

__all__ = [ 'Timeout', 'ResponseError', 'DetailedInvalidRequest',
            'InvalidRequest', 'InvalidSession', 'NotAuthorized',
            'NotFound', 'ServerError', 'CInP' ]

DELAY_MULTIPLIER = 15
# delay of 15 results in a delay of:
# min delay = 0, 10, 16, 20, 24, 26, 29, 31, 32, 34, 35, 37, 38, 39, 40 ....
# max delay = 0, 20, 32, 40, 48, 52, 58, 62, 64, 68, 70, 74, 76, 78, 80 .....


class Timeout( Exception ):
  pass


class ResponseError( Exception ):
  pass


class InvalidRequest( Exception ):
  pass


class DetailedInvalidRequest( InvalidRequest ):
  def __init__( self, data ):
    for name in ( 'exception', 'error', 'message' ):
      setattr( self, name, None )  # this makes sure it is at least set
      try:
        setattr( self, name, data[ name ] )
        del data[ name ]
      except KeyError:
        pass

    self.data = data
    super().__init__( self.message )


class InvalidSession( Exception ):
  pass


class NotAuthorized( Exception ):
  pass


class NotFound( Exception ):
  pass


class ServerError( Exception ):
  pass


class RetryableException( Exception ):
  def __init__( self, exception ):
    self.exception = exception


def _backOffDelay( count ):
  if count < 1:  # math.log dosen't do so well below 1
    count = 1

  factor = int( DELAY_MULTIPLIER * math.log( count ) )
  return int( factor + ( random.random() * factor ) )


def _headerMapToList( header_map ):
  return [ ( k.encode( 'ascii' ), v.encode( 'ascii' ) ) for k, v in header_map.items() ]


def _headerListToMap( header_list ):
  header_map = {}
  for ( k, v ) in header_list:
    header_map[ k.decode( 'ascii' ) ] = v.decode( 'ascii' )

  return header_map


class CInP():
  def __init__( self, host, root_path, proxy=None, verify_ssl=True, retry_event=None ):  # retry_event should be an Event Object, use to cancel retry loops, if the event get's set the retry loop will throw the most recent Exception it ignored
    super().__init__()
    if retry_event is not None:
      self.retry_event = retry_event
    else:
      self.retry_event = asyncio.Event()

    if not host.startswith( ( 'http:', 'https:' ) ):
      raise ValueError( 'hostname must start with http(s):' )

    if host[-1] == '/':
      raise ValueError( 'hostname must not end with "/"' )

    self.proxy = proxy
    self.host = host
    logging.debug( 'cinp: new client host: "{0}", root_path: "{1}", via: "{2}"'.format( self.host, root_path, self.proxy ) )

    self.uri = URI( root_path )

    if not verify_ssl:
      self.ssl_context = ssl._create_unverified_context()
    else:
      self.ssl_context = ssl.create_default_context()

    self.connection_pool = None

    self.header_list = _headerMapToList( {
                                            'User-Agent': 'python CInP client {0}'.format( __CLIENT_VERSION__ ),
                                            'Accepts': 'application/json',
                                            'Accept-Charset': 'utf-8',
                                            'CInP-Version': __CINP_VERSION__
                                          } )

    self.auth_header_list = []

  async def __aenter__( self ):
    # have a proxy option to take it from the envrionment vars
    if self.proxy:  # not doing 'is not None', so empty strings don't try and proxy
      proxy = httpcore.Proxy( self.proxy )
    else:
      proxy = None

    self.connection_pool = httpcore.AsyncConnectionPool( ssl_context=self.ssl_context )  # , proxy=proxy )  need a newer version of httpcore to support proxy, also make sure if we still need python3-anyio

    return self

  async def __aexit__( self, exc_type, exc_value, traceback ):
    await self.connection_pool.aclose()
    self.connection_pool = None

  def _checkRequest( self, verb, uri, data ):  # TODO: also check if verb is allowed to have headers ( other than the default ), also check to make sure they are valid heaaders
    logging.debug( 'cinp: check "{0}" to "{1}"'.format( verb, uri ) )

    if verb not in ( 'GET', 'LIST', 'UPDATE', 'CREATE', 'DELETE', 'CALL', 'DESCRIBE' ):
      raise InvalidRequest( 'Invalid Verb (HTTP Method) "{0}"'.format( verb ) )

    if data is not None and not isinstance( data, dict ):
      raise InvalidRequest( 'Data must be a dict' )

    try:
      ( _, model, action, id_list, _ ) = self.uri.split( uri )
    except ValueError as e:
      raise InvalidRequest( str( e ) )

    if id_list == []:
      id_list = None

    if action is not None and verb not in ( 'CALL', 'DESCRIBE' ):
      raise InvalidRequest( 'Invalid verb "{0}" for request with action'.format( verb ) )

    if verb in ( 'CALL', ) and action is None:
      raise InvalidRequest( 'Verb "{0}" requires action'.format( verb ) )

    if id_list is not None and verb not in ( 'GET', 'UPDATE', 'DELETE', 'CALL' ):
      raise InvalidRequest( 'Invalid verb "{0}" for request with id'.format( verb ) )

    if verb in ( 'GET', 'UPDATE', 'DELETE' ) and id_list is None:
      raise InvalidRequest( 'verb "{0}" requires id'.format( verb ) )

    if data is not None and verb not in ( 'LIST', 'UPDATE', 'CREATE', 'CALL' ):
      raise InvalidRequest( 'Invalid verb "{0}" for request with data'.format( verb ) )

    if verb in ( 'UPDATE', 'CREATE' ) and data is None:
      raise InvalidRequest( 'Verb "{0}" requires data'.format( verb ) )

    if verb in ( 'GET', 'LIST', 'UPDATE', 'CREATE', 'DELETE', 'CALL' ) and not model:
      raise InvalidRequest( 'Verb "{0}" requires model'.format( verb ) )

  async def _request( self, verb, uri, data=None, header_map=None, timeout=30, retry_count=0 ):
    if self.connection_pool is None:
      raise Exception( 'Connection pool is not initialized, make sure to use "async with CInP(...) as client:"' )

    last_exception = None
    for retry in range( 0, retry_count + 1 ):
      if retry > 0:
        logging.debug( 'cinp: retry "{0}" of "{1}" for request to "{2}"'.format( retry, retry_count, uri ) )
        if self.retry_event.is_set():
          raise last_exception

        try:
          await asyncio.wait_for( self.retry_event.wait(), _backOffDelay( retry ) )
        except asyncio.TimeoutError:
          pass
        else:
          logging.debug( 'cinp: request aborted' )
          raise Exception( 'Request Aborted' )

      try:
        return await self.__request( verb, uri, data, header_map, timeout )
      except RetryableException as e:
        logging.debug( 'cinp: got exception "{0}", retrying...'.format( e ) )
        last_exception = e.exception

    raise last_exception

  async def __request( self, verb, uri, data=None, header_map=None, timeout=30 ):
    logging.debug( 'cinp: making "{0}" request to "{1}"'.format( verb, uri ) )
    if header_map is None:
      header_map = {}

    if verb == 'UPLOAD':  # not a CINP verb, just using it to bypass some checking here in __request
      header_map[ 'Content-Type' ] = 'application/octet-stream'
      if not hasattr( data, 'read' ):
        raise InvalidRequest( 'data must be an readable stream' )
      verb = 'POST'  # not to be handled by CInP on the other end, but by a file upload handler

    elif verb == 'RAWGET':  # not a CINP verb, just using it to bypass some checking here in __request
      verb = 'GET'

    else:
      header_map[ 'Content-Type' ] = 'application/json;charset=utf-8'
      self._checkRequest( verb, uri, data )
      if data is None:
        data = ''.encode( 'utf-8' )
      else:
        data = json.dumps( data, default=JSONEncoder ).encode( 'utf-8' )

    header_list = self.header_list + self.auth_header_list + _headerMapToList( header_map )
    url = '{0}{1}'.format( self.host, uri )
    try:
      resp = await self.connection_pool.request( verb, url, content=data, headers=header_list, extensions={ 'timeout': { 'connect': timeout } } )
      http_code = resp.status
      if http_code not in ( 200, 201, 202, 400, 401, 403, 404, 500 ):
        raise ResponseError( 'HTTP code "{0}" unhandled'.format( http_code ) )

      logging.debug( 'cinp: got HTTP code "{0}"'.format( http_code ) )

      if http_code == 401:
        resp.close()
        logging.warning( 'cinp: Invalid Session' )
        raise InvalidSession()

      if http_code == 403:
        resp.close()
        logging.warning( 'cinp: Not Authorized' )
        raise NotAuthorized()

      if http_code == 404:
        resp.close()
        logging.warning( 'cinp: Not Found' )
        raise NotFound()

      buff = str( resp.content, 'utf-8' ).strip()
      if not buff:
        data = None
      else:
        try:
          data = json.loads( buff )
        except ValueError:
          data = None
          if http_code not in ( 400, 500 ):  # these two codes can deal with non dict data
            logging.warning( 'cinp: Unable to parse response "{0}"'.format( buff[ 0:200 ] ) )
            raise ResponseError( 'Unable to parse response "{0}"'.format( buff[ 0:200 ] ) )

        header_map = { k: v for k, v in _headerListToMap( resp.headers ).items() if k in ( 'Position', 'Count', 'Total', 'Type', 'Multi-Object', 'Object-Id', 'verb' ) }

    except httpcore.ProtocolError as e:
      raise Exception( ResponseError( 'ProtocolError "{0}"'.format( e ) ) )

    except httpcore.ProxyError as e:
      raise Exception( ResponseError( 'ProxyError "{0}" for "{1}" via "{2}"'.format( e, url, self.proxy ) ) )

    except httpcore.NetworkError as e:
      raise RetryableException( ResponseError( 'NetworkError "{0}"'.format( e ) ) )

    except httpcore.TimeoutException:
      raise RetryableException( Timeout( 'Request Timeout after {0} seconds'.format( timeout ) ) )

    if http_code == 400:
      try:
        data[ 'message' ]
        e = DetailedInvalidRequest( data )
      except ( KeyError, ValueError, TypeError ):
        e = InvalidRequest( buff[ 0:200 ] )

      logging.warning( 'cinp: Invalid Request "{0}"'.format( e.args[0] ) )
      raise e

    if http_code == 500:
      if isinstance( data, dict ):
        try:
          message = 'Server Error "{0}"\n{1}'.format( data[ 'message' ], data[ 'trace' ] )
        except KeyError:
          try:
            message = 'Server Error "{0}"'.format( data[ 'message' ] )
          except KeyError:
            message = data

      else:
        message = 'Server Error: "{0}"'.format( buff[ 0:200 ] )

      logging.error( 'cinp: {0}'.format( message ) )
      raise ServerError( message )

    return ( http_code, data, header_map )

  def setAuth( self, auth_id=None, auth_token=None ):
    """
    Sets the Authencation id and token headers, call with out paramaters to remove the headers.
    """
    logging.debug( 'cinp: removing auth info' )
    self.auth_header_list = []

    if auth_id:
      logging.debug( 'cinp: setting auth info, id "{0}"'.format( auth_id ) )
      self.auth_header_list = _headerMapToList( { 'Auth-Id': auth_id, 'Auth-Token': auth_token } )

  async def describe( self, uri, timeout=30, retry_count=0 ):
    """
    DESCRIE
    """
    logging.debug( 'cinp: DESCRIBE "{0}"'.format( uri ) )
    ( http_code, data, header_map ) = await self._request( 'DESCRIBE', uri, timeout=timeout, retry_count=retry_count )

    if http_code != 200:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for DESCRIBE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for DESCRIBE'.format( http_code ) )

    return data, header_map[ 'Type' ]

  async def list( self, uri, filter_name=None, filter_value_map=None, position=0, count=10, timeout=30, retry_count=0 ):
    """
    LIST
    """
    if filter_value_map is None:
      filter_value_map = {}

    if not isinstance( filter_value_map, dict ):
      raise InvalidRequest( 'list filter_value_map must be a dict' )

    if not isinstance( position, int ) or not isinstance( count, int ) or position < 0 or count < 0:
      raise InvalidRequest( 'position and count must bot be int and greater than 0' )

    header_map = { 'Position': str( position ), 'Count': str( count ) }  # TODO set position and coint to default to None, and don't send them if npt specified, rely on the server's defaults
    if filter_name is not None:
      header_map[ 'Filter' ] = filter_name

    logging.debug( 'cinp: LIST "{0}" with filter "{1}"'.format( uri, filter_name ) )
    ( http_code, id_list, header_map ) = await self._request( 'LIST', uri, data=filter_value_map, header_map=header_map, timeout=timeout, retry_count=retry_count )

    if http_code != 200:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for LIST'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for LIST'.format( http_code ) )

    if not isinstance( id_list, list ):
      logging.warning( 'cinp: Response id_list must be a list for LIST' )
      raise ResponseError( 'Response id_list must be a list for LIST' )

    count_map = { 'position': 0, 'count': 0, 'total': 0 }
    for item in ( 'Position', 'Count', 'Total' ):  # NOTE HTTP Headers typicaly are CamelCase, but we want lower case for our count dictomary
      try:
        count_map[ item.lower() ] = int( header_map[ item ] )
      except ( KeyError, ValueError ):
        pass

    return ( id_list, count_map )

  async def get( self, uri, force_multi_mode=False, timeout=30, retry_count=0 ):
    """
    GET
    """
    header_map = {}
    if force_multi_mode:
      header_map[ 'Multi-Object' ] = True

    logging.debug( 'cinp: GET "{0}"'.format( uri ) )
    ( http_code, rec_values, header_map ) = await self._request( 'GET', uri, header_map=header_map, timeout=timeout, retry_count=retry_count )

    if http_code != 200:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for GET'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for GET'.format( http_code ) )

    if not isinstance( rec_values, dict ):
      logging.warning( 'cinp: Response rec_values must be a dict for GET' )
      raise ResponseError( 'Response rec_values must be a dict for GET' )

    return rec_values

  async def create( self, uri, values, timeout=30, retry_count=0 ):
    """
    CREATE
    """
    if not isinstance( values, dict ):
      raise InvalidRequest( 'values must be a dict' )

    logging.debug( 'cinp: CREATE "{0}"'.format( uri ) )
    ( http_code, rec_values, header_map ) = await self._request( 'CREATE', uri, data=values, timeout=timeout, retry_count=retry_count )

    if http_code != 201:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for CREATE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for CREATE'.format( http_code ) )

    if not isinstance( rec_values, dict ):
      logging.warning( 'cinp: Response rec_values must be a dict for CREATE' )
      raise ResponseError( 'Response rec_values must be a dict for CREATE' )

    try:
      object_id = header_map[ 'Object-Id' ]
    except KeyError:
      raise ResponseError( 'Object-Id header missing' )

    return ( object_id, rec_values )

  async def update( self, uri, values, force_multi_mode=False, timeout=30, retry_count=0 ):
    """
    UPDATE
    """
    if not isinstance( values, dict ):
      raise InvalidRequest( 'values must be a dict' )

    header_map = {}
    if force_multi_mode:
      header_map[ 'Multi-Object' ] = True

    logging.debug( 'cinp: UPDATE "{0}"'.format( uri ) )
    ( http_code, rec_values, _ ) = await self._request( 'UPDATE', uri, data=values, header_map=header_map, timeout=timeout, retry_count=retry_count )

    if http_code != 200:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for UPDATE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for UPDATE'.format( http_code ) )

    if not isinstance( rec_values, dict ):
      logging.warning( 'cinp: Response rec_values must be a dict for UPDATE' )
      raise ResponseError( 'Response rec_values must be a str for UPDATE' )

    return rec_values

  async def delete( self, uri, timeout=30, retry_count=0 ):
    """
    DELETE
    """
    logging.debug( 'cinp: DELETE "{0}"'.format( uri ) )
    ( http_code, _, _ ) = await self._request( 'DELETE', uri, timeout=timeout, retry_count=retry_count )

    if http_code != 200:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for DELETE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for DELETE'.format( http_code ) )

    return True

  async def call( self, uri, args, force_multi_mode=False, timeout=30, retry_count=0 ):
    """
    CALL
    """
    if not isinstance( args, dict ):
      raise InvalidRequest( 'args must be a dict' )

    header_map = {}
    if force_multi_mode:
      header_map[ 'Multi-Object' ] = True

    logging.debug( 'cinp: CALL "{0}"'.format( uri ) )
    ( http_code, return_value, _ ) = await self._request( 'CALL', uri, data=args, header_map=header_map, timeout=timeout, retry_count=retry_count )

    if http_code != 200:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for CALL'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for CALL'.format( http_code ) )

    return return_value

  async def getMulti( self, uri, id_list=None, chunk_size=10, retry_count=0 ):
    """
    returns a generator that will iterate over the uri/id_list, reterieving from the server in chunk_size blocks
    each item is ( rec_id, rec_values )
    if uri is a list, id_list is ignored
    """
    if isinstance( uri, list ):
      id_list = []
      for item in uri:
        ( _, _, _, tmp_id_list, _ ) = self.uri.split( item )
        id_list += tmp_id_list

      ( namespace, model, _, tmp_id_list, _ ) = self.uri.split( uri[0] )

    else:
      ( namespace, model, _, tmp_id_list, _ ) = self.uri.split( uri )
      if id_list is None:
        id_list = tmp_id_list

    result_list = []
    pos = 0

    while pos < len( id_list ):
      tmp_data = await self.get( self.uri.build( namespace, model, None, id_list[ pos: pos + chunk_size ] ), force_multi_mode=True, retry_count=retry_count )
      pos += chunk_size
      for key in tmp_data:
        result_list.append( ( key, tmp_data[ key ] ) )

      while len( result_list ) > 0:
        yield result_list.pop( 0 )

  async def getFilteredObjects( self, uri, filter_name=None, filter_value_map=None, list_chunk_size=100, get_chunk_size=10, timeout=30, retry_count=0 ):
    pos = 0
    total = 1
    while pos < total:
      ( tmp_id_list, count_map ) = await self.list( uri, filter_name=filter_name, filter_value_map=filter_value_map, position=pos, count=list_chunk_size, retry_count=retry_count )
      id_list = self.uri.extractIds( tmp_id_list )
      pos = count_map[ 'position' ] + count_map[ 'count' ]
      total = count_map[ 'total' ]
      return self.getMulti( uri, id_list, get_chunk_size, retry_count=retry_count )  # TODO: need to found out how to get the next chunk, return/yeild something

  async def getFilteredURIs( self, uri, filter_name=None, filter_value_map=None, list_chunk_size=100, get_chunk_size=10, timeout=30, retry_count=0 ):
    pos = 0
    total = 1
    while pos < total:
      ( tmp_id_list, count_map ) = await self.list( uri, filter_name=filter_name, filter_value_map=filter_value_map, position=pos, count=list_chunk_size, retry_count=retry_count )
      id_list = self.uri.extractIds( tmp_id_list )
      pos = count_map[ 'position' ] + count_map[ 'count' ]
      total = count_map[ 'total' ]

      while len( id_list ) > 0:
        yield id_list.pop( 0 )

  async def getFile( self, uri, target_dir='/tmp', file_object=None, cb=None, timeout=30, chunk_size=( 4096 * 1024 ) ):
    """
    if file_object is defined:
       The file contense are written to it and the filename as specified by the
       server is returned, None is returned if not filename is detected.  The
       file_object is not closed. file_object must be opened with the 'b' attribute.

    Otherwise a file is created in target_dir, and the full path is returned.  If the
      filename is not specified by the server, and a random filename is chosen.
      WARNING: there isn't checking done to make sure the target file does not allready
      exist, there is a possibility it could clober something that allready exists.
      we do make sure the filename fits a regex pattern that prevents it from escaping
      the target_dir.  The "filename" as sent by the server is the "model" of the uri.
      make sure target_dir exists before calling getFile
    """

    uri_parser = URI( '/' )
    try:  # TODO: There has to be a better way to validate this uri
      ( _, filename, _, _, _ ) = uri_parser.split( uri )
    except ValueError as e:
      raise InvalidRequest( str( e ) )

    # Due to the return value we have to do our own request, this is pretty much a stright GET
    url = '{0}{1}'.format( self.host, uri )

    try:
      async with self.connection_pool.request( 'GET', url, headers=self.header_list + self.auth_header_list, extensions={ 'timeout': { 'connect': timeout } } ) as resp:
        http_code = resp.status
        if http_code != 200:
          logging.warning( 'cinp: Unexpected HTTP Code "{0}" for File Get'.format( http_code ) )
          raise ResponseError( 'Unexpected HTTP Code "{0}" for File Get'.format( http_code ) )

        header_map = _headerListToMap( resp.headers )

        try:
          size = header_map[ 'Content-Length' ]
        except KeyError:
          size = 0

        if file_object is not None:
          file_writer = file_object

        else:
          if filename is None:
            file_writer = NamedTemporaryFile( dir=target_dir, mode='wb' )
            filename = file_writer.name

          else:
            filename = os.path.join( target_dir, filename )
            file_writer = open( filename, 'wb' )

        async for buff in resp.iter_stream():
          file_writer.write( buff )
          if cb:
            cb( file_writer.tell(), size )

    except httpcore.ProtocolError as e:
      raise ResponseError( 'ProtocolError "{0}"'.format( e ) )

    except httpcore.ProxyError as e:
      raise ResponseError( 'ProxyError "{0}" for "{1}" via "{2}"'.format( e, url, self.proxy ) )

    except httpcore.NetworkError as e:
      raise ResponseError( 'NetworkError "{0}"'.format( e ) )

    except httpcore.TimeoutException:
      raise Timeout( 'Request Timeout after {0} seconds'.format( timeout ) )

    if file_object is None:
      file_writer.close()

    return filename

  async def uploadFile( self, uri, filepath, filename=None, cb=None, timeout=30 ):
    """
    filepath can be a string of the path name or a file object.  If a file object
    either specify the filename or make sure your file object exposes the attribute
    'name'.  Also if file object, must be opened in binary mode, ie: 'rb'

    NOTE: this is not a CInP function, but a conviance function for uploading large files.
    """
    uri_parser = URI( '/' )
    try:  # TODO: There has to be a better way to validate this uri
      ( namespace, model, action, id_list, _ ) = uri_parser.split( uri )
    except ValueError as e:
      raise InvalidRequest( str( e ) )

    if action is not None or id_list is not None:
      raise InvalidRequest( 'file upload target can\'t be an action nor have ids' )

    if isinstance( filepath, str ):
      if filename is None:
        filename = os.path.basename( filepath )

      file_reader = _readerWrapper( open( filepath, 'rb' ), cb )

    else:
      if filename is None:
        filename = os.path.basename( filepath.name )

      file_reader = _readerWrapper( filepath, cb )

    header_map = {
                   'Content-Disposition': 'inline: filename="{0}"'.format( filename ),
                   'Content-Length': len( file_reader )
                 }

    ( http_code, data, _ ) = await self._request( 'UPLOAD', uri_parser.build( namespace, model ), data=file_reader, header_map=header_map, timeout=timeout )

    if http_code != 202:
      logging.warning( 'cinp: Unexpected HTTP Code "{0}" for File Upload'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for File Upload'.format( http_code ) )

    return data[ 'uri' ]


class _readerWrapper():
  def __init__( self, reader, cb ):
    self._cb = cb
    self._size = os.fstat( reader.fileno() ).st_size
    self._reader = reader

  def __len__( self ):
    return self._size

  def read( self, size ):
    if self._cb:
      self._cb( self._reader.tell(), self._size )
    buff = self._reader.read( size )
    return buff


class JSONEncoder( json.JSONEncoder ):
  def default( self, obj ):
    if isinstance( obj, datetime ):
      return obj.isoformat()

    return super().default( obj )
