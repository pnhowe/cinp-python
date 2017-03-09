import hashlib
import random
import string
from datetime import datetime, timedelta, timezone

from django.db import models

from cinp.orm_django import DjangoCInP as CInP

class SystemAccount():
  @property
  def isSuperuser( self ):
    return False

  @property
  def isAnonymouse( self ):
    return False

def getUser( auth_id, auth_token ):
  if auth_id is None or auth_token is None:
    return None

  if auth_id == 'SystemAccount' and auth_token == 'System1234':
    return SystemAccount()

  try:
    session = Session.objects.get( user__username=auth_id, session_id=auth_token )
  except ( Session.DoesNotExist, User.DoesNotExist ):
    return None

  if not session.user.isActive:
    return None

  if not session.isActive:
    return None

  return session.user


cinp = CInP( 'User', '0.1' )


@cinp.model( property_list=[ 'isActive' ], not_allowed_method_list=[ 'LIST', 'DELETE', 'CREATE', 'CALL' ], hide_field_list=[ 'password' ] )
class User( models.Model ):
  username = models.CharField( max_length=40, primary_key=True )
  password = models.CharField( editable=False, max_length=64 )
  nick_name = models.CharField( max_length=100, null=True, blank=True )
  superuser = models.BooleanField( default=False, editable=False )
  updated = models.DateTimeField( editable=False, auto_now=True )
  created = models.DateTimeField( editable=False, auto_now_add=True )

  @property
  def isActive( self ):
    return True

  @property
  def isSuperuser( self ):
    return self.superuser

  @property
  def isAnonymouse( self ):
    return False

  @cinp.action( paramater_type_list=[ 'String' ] )
  def setPassword( self, password ):
    self.password = hashlib.sha256( password.encode( 'utf-8' ) ).hexdigest()
    self.save()

  @cinp.check_auth()
  @staticmethod
  def checkAuth( user, method, id_list, action=None ):
    if id_list is not None and len( id_list ) > 1 and id_list[0] != user.username:
      return False

    return True

  def __str__( self ):
    return 'User "{0}"'.format( self.username )


@cinp.model( property_list=[ 'isActive' ], not_allowed_method_list=[ 'GET', 'LIST', 'DELETE', 'CREATE', 'UPDATE' ] )
class Session( models.Model ):
  session_id = models.CharField( max_length=64, primary_key=True )
  user = models.ForeignKey( User )
  last_checkin = models.DateTimeField()
  created = models.DateTimeField( editable=False, auto_now_add=True )

  @property
  def isActive( self ):
    return self.last_checkin < ( datetime.now( timezone.utc ) + timedelta( seconds=30 ) )

  @cinp.action( return_type='String', paramater_type_list=[ 'String', 'String' ] )
  @staticmethod
  def login( username, password ):
    try:
      user =  User.objects.get( username=username )
    except User.DoesNotExist:
      raise ValueError( 'User Does Not Exist' )

    password = hashlib.sha256( password.encode( 'utf-8' ) ).hexdigest()
    if password != user.password:
      raise ValueError( 'Invalid Password' )

    token = ''.join( random.choice( string.ascii_letters ) for _  in range( 30 ) )
    session = Session( session_id=token, user=user )
    session.last_checkin = datetime.now( timezone.utc )
    session.save()
    session.hearbeat()

    return token

  @cinp.action()
  def logout( self ):
    self.delete()

  @cinp.action()
  def hearbeat( self ):
    self.last_checkin = datetime.now( timezone.utc )
    self.save()

  @cinp.check_auth()
  @staticmethod
  def checkAuth( user, method, id_list, action=None ):
    if action is not None:
      return True

    if method == 'DESCRIBE':
      return True

    return False

  def __str__( self ):
    return 'Session for "{0}"'.format( self.user.username )
