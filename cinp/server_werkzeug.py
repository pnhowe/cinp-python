import werkzeug
import json
import logging
from importlib import import_module

from cinp.server_common import Server, Request, Response, Namespace


class WerkzeugServer( Server ):
  def __init__( self, get_user, *args, **kwargs ):
    super().__init__( *args, **kwargs )
    self.getUser = get_user

  def handle( self, envrionment ):
    try:
      response = super().handle( WerkzeugRequest( envrionment ) )

      if not isinstance( response, Response ):
        if self.debug:
          message = 'Invalid Response from handle, got "{0}" expected WerkzeugResponse'.format( type( response ).__name__ )
        else:
          message = 'Invalid Response from handle'

        return werkzeug.wrappers.BaseResponse( response=message, status=500, content_type='text/plain' )

      return WerkzeugResponse( response ).buildNativeResponse()

    except Exception as e:
      logging.error( 'Top level Exception, "{0}"({1})'.format( str( e ), type( e ).__name__ ) )
      return werkzeug.wrappers.BaseResponse( response='Error getting WerkzeugResponse, "{0}"({1})'.format( str( e ), type( e ).__name__ ), status=500, content_type='text/plain' )

  def __call__( self, envrionment, start_response ):
    """
    called by werkzeug for every request
    """
    return self.handle( envrionment )( envrionment, start_response )

  # add a namespace to the path, either from included module, or an empty namespace with name and version
  def registerNamespace( self, path, module=None, name=None, version=None ):
    if module is None:
      if name is None or version is None:
        raise ValueError( 'name and version must be specified if no module is specified' )

      namespace = Namespace( name=name, version=version )

    else:
      if isinstance( module, Namespace ):
        namespace = module
      else:
        module = import_module( '{0}.models'.format( module ) )
        namespace = module.cinp.getNamespace()

    super().registerNamespace( path, namespace )


class WerkzeugRequest( Request ):
  def __init__( self, envrionment, *args, **kwargs ):
    werkzeug_request = werkzeug.wrappers.BaseRequest( envrionment )
    header_map = {}
    for ( key, value ) in werkzeug_request.headers:
      header_map[ key.upper().replace( '_', '-' ) ] = value

    super().__init__( method=werkzeug_request.method.upper(), uri=werkzeug_request.path, header_map=header_map, *args, **kwargs )

    self.fromJSON( str( werkzeug_request.stream.read( 164160 ), 'utf-8' ) )  # hopfully the request isn't larger than 160k, if so, we may need to rethink things

    self.remote_addr = werkzeug_request.remote_addr
    self.is_secure = werkzeug_request.is_secure
    werkzeug_request.close()


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

  def buildNativeResponse( self ):
    if self.content_type == 'json':
      return self.asJSON()
    elif self.content_type == 'xml':
      return self.asXML()

    return self.asText()

  def asText( self ):
    return werkzeug.wrappers.BaseResponse( response=self.data, status=self.status, headers=self.header_list, content_type='text/plain;charset=utf-8' )

  def asJSON( self ):
    if self.data is None:
      response = ''.encode( 'utf-8' )
    else:
      response = json.dumps( self.data ).encode( 'utf-8' )

    return werkzeug.wrappers.BaseResponse( response=response, status=self.status, headers=self.header_list, content_type='application/json;charset=utf-8'  )

  def asXML( self ):
    return werkzeug.wrappers.BaseResponse( response='<xml>Not Implemented</xml>', status=self.response.http_code, headers=self.header_list, content_type='application/xml;charset=utf-8' )
