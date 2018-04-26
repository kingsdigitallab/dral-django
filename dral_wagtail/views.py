from django.shortcuts import render
from collections import OrderedDict


def view_visualisation(visualisation_code, context):

    code = visualisation_code.replace('-', '_')

    method = globals().get('visualisation_{}'.format(code))

    method(context)

    template = 'dral_visualisations/{}.html'.format(code)

    return render(context['request'], template, context)


def visualisation_relative_omission_by_translation(context):

    query = r'''
select
    le.string as lemma, la.name as language, sc.qt as freq,
    coalesce(zc.qt::float, 0.0) omitted,
    coalesce(zc.qt::float, 0.0) / (sc.qt::float) as ratio_omitted
from
    (
        select lemma_id, language_id, count(*) qt
        from dral_text_occurence oc
        group by lemma_id, language_id
    ) as sc
    left join
    (
        select lemma_id, language_id, count(*) qt
        from dral_text_occurence oc
        where zero is true
        group by lemma_id, language_id
    ) as zc
    on (
        sc.language_id = zc.language_id
        and sc.lemma_id = zc.lemma_id
    ),
    dral_text_language la,
    dral_text_lemma le
where sc.language_id = la.id
and sc.lemma_id = le.id
and la.name = %s
order by sc.qt desc
;
    '''

    data = [
        (lg, get_rows_from_query(query, [lg])[0:])
        for lg
        in ['LT', 'RU', 'POL']
    ]
    context['vis_data'] = OrderedDict(data)

    import json
    context['vis_data'] = json.dumps(context['vis_data'])


def visualisation_svg_or_canvas(context):

    query = r'''
            select
                le.string as lemma, la.name as language, sc.qt as freq,
                coalesce(zc.qt::float, 0.0) omitted,
                coalesce(zc.qt::float, 0.0) / (sc.qt::float) as ratio_omitted
            from
                (
                    select lemma_id, language_id, count(*) qt
                    from dral_text_occurence oc
                    group by lemma_id, language_id
                ) as sc
                left join
                (
                    select lemma_id, language_id, count(*) qt
                    from dral_text_occurence oc
                    where zero is true
                    group by lemma_id, language_id
                ) as zc
                on (
                    sc.language_id = zc.language_id
                    and sc.lemma_id = zc.lemma_id
                ),
                dral_text_language la,
                dral_text_lemma le
            where sc.language_id = la.id
            and sc.lemma_id = le.id
            and la.name = %s
            order by sc.qt desc
            ;
            '''

    data = [
        (lg, get_rows_from_query(query, [lg])[0:])
        for lg
        in ['LT', 'RU', 'POL']
    ]
    context['vis_data'] = OrderedDict(data)

    import json
    context['vis_data'] = json.dumps(context['vis_data'])


def get_rows_from_query(query, params):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        ret = dictfetchall(cursor)

    return ret


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]
