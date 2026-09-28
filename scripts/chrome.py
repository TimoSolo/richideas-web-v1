"""Shared site chrome (header, footer, head extras) stamped into every page.

Run `python3 scripts/chrome.py` after editing NAV, header_html or footer_html
to re-apply the chrome to every HTML file under site/. Each page carries
marker comments (<!-- ri:header --> ... <!-- /ri:header -->) so the chrome
can be replaced without touching page content.
"""
import os, re, sys, html

SITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")

SITE = {
    "name": "Rich Ideas",
    "legal": "Rich Ideas Group (Pty) Ltd",
    "fsp": "50569",
    "phone": "011 568 1338",
    "email": "hello@richideas.co.za",
    "substack": "https://terencetobincfp.substack.com",
    "twitter": "https://twitter.com/richideasza",
    "facebook": "https://www.facebook.com/richideasza",
    "linkedin": "https://www.linkedin.com/in/terencetobin/",
}

# (label, root-relative path)
NAV = [
    ("Home", "/"),
    ("About Us", "/about-us/"),
    ("Fees", "/fee-structure/"),
    ("Book a Meeting", "/book-a-meeting/"),
    ("Free Will", "/free-will/"),
    ("Blogs", "/blogs/"),
]
NAV_BUTTON = ("Contact us", "/contact-us/")

FOOTER_LINKS = [
    ("Home", "/"),
    ("About Us", "/about-us/"),
    ("Fee Structure", "/fee-structure/"),
    ("Book A Meeting", "/book-a-meeting/"),
    ("Free Will", "/free-will/"),
    ("Blogs", "/blogs/"),
    ("Contact Us", "/contact-us/"),
]


def rel(root, path):
    """Root-relative path -> href relative to the current page (root is '' , '../', ...)."""
    if path == "/":
        return root if root else "./"
    return root + path.lstrip("/")


def head_html(root):
    return f'''<!-- ri:head -->
<link rel="stylesheet" href="{root}assets/css/site.css">
<script src="{root}assets/js/config.js"></script>
<!-- /ri:head -->'''


def header_html(root, current):
    items = []
    for label, path in NAV:
        cur = " current-menu-item current_page_item" if path == current else ""
        items.append(
            f'<li class="menu-item menu-item-type-post_type menu-item-object-page parent_menu_bizberg{cur}">'
            f'<a href="{rel(root, path)}"><span class="eb_menu_title">{label}</span></a></li>'
        )
    nav = "\n".join(items)
    blabel, bpath = NAV_BUTTON
    s = SITE
    return f'''<!-- ri:header -->
<header id="masthead" class="primary_header_left">
	<a class="skip-link screen-reader-text" href="#content">Skip to content</a>
	<div id="top-bar" class="">
		<div class="container">
			<div class="row">
				<div class="top_bar_wrapper">
					<div class="col-sm-4 col-xs-12">
		<div id="top-social-left" class="header_social_links">
			<ul>
				<li tabindex="0"><a tabindex="-1" href="{s["linkedin"]}" class="social_links_header_0" target="_blank" rel="noopener" aria-label="LinkedIn"><span class="ts-icon"><i class="fab fa-linkedin-in"></i></span><span class="ts-text">LinkedIn</span></a></li>
				<li tabindex="0"><a tabindex="-1" href="{s["facebook"]}" class="social_links_header_1" target="_blank" rel="noopener" aria-label="Facebook"><span class="ts-icon"><i class="fab fa-facebook-f"></i></span><span class="ts-text">Facebook</span></a></li>
				<li tabindex="0"><a tabindex="-1" href="{s["twitter"]}" class="social_links_header_2" target="_blank" rel="noopener" aria-label="Twitter"><span class="ts-icon"><i class="fab fa-twitter"></i></span><span class="ts-text">Twitter</span></a></li>
			</ul>
		</div>
					</div>
					<div class="col-sm-8 col-xs-12">
						<div class="top-bar-right">
		                   	<ul class="infobox_header_wrapper">
				<li><i class="fas fa-mobile-alt"></i> <a href="tel:+27115681338">{s["phone"]}</a></li>
				<li><i class="far fa-comment-alt"></i> <a href="mailto:{s["email"]}">{s["email"]}</a></li>
				<li><i class=""></i> Rich Ideas Group is an authorised financial services provider #{s["fsp"]}</li>
		                   	</ul>
	                    </div>
					</div>
				</div>
			</div>
		</div>
	</div>
    <nav class="navbar navbar-default with-slicknav">
        <div id="navbar" class="collapse navbar-collapse navbar-arrow">
            <div class="container">
            	<div class="row">
	            	<div class="bizberg_header_wrapper">
	<a class="logo pull-left " href="{rel(root, "/")}" target="_self">
        	<img src="{root}wp-content/uploads/2021/04/TTLogoDark.png" alt="Rich Ideas" class="site_logo">
    </a>
	<ul id="responsive-menu" class="nav navbar-nav pull-right">
{nav}
		    <li class="menu-item header_search_wrapper header_btn_wrapper">
	<a href="{rel(root, bpath)}" class="btn btn-primary menu_custom_btn">{blabel}</a>
    		    </li>
	    	</ul>
		                <div class="mobile_menu_wrapper">
		            	<div id="slicknav-mobile" class=""></div>
		            	</div>
		            </div>
		        </div>
            </div>
        </div><!--/.nav-collapse -->
    </nav>
</header><!-- header section end -->
<!-- /ri:header -->'''


def footer_html(root):
    s = SITE
    links = "\n".join(
        f'<li class="menu-item menu-item-type-post_type menu-item-object-page"><a href="{rel(root, p)}">{l}</a></li>'
        for l, p in FOOTER_LINKS
    )
    return f'''<!-- ri:footer -->
	<section class="ri-newsletter" id="newsletter">
		<div class="container">
			<div class="ri-newsletter__inner">
				<div class="ri-newsletter__text">
					<h2>Wealth Without Worry</h2>
					<p>Terence&rsquo;s newsletter on money, families and the decisions in between. A few times a month, free, and easy to leave.</p>
				</div>
				<form class="ri-newsletter__form" action="{s["substack"]}/subscribe" method="get" target="_blank" data-ri-newsletter>
					<label for="ri-nl-email" class="screen-reader-text">Email address</label>
					<input id="ri-nl-email" type="email" name="email" placeholder="Your email address" required autocomplete="email">
					<button type="submit" class="btn btn-primary">Subscribe</button>
				</form>
			</div>
		</div>
	</section>
	<footer id="footer" class="footer-style">
	    <div class="container">
	    	<div class="footer_social_links">
			        <ul class="social-net">
			        	<li><a target="_blank" rel="noopener" href="{s["linkedin"]}" aria-label="LinkedIn"><i class="fab fa-linkedin-in"></i></a></li>
			        	<li><a target="_blank" rel="noopener" href="{s["facebook"]}" aria-label="Facebook"><i class="fab fa-facebook-f"></i></a></li>
			        	<li><a target="_blank" rel="noopener" href="{s["twitter"]}" aria-label="Twitter"><i class="fab fa-twitter"></i></a></li>
			        	<li><a target="_blank" rel="noopener" href="{s["substack"]}" aria-label="Substack newsletter"><i class="fas fa-envelope-open-text"></i></a></li>
			        </ul>
		        </div>
	        <ul id="menu-footer-menu" class="inline-menu">
{links}
	        </ul>
	        <p class="copyright">
	            Copyright &copy;<span data-ri-year>2026</span> {s["legal"]} &#8211; FSP #{s["fsp"]}. All rights reserved.
	            <span class="bizberg_copyright_inner">6A Bioksiet Street, Jukskei Park, Randburg &middot; <a href="tel:+27115681338">{s["phone"]}</a> &middot; <a href="mailto:{s["email"]}">{s["email"]}</a> &middot; <a href="https://www.fsca.co.za/" target="_blank" rel="noopener">FSCA</a></span>
	        </p>
	    </div>
	</footer>
<!-- start Back To Top -->
<div id="back-to-top">
    <a href="javascript:void(0)"><i class="fa fa-angle-up"></i></a>
</div>
<!-- end Back To Top -->
<script src="{root}assets/js/site.js" defer></script>
<!-- /ri:footer -->'''


MARK = {
    "head": (re.compile(r"<!-- ri:head -->.*?<!-- /ri:head -->", re.S), head_html),
    "header": (re.compile(r"<!-- ri:header -->.*?<!-- /ri:header -->", re.S), header_html),
    "footer": (re.compile(r"<!-- ri:footer -->.*?<!-- /ri:footer -->", re.S), footer_html),
}


def page_meta(path):
    """Return (root_prefix, current_nav_path) for a file under site/."""
    relp = os.path.relpath(path, SITE_DIR).replace(os.sep, "/")
    depth = relp.count("/")
    root = "../" * depth
    cur = "/" + relp[: -len("index.html")] if relp.endswith("index.html") else "/" + relp
    if cur == "/index.html":
        cur = "/"
    return root, cur


def apply_to(path):
    root, cur = page_meta(path)
    h = open(path, encoding="utf-8").read()
    new = h
    for key, (rx, fn) in MARK.items():
        repl = fn(root, cur) if key == "header" else fn(root)
        new = rx.sub(lambda m: repl, new, count=1)
    if new != h:
        open(path, "w", encoding="utf-8").write(new)
        return True
    return False


def apply_all(site_dir=SITE_DIR):
    n = 0
    for base, _, files in os.walk(site_dir):
        for f in files:
            if f.endswith(".html"):
                n += apply_to(os.path.join(base, f))
    return n


if __name__ == "__main__":
    print("updated", apply_all(), "pages")
