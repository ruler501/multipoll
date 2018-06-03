# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Polls',
            fields=[
                ('timestamp', models.DateTimeField(unique=True, serialize=False, primary_key=True)),
                ('channel', models.CharField(max_length=1000)),
                ('question', models.CharField(max_length=1000)),
                ('options', models.CharField(max_length=1000)),
            ],
        ),
        migrations.CreateModel(
            name='Votes',
            fields=[
                ('vote_id', models.AutoField(serialize=False, primary_key=True)),
                ('user', models.CharField(max_length=1000)),
                ('content', models.CharField(max_length=1000)),
                ('poll', models.ForeignKey(to='main.Polls')),
            ],
        ),
    ]
