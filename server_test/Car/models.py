import uuid
from django.db import models

from cinp.orm_django import DjangoCInP as CInP

from User.models import User

cinp = CInP( 'Car', '0.1' )


@cinp.model()
class PartType( models.Model ):
  name = models.CharField( max_length=40, primary_key=True )
  description = models.CharField( max_length=255 )
  updated = models.DateTimeField( editable=False, auto_now=True )
  created = models.DateTimeField( editable=False, auto_now_add=True )

  @cinp.check_auth()
  @staticmethod
  def checkAuth( user, method, id_list, action=None ):
    return True

  def __str__( self ):
    return 'PartType "{0}"'.format( self.description )


@cinp.model()
class Part( models.Model ):
  id = models.CharField( max_length=36, primary_key=True, editable=False )
  part_type = models.ForeignKey( PartType, on_delete=models.CASCADE )
  price = models.FloatField()
  updated = models.DateTimeField( editable=False, auto_now=True )
  created = models.DateTimeField( editable=False, auto_now_add=True )

  def clean( self ):
    super().clean()
    if not self.id:
      self.id = str( uuid.uuid4() )

  @cinp.check_auth()
  @staticmethod
  def checkAuth( user, method, id_list, action=None ):
    return True

  def __str__( self ):
    return 'Part "{0}" of type "{1}"'.format( self.id, self.part_type.name )


@cinp.model()
class Car( models.Model ):
  name = models.CharField( max_length=40, primary_key=True )
  owner = models.ForeignKey( User, on_delete=models.CASCADE )
  part_list = models.ManyToManyField( Part )
  updated = models.DateTimeField( editable=False, auto_now=True )
  created = models.DateTimeField( editable=False, auto_now_add=True )

  @cinp.action( paramater_type_list=[ { 'type': 'Model', 'model': 'User.models.User' } ] )
  def sell( self, to ):
    self.owner = to
    self.save()

  @cinp.list_filter( name='owner', paramater_type_list=[ { 'type': 'Model', 'model': 'User.models.User' } ] )
  @staticmethod
  def filter_by_owner( owner ):
    return Car.objects.filter( owner=owner )

  @cinp.check_auth()
  @staticmethod
  def checkAuth( user, method, id_list, action=None ):
    if id_list is not None:
      for car in Car.objects.filter( pk__in=id_list ):
        if car.owner != user:
          return False

    return True

  def __str__( self ):
    return 'Car "{0}"'.format( self.name )
