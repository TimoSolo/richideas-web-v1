#!/usr/bin/env python3
"""One-time conversion of the wget mirror of www.richideas.co.za into site/.

Usage: python3 scripts/build.py <mirror-dir>   (dir containing www.richideas.co.za/)

What it does
- keeps the 10 real pages and the 27 blog posts; drops demo pages, shortlinks,
  category/date archives and Elementor placeholder posts
- normalises every internal link to a relative path (works at any base path,
  e.g. GitHub Pages project sites)
- strips the WordPress runtime: REST/RSD/oEmbed/feed links, emoji, speculation
  rules, Contact Form 7, Primary Addon JS, MediaElement, Cloudflare email
  obfuscation, search widgets, theme credits
- renames "file.css?ver=1.2" assets to "file.css" and copies only the assets
  the kept pages (and their CSS) actually reference
- injects the shared chrome (scripts/chrome.py) and page fragments from
  templates/ (native forms, About page, fee table, home hero copy)
- writes robots.txt, sitemap.xml, 404.html, .nojekyll

After this runs, site/ is the source of truth; edit it directly.
"""
import os, re, sys, shutil, html, json, glob
from urllib.parse import urljoin, urlparse, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import chrome  # noqa: E402

MIRROR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
if not MIRROR or not os.path.isdir(os.path.join(MIRROR, "www.richideas.co.za")):
    sys.exit("usage: build.py <mirror-dir containing www.richideas.co.za/>")
SRC = os.path.join(MIRROR, "www.richideas.co.za")
SITE = os.path.join(ROOT, "site")
TPL = os.path.join(ROOT, "templates")
HOST = "https://www.richideas.co.za"

PAGES = {  # canonical path -> mirror file
    "/": "index.html",
    "/about-us/": "about-us/index.html",
    "/fee-structure/": "fee-structure/index.html",
    "/book-a-meeting/": "book-a-meeting/index.html",
    "/free-will/": "free-will/index.html",
    "/review/": "review/index.html",
    "/questions/": "questions/index.html",
    "/contact-us/": "contact-us.html",
    "/blogs/": "blogs/index.html",
    "/thankyou/": "thankyou/index.html",
}
DROP_POSTS = {"elementor-1250", "elementor-1256"}
for f in sorted(glob.glob(os.path.join(SRC, "20*/*/*/*/index.html"))):
    slug = f.split(os.sep)[-2]
    if slug in DROP_POSTS:
        continue
    path = "/" + os.path.relpath(os.path.dirname(f), SRC).replace(os.sep, "/") + "/"
    PAGES[path] = os.path.relpath(f, SRC)

# ?p=N shortlink -> canonical path (from og:url in the shortlink copies)
SHORT = {}
for f in glob.glob(os.path.join(SRC, "index.html?p=*.html")):
    n = re.search(r"p=(\d+)", f).group(1)
    h = open(f, encoding="utf-8", errors="ignore").read()
    m = re.search(r'property="og:url" content="([^"]+)"', h)
    if m:
        SHORT[n] = urlparse(m.group(1)).path
SHORT.setdefault("11", "/")

ASSET_RENAMES = {}  # dest root path -> mirror file
NEEDED_CSS = set()


def strip_ver(p):
    return re.sub(r"\?[^/]*$", "", p)


def canon_path(path, query=""):
    """Map a mirror/WordPress path to its final root-relative path (or None to drop)."""
    p = unquote(path)
    m = re.match(r"^/index\.html\?p=(\d+)\.html$", p)
    if m:
        return SHORT.get(m.group(1), "/")
    if (p in ("/", "/index.html")) and query.startswith("p="):
        return SHORT.get(query[2:].split("&")[0], "/")
    if p.startswith(("/wp-content/", "/wp-includes/", "/cdn-cgi/")):
        if "email-protection" in p:
            return None
        p = strip_ver(p)
        if p == "/wp-content/uploads/2025/05/RIG-Services-2025_V1_1_May2025.pdf":
            p = "/wp-content/uploads/2026/04/RIG-Services-2026.pdf"
        return p
    if p.startswith(("/wp-json", "/xmlrpc", "/feed", "/comments/feed", "/wp-admin", "/wp-login")):
        return None
    if p.endswith("/index.html"):
        p = p[: -len("index.html")]
    if p == "/index.html":
        p = "/"
    if p in ("/contact-us.html", "/contact-us"):
        p = "/contact-us/"
    if not p.endswith("/") and "." not in os.path.basename(p):
        p += "/"
    if p in ("/sample-page/", "/agency-homepage-2/"):
        return "/"
    if p.startswith("/category/") or re.match(r"^/20\d\d/(\d\d(/|\.html)?)?$", p) or re.match(r"^/20\d\d/\d\d\.html$", p):
        return "/blogs/"
    if any(p.endswith("/" + s + "/") for s in DROP_POSTS):
        return "/blogs/"
    if p.startswith("/author/"):
        return "/about-us/"
    return p


def resolve(href, base_url):
    """Return (kind, value): ('ext', href) untouched, ('int', rootpath) or ('drop', None)."""
    h = href.strip()
    if not h or h.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "whatsapp:")):
        return "ext", h
    absu = urljoin(base_url, h)
    u = urlparse(absu)
    if u.netloc not in ("www.richideas.co.za", "richideas.co.za"):
        return "ext", h
    p = canon_path(u.path, u.query)
    if p is None:
        return "drop", None
    frag = ("#" + u.fragment) if u.fragment else ""
    return "int", p + frag


def relativize(rootpath, page_path):
    """rootpath like '/about-us/' or '/wp-content/x.css' -> href relative to page_path ('/x/')."""
    frag = ""
    if "#" in rootpath:
        rootpath, frag = rootpath.split("#", 1)
        frag = "#" + frag
    page_dir = page_path if page_path.endswith("/") else os.path.dirname(page_path) + "/"
    if rootpath == page_dir and frag:
        return frag
    if rootpath.endswith("/"):
        r = os.path.relpath(rootpath.rstrip("/") or "/", page_dir.rstrip("/") or "/")
        r = "./" if r == "." else r + "/"
    else:
        r = os.path.relpath(rootpath, page_dir.rstrip("/") or "/")
    return r + frag


def rewrite_urls(text, base_url, page_path, is_css=False):
    """Rewrite internal URLs in HTML attributes or CSS url()s."""
    def one(href):
        kind, v = resolve(href, base_url)
        if kind == "ext":
            return href
        if kind == "drop":
            return "#"
        if not v.startswith("/"):
            return v
        if v.split("#")[0].startswith(("/wp-content/", "/wp-includes/", "/assets/")):
            register_asset(v.split("#")[0], href, base_url)
        return relativize(v, page_path)

    if is_css:
        return re.sub(r"url\((['\"]?)([^'\")]+)\1\)", lambda m: "url(%s%s%s)" % (m.group(1), one(m.group(2)), m.group(1)), text)

    def attr(m):
        name, q, val = m.group(1), m.group(2), m.group(3)
        if name == "srcset":
            parts = []
            for c in val.split(","):
                c = c.strip()
                if not c:
                    continue
                bits = c.split()
                bits[0] = one(bits[0])
                parts.append(" ".join(bits))
            return f'{name}={q}{", ".join(parts)}{q}'
        return f"{name}={q}{one(val)}{q}"

    text = re.sub(r"\b(href|src|data-src|poster|action|srcset)=([\"'])(.*?)\2", attr, text, flags=re.S)
    text = re.sub(r"url\((['\"]?)([^'\")]+)\1\)", lambda m: "url(%s%s%s)" % (m.group(1), one(m.group(2)), m.group(1)), text)
    return text


def register_asset(rootpath, href, base_url):
    """Record that rootpath (final) must be copied; locate the mirror file that holds it."""
    if rootpath in ASSET_RENAMES or rootpath.startswith("/assets/"):
        return
    absu = urljoin(base_url, href.strip())
    u = urlparse(absu)
    p = unquote(u.path)
    cand = os.path.join(SRC, p.lstrip("/"))
    if u.query and not os.path.exists(cand):
        cand2 = cand + "?" + unquote(u.query)
        if os.path.exists(cand2):
            cand = cand2
    if not os.path.exists(cand):
        d, b = os.path.split(os.path.join(SRC, strip_ver(p).lstrip("/")))
        hits = sorted(glob.glob(os.path.join(d, glob.escape(b) + "?*"))) + sorted(glob.glob(os.path.join(d, glob.escape(b))))
        cand = hits[0] if hits else None
    if cand and os.path.isfile(cand):
        ASSET_RENAMES[rootpath] = cand
        if rootpath.endswith(".css"):
            NEEDED_CSS.add(rootpath)
    else:
        print("  ! missing asset", rootpath, "(from", href, ")")


# ---- HTML cleanup ---------------------------------------------------------
DROP_CSS = [
    "contact-form-7", "blog-designer-pack", "mediaelement",
    "primary-addon-for-elementor/assets/css/animate", "primary-addon-for-elementor/assets/css/themify-icons",
    "primary-addon-for-elementor/assets/css/linea", "primary-addon-for-elementor/assets/css/hover-min",
    "primary-addon-for-elementor/assets/css/icofont", "primary-addon-for-elementor/assets/css/magnific-popup",
    "primary-addon-for-elementor/assets/css/flickity", "primary-addon-for-elementor/assets/css/juxtapose",
    "elementor/assets/lib/animations/",
]
DROP_JS = [
    "contact-form-7", "primary-addon-for-elementor/", "mediaelement", "email-decode", "jotfor.ms",
    "essential-addons-for-elementor-lite/assets/front-end/js", "essential-addons-elementor/eael-",
]
DROP_INLINE_JS = ["var wpcf7", "mejsL10n", "_wpmejsSettings", 'var localize = {"ajaxurl"', "_wpemojiSettings",
                  "wp-emoji-settings", "EAELImageMaskingConfig"]


def cfemail_decode(hexs):
    b = bytes.fromhex(hexs)
    k = b[0]
    return "".join(chr(c ^ k) for c in b[1:])


def clean_head(head, path):
    rm = [
        r'<link rel="profile"[^>]*>', r"<link rel='dns-prefetch'[^>]*>", r"<link href='https://fonts.gstatic.com'[^>]*>",
        r'<link rel="alternate"[^>]*>', r"<link rel='https://api.w.org/'[^>]*>", r'<link rel="https://api.w.org/"[^>]*>',
        r'<link rel="EditURI"[^>]*>', r'<link rel="wlwmanifest"[^>]*>', r"<link rel='shortlink'[^>]*>",
        r'<meta name="generator"[^>]*>', r'<meta name="msapplication-TileImage"[^>]*>',
        r'<style id="wp-emoji-styles-inline-css">.*?</style>',
        r'<script type="speculationrules">.*?</script>',
    ]
    for r in rm:
        head = re.sub(r, "", head, flags=re.S)
    head = re.sub(r"<link[^>]+rel=['\"]stylesheet['\"][^>]*>", lambda m: "" if any(d in m.group(0) for d in DROP_CSS) else m.group(0), head)
    head = re.sub(r"<script[^>]+src=[\"'][^\"']*[\"'][^>]*>\s*</script>", lambda m: "" if any(d in m.group(0) for d in DROP_JS) else m.group(0), head)
    head = re.sub(r"<script(?![^>]*src)[^>]*>.*?</script>", lambda m: "" if any(d in m.group(0) for d in DROP_INLINE_JS) else m.group(0), head, flags=re.S)
    head = re.sub(r'<link rel="canonical" href="[^"]*" />', f'<link rel="canonical" href="{HOST}{path}" />', head)
    # tidy blank lines
    head = re.sub(r"\n\s*\n+", "\n", head)
    return head


def clean_body(body, path, root=""):
    # de-obfuscate Cloudflare emails
    body = re.sub(r'<a href="[^"]*email-protection[^"]*" class="__cf_email__" data-cfemail="([0-9a-f]+)">.*?</a>',
                  lambda m: '<a href="mailto:%s">%s</a>' % ((cfemail_decode(m.group(1)),) * 2), body, flags=re.S)
    body = re.sub(r'<span class="__cf_email__" data-cfemail="([0-9a-f]+)">.*?</span>', lambda m: cfemail_decode(m.group(1)), body, flags=re.S)
    body = re.sub(r'href="[^"]*/cdn-cgi/l/email-protection#([0-9a-f]+)"', lambda m: 'href="mailto:%s"' % cfemail_decode(m.group(1)), body)
    # WordPress/theme leftovers
    body = re.sub(r'<div class="full-screen-search".*?</div>\s*</div>\s*</div>\s*</div>', "", body, flags=re.S)
    body = re.sub(r'<section id="search-2" class="widget widget_search">.*?</section>', "", body, flags=re.S)
    body = re.sub(r'<script type="speculationrules">.*?</script>', "", body, flags=re.S)
    body = re.sub(r'<script[^>]*data-cfasync="false"[^>]*email-decode[^>]*>\s*</script>', "", body)
    body = re.sub(r"<script[^>]+src=[\"'][^\"']*[\"'][^>]*>\s*</script>", lambda m: "" if any(d in m.group(0) for d in DROP_JS) else m.group(0), body)
    body = re.sub(r"<script(?![^>]*src)[^>]*>.*?</script>", lambda m: "" if any(d in m.group(0) for d in DROP_INLINE_JS) else m.group(0), body, flags=re.S)
    # chrome markers (header/footer are regenerated by chrome.py)
    body = re.sub(r'<header id="masthead".*?</header><!-- header section end -->', "<!-- ri:header --><!-- /ri:header -->", body, flags=re.S)
    body = re.sub(r"<footer\s+id=\"footer\".*?</footer>", "<!-- ri:footer --><!-- /ri:footer -->", body, flags=re.S)
    body = re.sub(r"<!-- start Back To Top -->.*?<!-- end Back To Top -->", "", body, flags=re.S)
    # entrance animations depend on scroll handlers; render everything visible from the start
    body = body.replace(" elementor-invisible", "")
    body = re.sub(r'&quot;_animation&quot;:&quot;[^&]*&quot;,?', "", body)
    body = re.sub(r"\n\s*\n\s*\n+", "\n\n", body)
    # Elementor lazy-loads handler chunks from urls.assets: point it at the local copy
    body = body.replace('"assets":"https:\\/\\/www.richideas.co.za\\/wp-content\\/plugins\\/elementor\\/assets\\/"',
                        '"assets":"' + root.replace("/", "\\/") + 'wp-content\\/plugins\\/elementor\\/assets\\/"')
    return body


def fragment(name, **kw):
    t = open(os.path.join(TPL, name), encoding="utf-8").read()
    for k, v in kw.items():
        t = t.replace("{{" + k + "}}", v)
    return t


def post_index():
    """List of (date_iso, title, rootpath) for the kept posts, newest first."""
    out = []
    for path, f in PAGES.items():
        if not re.match(r"^/20\d\d/", path):
            continue
        h = open(os.path.join(SRC, f), encoding="utf-8", errors="ignore").read()
        t = re.search(r'<h3 class="blog-title">(.*?)</h3>', h, re.S)
        title = html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip() if t else path
        date = "-".join(path.split("/")[1:4])
        out.append((date, title, path))
    return sorted(out, reverse=True)


def nice_date(iso):
    import datetime
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def page_specific(body, path, root):
    if path == "/":
        body = re.sub(r'<h1 class="banner-title animated" data-animation="fadeInDown">.*?</p>',
                      fragment("pages/home-hero.html", root=root), body, count=1, flags=re.S)
        body = body.replace('<video class="elementor-video" src=', f'<video class="elementor-video" poster="{root}assets/img/video-poster.jpg" src=', 1)
        body = body.replace('preload="metadata"', 'preload="metadata" playsinline', 1)
        # "Why Rich Ideas" strip goes right after the "YOU deserve a great plan" section
        m = re.search(r'(<section class="elementor-section elementor-top-section elementor-element elementor-element-70f2246.*?</section>)', body, re.S)
        if m:
            body = body.replace(m.group(1), m.group(1) + fragment("pages/home-why.html", root=root), 1)
    elif path == "/about-us/":
        body = re.sub(r'<article id="post-322".*?</article><!-- #post-322 -->', fragment("pages/about-us.html", root=root), body, count=1, flags=re.S)
        body = body.replace('class="col-md-8 col-sm-12 col-xs-12 content-wrapper bizberg_blog_content"', 'class="col-md-12 col-sm-12 col-xs-12 content-wrapper bizberg_blog_content ri-about"', 1)
        body = re.sub(r'<div class="col-md-4 col-sm-12 bizberg_sidebar">\s*<div id="sidebar" class="sidebar-wrapper ">.*?</section>\s*</div>\s*</div>', "", body, count=1, flags=re.S)
    elif path == "/fee-structure/":
        body = re.sub(r'<p><a href="[^"]*RIG-Services-20[^"]*\.pdf">Download Our Services Guide</a></p>',
                      lambda m: fragment("pages/fees.html", root=root) + '<p><a class="btn ri-btn-outline" href="https://www.richideas.co.za/wp-content/uploads/2026/04/RIG-Services-2026.pdf" target="_blank" rel="noopener">Download our Services Guide (PDF)</a></p>', body, count=1, flags=re.S)
    elif path == "/book-a-meeting/":
        body = re.sub(r"<iframe[^>]*forms\.office\.com[^>]*>.*?</iframe>", fragment("forms/book-a-meeting.html", root=root), body, count=1, flags=re.S)
    elif path == "/free-will/":
        body = re.sub(r"<iframe[^>]*forms\.office\.com[^>]*>.*?</iframe>", fragment("forms/free-will.html", root=root), body, count=1, flags=re.S)
    elif path == "/review/":
        body = re.sub(r"<iframe[^>]*forms\.office\.com[^>]*>.*?</iframe>", fragment("forms/review.html", root=root), body, count=1, flags=re.S)
    elif path == "/questions/":
        body = re.sub(r"<iframe[^>]*jotform[^>]*>.*?</iframe>", fragment("forms/questions.html", root=root), body, count=1, flags=re.S)
    elif path == "/contact-us/":
        body = re.sub(r'(<div class="elementor-widget-container">)\s*https://forms\.microsoft\.com/r/XDPrW0u9V6\s*(</div>)',
                      lambda m: m.group(1) + fragment("forms/contact.html", root=root) + m.group(2), body, count=1, flags=re.S)
        body = body.replace("<iframe loading=\"lazy\"", "<iframe loading=\"lazy\"").replace('<iframe frameborder="0" scrolling="no" marginheight="0" marginwidth="0"', '<iframe loading="lazy" title="Map to Rich Ideas, Jukskei Park" frameborder="0" scrolling="no" marginheight="0" marginwidth="0"')
    elif path == "/blogs/":
        posts = post_index()
        nl = json.load(open(os.path.join(TPL, "newsletter.json"), encoding="utf-8"))
        nl_items = "\n".join(f'<li><a href="{i["url"]}" target="_blank" rel="noopener">{html.escape(i["title"])}</a><span class="ri-date">{i["date"]}</span><p>{html.escape(i["summary"])}</p></li>' for i in nl)
        post_items = "\n".join(f'<li><a href="{relativize(p, path)}">{html.escape(t)}</a><span class="ri-date">{nice_date(d)}</span></li>' for d, t, p in posts)
        body = re.sub(r"<iframe[^>]*substack[^>]*>.*?</iframe>", fragment("pages/blogs.html", root=root, newsletter=nl_items, posts=post_items), body, count=1, flags=re.S)
    return body


def process_page(path, relfile):
    src = os.path.join(SRC, relfile)
    base_url = HOST + "/" + relfile.replace(os.sep, "/")
    h = open(src, encoding="utf-8", errors="ignore").read()
    head_i, head_j = h.find("<head"), h.find("</head>")
    head, body = h[head_i:head_j], h[head_j:]
    pre = h[:head_i]
    root = "../" * (path.count("/") - 1)
    head = clean_head(head, path)
    head = head.replace("</title>", "</title>\n" + chrome.head_html(root), 1) if "</title>" in head else head + chrome.head_html(root)
    body = clean_body(body, path, root)
    body = page_specific(body, path, root)
    out = pre + rewrite_urls(head + body, base_url, path)
    # trim "index.html" from canonical/og where wget left it
    dest = os.path.join(SITE, path.lstrip("/"), "index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8").write(out)


def process_css(rootpath):
    srcf = ASSET_RENAMES[rootpath]
    css = open(srcf, encoding="utf-8", errors="ignore").read()
    base_url = HOST + "/" + os.path.relpath(srcf, SRC).replace(os.sep, "/")
    css = rewrite_urls(css, base_url, rootpath, is_css=True)
    dest = os.path.join(SITE, rootpath.lstrip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8").write(css)


def main():
    if os.path.isdir(SITE):
        for entry in os.listdir(SITE):
            if entry != "assets":
                p = os.path.join(SITE, entry)
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for a in ("/wp-content/uploads/2021/04/TTLogoDark.png", "/wp-content/uploads/2021/04/cropped-TTLogoDark-32x32.png",
              "/wp-content/uploads/2021/04/cropped-TTLogoDark-192x192.png", "/wp-content/uploads/2021/04/cropped-TTLogoDark-180x180.png",
              "/wp-content/uploads/2026/04/RIG-Services-2026.pdf"):
        register_asset(a, a, HOST + "/")
    # Elementor loads these on demand (handler chunks, lightbox, dialog, share links)
    for pat in ("wp-content/plugins/elementor/assets/js/chunks/*.js", "wp-content/plugins/elementor/assets/css/conditionals/lightbox.min.css",
                "wp-content/plugins/elementor/assets/css/conditionals/dialog.min.css", "wp-content/plugins/elementor/assets/lib/dialog/*.js",
                "wp-content/plugins/elementor/assets/lib/share-link/*.js"):
        for c in sorted(glob.glob(os.path.join(SRC, pat))):
            rp = "/" + os.path.relpath(c, SRC).replace(os.sep, "/")
            register_asset(strip_ver(rp), rp, HOST + "/")
    for path, f in PAGES.items():
        print("page", path)
        process_page(path, f)
    # CSS may reference more assets (fonts, images) -> iterate to a fixed point
    done = set()
    while NEEDED_CSS - done:
        for c in sorted(NEEDED_CSS - done):
            process_css(c)
            done.add(c)
    for rootpath, srcf in ASSET_RENAMES.items():
        if rootpath in done:
            continue
        dest = os.path.join(SITE, rootpath.lstrip("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(srcf, dest)
    # extras
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    open(os.path.join(SITE, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {HOST}/sitemap.xml\n")
    urls = "\n".join(f"  <url><loc>{HOST}{p}</loc></url>" for p in PAGES if p != "/thankyou/")
    open(os.path.join(SITE, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "\n</urlset>\n")
    open(os.path.join(SITE, "404.html"), "w", encoding="utf-8").write(fragment("pages/404.html"))
    n = chrome.apply_all(SITE)
    print("chrome applied to", n, "pages;", len(ASSET_RENAMES), "assets copied")


if __name__ == "__main__":
    main()
