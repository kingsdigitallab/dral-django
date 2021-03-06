# from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import ImportSheetForm
from .management.commands.drtext import Command
from dral_text.models import Text, Chapter, Occurence, Sentence, Lemma,\
    SheetStyle
from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import JsonResponse
from django.core.paginator import Paginator
from _collections import OrderedDict
from django.urls.base import reverse


def get_context():
    context = {
        'page': {'title': 'Remove data'},
        'texts': Text.get_all(),
        'chapters': Chapter.objects.all(),
    }

    return context


@staff_member_required
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


@staff_member_required
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


@staff_member_required
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


@staff_member_required
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


@staff_member_required
def view_upload_texts(request):
    def import_handler(file_path):
        importer = Command()
        importer.import_texts_from_file(file_path)
        return importer.get_messages()

    context = {
        'page': {'title': 'Import Text Metadata'},
        'import_type': 'texts',
    }
    return view_upload_sheet(request, import_handler, context)


@staff_member_required
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


def get_filters_from_request(request, param_filters):
    '''returns a Django QuerySet filter dictionary
    from a http request and a dictionary mapping arguments to filters
    '''
    ret = {}
    for param, filter in param_filters.items():
        values = request.GET.get(param, '')

        if param == 'repeteme' and values == 'ALL':
            continue

        if values:
            if ',' in values:
                ret[filter + '__in'] = values.split(',')
            else:
                ret[filter] = values

    return ret


def view_occurrences_api(request):
    ret = request_occurrences_api(request)
    return JsonResponse(ret)


def request_occurrences_api(request):
    per_page = 100
    page_index = int(request.GET.get('page', 1))

    data = []
    meta = {}
    res = OrderedDict([
        ['jsonapi', {'version': '1.1'}],
        ['meta', meta],
        ['links', {}],
        ['data', data],
        ['errors', []],
    ])

    param_filters = {
        'text': 'text__code',
        'repeteme': 'lemma__string',
        'chapter': 'chapter__slug',
    }
    filters = get_filters_from_request(request, param_filters)
    occs = Occurence.objects.filter(**filters)

    occs = occs.select_related('chapter', 'lemma', 'text')

    occs = occs.order_by('chapter__display_order', 'lemma',
                         'text', 'sentence_index', 'id')

    pages = Paginator(occs, per_page)
    page = pages.get_page(page_index)
    meta['totalPages'] = pages.count

    res['links'] = get_links_from_api_request(
        request, param_filters, page_index, pages)

    for occ in page:
        occ_dict = {
            'type': 'occurrences',
            'id': str(occ.id),
            'attributes': {
                'string': occ.string,
                'chapter': occ.chapter.slug,
                'repeteme': occ.lemma.string,
                'text': occ.text.code,
                'sentence': occ.sentence_index,
            }
        }
        data.append(occ_dict)

    return res


def get_links_from_api_request(request, param_filters, page_index, pages):
    base_url = '{}://{}{}?{}'.format(
        request.scheme,
        request.get_host(),
        reverse('api_occurrences'),
        '&'.join([
            '{}={}'.format(
                k, v
            )
            for k, v
            in request.GET.items()
            if k in param_filters.keys()
        ])
    )
    ret = {
        'first': base_url + '&page={}'.format(1),
        'self': base_url + '&page={}'.format(page_index),
        'last': base_url + '&page={}'.format(pages.count),
    }
    if page_index > 1:
        ret['previous'] = base_url + '&page={}'.format(page_index - 1)
    if page_index < pages.count - 1:
        ret['next'] = base_url + '&page={}'.format(page_index + 1)

    return ret
