from django.contrib.auth.models import Group
from geonode.groups.models import GroupProfile

for group in Group.objects.all():
    if not GroupProfile.objects.filter(slug=group.name).exists():
        GroupProfile.objects.create(
            title=group.name,
            slug=group.name,
            access="public",
            group=group,
            description=f"Auto-created profile for group {group.name}",
        )
        print(f"Created GroupProfile for group: {group.name}")
    else:
        print(f"GroupProfile already exists for group: {group.name}")