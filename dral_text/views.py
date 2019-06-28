# from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import ImportSheetForm
from .management.commands.drtext import Command
from dral_text.models import Text, Chapter, Occurence, Sentence, Lemma,\
    SheetStyle


def get_context():
    context = {
        'page': {'title': 'Remove data'},
        'texts': Text.get_all(),
        'chapters': Chapter.objects.all(),
    }

    return context


def view_import(request):
    '''landing page for all front-end data-related tasks'''
    context = get_context()
    context['page'] = {'title': 'Data management'}

    # add statistics about sentences and strings to context
    # broken down by texts and chapters
    context['stats'] = []
    for text in Text.get_all():
        stats_text = [text.code]
        for chapter in context['chapters']:
            stats_text.append(
                Occurence.objects.filter(
                    text=text, chapter=chapter
                ).count()
            )
            stats_text.append(
                Sentence.objects.filter(
                    text=text, chapter=chapter
                ).count()
            )

        context['stats'].append(stats_text)

    return render(request, 'dral_text/import.html', context)


def view_clean_data(request):

    context = get_context()

    if request.method == 'POST':
        for text in context['texts']:
            if request.POST.get('text-{}'.format(text.pk), None):
                Occurence.objects.filter(text=text).delete()
                Lemma.objects.filter(text=text).delete()
                Sentence.objects.filter(text=text).delete()
                text.delete()
        for chapter in context['chapters']:
            if request.POST.get('ch-{}'.format(chapter.pk), None):
                Occurence.objects.filter(chapter=chapter).delete()
                Sentence.objects.filter(chapter=chapter).delete()
                SheetStyle.objects.filter(chapter=chapter).delete()
                chapter.delete()

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
