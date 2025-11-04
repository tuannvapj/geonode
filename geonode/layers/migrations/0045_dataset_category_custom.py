# Generated manually for feature/metadata-edit-api

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layers', '0044_alter_dataset_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='category_custom',
            field=models.CharField(
                blank=True,
                help_text='Dataset category (e.g., \'Công trình thủy lợi\', \'Sử dụng đất\', etc.)',
                max_length=255,
                null=True,
                verbose_name='Category'
            ),
        ),
    ]
