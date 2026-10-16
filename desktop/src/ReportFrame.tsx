import { useEffect, useMemo, useRef } from "react";

// An opaque-origin frame cannot reach Tauri or the shell's DOM. Links are
// explicit messages, checked by the parent and the engine before opening.
export function ReportFrame({
  html,
  theme,
  anchor,
  onView,
  onLink,
}: {
  html: string;
  theme: string;
  anchor: string;
  onView: (view: "playbook" | "report", anchor?: string) => void;
  onLink: (url: string) => void;
}) {
  const frame = useRef<HTMLIFrameElement>(null);
  const keys = useMemo(
    () =>
      new Set(
        Array.from(
          html.matchAll(/data-review-key="([^"]+)"/g),
          (m) => m[1],
        ).filter(
          (key) =>
            /^necropsy:(boss|v1):[a-f0-9]{64}:/.test(key) && key.length < 600,
        ),
      ),
    [html],
  );
  const source = useMemo(() => {
    const stored: Record<string, string> = { "necropsy:theme": theme };
    let persistent = true;
    try {
      for (const key of keys)
        if (localStorage.getItem(key) === "1") stored[key] = "1";
    } catch {
      persistent = false;
    }
    const policy = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">`;
    const storage = `<script>
      (function() {
        var values = ${JSON.stringify(stored).replace(/</g, "\\u003c")};
        var allowed = ${JSON.stringify([...keys]).replace(/</g, "\\u003c")};
        Object.defineProperty(window, 'localStorage', {value: {
          getItem: function(key) { return values[key] || null; },
          setItem: function(key, value) {
            values[key] = String(value);
            if (allowed.indexOf(key) !== -1) parent.postMessage({type:'necropsy-review', key:key, value:String(value)}, '*');
          },
          removeItem: function(key) {
            delete values[key];
            if (allowed.indexOf(key) !== -1) parent.postMessage({type:'necropsy-review', key:key, value:null}, '*');
          }
        }});
      })();
    </script>`;
    const bridge = `<script>
      (function() {
      document.addEventListener('click', function(e) {
        var link = e.target.closest && e.target.closest('a');
        if (!link) return;
        var href = link.getAttribute('href') || '';
        e.preventDefault();
        if (href.charAt(0) === '#') {
          setTimeout(function() { var target = document.getElementById(href.slice(1)); if (target) target.scrollIntoView(); }, 0);
          return;
        }
        var view = /^(playbook|report)\\.html(?:#(.*))?$/.exec(href);
        if (view) {
          parent.postMessage({type:'necropsy-view', view:view[1], anchor:view[2] || ''}, '*');
        } else if (href.indexOf('https://') === 0) {
          parent.postMessage({type:'necropsy-link', url:href}, '*');
        }
      }, true);
      window.addEventListener('message', function(e) {
        if (e.source === parent && e.data && e.data.type === 'necropsy-theme') {
          document.documentElement.setAttribute('data-theme', e.data.theme);
        }
        if (e.source === parent && e.data && e.data.type === 'necropsy-anchor') {
          var target = document.getElementById(e.data.anchor);
          if (target) { target.scrollIntoView(); var heading = target.querySelector('h2'); if (heading) heading.focus({preventScroll:true}); }
        }
        if (e.source === parent && e.data && e.data.type === 'necropsy-storage-failed') {
          var status = document.getElementById('review-status');
          if (status) status.textContent = 'Review marks last until you close this view; local storage is unavailable.';
        }
      });
      document.documentElement.setAttribute('data-theme', '${theme === "light" ? "light" : "dark"}');
      var toggle = document.getElementById('theme-toggle');
      if (toggle) toggle.hidden = true;
      var status = document.getElementById('review-status');
      if (status) status.textContent = ${JSON.stringify(persistent ? "Review marks are saved on this computer, for this exact analysis." : "Review marks last until you close this view; local storage is unavailable.")};
      })();
    </script>`;
    return html
      .replace("<head>", "<head>" + policy + storage)
      .replace("</body>", bridge + "</body>");
    // Theme updates use postMessage to preserve scroll, expanded evidence and review marks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [html, keys]);
  useEffect(() => {
    frame.current?.contentWindow?.postMessage(
      { type: "necropsy-theme", theme },
      "*",
    );
  }, [theme, source]);
  useEffect(() => {
    const listener = (event: MessageEvent) => {
      if (event.source !== frame.current?.contentWindow || !event.data) return;
      if (
        event.data.type === "necropsy-view" &&
        ["playbook", "report"].includes(event.data.view)
      )
        onView(
          event.data.view,
          typeof event.data.anchor === "string" ? event.data.anchor : "",
        );
      if (
        event.data.type === "necropsy-link" &&
        typeof event.data.url === "string"
      )
        onLink(event.data.url);
      if (event.data.type === "necropsy-review" && keys.has(event.data.key)) {
        try {
          if (event.data.value === "1")
            localStorage.setItem(event.data.key, "1");
          else if (event.data.value === null)
            localStorage.removeItem(event.data.key);
        } catch {
          frame.current?.contentWindow?.postMessage(
            { type: "necropsy-storage-failed" },
            "*",
          );
        }
      }
    };
    window.addEventListener("message", listener);
    return () => window.removeEventListener("message", listener);
  }, [onView, onLink, keys]);
  return (
    <iframe
      ref={frame}
      title="Your Necropsy analysis"
      className="report-frame"
      sandbox="allow-scripts"
      srcDoc={source}
      onLoad={() => {
        frame.current?.contentWindow?.postMessage(
          { type: "necropsy-theme", theme },
          "*",
        );
        if (anchor)
          frame.current?.contentWindow?.postMessage(
            { type: "necropsy-anchor", anchor },
            "*",
          );
      }}
    />
  );
}
