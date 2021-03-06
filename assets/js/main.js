$(function() {
    /*
    Returns the height $element should have to fill the remaining
    space in the viewport.
    If noscrollbar =  1, returns height so that the whole page is
    contained within the viewport. i.e. no scrollbar
    */
    window.get_elastic_height = function($element, min, margin, noscrollbar) {
        var height = 0;

        // This is a hack for OL - we force 100% height when it is in
        // full screen mode. See zoom view of images on the faceted search.
        if ($element.find('.ol-full-screen-true').length > 0) {
            return '100%';
        }

        min = min || 0;
        margin = margin || 0;
        noscrollbar = noscrollbar || 0;

        var current_height = $element.outerHeight();
        if (noscrollbar) {
            // ! only works if body height is NOT 100% !
            height = $(window).outerHeight() - $('body').outerHeight() + current_height;
            height = (height <= min) ? min : height;
        } else {
            var window_height = $(window).height() - margin;
            height = window_height - $element.offset().top + $(document).scrollTop();
            height = (height <= min) ? min : height;
            height = (height > window_height) ? window_height : height;
        }

        return Math.floor(height);
    };

    /*
    Make $target height elastic. It will take the rest of the
    viewport space. This is automatically updated when the user
    scrolls or change the viewport size.
    $callback is called each time the height is updated.
    */
    window.elastic_element = function($target, callback, min, margin) {
        var on_resize = function(e) {
            var height = window.get_elastic_height($target, min, margin);
            $target.css('height', height);
            callback();
        };
        $(window).on('resize scroll', function(e) {on_resize(e);});
        $(document).on('webkitfullscreenchange mozfullscreenchange fullscreenchange MSFullscreenChange', function(e) {on_resize(e);});
        on_resize();
    };
});
