# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib

from django.db import migrations, models

def setPassword( user, password ):
  user.password = hashlib.sha256( password.encode( 'utf-8' ) ).hexdigest()
  user.save()

def load_users( app, schema_editor ):
  User = app.get_model( 'User', 'User' )
  u = User( username='ford', nick_name='Ford Prefect' )
  u.save()
  setPassword( u, 'betelgeuse7' )

  User = app.get_model( 'User', 'User' )
  u = User( username='arthur', nick_name='Arthor Dent' )
  u.save()
  setPassword( u, 'bulldozer2' )

  u = User( username='admin', nick_name='Admin', superuser=True )
  u.save()
  setPassword( u, 'adm1n' )


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Session',
            fields=[
                ('session_id', models.CharField(primary_key=True, max_length=64, serialize=False)),
                ('last_checkin', models.DateTimeField()),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('username', models.CharField(primary_key=True, max_length=40, serialize=False)),
                ('password', models.CharField(editable=False, max_length=50)),
                ('superuser', models.BooleanField(editable=False, default=False)),
                ('nick_name', models.CharField(blank=True, null=True, max_length=100)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name='session',
            name='user',
            field=models.ForeignKey(to='User.User'),
        ),
        migrations.RunPython( load_users ),
    ]
