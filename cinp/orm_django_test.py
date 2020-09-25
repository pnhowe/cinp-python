import pytest

from django.conf import settings
from django.db import models
from django.core.management import call_command

from cinp.orm_django import DjangoCInP
from cinp.server_common import Server, Request

#  The checkAuth lambda/eval mess has a way of trying to use the last checkAuth in
#  for everything (or everything in that model.py), make sure there is a test to guard
#  aginst that


class MockServer( Server ):
  def __init__( self, cinp ):
    super().__init__( root_path='/', root_version='0.0' )
    self.registerNamespace( '/', cinp.getNamespace( '/' ) )
    self.validate()

  def getTestNS( self, name ):
    return self.root_namespace.element_map[ name ]


def _ns_compare( ns, target, child_map ):
  assert ns.name == target[0]
  assert ns.version == target[1]
  assert ns.doc == target[2]
  assert ns.element_map.keys() == child_map.keys()
  for name, element in ns.element_map.items():
    _model_compare( element, child_map[ name ] )


def _model_compare( model, target ):
  assert model.name == target[0]
  assert model.doc == target[1]
  assert model.list_filter_map == target[2]
  assert model.constant_set_map == target[3]
  assert model.not_allowed_verb_list == target[4]
  for i in range( 0, len( target[5] ) ):
    field = model.field_map[target[5][i][0]]
    assert field.name == target[5][i][0]
    assert field.doc == target[5][i][1]
    assert field.type == target[5][i][2]
    assert field.mode == target[5][i][3]
    assert field.required == target[5][i][4]
    assert field.is_array == target[5][i][5]
    assert field.choice_list == target[5][i][6]
    assert field.default == target[5][i][7]
    if field.type == 'Model':
      assert field.model.name == target[5][i][8]

  # model.action_map = {}


def test_constructor():
  cinp = DjangoCInP( 'Bob' )
  assert cinp.name == 'Bob'
  assert cinp.version == '0.0'
  assert cinp.doc == ''
  ns = cinp.getNamespace( '/' )
  assert ns.converter.__class__.__name__ == 'DjangoConverter'
  _ns_compare( cinp.getNamespace( '/' ), ( 'Bob', '0.0', '' ), {} )

  cinp = DjangoCInP( 'Candice', '4.2', 'The Ultimate Model' )
  assert cinp.name == 'Candice'
  assert cinp.version == '4.2'
  assert cinp.doc == 'The Ultimate Model'
  _ns_compare( cinp.getNamespace( '/' ), ( 'Candice', '4.2', 'The Ultimate Model' ), {} )


@pytest.mark.django_db
def test_simple_model():
  cinp = DjangoCInP( 'Simple', '0.1' )

  @cinp.model()
  class Simon( models.Model ):
    """
    Simple Simon
    """
    name = models.CharField( max_length=20 )
    description = models.CharField( max_length=100, help_text='bob stuff' )

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  srv = MockServer( cinp )

  _ns_compare( srv.getTestNS( 'Simple' ), ( 'Simple', '0.1', '' ), {
                        'test_simple_model.<locals>.Simon':
                        ( 'test_simple_model.<locals>.Simon', 'Simple Simon', {}, {}, [], [
                          ( 'name', '', 'String', 'RW', True, False, None, None ),
                          ( 'description', 'bob stuff', 'String', 'RW', True, False, None, None )
                          ] ) } )

  r = srv.dispatch( Request( uri='/', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.0', 'models': [], 'multi-uri-max': 100, 'name': 'root', 'namespaces': ['/Simple/'], 'path': '/' }

  r = srv.dispatch( Request( uri='/Simple', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.1', 'models': ['/Simple/test_simple_model.<locals>.Simon'], 'multi-uri-max': 100, 'name': 'Simple', 'namespaces': [], 'path': '/Simple/' }

  r = srv.dispatch( Request( uri='/Simple/test_simple_model.<locals>.Simon', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.data == {
                      'actions': [],
                      'constants': {},
                      'doc': 'Simple Simon',
                      'fields': [{'default': None,
                                  'length': 20,
                                  'mode': 'RW',
                                  'name': 'name',
                                  'required': True,
                                  'type': 'String'},
                                 {'default': None,
                                  'doc': 'bob stuff',
                                  'length': 100,
                                  'mode': 'RW',
                                  'name': 'description',
                                  'required': True,
                                  'type': 'String'}],
                      'list-filters': {},
                      'name': 'test_simple_model.<locals>.Simon',
                      'not-allowed-methods': [],
                      'path': '/Simple/test_simple_model.<locals>.Simon'
                    }
  assert r.http_code == 200

  # TODO: can't figure out how to "migrate" and create the table
  # req = Request( uri='/Simple/test_simple_model.<locals>.Simon', verb='CREATE', header_map={ 'CINP-VERSION': '0.9' } )
  # req.data = { 'name': 'bob', 'description': 'The test bob' }
  # r = srv.dispatch( req )
  # assert r.data == { 'name': 'bob', 'description': 'The test bob' }
  # assert r.http_code == 200


@pytest.mark.django_db
def test_multi_model():
  cinp = DjangoCInP( 'Simple', '0.1' )

  @cinp.model()
  class Header( models.Model ):
    name = models.CharField( max_length=20, default='bob', primary_key=True )
    updated = models.DateTimeField( editable=False, auto_now=True )
    created = models.DateTimeField( editable=False, auto_now_add=True )

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  @cinp.model()
  class Detail( models.Model ):
    header = models.ForeignKey( Header )
    type = models.IntegerField( choices=( ( 1, 1 ), ( 2, 3 ) ) )
    viewable = models.BooleanField()

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  srv = MockServer( cinp )

  _ns_compare( srv.getTestNS( 'Simple' ), ( 'Simple', '0.1', '' ), {
                        'test_multi_model.<locals>.Header':
                        ( 'test_multi_model.<locals>.Header', 'Header(name, updated, created)', {}, {}, [], [
                          ( 'name', '', 'String', 'RC', True, False, None, 'bob' ),
                          ( 'updated', '', 'DateTime', 'RO', False, False, None, None ),
                          ( 'created', '', 'DateTime', 'RO', False, False, None, None )
                          ] ),
                        'test_multi_model.<locals>.Detail':
                        ( 'test_multi_model.<locals>.Detail', 'Detail(id, header, type, viewable)', {}, {}, [], [
                          ( 'header', '', 'Model', 'RW', True, False, None, None, 'test_multi_model.<locals>.Header' ),
                          ( 'type', '', 'Integer', 'RW', True, False, [1, 2], None ),
                          ( 'viewable', '', 'Boolean', 'RW', False, False, None, None )
                          ] ) } )

  r = srv.dispatch( Request( uri='/', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.0', 'models': [], 'multi-uri-max': 100, 'name': 'root', 'namespaces': ['/Simple/'], 'path': '/' }

  r = srv.dispatch( Request( uri='/Simple', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.1', 'models': ['/Simple/test_multi_model.<locals>.Header', '/Simple/test_multi_model.<locals>.Detail'], 'multi-uri-max': 100, 'name': 'Simple', 'namespaces': [], 'path': '/Simple/' }

  r = srv.dispatch( Request( uri='/Simple/test_multi_model.<locals>.Header', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.data == {
                      'actions': [],
                      'constants': {},
                      'doc': 'Header(name, updated, created)',
                      'fields': [{'default': 'bob',
                                  'length': 20,
                                  'mode': 'RC',
                                  'name': 'name',
                                  'required': True,
                                  'type': 'String'},
                                 {'default': None,
                                  'mode': 'RO',
                                  'name': 'updated',
                                  'required': False,
                                  'type': 'DateTime'},
                                 {'default': None,
                                  'mode': 'RO',
                                  'name': 'created',
                                  'required': False,
                                  'type': 'DateTime'}],
                      'list-filters': {},
                      'name': 'test_multi_model.<locals>.Header',
                      'not-allowed-methods': [],
                      'path': '/Simple/test_multi_model.<locals>.Header'
                    }
  assert r.http_code == 200

  r = srv.dispatch( Request( uri='/Simple/test_multi_model.<locals>.Detail', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.data == {
                      'actions': [],
                      'constants': {},
                      'doc': 'Detail(id, header, type, viewable)',
                      'fields': [{'default': None,
                                  'mode': 'RW',
                                  'name': 'header',
                                  'required': True,
                                  'type': 'Model',
                                  'uri': '/Simple/test_multi_model.<locals>.Header'},
                                 {'choices': [1, 2],
                                  'default': None,
                                  'mode': 'RW',
                                  'name': 'type',
                                  'required': True,
                                  'type': 'Integer'},
                                 {'default': None,
                                  'mode': 'RW',
                                  'name': 'viewable',
                                  'required': False,
                                  'type': 'Boolean'}],
                      'list-filters': {},
                      'name': 'test_multi_model.<locals>.Detail',
                      'not-allowed-methods': [],
                      'path': '/Simple/test_multi_model.<locals>.Detail'
                    }
  assert r.http_code == 200


@pytest.mark.django_db
def test_multi_model_manytomany():
  cinp = DjangoCInP( 'Simple', '0.1' )

  @cinp.model()
  class Header( models.Model ):
    name = models.CharField( max_length=20, default='bob', primary_key=True )
    updated = models.DateTimeField( editable=False, auto_now=True )
    created = models.DateTimeField( editable=False, auto_now_add=True )

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  @cinp.model()
  class Detail( models.Model ):
    header = models.ManyToManyField( Header )
    type = models.IntegerField( choices=( ( 1, 1 ), ( 2, 3 ) ) )
    viewable = models.BooleanField()

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  srv = MockServer( cinp )

  _ns_compare( srv.getTestNS( 'Simple' ), ( 'Simple', '0.1', '' ), {
                        'test_multi_model_manytomany.<locals>.Header':
                        ( 'test_multi_model_manytomany.<locals>.Header', 'Header(name, updated, created)', {}, {}, [], [
                          ( 'name', '', 'String', 'RC', True, False, None, 'bob' ),
                          ( 'updated', '', 'DateTime', 'RO', False, False, None, None ),
                          ( 'created', '', 'DateTime', 'RO', False, False, None, None )
                          ] ),
                        'test_multi_model_manytomany.<locals>.Detail':
                        ( 'test_multi_model_manytomany.<locals>.Detail', 'Detail(id, type, viewable)', {}, {}, [], [
                          ( 'header', '', 'Model', 'RW', True, True, None, None, 'test_multi_model_manytomany.<locals>.Header' ),
                          ( 'type', '', 'Integer', 'RW', True, False, [1, 2], None ),
                          ( 'viewable', '', 'Boolean', 'RW', False, False, None, None )
                          ] ) } )

  r = srv.dispatch( Request( uri='/', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.0', 'models': [], 'multi-uri-max': 100, 'name': 'root', 'namespaces': ['/Simple/'], 'path': '/' }

  r = srv.dispatch( Request( uri='/Simple', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.1', 'models': ['/Simple/test_multi_model_manytomany.<locals>.Header', '/Simple/test_multi_model_manytomany.<locals>.Detail'], 'multi-uri-max': 100, 'name': 'Simple', 'namespaces': [], 'path': '/Simple/' }

  r = srv.dispatch( Request( uri='/Simple/test_multi_model_manytomany.<locals>.Header', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.data == {
                      'actions': [],
                      'constants': {},
                      'doc': 'Header(name, updated, created)',
                      'fields': [{'default': 'bob',
                                  'length': 20,
                                  'mode': 'RC',
                                  'name': 'name',
                                  'required': True,
                                  'type': 'String'},
                                 {'default': None,
                                  'mode': 'RO',
                                  'name': 'updated',
                                  'required': False,
                                  'type': 'DateTime'},
                                 {'default': None,
                                  'mode': 'RO',
                                  'name': 'created',
                                  'required': False,
                                  'type': 'DateTime'}],
                      'list-filters': {},
                      'name': 'test_multi_model_manytomany.<locals>.Header',
                      'not-allowed-methods': [],
                      'path': '/Simple/test_multi_model_manytomany.<locals>.Header'
                    }
  assert r.http_code == 200

  r = srv.dispatch( Request( uri='/Simple/test_multi_model_manytomany.<locals>.Detail', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.data == {
                      'actions': [],
                      'constants': {},
                      'doc': 'Detail(id, type, viewable)',
                      'fields': [{'choices': [1, 2],
                                  'default': None,
                                  'mode': 'RW',
                                  'name': 'type',
                                  'required': True,
                                  'type': 'Integer'},
                                 {'default': None,
                                  'mode': 'RW',
                                  'name': 'viewable',
                                  'required': False,
                                  'type': 'Boolean'},
                                 {'default': [],
                                  'is_array': True,
                                  'mode': 'RW',
                                  'name': 'header',
                                  'required': True,
                                  'type': 'Model',
                                  'uri': '/Simple/test_multi_model_manytomany.<locals>.Header'}],
                      'list-filters': {},
                      'name': 'test_multi_model_manytomany.<locals>.Detail',
                      'not-allowed-methods': [],
                      'path': '/Simple/test_multi_model_manytomany.<locals>.Detail'
                    }
  assert r.http_code == 200


@pytest.mark.django_db
def test_multi_through_model_manytomany():
  cinp = DjangoCInP( 'Simple', '0.1' )

  @cinp.model()
  class Header( models.Model ):
    name = models.CharField( max_length=20, primary_key=True )

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  @cinp.model()
  class Detail( models.Model ):
    stuff = models.CharField( max_length=50 )
    header = models.ManyToManyField( Header, through='testing.HeaderDetail' )

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  @cinp.model()
  class HeaderDetail( models.Model ):
    header = models.ForeignKey( Header )
    detail = models.ForeignKey( Detail )
    extra = models.CharField( blank=True, null=True )

    @cinp.check_auth()
    @staticmethod
    def checkAuth( user, verb, id_list, action=None ):
      return True

    class Meta:
      app_label = 'testing'

  srv = MockServer( cinp )

  _ns_compare( srv.getTestNS( 'Simple' ), ( 'Simple', '0.1', '' ), {
                        'test_multi_through_model_manytomany.<locals>.Header':
                        ( 'test_multi_through_model_manytomany.<locals>.Header', 'Header(name)', {}, {}, [], [
                          ( 'name', '', 'String', 'RC', True, False, None, None ),
                          ] ),
                        'test_multi_through_model_manytomany.<locals>.Detail':
                        ( 'test_multi_through_model_manytomany.<locals>.Detail', 'Detail(id, stuff)', {}, {}, [], [
                          ( 'stuff', '', 'String', 'RW', True, False, None, None ),
                          ( 'header', '', 'Model', 'RW', True, True, None, None, 'test_multi_through_model_manytomany.<locals>.Header' ),
                          ] ),
                        'test_multi_through_model_manytomany.<locals>.HeaderDetail':
                        ( 'test_multi_through_model_manytomany.<locals>.HeaderDetail', 'HeaderDetail(id, header, detail, extra)', {}, {}, [], [
                          ( 'header', '', 'Model', 'RW', True, False, None, None, 'test_multi_through_model_manytomany.<locals>.Header' ),
                          ( 'detail', '', 'Model', 'RW', True, False, None, None, 'test_multi_through_model_manytomany.<locals>.Detail' ),
                          ( 'extra', '', 'String', 'RW', False, False, None, None ),
                          ] ) } )

  r = srv.dispatch( Request( uri='/', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.0', 'models': [], 'multi-uri-max': 100, 'name': 'root', 'namespaces': ['/Simple/'], 'path': '/' }

  r = srv.dispatch( Request( uri='/Simple', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.http_code == 200
  assert r.data == { 'api-version': '0.1', 'models': ['/Simple/test_multi_through_model_manytomany.<locals>.Header', '/Simple/test_multi_through_model_manytomany.<locals>.Detail', '/Simple/test_multi_through_model_manytomany.<locals>.HeaderDetail'], 'multi-uri-max': 100, 'name': 'Simple', 'namespaces': [], 'path': '/Simple/' }

  r = srv.dispatch( Request( uri='/Simple/test_multi_through_model_manytomany.<locals>.Header', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.data == {
                      'actions': [],
                      'constants': {},
                      'doc': 'Header(name)',
                      'fields': [{'default': None,
                                  'length': 20,
                                  'mode': 'RC',
                                  'name': 'name',
                                  'required': True,
                                  'type': 'String'}],
                      'list-filters': {},
                      'name': 'test_multi_through_model_manytomany.<locals>.Header',
                      'not-allowed-methods': [],
                      'path': '/Simple/test_multi_through_model_manytomany.<locals>.Header'
                    }
  assert r.http_code == 200

  r = srv.dispatch( Request( uri='/Simple/test_multi_through_model_manytomany.<locals>.Detail', verb='DESCRIBE', header_map={ 'CINP-VERSION': '0.9' } ) )
  assert r.data == {
                      'actions': [],
                      'constants': {},
                      'doc': 'Detail(id, stuff)',
                      'fields': [{'default': None,
                                  'length': 50,
                                  'mode': 'RW',
                                  'name': 'stuff',
                                  'required': True,
                                  'type': 'String'},
                                 {'default': [],
                                  'is_array': True,
                                  'mode': 'RW',
                                  'name': 'header',
                                  'required': True,
                                  'type': 'Model',
                                  'uri': '/Simple/test_multi_through_model_manytomany.<locals>.Header'}],
                      'list-filters': {},
                      'name': 'test_multi_through_model_manytomany.<locals>.Detail',
                      'not-allowed-methods': [],
                      'path': '/Simple/test_multi_through_model_manytomany.<locals>.Detail'
                    }
  assert r.http_code == 200
