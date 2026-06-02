import base64
import os
from urllib import request, parse
from io import BytesIO

# reader is a function that returns a tuple that is file handle and filename, it is given the URI that is the value of the field from the client

# set this to a list of http hosts that the http reader is allowed to retrieve from
ALLOWED_HTTP_HOSTS = []

READER_REGISTRY = {}
HTTP_TIMEOUT = 30


class InlineReader( BytesIO ):
  def __init__( self, uri ):  # format 'inline://filename;encoding,data', only base64 encoding for now
    if not uri.startswith( 'inline://' ):
      raise ValueError( 'Invalid URI format for inline' )

    try:
      head, data = uri[ len( 'inline://' ): ].split( ',', 1 )
      self.filename, self.encoding = head.rsplit( ';', 1 )
    except ValueError:
      raise ValueError( 'Invalid URI format for inline' )

    if self.encoding != 'base64':
      raise NotImplementedError( 'Invalid Encoding type for inline' )

    try:
      data = base64.b64decode( data )
    except ValueError:
      raise ValueError( 'Invalid Inline Data' )

    super().__init__( data )


def inline( uri ):
  reader = InlineReader( uri )

  return ( reader, reader.filename )


READER_REGISTRY[ 'inline' ] = inline


class AllowedHostsRedirectHandler( request.HTTPRedirectHandler ):
  def redirect_request( self, req, fp, code, msg, headers, url ):
    parts = parse.urlparse( url )
    if parts.hostname not in ALLOWED_HTTP_HOSTS:
      raise ValueError( f'Redirect to {parts.hostname} not in ALLOWED_HTTP_HOSTS' )

    return super().redirect_request( req, fp, code, msg, headers, url )


def http( uri ):
  parts = parse.urlparse( uri )
  if parts.hostname not in ALLOWED_HTTP_HOSTS:
    raise ValueError( f'{parts.hostname} not in ALLOWED_HTTP_HOSTS' )

  opener = request.build_opener( AllowedHostsRedirectHandler )
  reader = opener.open( uri, timeout=HTTP_TIMEOUT )

  return ( reader, os.path.basename( parts.path ) )


READER_REGISTRY[ 'http' ] = http
