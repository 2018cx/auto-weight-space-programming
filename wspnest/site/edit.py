"""Edit the WSPNest page in the browser: click any text and type. Saves write the edited <main> back to index.html.

  python3 edit.py      # then open http://localhost:8011
"""
import hashlib
import http.server
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "index.html")
PORT = int(os.environ.get("PORT", "8011"))

TOOLBAR = """
<div id="edbar" style="position:fixed;bottom:16px;right:16px;z-index:99;color:#1a1240;background:#fff;border:1px solid #c9c8c2;
 border-radius:8px;padding:8px 12px;font:13px -apple-system,Segoe UI,sans-serif;box-shadow:0 2px 10px rgba(0,0,0,.08)">
 <b>Editing</b> · click any text to change it · <span id="edst">loaded</span>
 <button id="edsave" style="margin-left:8px">Save (Cmd+S)</button></div>
<script>
const REV0 = "__REV__"; let REV = REV0, dirty = false;
const main = document.querySelector('main');
main.querySelectorAll('h1,h2,h3,p,li,td,th,div.tree,div.status,div.kicker,footer').forEach(e => e.contentEditable = 'true');
document.querySelector('footer') && (document.querySelector('footer').contentEditable = 'true');
document.addEventListener('input', () => { dirty = true; document.getElementById('edst').textContent = 'unsaved changes'; });
async function save() {
  const clone = main.cloneNode(true);
  clone.querySelectorAll('[contenteditable]').forEach(e => e.removeAttribute('contenteditable'));
  const r = await fetch('/save', {method: 'POST', headers: {'X-Rev': REV}, body: clone.innerHTML});
  const st = document.getElementById('edst');
  if (r.status === 409) { st.textContent = 'NOT SAVED: the file changed elsewhere. Copy your text, then reload.'; st.style.color = '#c62828'; return; }
  REV = r.headers.get('X-Rev'); dirty = false; st.style.color = ''; st.textContent = 'saved ' + new Date().toLocaleTimeString();
}
document.getElementById('edsave').onclick = save;
document.addEventListener('keydown', e => { if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); save(); } });
setInterval(() => { if (dirty) save(); }, 8000);
window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
</script>"""


def rev(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8", headers=None):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            s = open(PAGE).read()
            return self._send(200, s.replace("</body>", TOOLBAR.replace("__REV__", rev(s)) + "</body>"))
        f = os.path.join(HERE, os.path.basename(path))
        if os.path.isfile(f) and f.endswith((".svg", ".png", ".jpg", ".gif")):
            return self._send(200, open(f, "rb").read(), "image/svg+xml" if f.endswith(".svg") else "image/" + f.rsplit(".", 1)[1])
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/save":
            return self._send(404, "not found", "text/plain")
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        s = open(PAGE).read()
        if self.headers.get("X-Rev") != rev(s):
            return self._send(409, "stale", "text/plain")
        new = re.sub(r"(<main>)(.*)(</main>)", lambda m: m.group(1) + body + m.group(3), s, count=1, flags=re.S)
        open(PAGE, "w").write(new)
        self._send(200, "ok", "text/plain", {"X-Rev": rev(new)})


if __name__ == "__main__":
    print(f"page editor at http://localhost:{PORT}")
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
