from django.shortcuts import render
from collections import OrderedDict
from dral_wagtail.api_vars import API_Vars
from dral_text.models import Chapter, Language
from django.conf import settings


class Visualisation(object):

    def __init__(self):
        self.chapter_slugs = OrderedDict(list(
            Chapter.objects.values_list('slug', 'id').order_by('display_order')
        ))
        self.language_names = list(
            Language.objects.values_list(
                'name', flat=True
            ).exclude(name=settings.DRAL_REFERENCE_LANGUAGE).order_by('name')
        )

    def process_request(self, visualisation_code, context, request):
        self.visualisation_code = visualisation_code
        self.context = context
        self.request = request

        ret = self.view_visualisation()

        return ret

    def get_config(self):
        ret = API_Vars(self.get_config_schema())

        ret.reset_vars_from_request(self.request)

        return ret

    def get_config_schema(self, alignment_data=None):
        # cache = caches['kiln']

        ret = [
            {
                'key': 'viz',
                'default': 'relative_omission',
                'options': ['relative_omission',
                            'relative_omission_calendar',
                            'variants_progression',
                            'proof_read'
                            ],
                'name': 'Visualisation',
                'type': 'single',
            },
            {
                'key': 'chapter',
                'default': list(self.chapter_slugs.keys()),
                'options': list(self.chapter_slugs.keys()),
                'name': 'Chapter',
                'type': 'multi',
            },
            {
                'key': 'sort',
                'default': 'frequency',
                'options': ['frequency', 'name', 'omission'],
                'name': 'Sort by',
                'type': 'single',
            },
            {
                'key': 'freq-min',
                'default': 0,
                'name': 'Minimum frequency',
                'type': 'int',
            },
            {
                'key': 'lemma',
                'default': 'SAY',
                'name': 'Lemma',
                'type': 'str',
            },
            {
                'key': 'language',
                'default': self.language_names[:],
                'options': self.language_names[:],
                'name': 'Language',
                'type': 'multi',
            },
        ]

        # cache.set('alignment_config_options', ret)
        return ret

    def view_visualisation(self):

        config = self.config = self.get_config()
        self.context['config'] = config.get_list()

        # code = self.visualisation_code.replace('-', '_')
        code = config.get('viz', 1)

        method = getattr(self, 'visualisation_{}'.format(code))
        method()

        template_path = 'dral_visualisations/{}.html'.format(code)

        from django.template.loader import get_template
        template = get_template(template_path)

        if self.request.GET.get('js', '') == '1':
            # template_path = 'text_alignment/views/%s.html' % selected_view
            json_res = {
                'config': config.get_list(),
                'html': template.render(self.context),
                'qs': config.get_query_string(),
                'page_title': code,
            }

            from django.http import JsonResponse
            return JsonResponse(json_res)
        else:
            return render(
                self.context['request'],
                'dral_wagtail/visualisation_page.html',
                self.context
            )

    def visualisation_variants_progression(self):
        query = r'''
            SELECT ch.slug as ch,
                oc.sentence_index as sidx,
                oc.string as word,
                oc.lemma_group as grp,
                oc.zero as omitted,
                oc.paraphrase as para,
                oc.replace as repl
            FROM dral_text_occurence oc
                join dral_text_language la
                on (oc.language_id = la.id)
                join dral_text_lemma le
                on (oc.lemma_id = le.id)
                join dral_text_chapter ch
                on (oc.chapter_id = ch.id)
            WHERE la.name = %s
                and le.string = %s
                and ch.slug = ANY(%s)
            ORDER by array_position(%s, ch.slug::text),
                sentence_index
            ;
        '''

        lemma = self.config.get('lemma', 'DOORS')
        chapters = self.config.get('chapter')
        languages = [c.upper() for c in self.config.get('language')]

        data = OrderedDict()

        for lg in languages:
            variants = {}
            # fetch all the occurrences
            words = get_rows_from_query(
                query,
                [lg, lemma, chapters, chapters],
                rounding=3
            )

            # build variants table
            word_count = 0
            for word in words:
                if word['omitted']:
                    continue
                word_count += 1
                k = word['ch'] + '-' + str(word['grp'])
                variants[k] = variants.get(k, 0) + 1

            # TODO: find a way to unify lemma across chapters!
            sum = word_count
            variants_data = OrderedDict()
            for k, c in sorted(variants.items(), key=lambda v: -v[1]):
                variants_data[k] = {
                    'count': c,
                    'color': round(sum / word_count, 4)
                }
                sum -= c

            # print(variants_data)

            language_data = {
                'words': words,
                'variants': variants_data,
            }
            data[lg] = language_data

        self.context['vis_data'] = data

    def visualisation_proof_read(self):
        lemma = self.config.get('lemma', 'DOORS')
        chapters = self.config.get('chapter')
        languages = [c.upper() for c in self.config.get('language')]

        from dral_text.models import Occurence

        data_chapters = []

        for chapter in chapters:
            blocks = []
            block = {}

            occurrences = Occurence.objects.filter(
                chapter__slug=chapter,
                language__name__in=['EN'] + languages,
            ).order_by('lemma', 'language_id').select_related(
                'lemma', 'language'
            )

            last_lemma = None
            last_lg = None
            for occ in occurrences:
                lg = occ.language
                lemma = occ.lemma

                if lemma != last_lemma:
                    if block:
                        blocks.append(block)
                    block = {
                        'keyword': lemma,
                        'languages': [],
                    }

                if lg != last_lg:
                    strings = []
                    block['languages'].append({
                        'name': occ.language.name,
                        'strings': strings,
                    })

                strings.append([occ.string])

                last_lg = lg
                last_lemma = lemma

            data_chapter = {
                'name': chapter,
                'blocks': blocks
            }
            data_chapters.append(data_chapter)

        self.context['vis_data'] = {
            'chapters': data_chapters
        }

    def visualisation_relative_omission(self):
        '''
        For each unique (lemma, lg) pair we get:
            * the frequency (sc.qt)
            * the number of ommissions (zc.qt)
        '''
        query = r'''
            select
                le.string as lemma, la.name as language, sc.qt as freq,
                coalesce(zc.qt::float, 0.0) omitted,
                coalesce(zc.qt::float, 0.0) / (sc.qt::float) as ratio_omitted
            from
                (
                    select lemma_id, language_id, count(*) qt
                    from dral_text_occurence oc
                    where chapter_id = ANY (%s)
                    group by lemma_id, language_id
                ) as sc
                left join
                (
                    select lemma_id, language_id, count(*) qt
                    from dral_text_occurence oc
                    where chapter_id = ANY(%s)
                    and zero is true
                    group by lemma_id, language_id
                ) as zc
                on (
                    sc.language_id = zc.language_id
                    and sc.lemma_id = zc.lemma_id
                ),
                dral_text_language la,
                dral_text_lemma le
            where sc.language_id = la.id
            and sc.qt >= %s
            and sc.lemma_id = le.id
            and la.name = %s
        '''

        sort_by = self.config.get('sort', True)
        if sort_by == 'name':
            query += '''
                order by lemma
            '''
        elif sort_by == 'omission':
            query += '''
                order by ratio_omitted desc
            '''
        else:
            query += '''
                order by sc.qt desc
            '''

        chapter_ids = [self.chapter_slugs[slug]
                       for slug in self.config.get('chapter')]
        languages = [c.upper() for c in self.config.get('language')]

        freq_min = self.config.get('freq-min', 0)

        data = [
            (lg, get_rows_from_query(
                query,
                [chapter_ids, chapter_ids, freq_min, lg],
                rounding=3
            )[0:])
            for lg
            in languages
        ]
        self.context['vis_data'] = OrderedDict(data)

    def visualisation_relative_omission_calendar(self):
        ret = self.visualisation_relative_omission()
        return ret


def get_rows_from_query(query, params, rounding=None):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        ret = dictfetchall(cursor)

    if rounding:
        for row in ret:
            for k, v in row.items():
                if isinstance(v, float):
                    row[k] = round(v, 3)

    return ret


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]
