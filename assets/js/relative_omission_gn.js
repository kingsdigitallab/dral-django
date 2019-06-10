/*jshint esversion: 6 */
"use strict";

function log() {
  window.console.log.apply(null, arguments)
}

function get_lang_info(lang_code) {
  var lang_codes = {
      'LT': {
          'label': 'Lituanian'
      },
      'RU': {
          'label': 'Russian'
      },
      'POL': {
          'label': 'Polish'
      },
      'default': {
          'label': lang_code
      }
  };
  var ret = lang_codes[lang_code];
  if (!ret) ret = lang_codes['default'];
  return ret;
}

function relative_omission() {

    var d3 = window.d3;

    if (!window.vis_data) return;

    var data_size = Object.values(window.vis_data)[0].length;

    log(window.vis_data, Object.values(window.vis_data)[0], data_size);

    var $charts_wrapper = $('.charts-wrapper');
    const margins = {top: 20, right: 20, bottom: 20, left: 35};
    const dims = {
        ch: 200.0,         // total height of the svg (includes margins)
        // cw: 200.0,
        // https://devdocs.io/d3~5/d3-scale#scaleImplicit
        step_width: 20,    // step width for the bars (see d3.js doc)
        bar_padding: 0.2,  // ratio of step width used as a gap between 2 bars
    };
    // height and width for the bars area of the svg
    dims.h = dims.ch - margins.bottom - margins.top;
    dims.w = (dims.step_width) * data_size;
    dims.cw = dims.w + margins.left + margins.right;

    // treat each dataset, one by one, one for each translatation
    $.each(window.vis_data, (lang, data) => {
        var lang_info = get_lang_info(lang);

        // render the template and add it to viz div wrapper
        $charts_wrapper.append(window.apply_template(
            'chart-wrapper-template',
            {'language': lang}
        ));
        var chart_wrapper = d3.select($charts_wrapper.children(':last')[0]);

        // update the svg element
        // https://chartio.com/resources/tutorials/how-to-resize-an-svg-when-the-window-is-resized-in-d3-js/
        var svg = chart_wrapper.select('.chart');
        svg.attr('viewBox', '0 0 '+dims.cw+' '+dims.ch)
        //  .attr("preserveAspectRatio", "xMinYMin meet")
        ;
        var chart_group = svg.append('g')
          .attr('transform', 'translate('+margins.left+', '+margins.top+')');
        
        // scales & axes
        // var scale_y = d3.scaleLinear().domain([0, 1.0]).range([dims.h, 0]);
        var scale_y = d3.scaleLinear().domain([0, 1.0]).range([0, dims.h]);
        var axis_y = chart_group.append('g').classed('axis-y', true)
            .call(d3.axisLeft(scale_y)
              .ticks(3, '%')
              // TODO: add more ticks on Y axes but d3.js won't listen!
              //.tickValues([0, 0.25, 0.5, 0.75, 1])
              //.tickFormat(d3.format('%'))
            )
        ;

        var scale_x = d3.scaleBand()
            .domain(data.map(d => d.lemma))
            .range([0, dims.w])
            .padding(dims.bar_padding)
        ;

        // http://bl.ocks.org/d3noob/ccdcb7673cdb3a796e13 (rotated labels)
        var axis_x = chart_group.append('g').classed('axis-x', true)
            .attr('transform', 'translate(0, '+dims.h+')')
            //.attr('transform', 'translate(0, '+0+')')
            .call(d3.axisTop(scale_x))
            .selectAll('text')
                .attr("y", "0.4em")
                .attr("x", "0.7em")
                .attr('transform', d => 'rotate(-'+90+')')
        ;

        // bars
        var bars = chart_group.append('g');
        bars.selectAll('.bar')
            .data(data).enter()
            .append('rect')
                .classed('bar', true)
                .attr('x', d => scale_x(d.lemma))
                .attr('y', 0)
                .attr('width', scale_x.bandwidth())
                .attr('height', d => scale_y(d.omitted / d.freq))
        ;

        // vertical "cursor" for the hovered bar
        // and corresponding ones in the other languages
        bars.append('line')
            .classed('cursor', true)
            .attr('x1', 0)
            .attr('x2', 0)
            .attr('y1', 0)
            .attr('y2', scale_y(1.0))
            .classed('show', false)
        ;

        // title of the chart
        svg.append('g').classed('title', true)
            .append('text')
            .text(lang_info.label)
            .attr('x', 0)
            .attr('y', '1em')
        ;

        // for optimisation purpose
        window.viz_highlights = null;
        window.viz_cursors = null;

        function on_leave_bar() {
            window.infobox_dict({});
            if (window.viz_cursors)
                window.viz_cursors.classed('show', false);
            clear_highlight();
        }

        function clear_highlight() {
            if (window.viz_highlights)
                window.viz_highlights.classed('highlighted', false);
        }

        // mouseover
        // We don't attach an event to every bar:
        // a) that would be prohibitive
        // b) user couldn't select lemma without omissions (0-height bar)
        // See https://bl.ocks.org/mbostock/3902569
        svg.on(
          'mousemove', function() {
              var xy = d3.mouse(this);
              
              var idx = (
                xy[0] - margins.left - scale_x.paddingOuter() * scale_x.step()
              ) / scale_x.step();
              idx = Math.floor(idx);

              if (data[idx]) {
                  var bar = bars.select('.bar:nth-child('+(idx+1)+')');
                  if (bar.classed('highlighted')) return;

                  clear_highlight();
                  bar.classed('highlighted', true);

                  window.viz_highlights = bar;

                  var datum = bar.datum();

                  datum.omitted_pc = (datum.ratio_omitted * 100.0).toFixed(1);
                  datum.language_full = get_lang_info(lang).label;

                  // log(datum);
                  window.infobox_dict(datum);

                  var x0 = scale_x(datum.lemma);
                  if (!window.viz_cursors)
                    window.viz_cursors = d3.selectAll('.cursor');
                  window.viz_cursors
                    .attr('x1', x0)
                    .attr('x2', x0)
                    .classed('show', true)
                  ;

              } else {
                  on_leave_bar();
              }
          }
        );
        svg.on(
          'mouseleave', function() {
            on_leave_bar();
          }
        );
        
    });


}

/*
{% comment %}
  JSON input format:

  Lng x Lemma

  {'LT':
    [
      {
        freq: 2725,
        language:"LT",
        lemma:"SAY/SAID",
        omitted:106,
        ratio_omitted: 0.038,
      },
      <...>
    ],
    <...>
  }
{% endcomment %}
*/
