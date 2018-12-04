(function() {
  var fn = function() {
    Bokeh.safely(function() {
      (function(root) {
        function embed_document(root) {
          
        var docs_json = '{"4ec8e6e0-f060-479d-bd77-fcc426a13c05":{"roots":{"references":[{"attributes":{"dimension":1,"plot":{"id":"1003","subtype":"Figure","type":"Plot"},"ticker":{"id":"1019","type":"BasicTicker"}},"id":"1022","type":"Grid"},{"attributes":{},"id":"1009","type":"LinearScale"},{"attributes":{"data_source":{"id":"1034","type":"ColumnDataSource"},"glyph":{"id":"1036","type":"Circle"},"hover_glyph":null,"muted_glyph":null,"nonselection_glyph":{"id":"1037","type":"Circle"},"selection_glyph":null,"view":{"id":"1039","type":"CDSView"}},"id":"1038","type":"GlyphRenderer"},{"attributes":{},"id":"1043","type":"BasicTickFormatter"},{"attributes":{"active_drag":"auto","active_inspect":"auto","active_multi":null,"active_scroll":{"id":"1025","type":"WheelZoomTool"},"active_tap":"auto","tools":[{"id":"1023","type":"HoverTool"},{"id":"1024","type":"PanTool"},{"id":"1025","type":"WheelZoomTool"},{"id":"1026","type":"ResetTool"},{"id":"1027","type":"TapTool"}]},"id":"1028","type":"Toolbar"},{"attributes":{},"id":"1045","type":"Selection"},{"attributes":{"below":[{"id":"1013","type":"LinearAxis"}],"left":[{"id":"1018","type":"LinearAxis"}],"plot_width":950,"renderers":[{"id":"1013","type":"LinearAxis"},{"id":"1017","type":"Grid"},{"id":"1018","type":"LinearAxis"},{"id":"1022","type":"Grid"},{"id":"1038","type":"GlyphRenderer"}],"title":{"id":"1002","type":"Title"},"toolbar":{"id":"1028","type":"Toolbar"},"toolbar_location":"below","x_range":{"id":"1005","type":"DataRange1d"},"x_scale":{"id":"1009","type":"LinearScale"},"y_range":{"id":"1007","type":"DataRange1d"},"y_scale":{"id":"1011","type":"LinearScale"}},"id":"1003","subtype":"Figure","type":"Plot"},{"attributes":{},"id":"1046","type":"UnionRenderers"},{"attributes":{},"id":"1011","type":"LinearScale"},{"attributes":{},"id":"1041","type":"BasicTickFormatter"},{"attributes":{"callback":null,"renderers":"auto","tooltips":[["title","@title"],["Length","@Length"]]},"id":"1023","type":"HoverTool"},{"attributes":{"plot":null,"text":""},"id":"1002","type":"Title"},{"attributes":{"url":"@dlink"},"id":"1047","type":"OpenURL"},{"attributes":{"callback":null},"id":"1007","type":"DataRange1d"},{"attributes":{},"id":"1024","type":"PanTool"},{"attributes":{"axis_label":"Number of internal links","formatter":{"id":"1041","type":"BasicTickFormatter"},"plot":{"id":"1003","subtype":"Figure","type":"Plot"},"ticker":{"id":"1014","type":"BasicTicker"}},"id":"1013","type":"LinearAxis"},{"attributes":{"source":{"id":"1034","type":"ColumnDataSource"}},"id":"1039","type":"CDSView"},{"attributes":{"axis_label":"Number of language pages","formatter":{"id":"1043","type":"BasicTickFormatter"},"plot":{"id":"1003","subtype":"Figure","type":"Plot"},"ticker":{"id":"1019","type":"BasicTicker"}},"id":"1018","type":"LinearAxis"},{"attributes":{},"id":"1025","type":"WheelZoomTool"},{"attributes":{},"id":"1014","type":"BasicTicker"},{"attributes":{},"id":"1026","type":"ResetTool"},{"attributes":{"plot":{"id":"1003","subtype":"Figure","type":"Plot"},"ticker":{"id":"1014","type":"BasicTicker"}},"id":"1017","type":"Grid"},{"attributes":{"fill_alpha":{"value":0.1},"fill_color":{"value":"#1f77b4"},"line_alpha":{"value":0.1},"line_color":{"value":"#1f77b4"},"size":{"units":"screen","value":10},"x":{"field":"num_ilinks"},"y":{"field":"num_langs"}},"id":"1037","type":"Circle"},{"attributes":{"callback":{"id":"1047","type":"OpenURL"}},"id":"1027","type":"TapTool"},{"attributes":{"fill_alpha":{"value":0.5},"fill_color":{"field":"COLOR"},"line_color":{"field":"COLOR"},"size":{"units":"screen","value":10},"x":{"field":"num_ilinks"},"y":{"field":"num_langs"}},"id":"1036","type":"Circle"},{"attributes":{},"id":"1019","type":"BasicTicker"},{"attributes":{"callback":null},"id":"1005","type":"DataRange1d"},{"attributes":{"callback":null,"data":{"COLOR":["#FDE724","#208F8C","#440154"],"Length":[64171,58228,29119],"dlink":["docs.html#sec-1","docs.html#sec0","docs.html#sec1"],"index":[0,1,2],"num_ilinks":[1735,1779,258],"num_langs":[186,189,37],"title":["Plato","Aristotle","Paris Agreement"]},"selected":{"id":"1045","type":"Selection"},"selection_policy":{"id":"1046","type":"UnionRenderers"}},"id":"1034","type":"ColumnDataSource"}],"root_ids":["1003"]},"title":"Bokeh Application","version":"1.0.1"}}';
        var render_items = [{"docid":"4ec8e6e0-f060-479d-bd77-fcc426a13c05","roots":{"1003":"54590971-a1ca-4ad8-b42b-f374afa5bac5"}}];
        root.Bokeh.embed.embed_items(docs_json, render_items);
      
        }
        if (root.Bokeh !== undefined) {
          embed_document(root);
        } else {
          var attempts = 0;
          var timer = setInterval(function(root) {
            if (root.Bokeh !== undefined) {
              embed_document(root);
              clearInterval(timer);
            }
            attempts++;
            if (attempts > 100) {
              console.log("Bokeh: ERROR: Unable to run BokehJS code because BokehJS library is missing");
              clearInterval(timer);
            }
          }, 10, root)
        }
      })(window);
    });
  };
  if (document.readyState != "loading") fn();
  else document.addEventListener("DOMContentLoaded", fn);
})();