#!/usr/bin/env python3
import sys

sys.path.insert( 1, '..')

import http.client as httplib
from cinp.client import CInP, NotFound, NotAuthorized


client = CInP( host='http://127.0.0.1', root_path='/api/v1/', port=8888 )

print( 'First we will get OPTIONS on a few things to see what that looks like' )
conn = httplib.HTTPConnection( '127.0.0.1', '8888' )
conn.request( 'OPTIONS', '/api/v1/User/' )
conn.getresponse().getheader( 'allow' )
conn.request( 'OPTIONS', '/api/v1/User/User' )
conn.getresponse().getheader( 'allow' )
conn.request( 'OPTIONS', '/api/v1/User/User(setPassword)' )
conn.getresponse().getheader( 'allow' )

print( 'Now We will DESCRIBE, see what it is we are going to play with' )
print( client.describe( '/api/v1/' ) )
print( client.describe( '/api/v1/User/' ) )
print( client.describe( '/api/v1/User/User' ) )
print( client.describe( '/api/v1/User/User(setPassword)' ) )
print( client.describe( '/api/v1/User/Session(login)' ) )
print( client.describe( '/api/v1/User/Session(logout)' ) )
print( client.describe( '/api/v1/User/Session(hearbeat)' ) )
print( client.describe( '/api/v1/Car/' ) )
print( client.describe( '/api/v1/Car/PartType' ) )
print( client.describe( '/api/v1/Car/Part' ) )
print( client.describe( '/api/v1/Car/Car' ) )

print( 'List is not allowed on Users' )
try:
  print( client.list( '/api/v1/User/User' ) )
except NotAuthorized:
  pass

print( 'Let''s get ford''s user info' )
print( client.get( '/api/v1/User/User:ford:' ) )

print( 'What kind of Part Types do we have to work with' )
print( client.list( '/api/v1/Car/PartType' ) )

print( 'Let''s make some parts' )
print( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Bumper:', 'price': 10.00 } ) )
print( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:MotorMount:', 'price': 42.00 } ) )
print( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Wheel:', 'price': 5.12 } ) )
print( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Wheel:', 'price': 5.12 } ) )
print( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Wheel:', 'price': 5.12 } ) )
print( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Wheel:', 'price': 5.12 } ) )

print( 'look at all thoes new parts' )
part_list = client.list( '/api/v1/Car/Part' )
print( part_list )

print( 'get''s try and get our car that does not exist yet' )
try:
  print( client.get( '/api/v1/Car/Car:gremlin:' ) )
except NotFound:
  pass

print( 'Now to make a car' )
print( client.create( '/api/v1/Car/Car', { 'name': 'gremlin', 'owner': '/api/v1/User/User:ford:', 'part_list': part_list[0] } ) )

print( 'look there it is' )
print( client.list( '/api/v1/Car/Car' ) )

print( 'but we can not look at it, checkAuth in that model saies that only owners can do that' )
try:
  print( client.get( '/api/v1/Car/Car:gremlin:' ) )
except NotAuthorized:
  pass

print( 'let us login...')
auth_token = client.call( '/api/v1/User/Session(login)', { 'username': 'ford', 'password': 'betelgeuse7' } )
client.setAuth( 'ford', auth_token )
print( 'Now we can see it' )
print( client.get( '/api/v1/Car/Car:gremlin:' ) )

print( 'login as a super user...' )
auth_token = client.call( '/api/v1/User/Session(login)', { 'username': 'admin', 'password': 'adm1n' } )
client.setAuth( 'admin', auth_token )
print( 'can still see it, superusers are subjext to checkAuth' )
print( client.get( '/api/v1/Car/Car:gremlin:' ) )

print( 'let us login again...')
auth_token = client.call( '/api/v1/User/Session(login)', { 'username': 'ford', 'password': 'betelgeuse7' } )
client.setAuth( 'ford', auth_token )
print( 'Ford does not want the car anymore, sell it to the Arthur' )
print( client.call( '/api/v1/Car/Car:gremlin:(sell)', { 'to': '/api/v1/User/User:arthur:' } ) )

print( 'now we can not see the car anymore' )
try:
  print( client.get( '/api/v1/Car/Car:gremlin:' ) )
except NotAuthorized:
  pass

print( 'drop our auth id and token, in effect logging out' )
client.setAuth()

print( 'our fleet of cars nees more than one, let\'s create another' )
part_list = []
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Bumper:', 'price': 11.00 } )[0] )
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Bumper:', 'price': 14.00 } )[0] )
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:MotorMount:', 'price': 42.00 } )[0] )
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:MotorMount:', 'price': 42.00 } )[0] )
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:MotorMount:', 'price': 42.00 } )[0] )
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Wheel:', 'price': 100.10 } )[0] )
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Wheel:', 'price': 100.10 } )[0] )
part_list.append( client.create( '/api/v1/Car/Part', { 'part_type': '/api/v1/Car/PartType:Wheel:', 'price': 100.10 } )[0] )
print( part_list )

print( 'Now to make a car' )
print( client.create( '/api/v1/Car/Car', { 'name': 'heartofgold', 'owner': '/api/v1/User/User:ford:', 'part_list': part_list } ) )

print( 'look there it is' )
print( client.list( '/api/v1/Car/Car' ) )

print( 'let\'s see Ford\'s cars' )
print( client.list( '/api/v1/Car/Car', filter_name='owner', filter_value_map={ 'owner': '/api/v1/User/User:ford:' } ) )

print( 'let\'s see Arthur\'s cars' )
print( client.list( '/api/v1/Car/Car', filter_name='owner', filter_value_map={ 'owner': '/api/v1/User/User:arthur:' } ) )

print( 'And that is it, thanks for playing, don''t forget to take your towel with you' )
sys.exit( 0 )
