import werkzeug
import json
import logging
from importlib import import_module

from cinp.server_common import Server, Request, Response, Namespace, Converter, InvalidRequest


class NoCINP( Exception ):
  pass


class WerkzeugServer( Server ):
  def handle( self, environment ):
    try:
      response = super().handle( WerkzeugRequest( environment ) )

      if not isinstance( response, Response ):
        if self.debug:
          message = 'Invalid Response from handle, got "{0}" expected Response'.format( type( response ).__name__ )
        else:
          message = 'Invalid Response from handle'

        response = Response( 500, data={ 'message': message } )

    except InvalidRequest as e:
      response = e.asResponse()

    except Exception as e:
      logging.exception( 'Top level Exception, "{0}"({1})'.format( e, type( e ).__name__ ) )
      if self.debug:
        message = 'Top level Exception, "{0}"({1})'.format( e, type( e ).__name__ )
      else:
        message = 'Top level Exception'

      response = Response( 500, data={ 'message': message } )

    try:
      return WerkzeugResponse( response ).buildNativeResponse()

    except Exception as e:  # last ditch effort, the response it's self could not be converted
      logging.exception( 'Exception building the response, "{0}"({1})'.format( e, type( e ).__name__ ) )
      return werkzeug.wrappers.Response( response='Error building the response', status=500, content_type='text/plain' )

  def __call__( self, environment, start_response ):
    """
    called by werkzeug for every request
    """
    return self.handle( environment )( environment, start_response )

  # add a namespace to the path, either from included module, or an empty namespace with name and version
  def registerNamespace( self, path, module=None, name=None, version=None ):
    if module is None:
      if name is None or version is None:
        raise ValueError( 'name and version must be specified if no module is specified' )

      namespace = Namespace( name=name, version=version, converter=Converter( self.uri ) )

    else:
      if isinstance( module, Namespace ):
        namespace = module

      else:
        module = import_module( '{0}.models'.format( module ) )
        if not hasattr( module, 'cinp' ):
          raise NoCINP( 'module "{0}" missing cinp'.format( module ) )

        namespace = module.cinp.getNamespace( self.uri )

    super().registerNamespace( path, namespace )


class WerkzeugRequest( Request ):
  def __init__( self, environment, *args, **kwargs ):
    werkzeug_request = werkzeug.wrappers.Request( environment )
    header_map = {}
    for ( key, value ) in werkzeug_request.headers:
      header_map[ key.upper().replace( '_', '-' ) ] = value

    self.max_request_size = 524288  # 512k bytes

    # script_root should be what ever path was consumed by the script handler configuration
    # ie: the  "/api" of: WSGIScriptAlias /api <path to wsgi script>
    uri = werkzeug_request.script_root + werkzeug_request.path
    super().__init__( verb=werkzeug_request.method.upper(), uri=uri, header_map=header_map, cookie_map=werkzeug_request.cookies, *args, **kwargs )

    content_type = self.header_map.get( 'CONTENT-TYPE', None )
    content_length = werkzeug_request.content_length
    if content_length is not None and content_length > self.max_request_size and content_type is not None and not content_type.startswith( 'application/octet-stream' ):
      raise InvalidRequest( 'Request body too large' )  # hopefully the request isn't larger than 512k, if so, we may need to rethink things

    stream = werkzeug.wsgi.LimitedStream( werkzeug_request.stream, self.max_request_size, is_max=True )

    if content_type is not None:  # if it is none, there isn't (or shouldn't) be anything to bring in anyway
      if content_type.startswith( 'application/json' ):
        self.fromJSON( stream )

      elif content_type.startswith( 'text/plain' ):
        self.fromText( stream )

      elif content_type.startswith( 'application/xml' ):
        self.fromXML( stream )

      elif content_type.startswith( 'application/octet-stream' ):
        self.stream = werkzeug_request.stream
        if 'CONTENT-DISPOSITION' in header_map:  # cheat a little, Content-Disposition isn't pure CInP, but this is a bolt on file uploader
          self.header_map[ 'CONTENT-DISPOSITION' ] = header_map[ 'CONTENT-DISPOSITION' ]
        pass  # do nothing, down stream is going to have to read from the stream

      elif content_type.startswith( 'application/x-www-form-urlencoded' ):
        self.fromURLEncodedForm( stream )  # TODO: pass in the encoding as well so it can be handled better

      else:
        raise InvalidRequest( message='Unknown Content-Type "{0}"'.format( content_type ) )

    self.remote_addr = werkzeug_request.remote_addr
    self.is_secure = werkzeug_request.is_secure

    werkzeug_request.close()

  def read( self, size ):
    return self.stream.read( size )


class WerkzeugResponse():  # TODO: this should be a subclass of the server_common Response, to much redundant stuff
  def __init__( self, response ):
    if not isinstance( response, Response ):
      raise ValueError( 'response must be of type Response' )

    super().__init__()
    self.content_type = response.content_type
    self.data = response.data
    self.status = response.http_code
    self.header_list = []
    for name in response.header_map:
      self.header_list.append( ( name, response.header_map[ name ] ) )

    for ( key, value, max_age, expires, path, domain, secure, httponly, samesite ) in response.cookie_list:
      self.header_list.append( ( 'Set-Cookie', werkzeug.http.dump_cookie( key, value=value, max_age=max_age, expires=expires, path=path, domain=domain, secure=secure, httponly=httponly, samesite=samesite ) ) )

  def buildNativeResponse( self ):
    if self.content_type == 'json':
      return self.asJSON()
    elif self.content_type == 'xml':
      return self.asXML()
    elif self.content_type == 'bytes':
      return self.asBytes()

    return self.asText()

  def asText( self ):
    if self.data is None:
      response = ''.encode( 'utf-8' )
    else:
      response = self.data.encode( 'utf-8' )

    if self.content_type == 'text':
      content_type = 'text/plain;charset=utf-8'
    else:
      content_type = self.content_type + ';charset=utf-8'

    return werkzeug.wrappers.Response( response=response, status=self.status, headers=self.header_list, content_type=content_type )

  def asJSON( self ):
    if self.data is None:
      response = ''.encode( 'utf-8' )
    else:
      response = json.dumps( self.data ).encode( 'utf-8' )

    return werkzeug.wrappers.Response( response=response, status=self.status, headers=self.header_list, content_type='application/json;charset=utf-8'  )

  def asXML( self ):
    return werkzeug.wrappers.Response( response='<xml>Not Implemented</xml>', status=self.status, headers=self.header_list, content_type='application/xml;charset=utf-8' )

  def asBytes( self ):
    if self.data is None:
      response = ''
    else:
      response = self.data

    return werkzeug.wrappers.Response( response=response, status=self.status, headers=self.header_list, content_type='application/octet-stream'  )
