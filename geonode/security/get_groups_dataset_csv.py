
def get_data():
    # Get the list of objects the user has access to
    from geonode.groups.models import GroupProfile

    group_profiles = GroupProfile.objects.values('group')
    groups = []
    group_list_all = []
    try:
        group_list_all = user.group_list_all().values('group')
    except Exception:
        pass

    try:
        anonymous_group = Group.objects.get(name='anonymous')
        if anonymous_group and anonymous_group not in groups:
            groups.append(anonymous_group)
    except Exception:
        pass

    filter_set = queryset.filter(dirty_state=False)

    if metadata_only is not None:
        # Hide Dirty State Resources
        filter_set = filter_set.filter(metadata_only=metadata_only)

    if not is_admin:
        if user:
            _allowed_resources = get_objects_for_user(
                user,
                ['base.view_resourcebase', 'base.change_resourcebase'],
                any_perm=True)
            filter_set = filter_set.filter(id__in=_allowed_resources.values('id'))

        if admin_approval_required and not AdvancedSecurityWorkflowManager.is_simplified_workflow():
            if not user or not user.is_authenticated or user.is_anonymous:
                filter_set = filter_set.filter(
                    Q(is_published=True) |
                    Q(group__in=public_groups) |
                    Q(group__in=groups)
                ).exclude(is_approved=False)

        # Hide Unpublished Resources to Anonymous Users
        if unpublished_not_visible:
            if not user or not user.is_authenticated or user.is_anonymous:
                filter_set = filter_set.exclude(is_published=False)

        # Hide Resources Belonging to Private Groups
        if private_groups_not_visibile:
            private_groups = GroupProfile.objects.filter(access="private").values('group')
            if user and user.is_authenticated:
                filter_set = filter_set.exclude(
                    Q(group__in=private_groups) & ~(
                        Q(owner__username__iexact=str(user)) | Q(group__in=group_list_all))
                )
            else:
                filter_set = filter_set.exclude(group__in=private_groups)

    return filter_set
