# from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import ImportOccurrencesForm


def handle_uploaded_file(f):
    ret = {}

    file_path = '/tmp/{}'.format(f.name)
    with open(file_path, 'wb') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    from .management.commands.drtext import Command
    importer = Command()

    try:
        importer.import_occurrences_from_file(file_path)
        ret = importer.get_messages()
    except Exception as e:
        # Coding error, unexpected
        ret['error'] = '{} ({})'.format(e, e.__class__.__name__)

    return ret


def view_upload_occurrences(request):
    context = {
        'page': {'title': 'Import Strings'},
    }

    form = ImportOccurrencesForm()
    if request.method == 'POST':
        form = ImportOccurrencesForm(request.POST, request.FILES)
        if form.is_valid():
            upload_context = handle_uploaded_file(request.FILES['file'])
            context.update(upload_context)
            if context.get('error', None):
                form = ImportOccurrencesForm()
            # return HttpResponseRedirect('/visualisations/')

    context['form'] = form

    return render(request, 'dral_text/import_occurrences.html', context)
