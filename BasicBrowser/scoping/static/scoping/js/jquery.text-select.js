(function (factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['jquery'], factory);
    } else if (typeof module === 'object' && module.exports) {
        // Node/CommonJS
        module.exports = factory(require('jquery'));
    } else {
        // Browser globals
        factory(jQuery);
    }
}(function($, undefined) {
    "use strict";

    var _select = function() {
        var el = this.get(0);
        var doc = window.document,
            sel, range;
        if (window.getSelection && doc.createRange) {
            sel = window.getSelection();
            range = doc.createRange();
            range.selectNodeContents(el);
            sel.removeAllRanges();
            sel.addRange(range);
        } else if (doc.body.createTextRange) {
            range = doc.body.createTextRange();
            range.moveToElementText(el);
            range.select();
        }
        this.trigger("selecttext.selected");
        return this;
    };

    var _unselect = function() {
        if (window.getSelection) {
            if (window.getSelection().empty) {
                window.getSelection().empty();
            } else if (window.getSelection().removeAllRanges) {
                window.getSelection().removeAllRanges();
            }
        } else if (document.selection) {
            document.selection.empty();
        }
        this.trigger("selecttext.unselected");
        return this;
    };

    var _copyText = function() {
        try {
            this.selectText();
            if(!$.canCopyText) {
                throw "Unsupported";
            }
            document.execCommand('copy');
            this.selectText(false);
            this.trigger("selecttext.copied");
        } catch (e) {
            console.warn("Copying text unsupported");
        }
        return this;
    };

    $.fn.extend({
        selectText: function(select) {
            select = select !== false;
            var method = select ? _select : _unselect;
            return method.call(this);
        },
        copyText: _copyText.bind(this),
    });
    $.canCopyText = document.queryCommandSupported("copy");

    return $;
}));

