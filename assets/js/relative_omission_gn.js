/*jshint esversion: 6 */

function log() {
  window.console.log.apply(null, arguments);
}

function relative_omission() {
    "use strict";

    // https://observablehq.com/@d3/zoomable-bar-chart

    var d3 = window.d3;

    if (!window.vis_data) return;

    var data_size = Object.values(window.vis_data)[0].length;

    log(window.vis_data, Object.values(window.vis_data)[0], data_size);

    var $charts_wrapper = $('.charts-wrapper');

    // visualisation parameters
    const zoom_threshold = 10.0;
    const zoom_max = 20;
    const zoom_speed = 1; // 0.5 fast, 1 medium, 2: slow
    const margins = {top: 20, right: 20, bottom: 20, left: 40};
    const dims = {
        ch: 200.0,         // total height of the svg (includes margins)
        // https://devdocs.io/d3~5/d3-scale#scaleImplicit
        step_width: 1,    // step width for the bars (see d3.js doc)
        bar_padding: 0.2,  // ratio of step width used as a gap between 2 bars
    };

    // height and width for the bars area of the svg
    dims.h = dims.ch - margins.bottom - margins.top;
    dims.w = (dims.step_width) * data_size;
    dims.cw = dims.w + margins.left + margins.right;
    dims.extent = [[margins.left, margins.top], [margins.left + dims.w, margins.top + dims.h]];

    var charts = [];
    // scale shared betwen all charts.
    var g_scale_x = null;
    // the zoom tranform that was last drawn.
    // shared between all charts.
    var g_trans = get_unique_transform();

    // for optimisation purpose
    window.viz_highlights = null;
    window.viz_cursors = null;

    function get_unique_transform() {
        // returns a unique identity tranform
        // NOT the zoomIdentitySingleton
        return d3.zoomIdentity.scale(2).scale(0.5);
    }

    // treat each dataset, one by one, one for each translatation
    $.each(window.vis_data, (text_code, data) => {
        var text_info = window.get_text_info(text_code);

        // render the template and add it to viz div wrapper
        $charts_wrapper.append(window.apply_template(
            'chart-wrapper-template',
            {'text_code': text_code}
        ));
        var chart_wrapper = d3.select($charts_wrapper.children(':last')[0]);

        // update the svg element
        // https://chartio.com/resources/tutorials/how-to-resize-an-svg-when-the-window-is-resized-in-d3-js/
        var svg = chart_wrapper.select('.chart');
        svg.attr('viewBox', '0 0 '+dims.cw+' '+dims.ch)
        //  .attr("preserveAspectRatio", "xMinYMin meet")
        ;

        function myDelta() {
            // 500: medium zooming increment for each mouse wheel tick
            // 1500: very slow; 200: fast
            // Note that speed is also browser depdendent (FF much faster).
            var ret = -d3.event.deltaY * (d3.event.deltaMode ? 120 : 1) / 500 / zoom_speed;
            // var ret = 0.4 * (d3.event.deltaY > 0.0 ? -1 : 1);
            // window.console.log(ret);
            return ret;
        }

        var zoom = svg.call(
            d3.zoom()
            .scaleExtent([1, zoom_max])
            .translateExtent(dims.extent)
            .extent(dims.extent)
            .wheelDelta(myDelta)
            .on("zoom", zoomed)
        );
        // default transform is the immutable identity singleton.
        // we replace that because we cheat and mutate it in the zoomed event.
        // without a wrong identity transform would be used next time we
        // add / replace a chart on the web page and cause misalignment of
        // highlighted bar, etc.
        // A bit of a hack but d3 zoom doesn't allow us to change
        // a transform applied to a svg...
        svg.node().__zoom = get_unique_transform();

        var chart_group = svg.append('g')
          // .attr('transform', 'translate('+margins.left+', '+margins.top+')')
        ;

        // scales & axes
        // var scale_y = d3.scaleLinear().domain([0, 1.0]).range([dims.h, 0]);
        var scale_y = d3.scaleLinear()
            .domain([0, 1.0])
            .range([dims.extent[0][1], dims.extent[1][1]])
        ;
        if (g_scale_x === null) {
            g_scale_x = d3.scaleBand()
                .domain(data.map(d => d.lemma))
                .range([dims.extent[0][0], dims.extent[1][0]])
                // .padding(dims.bar_padding)
                .padding(0.0)
            ;
        }

        charts.push({
            svg: svg,
        });

        // bars
        var bars = chart_group.append('g').classed('bars', true);
        bars.selectAll('.bar')
            .data(data).enter()
            .append('rect')
                .classed('bar', true)
                .attr('x', d => g_scale_x(d.lemma))
                .attr('y', scale_y(0.0))
                .attr('width', g_scale_x.bandwidth())
                .attr('height', d => scale_y(d.omitted / d.freq) - scale_y(0))
        ;

        // vertical "cursor" for the hovered bar
        // and corresponding ones in the other languages
        bars.append('line')
            .classed('cursor', true)
            .attr('x1', 0)
            .attr('x2', 0)
            .attr('y1', scale_y(0.0))
            .attr('y2', scale_y(1.0))
            .classed('show', false)
        ;

        // http://bl.ocks.org/d3noob/ccdcb7673cdb3a796e13 (rotated labels)
        function axis_x(g, zoom_factor) {
            var is_hidden = zoom_factor < zoom_threshold;

            if (!g.classed('ticked')) {
                // set up first time
                g.attr('transform', 'translate(0, '+(margins.top + dims.h)+')')
                .call(d3.axisTop(g_scale_x));
                g.selectAll('text')
                    .attr("y", "0.4em")
                    .attr("x", "0.7em")
                    .attr('transform', 'rotate(-90)')
                ;
                g.classed('ticked', true);
            } else {
                // optimisation: we only translate according to change in zoom
                if (!is_hidden) {
                    var offset = g_scale_x.bandwidth() / 2.0;
                    g.selectAll('g').attr('transform', d => 'translate('+(g_scale_x(d)+offset).toFixed(3)+',0)');
                }
            }

            g.classed('hidden', is_hidden);
        }

        chart_group.append('g').classed('axis-x', true).call(axis_x, 1.0);

        // white rectangle to cover the bars than can spill out of the central
        // area and overlap with the y axis.
        chart_group.append('rect')
            .attr('height', dims.ch)
            .attr('y', margins.top)
            .attr('fill', 'white')
            .attr('width', margins.left)
        ;

        chart_group.append('rect')
            .attr('height', dims.ch)
            .attr('y', margins.top)
            .attr('fill', 'white')
            .attr('x', margins.left + dims.w)
            .attr('width', margins.right + 2)
        ;

        var axis_y = chart_group.append('g').classed('axis-y', true)
            .attr('transform', 'translate('+margins.left+', 0)')
            .call(d3.axisLeft(scale_y)
                .ticks(3, '%')
                // TODO: add more ticks on Y axes but d3.js won't listen!
                //.tickValues([0, 0.25, 0.5, 0.75, 1])
                //.tickFormat(d3.format('%'))
            )
        ;

        // title of the chart
        svg.append('g').classed('title', true)
            .append('text')
            .text(text_info.label)
            .attr('x', 0)
            .attr('y', '1em')
        ;

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

                var idx = g_trans.invertX(xy[0]) - margins.left;
                idx = Math.floor(idx);

                if (data[idx]) {
                    var bar = bars.select('.bar:nth-child('+(idx+1)+')');
                    if (bar.classed('highlighted')) return;

                    clear_highlight();
                    bar.classed('highlighted', true);

                    window.viz_highlights = bar;

                    var datum = bar.datum();

                    datum.text_label = window.get_text_info(text_code).label;

                    // log(datum);
                    window.infobox_dict(datum);

                    var x0 = g_scale_x(datum.lemma);
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

        function zoomed() {
            // the event transform;
            // at this stage it is the same as svg.node().__zoom
            // i.e. d3.zoomTransform(chart.svg.node())
            var t = d3.event.transform;

            // only apply that transform if it's significantly different;
            // we don't want to trigger to many expensive redraws.
            // Continue if any of these conditions is true:
            //  pan by half a bar width
            //  zoom by half a unit
            var xy = d3.mouse(this);
            var diff = Math.abs(g_trans.applyX(xy[0]) - t.applyX(xy[0]));
            if (
                ((diff / g_scale_x.step() * 2.0) < 1.0) &&
                ((Math.abs(t.k - g_trans.k) * 2.0) < 1.0)
            ) {
                // window.console.log('SKIPPED');
                return;
            }

            // true if zoom scale has changed from or to the
            // range where the label are on teh x axis
            // and the bars have a padding
            // var has_transitioned = g_scale_x.padding() != old_padding;
            var has_transitioned = ((t.k < zoom_threshold) && (g_trans.k >= zoom_threshold)) ||
                (t.k >= zoom_threshold) && (g_trans.k < zoom_threshold);

            g_trans.x = t.x;
            g_trans.k = t.k;
            // window.console.log(g_trans.k, g_trans.x);

            var new_range = [dims.extent[0][0], dims.extent[1][0]]
                .map(d => g_trans.applyX(d));
            var new_xs = d => g_scale_x(d.lemma).toFixed(3);

            g_scale_x.range(new_range);
            var old_padding = g_scale_x.padding();
            g_scale_x.padding(
                g_trans.k >= zoom_threshold ? dims.bar_padding : 0.0
            );

            // window.console.log(has_transitioned);

            for (var chart of charts) {
                // copy the triggering transform into other svgs
                // to keep them in sync
                // Otherwise, if we zoom in on first svg
                // then zoom in on second, the second will start from overview
                // It also solves other issues with mousemove bar detection
                var t2 = d3.zoomTransform(chart.svg.node());
                t2.x = t.x;
                t2.y = t.y;
                t2.k = t.k;

                if (1) {
                    var bw = g_scale_x.bandwidth().toFixed(3);
                    chart.svg.selectAll(".bar")
                        .attr("x", new_xs)
                        .attr("width", bw)
                    ;
                } else {
                    // Several times faster, makes it more accessible,
                    // but would need to fix the cursor (position & width)
                    // and the highlighted bar (stroke too wide)
                    chart.svg.selectAll('.bars')
                        .attr('transform', 'translate('+g_trans.x+',0) scale('+g_trans.k+', 1)');
                }

                chart.svg.selectAll('.axis-x').call(axis_x, g_trans.k);
            }
        }
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
