import dateutil
import traceback
import json

from cinp.common import URI

__CINP_VERSION__ = '0.9'
__MULTI_URI_MAX__ = 100

FIELD_TYPE_LIST = ( 'String', 'Integer', 'Float', 'Boolean', 'DateTime', 'Map', 'Model', 'File' )


class InvalidRequest( Exception ):
  def __init__( self, message=None, data=None):
    self.data = data or { 'message': message } or 'Unknown'

  def asResponse( self ):
    return Response( 400, data=self.data )

  def __str__( self ):
    return 'InvalidRequest: "{0}"'.format( self.data )


class ServerError( Exception ):
  def __init__( self, message ):
    self.message = message

  def asResponse( self ):
    return Response( 500, data={ 'message': self.message } )

  def __str__( self ):
    return 'ServerError: "{0}"'.format( self.message )


class ObjectNotFound( Exception ):
  def __init__( self, model_path, object_id ):
    self.model_path = model_path
    self.object_id = object_id

  def asResponse( self ):
    return Response( 404, data={ 'model_path': self.model_path, 'object_id': self.object_id } )

  def __str__( self ):
    return 'ObjectNotFound: "{0}":"{1}":'.format( self.model_path, self.object_id )


class NotAuthorized( Exception ):
  pass


class AnonymouseUser():
  @property
  def isSuperuser( self ):
    return False

  @property
  def isAnonymouse( self ):
    return True


def _dictConverter( value ):
  _fromPythonMap( value )
  return value

MAP_TYPE_CONVERTER = {
                       'NoneType': lambda a: None,
                       'str': str,
                       'int': str,
                       'float': str,
                       'bool': lambda a: True if a else False,
                       'datetime': lambda a: a.isoformat(),
                       'timedelta': lambda a: a.total_seconds(),
                       'dict': _dictConverter
                     }


def _fromPythonMap_converter( value ):
  try:
    return MAP_TYPE_CONVERTER[ type( value ).__name__ ]( value )
  except KeyError:
    raise ValueError( 'no converter for type "{0}" in map converter'.format( type( value ).__name__ ) )


def _fromPythonMap( value ):
  for key in value.keys():
    if isinstance( value[ key ], tuple ):  # convert tuple to list before iterating
      value[ key ] = list( value[ key ] )

    if isinstance( value[ key ], dict ):
      _fromPythonMap( value[ key ] )

    elif isinstance( value[ key ], list ):
      for index in range( 0, len( value[ key ] ) ):
        value[ key ][ index ] = _fromPythonMap_converter( value[ key ][ index ] )

    else:
      value[ key ] = _fromPythonMap_converter( value[ key ] )


class Converter():
  def __init__( self, uri ):
    self.uri = uri

  def _toPython( self, paramater, cinp_value, transaction ):
    if paramater.type == 'String':
      if cinp_value is None:
        return None

      cinp_value = str( cinp_value )
      if paramater.length is not None and len( cinp_value ) > paramater.length:
        raise ValueError( 'Value to long' )

      return cinp_value

    if paramater.type == 'Integer':
      if cinp_value is None or cinp_value == '':
        return None

      try:
        return int( cinp_value )
      except ( TypeError, ValueError ):
        raise ValueError( 'Unable to convert to an int' )

    if paramater.type == 'Float':
      if cinp_value is None or cinp_value == '':
        return None

      try:
        return float( cinp_value )
      except ( TypeError, ValueError ):
        raise ValueError( 'Unable to convert to an float' )

    if paramater.type == 'Boolean':
      if cinp_value is None or cinp_value == '':
        return None

      if isinstance( cinp_value, bool ):
        return cinp_value

      cinp_value = str( cinp_value ).lower()

      if cinp_value in ( 'true', 't', '1' ):
        return True

      if cinp_value in ( 'false', 'f', '0' ):
        return False

      raise ValueError( 'Unable to convert to boolean' )

    if paramater.type == 'DateTime':
      if cinp_value is None or cinp_value == '':
        return None

      try:
        return dateutil.parser.parse( cinp_value )
      except ( AttributeError, ValueError ):
        raise ValueError( 'DateUtil value must be a string in a format dateutil can understand' )

    if paramater.type == 'Map':
      if cinp_value is None or cinp_value == '':
        return {}

      if not isinstance( cinp_value, dict ):
        raise ValueError( 'Map must be a dict' )

      return cinp_value

    if paramater.type == 'Model':
      if cinp_value is None or cinp_value == '':
        return None

      ( path, model, action, id_list, multi ) = self.uri.split( cinp_value )

      if self.uri.build( path, model ) != paramater.model.path:
        raise ValueError( 'Object "{0}" is for a model other than "{1}"'.format( cinp_value, paramater.model.path )  )

      result = transaction.get( paramater.model, id_list[0] )   # TODO: handle multi id id_lists  right
      if result is None:
        raise ValueError( 'Object "{0}" for model "{1}" NotFound'.format( cinp_value, paramater.model.path ) )

      return result

    if paramater.type == 'File':
      if cinp_value is None or cinp_value == '':
        return None

      raise Exception( 'Unimplemented' )

    raise Exception( 'Unknown type "{0}"'.format( self.type ) )

  def _fromPython( self, paramater, python_value ):
    if paramater.type == 'String':
      if python_value is None:
        return None

      python_value = str( python_value )
      if paramater.length is not None and len( python_value ) > paramater.length:
        raise ValueError( 'String value to long' )

      return str( python_value )

    if paramater.type == 'Boolean':
      if python_value is None:
        return None

      return str( python_value  )

    if paramater.type == 'Integer':
      if python_value is None:
        return None

      try:
        return int( python_value )
      except ( TypeError, ValueError ):
        raise ValueError( 'Invalid int' )

    if paramater.type == 'Float':
      if python_value is None:
        return None

      try:
        return float( python_value )
      except ( TypeError, ValueError ):
        raise ValueError( 'Invalid float' )

    if paramater.type == 'DateTime':
      if python_value is None:
        return None

      return python_value.isoformat()

    if paramater.type == 'Map':
      if python_value is None:
        return None

      if not isinstance( python_value, dict ):
        raise ValueError( 'Map must be dict' )

      result = python_value.copy()
      _fromPythonMap( result )

      return result

    if paramater.type == 'Model':
      if python_value is None:
        return None

      return '{0}:{1}:'.format( paramater.model.path, python_value.pk )

    if paramater.type == 'File':
      if python_value is None:
        return None

      raise Exception( 'Unimplemented' )

    raise Exception( 'Unknown type "{0}"'.format( self.type ) )

  def toPython( self, paramater, cinp_value, transaction ):
    if paramater.type is None:
      return None

    if paramater.is_array:
      if cinp_value is None or cinp_value == '':
        return []

      if not isinstance( cinp_value, list ):
        raise ValueError( 'Must be an Array/List, got "{0}"'.format( type( cinp_value ).__name__ ) )

      result = []
      for value in cinp_value:
        result.append( self._toPython( paramater, value, transaction ) )

      return result

    else:
      return self._toPython( paramater, cinp_value, transaction )

  def fromPython( self, paramater, python_value ):
    if paramater.type is None:
      return None

    if paramater.is_array:
      result = []
      if paramater.type == 'Model':
        python_value = list( python_value.all() )  # django specific again, and really should only get the pk

      if not isinstance( python_value, list ):
        raise ValueError( 'Must be an Array/List, got "{0}"'.format( type( python_value ).__name__ ) )

      for value in python_value:
        result.append( self._fromPython( paramater, value ) )

      return result

    else:
      return self._fromPython( paramater, python_value )


class Paramater():
  def __init__( self, type, name=None, is_array=False, doc=None, length=None, model=None, model_resolve=None, choice_list=None, default=None ):
    super().__init__()
    self.name = name
    self.doc = doc
    if type is None:
      self.type = None

    else:
      if type not in FIELD_TYPE_LIST:
        raise ValueError( 'Unknown field type "{0}"'.format( type ) )

      if type == 'String':
        self.length = length

      elif type == 'Model':
        if model is None:
          raise ValueError( 'model is requred for Model type' )

        if not isinstance( model, Model ):
          if model_resolve is None:
            raise ValueError( 'must provide model_resolve for late model resolution if model is not of type Model' )
          else:
            self.model_resolve = model_resolve

        self.model = model

      self.type = type
      self.is_array = is_array
      self.choice_list = choice_list
      self.default = default

  def describe( self ):
    result = { 'name': self.name, 'type': self.type }
    if self.doc is not None:
      result[ 'doc' ] = self.doc

    if self.type == 'String':
      result[ 'length' ] = self.length

    if self.type == 'Model':
      result[ 'uri' ] = self.model.path

    if self.type is not None:
      if self.choice_list:
        result[ 'choices' ] = self.choice_list
      if self.is_array:
        result[ 'is_array' ] = True
      if self.default is not None:
        result[ 'default' ] = self.default

    return result


class Field( Paramater ):
  def __init__( self, mode='RW', required=True, *args, **kwargs ):
    if mode not in ( 'RW', 'RC', 'RO' ):
      raise ValueError( 'Mode must be RW, RC, or RO' )

    super().__init__( *args, **kwargs )
    self.mode = mode
    self.required = required

  def describe( self ):
    result = super().describe()
    result[ 'mode' ] = self.mode
    result[ 'required' ] = self.required

    return result


class Element():
  def __init__( self, name, doc='' ):
    if name is None:
      raise ValueError( 'name is required' )
    super().__init__()
    self.parent = None
    self.name = name
    self.doc = doc

  @property
  def path( self ):
    return None

  def getElement( self, path ):
    return None

  def startTransaction( self ):
    raise InvalidRequest( 'No Transaction to start' )

  def describe( self ):
    raise InvalidRequest( 'Not DESCRIBE able' )

  def get( self, converter, transaction, id_list, multi ):
    raise InvalidRequest( 'Not GET able' )

  def list( self, converter, transaction, data, header_map ):
    raise InvalidRequest( 'Not LIST able' )

  def create( self, converter, transaction, data ):
    raise InvalidRequest( 'Not CREATE able' )

  def update( self, converter, transaction, id_list, data, multi ):
    raise InvalidRequest( 'Not UPDATE able' )

  def delete( self, transaction, id_list ):
    raise InvalidRequest( 'Not DELETE able' )

  def call( self, converter, transaction, id_list, data, multi ):
    raise InvalidRequest( 'Not CALL able' )

  def options( self ):
    raise InvalidRequest( 'Not OPTION able' )

  @staticmethod
  def checkAuth( user, method, id_list ):
    raise ValueError( 'checkAuth not implemented' )


class Namespace( Element ):
  def __init__( self, name, version, root_path=None, *args, **kwargs ):  # set name and parent to None for a root node
    if name == 'root':
      raise ValueError( 'namespace name "root" is reserved' )

    if name is None:
      if root_path is None:
        raise ValueError( 'root_path is required when name is None (for root namespace)' )
      if root_path[0] != '/' or root_path[-1] != '/':
        raise ValueError( 'root_path must start and end with "/"' )
      self.root_path = root_path
      name = 'root'

    super().__init__( name=name, *args, **kwargs )
    self.version = version
    self.element_map = {}

  @property
  def path( self ):
    if self.name == 'root':
      return self.root_path

    if self.parent is None:
      return None

    return '{0}{1}/'.format( self.parent.path, self.name )

  def getElement( self, path ):
    if isinstance( path, tuple ) and self.name == 'root':  # tuple is ( path, model, action .... )
      new_path = path[0]
      if path[1] is not None:
        new_path.append( path[1] )
        if path[2] is not None:
          new_path.append( path[2] )

      path = new_path

    if path is None or len( path ) < 1:
      return self

    if not isinstance( path, list ):
      raise ValueError( 'getElement must be called with a list of the path parts, or a tuple from URI.split()' )

    try:
      return self.element_map[ path[0] ].getElement( path[ 1: ] )
    except KeyError:
      return None

  def addElement( self, element ):
    if not isinstance( element, ( Namespace, Model ) ):
      raise ValueError( 'element must be of type Namespace or Model' )

    element.parent = self
    self.element_map[ element.name ] = element

  def describe( self ):
    data = { 'name': self.name, 'path': self.path, 'api-version': self.version, 'multi-uri-max': __MULTI_URI_MAX__, 'doc': self.doc }
    namespace_list = []
    model_list = []
    for name in self.element_map:
      element = self.element_map[ name ]
      if isinstance( element, Namespace ):
        namespace_list.append( element.path )
      elif isinstance( element, Model ):
        model_list.append( element.path )
      else:
        raise ValueError( 'Unknown Element type in element_map "{0}"'.format( element ) )

    data[ 'namespaces' ] = namespace_list
    data[ 'models' ] = model_list
    return Response( 200, data=data, header_map={ 'Method': 'DESCRIBE', 'Type': 'Namespace', 'Cache-Control': 'max-age=0' } )

  def options( self ):
    header_map = {}
    header_map[ 'Allow' ] = 'OPTIONS, DESCRIBE'
    header_map[ 'Cache-Control' ] = 'max-age=0'

    return Response( 200, data=None, header_map=header_map )


class Model( Element ):
  def __init__( self, field_list, transaction_class, list_filter_map=None, constant_list=None, not_allowed_method_list=None, *args, **kwargs ):
    super().__init__( *args, **kwargs )
    self.transaction_class = transaction_class
    self.field_map = {}
    for field in field_list:
      if not isinstance( field, Field ):
        raise ValueError( 'field must be of type Field' )

      self.field_map[ field.name ] = field

    self.action_map = {}
    self.list_filter_map = list_filter_map or {}  # TODO: check list_filter_map  for  saninty, should  be [ filter_name ][ paramater_name ] = Paramater
    self.constant_list = constant_list or []
    self.not_allowed_method_list = []
    for method in not_allowed_method_list or []:
      if method == 'OPTIONS':
        raise ValueError( 'Can not block OPTIONS method' )
      if method not in ( 'GET', 'LIST', 'CALL', 'CREATE', 'UPDATE', 'DELETE', 'DESCRIBE' ):
        raise ValueError( 'Invalid blocked Method "{0}"'.format( method ) )
      self.not_allowed_method_list.append( method )

  @property
  def path( self ):
    if self.parent is None:
      return None

    return '{0}{1}'.format( self.parent.path, self.name )

  def getElement( self, path ):
    if path is None or len( path ) < 1:
      return self

    if len( path ) != 1:
      raise ValueError( 'Invalid Path for an action "{0}"'.format( path ) )

    try:
      return self.action_map[ path[0] ]
    except KeyError:
      return None

  def addAction( self, action ):
    if not isinstance( action, Action ):
      raise ValueError( 'action must be of type Action' )

    action.parent = self
    self.action_map[ action.name ] = action

  def describe( self ):
    data = { 'name': self.name, 'path': self.path, 'doc': self.doc }
    data[ 'constants' ] = self.constant_list
    data[ 'fields' ] = [ item.describe() for item in self.field_map.values() ]
    data[ 'actions' ] = [ item.path for item in self.action_map.values() ]
    data[ 'not-allowed-metods' ] = self.not_allowed_method_list
    data[ 'list-filters' ] = {}
    for name in self.list_filter_map:
      data[ 'list-filters' ][ name ] = [ item.describe() for item in self.list_filter_map[ name ].values() ]

    return Response( 200, data=data, header_map={ 'Method': 'DESCRIBE', 'Type': 'Model', 'Cache-Control': 'max-age=0' } )

  def options( self ):
    header_map = {}
    header_map[ 'Allow' ] = 'OPTIONS, DESCRIBE, GET, LIST, CREATE, UPDATE, DELETE'

    return Response( 200, data=None, header_map=header_map )

  def _asDict( self, converter, target_object ):  # yes this is a bit of a hack, would be best if the transaction did this.  This iteration is really for django with a unittest pass through
    if target_object is None:
      return None

    if isinstance( target_object, dict ):
      return target_object

    result = {}
    for field_name in self.field_map:
      try:
        result[ field_name ] = converter.fromPython( self.field_map[ field_name ], getattr( target_object, field_name ) )
      except ValueError as e:
        raise ValueError( 'Error with "{0}": "{1}"'.format( field_name, str( e ) ) )
      except AttributeError:
        raise ServerError( 'taret_object missing field "{0}"'.format( field_name ) )  # yes, internal server error, target_object comes from inside the house

    return result

  def _get( self, transaction, object_id ):
    result = transaction.get( self, object_id )
    if result is None:
      raise ObjectNotFound( self.path, object_id )

    return result

  def get( self, converter, transaction, id_list, multi ):
    result = {}
    if multi:
      for object_id in id_list:
        result[ '{0}:{1}:'.format( self.path, object_id ) ] = self._asDict( converter, self._get( transaction, object_id ) )

    else:
      result = self._asDict( converter, self._get( transaction, id_list[0] ) )

    return Response( 200, data=result, header_map={ 'Method': 'GET', 'Cache-Control': 'no-cache', 'Multi-Object': str( multi ) } )

  def list( self, converter, transaction, data, header_map ):
    if data is not None and not isinstance( data, dict ):
      raise InvalidRequest( 'LIST data must be a dict or None' )

    filter_name = header_map.get( 'FILTER', None )
    try:
      count = int( header_map.get( 'COUNT', 10 ) )
      position = int( header_map.get( 'POSITION', 0 ) )
    except ValueError:
      raise InvalidRequest( 'Count and Position must be integers if specified' )
    filter_values = {}

    if filter_name is not None:
      try:
        paramater_map = self.list_filter_map[ filter_name ]
      except KeyError:
        raise InvalidRequest( 'Invalid Filter Name "{0}"'.format( filter_name ) )

      for name in paramater_map:
        paramater = paramater_map[ name ]
        try:
          filter_values[ name ] = converter.toPython( paramater, data[ name ], transaction )
        except ValueError as e:
          raise InvalidRequest( 'Invalid Value "{0}" for list filter paramater "{1}" of filter "{2}"'.format( str( e ), name, filter_name ) )
        except KeyError:
          raise InvalidRequest( 'Filter paramater "{0}" of filter "{1}" missing'.format( name, filter_name ) )

    try:
      result = transaction.list( self, filter_name, filter_values, position, count )
    except ValueError as e:
      if isinstance( e.args[0], dict ):
        raise InvalidRequest( data=e.args[0] )
      else:
        raise InvalidRequest( str( e ) )

    if not isinstance( result, tuple ) and len( result ) != 3:
      raise ServerError( 'List result is not a valid tuple' )

    ( id_list, position, total ) = result
    return Response( 200, data=[ '{0}:{1}:'.format( self.path, item ) for item in id_list ], header_map={ 'Method': 'LIST', 'Cache-Control': 'no-cache', 'Count': str( len( id_list ) ), 'Position': str( position ), 'Total': str( total ) } )

  def create( self, converter, transaction, data ):
    if not isinstance( data, dict ):
      raise InvalidRequest( 'CREATE data must be a dict' )

    value_map = {}
    update_value_map = {}
    error_map = {}
    for field_name in data:  # first make sure the fields are ok to look at
      try:
        field = self.field_map[ field_name ]
      except KeyError:
        # if someone is messing with us, just InvalidRequest Immeditally, otherwise make a list and let the client try and fix as many at the same time as possible
        raise InvalidRequest( 'no field named "{0}"'.format( field_name ) )

      if field.mode not in ( 'RW', 'RC' ):
        error_map[ field_name ] = 'Not Writeable'

    for field_name in self.field_map:  # now let's import the values
      field = self.field_map[ field_name ]
      if field.mode not in ( 'RW', 'RC' ):
        continue

      try:
        if field.is_array and field.type == 'Model':
          update_value_map[ field_name ] = converter.toPython( field, data[ field_name ], transaction )
        else:
          value_map[ field_name ] = converter.toPython( field, data[ field_name ], transaction )
      except ValueError as e:
        error_map[ field_name ] = 'Invalid Value "{0}"'.format( str( e ) )
      except KeyError:
        if field.required:
          error_map[ field_name ] = 'Required Field'
        else:
          value_map[ field_name ] = field.default

    if error_map != {}:
      raise InvalidRequest( data=error_map )

    try:
      result = transaction.create( self, value_map )
    except ValueError as e:
      if isinstance( e.args[0], dict ):
        raise InvalidRequest( data=e.args[0] )
      else:
        raise InvalidRequest( str( e ) )

    if not isinstance( result, tuple ) and len( result ) != 2:
      raise ServerError( 'Create result is not a valid tuple' )

    ( object_id, result ) = result

    if update_value_map:
      try:
        result = self._asDict( converter, transaction.update( self, object_id, update_value_map ) )
      except ValueError as e:
        if isinstance( e.args[0], dict ):
          raise InvalidRequest( data=e.args[0] )
        else:
          raise InvalidRequest( str( e ) )

      if result is None:
        raise ServerError( 'Newly created object disapeared' )

    else:
      result = self._asDict( converter, result )

    return Response( 201, data=result, header_map={ 'Method': 'CREATE', 'Cache-Control': 'no-cache', 'Object-Id': '{0}:{1}:'.format( self.path, object_id ) } )

  def _update( self, converter, transaction, object_id, value_map ):
    try:
      result = self._asDict( converter, transaction.update( self, object_id, value_map ) )
    except ValueError as e:
      if isinstance( e.args[0], dict ):
        raise InvalidRequest( data=e.args[0] )
      else:
        raise InvalidRequest( str( e ) )

    if result is None:
      raise ObjectNotFound( self.path, object_id )

    return result

  def update( self, converter, transaction, id_list, data, multi ):
    if not isinstance( data, dict ):
      raise InvalidRequest( 'UPDATE data must be a dict' )

    value_map = {}
    error_map = {}
    for field_name in data:  # first make sure the fields are ok to look at
      try:
        field = self.field_map[ field_name ]
      except KeyError:
        # if someone is messing with us, just InvalidRequest Immeditally, otherwise make a list and let the client try and fix as many at the same time as possible
        raise InvalidRequest( 'no field named "{0}"'.format( field_name ) )

      if field.mode != 'RW':
        error_map[ field_name ] = 'Not Writeable'

    for field_name in self.field_map:  # now let's import the values
      field = self.field_map[ field_name ]
      if field.mode != 'RW':
        continue

      try:
        value_map[ field_name ] = converter.toPython( field, data[ field_name ], transaction )
      except ValueError as e:
        error_map[ field_name ] = 'Invalid Value "{0}"'.format( str( e ) )
      except KeyError:
        pass

    if error_map != {}:
      raise InvalidRequest( data=error_map )

    result = {}
    if multi:
      for object_id in id_list:
        result[ '{0}:{1}:'.format( self.path, object_id ) ] = self._update( converter, transaction, object_id, value_map )

    else:
      result = self._update( converter, transaction, id_list[0], value_map )

    return Response( 200, data=result, header_map={ 'Method': 'UPDATE', 'Cache-Control': 'no-cache', 'Multi-Object': str( multi ) } )

  def delete( self, transaction, id_list ):
    for object_id in id_list:
      if transaction.delete( self, object_id ) is False:
        raise ObjectNotFound( self.path, object_id )

    return Response( 200, header_map={ 'Method': 'DELETE', 'Cache-Control': 'no-cache' } )


class Action( Element ):
  def __init__( self, func, return_paramater=None, paramater_list=None, static=True, *args, **kwargs ):
    if return_paramater is not None and not isinstance( return_paramater, Paramater ):
      raise ValueError( 'return_paramater must be a Paramater' )

    super().__init__( *args, **kwargs )
    self.func = func
    self.paramater_map = {}
    for paramater in paramater_list or []:
      if not isinstance( paramater, Paramater ):
        raise ValueError( 'paramater must be of type Paramater' )

      self.paramater_map[ paramater.name ] = paramater

    if return_paramater is None:
      self.return_paramater = Paramater( name=None, type=None )
    else:
      return_paramater.name = None
      self.return_paramater = return_paramater

    self.static = static

  @property
  def path( self ):
    if self.parent is None:
      return None

    return '{0}({1})'.format( self.parent.path, self.name )

  def describe( self ):
    return_type = self.return_paramater.describe()
    del return_type[ 'name' ]
    data = { 'name': self.name, 'path': self.path, 'doc': self.doc, 'return-type': return_type, 'static': self.static }
    data[ 'paramaters' ] = [ item.describe() for item in self.paramater_map.values() ]

    return Response( 200, data=data, header_map={ 'Method': 'DESCRIBE', 'Type': 'Action', 'Cache-Control': 'max-age=0' } )

  def call( self, converter, transaction, id_list, data, multi ):
    error_map = {}
    value_map = {}
    for paramater_name in self.paramater_map:  # should we be ignorning data?
      paramater = self.paramater_map[ paramater_name ]
      try:
        value_map[ paramater_name ] = converter.toPython( paramater, data[ paramater_name ], transaction )
      except KeyError:
        value_map[ paramater_name ] = paramater.default
      except ValueError as e:
        error_map[ paramater_name ] = 'Invalid Value "{0}"'.format( str( e ) )

    if error_map != {}:
      raise InvalidRequest( data=error_map )

    result = {}
    if id_list:
      if self.static:
        raise InvalidRequest( 'Static Actions should not be passed ids' )

      try:
        if multi:
          for object_id in id_list:
            result[ '{0}:{1}:'.format( self.parent.path, object_id ) ] = converter.fromPython( self.return_paramater, self.func( self.parent._get( transaction, object_id ), **value_map ) )
        else:
          result = converter.fromPython( self.return_paramater, self.func( self.parent._get( transaction, id_list[0] ), **value_map ) )
      except ValueError as e:
        raise InvalidRequest( str( e ) )

    else:
      if not self.static:
        raise InvalidRequest( 'Non-Static Actions should be passed ids' )

      try:
        result = converter.fromPython( self.return_paramater, self.func( **value_map ) )
      except ValueError as e:
        raise InvalidRequest( 'Invalid Result Value: "{0}"'.format( str( e ) ) )

    return Response( 200, data=result, header_map={ 'Method': 'CALL', 'Cache-Control': 'no-cache', 'Multi-Object': str( multi ) } )

  def options( self ):
    header_map = {}
    header_map[ 'Allow' ] = 'OPTIONS, DESCRIBE, CALL'

    return Response( 200, data=None, header_map=header_map )


class Server():
  def __init__( self, root_path, root_version, debug=False, cors_allow_list=None ):
    super().__init__()
    self.uri = URI( root_path )
    self.converter = Converter( self.uri )
    self.debug = debug
    self.root_namespace = Namespace( name=None, version=root_version, root_path=root_path )
    self.root_namespace.checkAuth = lambda user, method, id_list: True
    self.cors_allow_list = cors_allow_list
    self.path_handlers = {}

  def getUser( self, auth_id, auth_token ):
    raise ValueError( 'getUser not implemented' )

  def _validateModel( self, model ):
    for field_name in model.field_map:
      field = model.field_map[ field_name ]
      if field.type == 'Model' and hasattr( field, 'model_resolve' ):
        ( mode, is_array, new_model ) = field.model_resolve( field.model )  # this is django specific again
        del field.model_resolve
        if not isinstance( new_model, Model ):
          raise ValueError( 'late resolved model is not a Model: "{0}" from "{1}"'.format( new_model, field.model ) )

        if mode is not None:
          field.mode = mode
        if is_array is not None:
          field.is_array = is_array

        field.model = new_model

      for action_name in model.action_map:
        action = model.action_map[ action_name ]
        paramater_map = action.paramater_map
        for paramater_name in paramater_map:
          paramater = paramater_map[ paramater_name ]
          if paramater.type == 'Model' and hasattr( paramater, 'model_resolve' ):
            ( _, _, new_model ) = paramater.model_resolve( paramater.model )  # this is django specific again
            del paramater.model_resolve
            if not isinstance( new_model, Model ):
              raise ValueError( 'late resolved model is not a Model: "{0}" from "{1}"'.format( new_model, field.model ) )

            paramater.model = new_model

      for filter_name in model.list_filter_map:
        paramater_map = model.list_filter_map[ filter_name ]
        for paramater_name in paramater_map:
          paramater = paramater_map[ paramater_name ]
          if paramater.type == 'Model' and hasattr( paramater, 'model_resolve' ):
            new_model = paramater.model_resolve( paramater.model )  # this is django specific again
            del paramater.model_resolve
            if not isinstance( new_model, Model ):
              raise ValueError( 'late resolved model is not a Model: "{0}" from "{1}"'.format( new_model, field.model ) )

            paramater.model = new_model

  def _validateNamespace( self, namespace ):
    for name in namespace.element_map:
      element = namespace.element_map[ name ]
      if isinstance( element, Namespace ):
        self._validateNamespace( element )
      elif isinstance( element, Model ):
        self._validateModel( element )
      else:
        raise ValueError( 'Unknown element in element_map: "{0}"'.format( element ) )

  def validate( self ):
    self._validateNamespace( self.root_namespace )

  def handle( self, request ):
    response = None
    try:
      for path in self.path_handlers:
       if request.uri.startswith( path ):
         response = self.path_handlers[ path ]( request )
         break

    except Exception as e:
      if self.debug:
        response = Response( 500, data={ 'message': 'Path Handler Exception ({0})"{1}"'.format( type( e ).__name__, str( e ) ), 'trace': traceback.format_exc() } )
      else:
        response = Response( 500, data={ 'message': 'Path Handler Exception ({0})"{1}"'.format( type( e ).__name__, str( e ) ) } )

    if response is None:
      try:
        response = self.dispatch( request )

      except ObjectNotFound as e:
        response = e.asResponse()

      except InvalidRequest as e:
        response = e.asResponse()

      except ServerError as e:
        response = e.asResponse()

      except NotAuthorized:
        response = Response( 403, data={ 'message': 'Not Authorized' } )

      except Exception as e:
        if self.debug:
          response = Response( 500, data={ 'message': 'Exception ({0})"{1}"'.format( type( e ).__name__, str( e ) ), 'trace': traceback.format_exc() } )
        else:
          response = Response( 500, data={ 'message': 'Exception ({0})"{1}"'.format( type( e ).__name__, str( e ) ) } )

    response.header_map[ 'Cinp-Version' ] = __CINP_VERSION__
    if self.cors_allow_list is not None:
      response.header_map[ 'Access-Control-Allow-Origin' ] = ', '.join( self.cors_allow_list )
      response.header_map[ 'Access-Control-Expose-Headers' ] = 'Method, Type, Cinp-Version, Count, Position, Total, Multi-Object, Object-Id'  # TODO: probably should only list the ones actually sent

    return response

  def dispatch( self, request ):
    if request.method not in ( 'GET', 'LIST', 'CALL', 'CREATE', 'UPDATE', 'DELETE', 'DESCRIBE', 'OPTIONS' ):
      return Response( 400, data={ 'message': 'Invalid HTTP Method "{0}"'.format( request.method ) } )

    try:
      ( path, model, action, id_list, multi ) = self.uri.split( request.uri )
    except ValueError as e:
      return Response( 400, data={ 'message': 'Unable to Parse "{0}"'.format( request.uri ) } )

    if id_list is not None and len( id_list ) > __MULTI_URI_MAX__:
      raise InvalidRequest( 'id_list longer than supported length of "{0}"'.format( __MULTI_URI_MAX__ ) )

    element = self.root_namespace.getElement( ( path, model, action ) )
    if element is None:
      return Response( 404, 'path not found "{0}"'.format( request.uri ) )
    if not isinstance( element, Element ):
      return Response( 500, 'confused, path ("{0}") yeilded non element "{1}"'.format( request.uri, element ) )

    if request.method == 'OPTIONS':  # options never need auth, nor is the Cinp-Version header required, we can take care of it early
      response = element.options()
      if self.cors_allow_list is not None:
        response.header_map[ 'Access-Control-Allow-Methods' ] = response.header_map[ 'Allow' ]
        response.header_map[ 'Access-Control-Allow-Headers' ] = 'Accept, Cinp-Version, Auth-Id, Auth-Token, Filter, Content-Type, Count, Position, Multi-Object'

      return response

    if request.header_map.get( 'CINP-VERSION', None ) != __CINP_VERSION__:
      return Response( 400, data={ 'message': 'Invalid CInP Protocol Version' } )

    if ( action is not None ) and ( request.method not in ( 'CALL', 'DESCRIBE' ) ):
      raise InvalidRequest( 'Invalid method "{0}" for request with action'.format( request.method ) )

    if request.method in ( 'CALL', ) and not isinstance( element, Action ):
      raise InvalidRequest( 'Method "{0}" requires action'.format( request.method ) )

    if ( id_list is not None ) and ( request.method not in ( 'GET', 'UPDATE', 'DELETE', 'CALL' ) ):
      raise InvalidRequest( 'Invalid method "{0}" for request with id'.format( request.method ) )

    if ( request.method in ( 'GET', 'UPDATE', 'DELETE' ) ) and ( id_list is None ):
      raise InvalidRequest( 'Method "{0}" requires id'.format( request.method ) )

    if ( request.data is not None ) and ( request.method not in ( 'LIST', 'UPDATE', 'CREATE', 'CALL' ) ):
      raise InvalidRequest( 'Invalid method "{0}" for request with data'.format( request.method ) )

    if (request.method in ( 'UPDATE', 'CREATE' ) ) and ( request.data is None ):
      raise InvalidRequest( 'Method "{0}" requires data'.format( request.method ) )

    if ( request.method in ( 'GET', 'LIST', 'UPDATE', 'CREATE', 'DELETE' ) ) and not isinstance( element, Model ):
      raise InvalidRequest( 'Method "{0}" requires model'.format( request.method ) )

    if ( isinstance( element, Model ) and ( request.method in element.not_allowed_method_list ) ) or ( isinstance( element, Action ) and ( request.method in element.parent.not_allowed_method_list ) ):
      raise NotAuthorized()

    multi = id_list is not None and len( id_list ) > 1
    multi_header = request.header_map.get( 'MULTI-OBJECT', None )
    if multi_header is not None:
      if multi_header.upper() == 'TRUE':
        multi = True
      elif multi:
        raise InvalidRequest( 'requested non multi-object, however multiple ids where sent' )

    auth_id = request.header_map.get( 'AUTH-ID', None )
    auth_token = request.header_map.get( 'AUTH-TOKEN', None )
    if auth_id is not None and auth_token is not None:
      user = self.getUser( auth_id, auth_token )
      if user is None:
        return Response( 401, data={ 'message': 'Invalid Session' } )

    else:
      user = AnonymouseUser()

    if not user.isSuperuser:
      if not element.checkAuth( user, request.method, id_list ):
        raise NotAuthorized()

    if request.method == 'DESCRIBE':
      return element.describe()

    result = None
    if isinstance( element, Action ):
      transaction = element.parent.transaction_class()
    else:
      transaction = element.transaction_class()

    try:
      if request.method == 'GET':
        result = element.get( self.converter, transaction, id_list, multi )

      elif request.method == 'LIST':
        result = element.list( self.converter, transaction, request.data, request.header_map )

      # some CREATE thoughts
      #    pass back the re_id has a header
      #    allow list of dicts to create more than one at a time
      #    if multi create, then mutli-object header options
      #    if multi create, return values like multi GET
      elif request.method == 'CREATE':
        result = element.create( self.converter, transaction, request.data )

      elif request.method == 'UPDATE':
        result = element.update( self.converter, transaction, id_list, request.data, multi )

      if request.method == 'DELETE':
        result = element.delete( transaction, id_list )

      elif request.method == 'CALL':
        result = element.call( self.converter, transaction, id_list, request.data, multi )

    except Exception as e:
      transaction.abort()
      raise e

    if result is None:
      transaction.abort()
      return Response( 500, 'Confused,  method "{0}"'.format( request.method ) )

    transaction.commit()
    return result

  def registerNamespace( self, path, namespace ):
    parent = None
    try:
      parent = self.root_namespace.getElement( self.uri.split( path, root_optional=True ) )
    except ValueError:
      pass

    if parent is None:
      raise ValueError( 'path "{0}" is not found'.format( path ) )

    parent.addElement( namespace )

  def registerPathHandler( self, path, handler ):
    if path.startswith( self.uri.root_path ):
      raise ValueError( 'path can not be in the api root path' )

    self.path_handlers[ path ] = handler


class Request():
  def __init__( self, method, uri, header_map ):
    super().__init__()
    self.method = method
    self.uri = uri  # make sure the query string/fragment/etc has allreay been stripped by the Child Class
    self.header_map = {}
    for name in header_map:
      if name in ( 'CINP-VERSION', 'AUTH-ID', 'AUTH-TOKEN', 'CONTENT-TYPE', 'FILTER', 'POSITION', 'COUNT', 'MULTI-OBJECT' ):
        self.header_map[ name ] = header_map[ name ]

    self.data = None

  def fromText( self, buff ):
    pass

  def fromJSON( self, buff ):
    buff = buff.strip()
    if not buff:
      self.data = None
    else:
      try:
        self.data = json.loads( buff )
      except ValueError as e:
        self.data = None
        raise InvalidRequest( 'Error Parsing JSON Request data: "{0}"'.format( e ) )

    def fromXML( self, buff ):
      pass


class Response():
  def __init__( self, http_code, data=None, header_map=None, content_type='json' ):
    super().__init__()
    self.content_type = content_type
    self.http_code = http_code
    self.data = data
    self.header_map = header_map or {}

  def buildNativeResponse( self ):
    if self.content_type == 'json':
      return self.asJSON()
    elif self.content_type == 'xml':
      return self.asXML()

    return self.asText()

  def asText( self ):
    return None

  def asJSON( self ):
    return None

  def asXML( self ):
    return None
