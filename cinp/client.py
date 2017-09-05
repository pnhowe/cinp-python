import socket
import json
import logging
from urllib import request

from cinp.common import URI

__CLIENT_VERSION__ = '0.9.0'
__CINP_VERSION__ = '0.9'

__all__ = [ 'Timeout', 'ResponseError', 'InvalidRequest', 'InvalidSession',
            'NotAuthorized', 'NotFound', 'ServerError', 'CInP' ]


class Timeout( Exception ):
  pass


class ResponseError( Exception ):
  pass


class InvalidRequest( Exception ):
  pass


class InvalidSession( Exception ):
  pass


class NotAuthorized( Exception ):
  pass


class NotFound( Exception ):
  pass


class ServerError( Exception ):
  pass


class HTTPErrorProcessorPassthrough( request.HTTPErrorProcessor ):
  def http_response( self, request, response ):
    return response


class CInP():
  def __init__( self, host, root_path, port, proxy=None ):
    super().__init__()

    if not host.startswith( ( 'http:', 'https:' ) ):
      raise ValueError( 'hostname must start with http(s):' )

    if host[-1] == '/':
      raise ValueError( 'hostname must not end with "/"' )

    self.proxy = proxy
    self.host = host
    self.port = port
    logging.debug( 'cinp: new client host: "{0}:{1}", root_path: "{2}", via: "{3}"'.format( self.host, self.port, root_path, self.proxy ) )

    self.uri = URI( root_path )

    if self.proxy is not None:  # have a prxy option to take it from the envrionment vars
      self.opener = request.build_opener( HTTPErrorProcessorPassthrough, request.ProxyHandler( { 'http': self.proxy, 'https': self.proxy } ) )
    else:
      self.opener = request.build_opener( HTTPErrorProcessorPassthrough, request.ProxyHandler( {} ) )

    self.opener.addheaders = [
                                ( 'User-Agent', 'python client {0}'.format( __CLIENT_VERSION__ ) ),
                                ( 'Accepts', 'application/json' ),
                                ( 'Accept-Charset', 'utf-8' ),
                                ( 'Content-Type', 'application/json;charset=utf-8' ),
                                ( 'CInP-Version', __CINP_VERSION__ )
                              ]

  def _checkRequest( self, method, uri, data ):  # TODO: also check if method is allowed to have headers ( other than thoes provided by the opener ), also check to make sure they are valid heaaders
    logging.debug( 'cinp: check "{0}" to "{1}"'.format( method, uri ) )

    if method not in ( 'GET', 'LIST', 'UPDATE', 'CREATE', 'DELETE', 'CALL', 'DESCRIBE' ):
      raise InvalidRequest( 'Invalid HTTP Method "{0}"'.format( method ) )

    if data is not None and not isinstance( data, dict ):
      raise InvalidRequest( 'Data must be a dict' )

    try:
      ( _, model, action, id_list, _ ) = self.uri.split( uri )
    except ValueError as e:
      raise InvalidRequest( str( e ) )

    if id_list == []:
      id_list = None

    if action is not None and method not in ( 'CALL', 'DESCRIBE' ):
      raise InvalidRequest( 'Invalid method "{0}" for request with action'.format( method ) )

    if method in ( 'CALL', ) and action is None:
      raise InvalidRequest( 'Method "{0}" requires action'.format( method ) )

    if id_list is not None and method not in ( 'GET', 'UPDATE', 'DELETE', 'CALL' ):
      raise InvalidRequest( 'Invalid method "{0}" for request with id'.format( method ) )

    if method in ( 'GET', 'UPDATE', 'DELETE' ) and id_list is None:
      raise InvalidRequest( 'Method "{0}" requires id'.format( method ) )

    if data is not None and method not in ( 'LIST', 'UPDATE', 'CREATE', 'CALL' ):
      raise InvalidRequest( 'Invalid method "{0}" for request with data'.format( method ) )

    if method in ( 'UPDATE', 'CREATE' ) and data is None:
      raise InvalidRequest( 'Method "{0}" requires data'.format( method ) )

    if method in ( 'GET', 'LIST', 'UPDATE', 'CREATE', 'DELETE', 'CALL' ) and not model:
      raise InvalidRequest( 'Method "{0}" requires model'.format( method ) )

  def _request( self, method, uri, data=None, header_map=None, timeout=30 ):
    logging.debug( 'cinp: making "{0}" request to "{1}"'.format( method, uri ) )
    if header_map is None:
      header_map = {}

    self._checkRequest( method, uri, data )
    if data is None:
      data = ''.encode( 'utf-8' )
    else:
      data = json.dumps( data ).encode( 'utf-8' )

    url = '{0}:{1}{2}'.format( self.host, self.port, uri )
    req = request.Request( url, data=data, headers=header_map )
    req.get_method = lambda: method
    try:
      resp = self.opener.open( req, timeout=timeout )

    except request.HTTPError as e:
      raise ResponseError( 'HTTPError "{0}"'.format( e ) )

    except request.URLError as e:
      if isinstance( e.reason, socket.timeout ):
        raise Timeout( 'Request Timeout after {0} seconds'.format( timeout ) )

      raise ResponseError( 'URLError "{0}" for "{1}" via "{2}"'.format( e, url, self.proxy ) )

    http_code = resp.code
    if http_code not in ( 200, 201, 400, 401, 403, 404, 500 ):
      raise ResponseError( 'HTTP code "{0}" unhandled'.format( resp.code ) )

    logging.debug( 'cinp: got http code "{0}"'.format( http_code ) )

    buff = str( resp.read(), 'utf-8' ).strip()
    if not buff:
      data = None
    else:
      try:
        data = json.loads( buff )
      except ValueError:
        data = None
        if http_code not in ( 400, 500 ):  # these two codes can deal with non dict data
          logging.warning( 'cinp: Unable to parse response "{0}"'.format( buff[ 0:100 ] ) )
          raise ResponseError( 'Unable to parse response "{0}"'.format( buff[ 0:100 ] ) )

    header_map = {}
    for item in ( 'Position', 'Count', 'Total', 'Type', 'Multi-Object', 'Object-Id', 'Method' ):
      try:
        header_map[ item ] = resp.headers[ item ]
      except KeyError:
        pass

    resp.close()

    if http_code == 400:
      try:
        message = data[ 'message' ]
      except ( KeyError, ValueError, TypeError ):
        message = buff[ 0:100 ]

      logging.warning( 'cinp: Invalid Request "{0}"'.format( message ) )
      raise InvalidRequest( message )

    if http_code == 401:
      logging.warning( 'cinp: Invalid Session' )
      raise InvalidSession()

    if http_code == 403:
      logging.warning( 'cinp: Not Authorized' )
      raise NotAuthorized()

    if http_code == 404:
      logging.warning( 'cinp: Not Found' )
      raise NotFound()

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
        message = 'Server Error: "{0}"'.format( buff[ 0:100 ] )

      logging.error( 'cinp: {0}'.format( message ) )
      raise ServerError( message )

    return ( http_code, data, header_map )

  def setAuth( self, auth_id=None, auth_token=None ):
    """
    Sets the Authencation id and token headers, call with out paramaters to remove the headers.
    """
    if not auth_id:
      logging.debug( 'cinp: removing auth info' )
      for index in range( len( self.opener.addheaders ) - 1, -1, -1 ):
        if self.opener.addheaders[ index ][0] in ( 'Auth-Id', 'Auth-Token' ):
          del self.opener.addheaders[ index ]

    else:
      logging.debug( 'cinp: setting auth info, id "{0}"'.format( auth_id ) )
      self.opener.addheaders += [ ( 'Auth-Id', auth_id ), ( 'Auth-Token', auth_token ) ]

  def describe( self, uri, timeout=30  ):
    """
    DESCRIE
    """
    logging.debug( 'cinp: DESCRIBE "{0}"'.format( uri ) )
    ( http_code, data, _ ) = self._request( 'DESCRIBE', uri, timeout=timeout )

    if http_code != 200:
      logging.warning( 'cinp: unexpected HTTP Code "{0}" for DESCRIBE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for DESCRIBE'.format( http_code ) )

    return data

  def list( self, uri, filter_name=None, filter_value_map=None, position=0, count=10, timeout=30 ):
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
    ( http_code, id_list, header_map ) = self._request( 'LIST', uri, data=filter_value_map, header_map=header_map, timeout=timeout )

    if http_code != 200:
      logging.warning( 'cinp: unexpected HTTP Code "{0}" for LIST'.format( http_code ) )
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

  def get( self, uri, force_multi_mode=False, timeout=30 ):
    """
    GET
    """
    header_map = {}
    if force_multi_mode:
      header_map[ 'Multi-Object' ] = True

    logging.debug( 'cinp: GET "{0}"'.format( uri ) )
    ( http_code, rec_values, header_map ) = self._request( 'GET', uri, header_map=header_map, timeout=timeout )

    if http_code != 200:
      logging.warning( 'cinp: unexpected HTTP Code "{0}" for GET'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for GET'.format( http_code ) )

    if not isinstance( rec_values, dict ):
      logging.warning( 'cinp: Response rec_values must be a dict for GET' )
      raise ResponseError( 'Response rec_values must be a dict for GET' )

    return rec_values

  def create( self, uri, values, timeout=30 ):
    """
    CREATE
    """
    if not isinstance( values, dict ):
      raise InvalidRequest( 'values must be a dict' )

    logging.debug( 'cinp: CREATE "{0}"'.format( uri ) )
    ( http_code, rec_values, header_map ) = self._request( 'CREATE', uri, data=values, timeout=timeout )

    if http_code != 201:
      logging.warning( 'cinp: unexpected HTTP Code "{0}" for CREATE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for CREATE'.format( http_code ) )

    if not isinstance( rec_values, dict ):
      logging.warning( 'cinp: Response rec_values must be a dict for CREATE' )
      raise ResponseError( 'Response rec_values must be a dict for CREATE' )

    try:
      object_id = header_map[ 'Object-Id' ]
    except KeyError:
      raise ResponseError( 'Object-Id header missing' )

    return ( object_id, rec_values )

  def update( self, uri, values, force_multi_mode=False, timeout=30 ):
    """
    UPDATE
    """
    if not isinstance( values, dict ):
      raise InvalidRequest( 'values must be a dict' )

    header_map = {}
    if force_multi_mode:
      header_map[ 'Multi-Object' ] = True

    logging.debug( 'cinp: UPDATE "{0}"'.format( uri ) )
    ( http_code, rec_values, _ ) = self._request( 'UPDATE', uri, data=values, header_map=header_map, timeout=timeout )

    if http_code != 200:
      logging.warning( 'cinp: unexpected HTTP Code "{0}" for UPDATE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for UPDATE'.format( http_code ) )

    if not isinstance( rec_values, dict ):
      logging.warning( 'cinp: Response rec_values must be a dict for UPDATE' )
      raise ResponseError( 'Response rec_values must be a str for UPDATE' )

    return rec_values

  def delete( self, uri, timeout=30 ):
    """
    DELETE
    """
    logging.debug( 'cinp: DELETE "{0}"'.format( uri ) )
    ( http_code, _, _ ) = self._request( 'DELETE', uri, timeout=timeout )

    if http_code != 200:
      logging.warning( 'cinp: unexpected HTTP Code "{0}" for DELETE'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for DELETE'.format( http_code ) )

    return True

  def call( self, uri, args, force_multi_mode=False, timeout=30 ):
    """
    CALL
    """
    if not isinstance( args, dict ):
      raise InvalidRequest( 'args must be a dict' )

    header_map = {}
    if force_multi_mode:
      header_map[ 'Multi-Object' ] = True

    logging.debug( 'cinp: CALL "{0}"'.format( uri ) )
    ( http_code, return_value, _ ) = self._request( 'CALL', uri, data=args, header_map=header_map, timeout=timeout )

    if http_code != 200:
      logging.warning( 'cinp: unexpected HTTP Code "{0}" for CALL'.format( http_code ) )
      raise ResponseError( 'Unexpected HTTP Code "{0}" for CALL'.format( http_code ) )

    return return_value

  def getMulti( self, uri, id_list=None, chunk_size=10 ):
    """
    returns a generator that will iterate over the uri/id_list, reterieving from the server in chunk_size blocks
    each item is ( rec_id, rec_values )
    """
    ( namespace, model, _, tmp_id_list, _ ) = self.uri.split( uri )
    if id_list is None:
      id_list = tmp_id_list

    result_list = []
    pos = 0

    while pos < len( id_list ):
      tmp_data = self.get( self.uri.build( namespace, model, None, id_list[ pos: pos + chunk_size ] ), force_multi_mode=True )
      pos += chunk_size
      for key in tmp_data:
        result_list.append( ( key, tmp_data[ key ] ) )

      while len( result_list ) > 0:
        yield result_list.pop( 0 )

  def getFilteredObjects( self, uri, filter_name=None, filter_value_map=None, list_chunk_size=100, get_chunk_size=10, timeout=30 ):
    pos = 0
    total = 1
    while pos < total:
      ( tmp_id_list, count_map ) = self.list( uri, filter_name=filter_name, filter_value_map=filter_value_map, position=pos, count=list_chunk_size )
      id_list = self.uri.extractIds( tmp_id_list )
      pos = count_map[ 'position' ] + count_map[ 'count' ]
      total = count_map[ 'total' ]
      return self.getMulti( uri, id_list, get_chunk_size )
