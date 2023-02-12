import csv

from geonode.layers.models import Dataset
from geonode.geoserver.helpers import gs_catalog

from django.core.management.base import BaseCommand
from geonode.notifications_helper import E


class Command(BaseCommand):
    help = ("help")

    def handle(self, *args, **options):
        cat = gs_catalog
        geonode_datasets = Dataset.objects.all()
        geoserver_only = []
        geonode_only = []

        resources = cat.get_resources()

        # filter out layers already registered in geonode
        dataset_names = Dataset.objects.values_list("alternate", flat=True)
        try:
            # for resource in [k for k in resources if f"{k.workspace.name}:{k.name}" not in dataset_names]:
            #     print(resource)
            
            for resource in [k for k in geonode_datasets if k.alternate not in [f"{m.workspace.name}:{m.name}" for m in resources]]:
                path = k.path
            geoserver_only = [[f"{k.workspace.name}:{k.name}"] for k in resources if f"{k.workspace.name}:{k.name}" not in dataset_names]
            geonode_only = [[k.id, k.alternate] for k in geonode_datasets if k.alternate not in [f"{m.workspace.name}:{m.name}" for m in resources]]

            with open('demo_geoserver_only.csv', 'w', encoding='UTF8', newline='') as f:
                writer = csv.writer(f)
                # write the header
                writer.writerow(['title'])

                # write multiple rows
                writer.writerows(geoserver_only)

            with open('demo_geonode_only.csv', 'w', encoding='UTF8', newline='') as f:
                writer = csv.writer(f)
                # write the header
                writer.writerow(['id', 'title'])

                # write multiple rows
                writer.writerows(geonode_only)
        except Exception:
            print("Error occured")
