# from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import ImportSheetForm
from .management.commands.drtext import Command
from dral_text.models import Language, Chapter, Occurence, Sentence, Lemma,\
    SheetStyle


def view_clean_data(request):

    def get_context():
        context = {
            'page': {'title': 'Data cleaning'},
            'languages': Language.objects.all(),
            'chapters': Chapter.objects.all(),
        }
        return context

    context = get_context()

    if request.method == 'POST':
        for l in context['languages']:
            if request.POST.get('lg-{}'.format(l.pk), None):
                Occurence.objects.filter(language=l).delete()
                Lemma.objects.filter(language=l).delete()
                Sentence.objects.filter(language=l).delete()
                l.delete()
        for c in context['chapters']:
            if request.POST.get('ch-{}'.format(c.pk), None):
                Occurence.objects.filter(chapter=c).delete()
                Sentence.objects.filter(chapter=c).delete()
                SheetStyle.objects.filter(chapter=c).delete()
                c.delete()

        context = get_context()

    return render(request, 'dral_text/clean_data.html', context)


def view_upload_occurrences(request):
    def import_handler(file_path):
        importer = Command()
        importer.import_occurrences_from_file(file_path)
        return importer.get_messages()

    context = {
        'page': {'title': 'Import Strings'},
        'import_type': 'occurrences',
    }

    return view_upload_sheet(request, import_handler, context)


def view_upload_sentences(request):
    def import_handler(file_path):
        importer = Command()
        importer.import_sentences_from_file(file_path)
        return importer.get_messages()

    context = {
        'page': {'title': 'Import Sentences'},
        'import_type': 'sentences',
    }
    return view_upload_sheet(request, import_handler, context)


def view_upload_sheet(request, import_handler, context):

    form = ImportSheetForm()
    if request.method == 'POST':
        form = ImportSheetForm(request.POST, request.FILES)
        if form.is_valid():
            upload_context = handle_uploaded_file(
                request.FILES['file'], import_handler
            )
            context.update(upload_context)
            if context.get('error', None):
                form = ImportSheetForm()
            # return HttpResponseRedirect('/visualisations/')

    context['form'] = form

    return render(request, 'dral_text/import_sheet.html', context)


def handle_uploaded_file(f, import_handler):
    ret = {}

    file_path = '/tmp/{}'.format(f.name)
    with open(file_path, 'wb') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    try:
        ret = import_handler(file_path)
    except Exception as e:
        # Coding error, unexpected
        ret['error'] = '{} ({})'.format(e, e.__class__.__name__)

    return ret
