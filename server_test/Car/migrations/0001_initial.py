# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def load_types( app, schema_editor ):
  PartType = app.get_model( 'Car', 'PartType' )
  p = PartType( name='Bumper', description='Protect your car from thoes crazy Vogons' )
  p.save()
  p = PartType( name='MotorMount', description='Replace flexible and sloppy mount with this Replacement Motor Mount.' )
  p.save()
  p = PartType( name='Wheel', description='These help your car move down the road better' )
  p.save()


class Migration(migrations.Migration):

    dependencies = [
        ('User', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Car',
            fields=[
                ('name', models.CharField(primary_key=True, max_length=40, serialize=False)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(to='User.User')),
            ],
        ),
        migrations.CreateModel(
            name='Part',
            fields=[
                ('id', models.CharField(max_length=36, primary_key=True, editable=False, serialize=False)),
                ('price', models.FloatField()),
                ('updated', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='PartType',
            fields=[
                ('name', models.CharField(primary_key=True, max_length=40, serialize=False)),
                ('description', models.CharField(max_length=255)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name='part',
            name='part_type',
            field=models.ForeignKey(to='Car.PartType'),
        ),
        migrations.AddField(
            model_name='car',
            name='part_list',
            field=models.ManyToManyField(to='Car.Part'),
        ),
        migrations.RunPython( load_types ),
    ]
