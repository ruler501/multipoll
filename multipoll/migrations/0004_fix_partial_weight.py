# Generated by Django 2.2.5 on 2019-09-19 23:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('multipoll', '0003_allow_null_approval'),
    ]

    operations = [
        migrations.RenameField(
            model_name='partialapprovalvote',
            old_name='weights',
            new_name='weight',
        ),
        migrations.RenameField(
            model_name='partialmultivote',
            old_name='weights',
            new_name='weight',
        ),
    ]