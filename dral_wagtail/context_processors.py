
def settings(request):
    from django.conf import settings as djsettings

    var_names = djsettings.CONTEXT_VARIABLES

    ret = {
        k: getattr(djsettings, k, None) for k in var_names
    }

    ret['in_data_portal'] = request.path.startswith('/data/')

    return ret
