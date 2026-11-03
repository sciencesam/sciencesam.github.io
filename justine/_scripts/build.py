"""Generate a static copy of the blog: content from the WordPress.com API, wrapped in the
real theme chrome (header / banner / footer / CSS) taken from an archived render of the site.
Usage: python3 -I build.py <mirror_dir> <out_dir>
All internal links use a __ROOT__ placeholder that becomes a relative prefix per page.
"""
import json, re, os, sys, shutil, math, collections
from html import unescape, escape
from urllib.parse import urlsplit, unquote
from datetime import datetime

M, OUT = sys.argv[1], sys.argv[2]
W = f'{M}/wayback'
HERE = os.path.dirname(os.path.abspath(__file__))
SITE_NAME = 'Blog | Justine Huang'
PER_PAGE = 12

posts = json.load(open(f'{M}/posts.json'))['posts']
pages = {p['slug']: p for p in json.load(open(f'{M}/pages.json'))['posts']}
cats = {c['slug']: c for c in json.load(open(f'{M}/categories.json'))['categories']}
tags = {t['slug']: t for t in json.load(open(f'{M}/tags.json'))['tags'] + json.load(open(f'{M}/tags2.json'))['tags']}
manifest = json.load(open(f'{M}/manifest.json'))
posts.sort(key=lambda p: p['date'], reverse=True)
post_by_slug = {p['slug']: p for p in posts}
cslugs = lambda p: {c['slug'] for c in p['categories'].values()}
tslugs = lambda p: {t['slug'] for t in p['tags'].values()}

# ---------- image mapping ----------
VAR = re.compile(r'^(.*?)(-\d+x\d+)?(-scaled)?(\.(jpe?g|png|gif|webp))$', re.I)
def canon(url):
    u = urlsplit(unescape(url)); host, path = u.netloc.lower(), unquote(u.path)
    if host in ('i0.wp.com', 'i1.wp.com', 'i2.wp.com', 'i3.wp.com'):
        host, _, path = path.lstrip('/').partition('/'); path = '/' + path
    if host == 'strawberry19blog.wordpress.com' and path.startswith('/wp-content/uploads/'):
        host, path = 'strawberry19blog.files.wordpress.com', path.replace('/wp-content/uploads', '', 1)
    if not ((host == 'justine-huang.com' and path.startswith('/wp-content/uploads/')) or host == 'strawberry19blog.files.wordpress.com'):
        return None
    m = VAR.match(path)
    return host + m.group(1) + m.group(4) if m else None
local_of = {m['base']: m for m in manifest}
unmapped = collections.Counter()
def img_local(url, thumb=False):
    b = canon(url)
    if b and b in local_of:
        m = local_of[b]
        return '__ROOT__' + ((m['thumb'] or m['local']) if thumb else m['local'])
    u = urlsplit(unescape(url))
    if u.netloc in ('i0.wp.com', 'i1.wp.com', 'i2.wp.com') and not u.path.startswith(('/justine-huang.com', '/strawberry19blog')):
        return 'https://' + u.path.lstrip('/')          # third-party image proxied by Jetpack: use the origin directly
    unmapped[re.sub(r'\?.*', '', unescape(url))] += 1
    return None

# ---------- link mapping ----------
ext_links = collections.Counter()
def map_link(href):
    h = unescape(href); u = urlsplit(h)
    if u.netloc in ('justine-huang.com', 'www.justine-huang.com', 'strawberry19blog.wordpress.com'):
        if u.path.lower().endswith('.pdf'):
            return '__ROOT__files/' + os.path.basename(u.path)
        if re.search(r'\.(jpe?g|png|gif|webp)$', u.path, re.I) or '/wp-content/uploads/' in u.path:
            return img_local(h) or h
        path = u.path
        if re.match(r'^/\d{4}/\d{2}/\d{2}/[^/]+/[^/]+/$', path) or (re.match(r'^/\d{4}/\d{2}/\d{2}/[^/]+/$', path) and h.endswith('#')):
            return '__ATTACH__'                              # old gallery link to an attachment page: point at the image itself
        m = re.match(r'^/\d{4}/\d{2}/\d{2}/([^/]+)/?$', path)   # old wordpress.com permalinks
        if m: path = '/' + m.group(1) + '/'
        seg = path.strip('/')
        if seg in ('', 'home'): return '__ROOT__'
        if seg in post_by_slug or seg in pages: return '__ROOT__' + seg + '/'
        if seg.startswith(('category/', 'tag/')):
            return '__ROOT__' + seg.split('/')[0] + '/' + seg.split('/')[-1] + '/'   # nested category URLs -> flat
        ext_links[h] += 1
        return h
    if u.netloc.endswith('wp.com') or 'files.wordpress.com' in u.netloc:
        return img_local(h) or h
    return h

STRIP_ATTRS = ('srcset', 'sizes', 'data-recalc-dims', 'decoding', 'fetchpriority', 'loading', 'data-id', 'data-link', 'data-url', 'data-amp-layout',
               'data-image-title', 'data-image-description', 'data-image-caption', 'data-orig-file', 'data-orig-size', 'data-medium-file',
               'data-large-file', 'data-comments-opened', 'data-image-meta', 'data-permalink')
def remove_block(html, start):
    """Remove every <div ...> matched by `start` together with its balanced contents."""
    while True:
        m = re.search(start, html)
        if not m: return html
        i, depth = m.start(), 0
        for t in re.finditer(r'<div\b|</div>', html[i:]):
            depth += 1 if t.group(0) == '<div' else -1
            if depth == 0:
                html = html[:i] + html[i + t.end():]; break
        else:
            return html

def rewrite(html, thumb=False):
    """Localise images, background images and links; drop scripts, forms, embeds and Jetpack leftovers."""
    def fix_img(m):
        tag = m.group(0)
        src = re.search(r'\ssrc="([^"]+)"', tag)
        if not src: return tag
        local = img_local(src.group(1), thumb)
        for attr in STRIP_ATTRS:
            tag = re.sub(r'\s' + attr + r'="[^"]*"', '', tag)
        if local: tag = tag.replace(src.group(0), f' src="{local}"', 1)
        return tag.replace('<img ', '<img loading="lazy" ', 1)
    html = re.sub(r'<img[^>]*>', fix_img, html)
    html = re.sub(r'(<a\s[^>]*href=")([^"]+)(")', lambda m: m.group(1) + escape(map_link(m.group(2)), quote=True) + m.group(3), html)
    html = re.sub(r'background-image:url\(([^)]+)\)', lambda m: 'background-image:url(' + (img_local(m.group(1)) or m.group(1)) + ')', html)
    html = re.sub(r'(<a\s[^>]*href=")__ATTACH__("[^>]*>\s*<img[^>]*\ssrc=")([^"]+)"', lambda m: m.group(1) + m.group(3) + m.group(2) + m.group(3) + '"', html)
    html = re.sub(r'<a\s[^>]*href="__ATTACH__"[^>]*>(.*?)</a>', r'\1', html, flags=re.S)
    html = remove_block(html, r'<div class=[\'"]sharedaddy')                                             # Jetpack likes widget
    html = remove_block(html, r'<div class="wp-block-group[^>]*>(?=\s*<hr[^>]*>\s*<h3[^>]*>Discover more)')   # Jetpack subscribe nag
    html = re.sub(r'<(script|form|iframe|object|noscript)\b.*?</\1>', '', html, flags=re.S)
    return html

# ---------- theme chrome from the archived render ----------
header = rewrite(open(f'{W}/home2026-header.html').read())
footer = rewrite(open(f'{W}/home2026-footer.html').read())
home_main = rewrite(open(f'{W}/home2026-main.html').read())   # runs from <main> to the footer
about_main = rewrite(open(f'{W}/about-main.html').read())
BANNER_BG = img_local('https://justine-huang.com/wp-content/uploads/2024/05/IMG_4351-scaled.jpeg')

def nice_date(s): return datetime.fromisoformat(s).strftime('%B %-d, %Y')
def text(h): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', unescape(h))).strip()
def esc(s): return escape(unescape(s))

# footer: swap the Jetpack subscribe form (needs WordPress) for search + browse dropdowns
cat_opts = ''.join(f'<option value="__ROOT__category/{s}/">{esc(c["name"])} ({c["post_count"]})</option>' for s, c in sorted(cats.items(), key=lambda kv: kv[1]['name']) if c['post_count'])
months = sorted({p['date'][:7] for p in posts}, reverse=True)
mon_opts = ''.join(f'<option value="__ROOT__{m[:4]}/{m[5:7]}/">{datetime.strptime(m, "%Y-%m").strftime("%B %Y")}</option>' for m in months)
tools = f'<div class="footer-tools"><div id="search"></div><select onchange="if(this.value)location.href=this.value"><option value="">Browse by category</option>{cat_opts}</select><select onchange="if(this.value)location.href=this.value"><option value="">Browse by month</option>{mon_opts}</select></div>'
n1 = footer.count('Subscribe to My Blog')
footer = footer.replace('Subscribe to My Blog', 'Find a Post')
footer, n2 = re.subn(r'(<p[^>]*>)Subscribe to receive the latest posts in your inbox!(</p>)', r'\1Search the blog, or browse by category or month.\2' + tools, footer)
if not (n1 and n2): print('WARNING: footer subscribe block not found as expected', n1, n2)
footer = re.sub(r'<div class="wp-block-jetpack-subscriptions.*?</div>\s*</div>', '', footer, flags=re.S)

def layout(title, main, depth, desc='', body_class='page-template-default page'):
    root = '../' * depth
    page = f'''<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}{'' if title == SITE_NAME else ' - ' + SITE_NAME}</title>
<meta name="description" content="{esc(desc or 'Travel, law, and more.')}">
<link rel="icon" href="__ROOT__img/2024/05/3962e5b3f1c91aacd84f1c35bffa6745.webp">
<link rel="stylesheet" href="__ROOT__assets/theme.css">
<link rel="stylesheet" href="__ROOT__pagefind/pagefind-ui.css">
</head>
<body class="{body_class} wp-custom-logo wp-embed-responsive wp-theme-basal-fse">
<div class="wp-site-blocks">
{header}
{main}
{footer}
</div>
<script src="__ROOT__pagefind/pagefind-ui.js"></script>
<script>
document.addEventListener('click',function(e){{
  var o=e.target.closest('.wp-block-navigation__responsive-container-open'),c=e.target.closest('.wp-block-navigation__responsive-container-close'),t=e.target.closest('.wp-block-navigation-submenu__toggle');
  if(o){{var r=o.closest('nav').querySelector('.wp-block-navigation__responsive-container');r.classList.add('is-menu-open','has-modal-open');document.documentElement.classList.add('has-modal-open');}}
  if(c){{var r=c.closest('.wp-block-navigation__responsive-container');r.classList.remove('is-menu-open','has-modal-open');document.documentElement.classList.remove('has-modal-open');}}
  if(t){{var li=t.closest('li');var open=t.getAttribute('aria-expanded')==='true';t.setAttribute('aria-expanded',open?'false':'true');li.classList.toggle('is-open',!open);}}
}});
window.addEventListener('DOMContentLoaded',function(){{if(window.PagefindUI)new PagefindUI({{element:'#search',showImages:false,showSubResults:false}});}});
</script>
</body>
</html>
'''
    return page.replace('__ROOT__', root)

def shell(title_html, body, bg=None, dim=0):
    span = 'has-luminous-vivid-orange-background-color has-background-dim-0 has-background-dim has-background-gradient has-luminous-vivid-amber-to-luminous-vivid-orange-gradient-background' if not dim else f'has-background-dim-{dim} has-background-dim" style="background-color:#1d1d1d'
    return f'''<main class="wp-block-group is-layout-flow wp-block-group-is-layout-flow">
<div class="basal-fse-inner-banner wp-block-group is-layout-constrained wp-container-core-group-is-layout-88816f74 wp-block-group-is-layout-constrained" style="padding-top:0px;padding-right:0px;padding-bottom:0px;padding-left:0px">
<div class="wp-block-cover is-light has-parallax" style="min-height:400px;aspect-ratio:unset;"><span aria-hidden="true" class="wp-block-cover__background {span}"></span><div class="wp-block-cover__image-background has-parallax" style="background-position:50% 50%;background-image:url({bg or BANNER_BG})"></div><div class="wp-block-cover__inner-container is-layout-flow wp-block-cover-is-layout-flow"><h1 style="padding-top:0px;" class="has-text-align-center basal-fse-inner-banner-title wp-block-post-title has-text-color has-banner-color has-poppins-font-family">{title_html}</h1></div></div>
</div>
<div class="basal-fse-page-outer wp-block-group has-secondary-color has-text-color is-layout-constrained wp-container-core-group-is-layout-1d402a18 wp-block-group-is-layout-constrained" style="padding-top:80px;padding-right:15px;padding-bottom:80px;padding-left:15px"><div class="entry-content wp-block-post-content is-layout-flow wp-container-core-post-content-is-layout-5dafc681 wp-block-post-content-is-layout-flow">
{body}
</div></div>
</main>'''

def write(path, html):
    p = os.path.join(OUT, path, 'index.html') if path else os.path.join(OUT, 'index.html')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w').write(html)

# post card: the theme's own cover-card markup from the archived home page, templated
_after = open(f'{W}/home2026-after.html').read()
_card = re.search(r'<li class="wp-block-post [^"]*">\s*<div class="nfd-p-card-md.*?</li>', _after, re.S).group(0)
_card = rewrite(_card)
def card(p):
    c = _card
    fi = img_local(p['featured_image'], thumb=True) if p.get('featured_image') else BANNER_BG
    c = re.sub(r'(<img[^>]*\ssrc=")[^"]+(")', lambda m: m.group(1) + fi + m.group(2), c, count=1)
    cat = next(iter(p['categories'].values()), None)
    c = re.sub(r'<div class="taxonomy-category[^>]*>.*?</div>', lambda m: f'<div class="taxonomy-category has-link-color wp-block-post-terms"><a href="__ROOT__category/{cat["slug"]}/" rel="tag">{esc(cat["name"])}</a></div>' if cat else '', c, count=1, flags=re.S)
    c = re.sub(r'(<h2[^>]*wp-block-post-title[^>]*>)<a href="[^"]*"[^>]*>.*?</a>(</h2>)', lambda m: f'{m.group(1)}<a href="__ROOT__{p["slug"]}/">{esc(p["title"])}</a>{m.group(2)}', c, count=1, flags=re.S)
    c = re.sub(r'<time[^>]*>.*?</time>', f'<time datetime="{p["date"][:10]}">{nice_date(p["date"])}</time>', c, count=1, flags=re.S)
    c = re.sub(r'class="wp-block-post [^"]*"', 'class="wp-block-post"', c, count=1)
    c = re.sub(r'has-background-dim-\d+ has-background-dim" style="background-color:#[0-9a-f]+"', 'has-background-dim-40 has-background-dim" style="background-color:#222"', c, count=1)
    return c

def listing(title, items, base, depth):
    n = max(1, math.ceil(len(items) / PER_PAGE))
    for i in range(n):
        chunk = items[i * PER_PAGE:(i + 1) * PER_PAGE]
        pag = ''
        if n > 1:
            prev = f'<a href="__ROOT__{base}{"" if i == 1 else f"page/{i}/"}">&larr; Newer posts</a>' if i > 0 else '<span></span>'
            nxt = f'<a href="__ROOT__{base}page/{i + 2}/">Older posts &rarr;</a>' if i < n - 1 else '<span></span>'
            pag = f'<nav class="archive-pagination">{prev}<span>Page {i + 1} of {n}</span>{nxt}</nav>'
        body = f'<ul class="archive-grid wp-block-post-template">{"".join(card(p) for p in chunk)}</ul>{pag}'
        path = base.rstrip('/') if i == 0 else f'{base}page/{i + 1}'
        d = depth if i == 0 else depth + 2
        write(path, layout(title if i == 0 else f'{title} (page {i + 1})', shell(esc(title), body), d, body_class='archive'))

# ---------- build ----------
if os.path.isdir(OUT):
    for name in os.listdir(OUT):
        if name not in ('img', '_scripts'):
            p = os.path.join(OUT, name); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
os.makedirs(os.path.join(OUT, 'assets'), exist_ok=True)
css = open(f'{W}/theme.css').read()
css = re.sub(r'/\*[^*]*justine-huang\.com[^*]*\*/', '', css)
open(os.path.join(OUT, 'assets', 'theme.css'), 'w').write(css)
shutil.copytree(f'{W}/fonts', os.path.join(OUT, 'assets', 'fonts'))
if os.path.isdir(os.path.join(M, 'files')): shutil.copytree(os.path.join(M, 'files'), os.path.join(OUT, 'files'))

# home + about straight from the archived renders
write('', layout(SITE_NAME, home_main, 0, body_class='home blog'))
write('about', layout('About Me', about_main, 1, body_class='page-template-default page'))

# posts
for i, p in enumerate(posts):
    fi = img_local(p['featured_image']) if p.get('featured_image') else None
    catl = ', '.join(f'<a href="__ROOT__category/{c["slug"]}/">{esc(c["name"])}</a>' for c in p['categories'].values())
    tagl = ' '.join(f'<a href="__ROOT__tag/{t["slug"]}/">#{esc(t["name"])}</a>' for t in p['tags'].values())
    newer = posts[i - 1] if i > 0 else None
    older = posts[i + 1] if i < len(posts) - 1 else None
    nav = '<nav class="post-nav">' + (f'<a href="__ROOT__{newer["slug"]}/">&larr; {esc(newer["title"])}</a>' if newer else '<span></span>') + (f'<a href="__ROOT__{older["slug"]}/">{esc(older["title"])} &rarr;</a>' if older else '<span></span>') + '</nav>'
    body = f'''<div class="post-body"><p class="post-meta"><time datetime="{p["date"][:10]}">{nice_date(p["date"])}</time>{' &middot; ' + catl if catl else ''}</p>
<div data-pagefind-body>{rewrite(p["content"])}</div>
<div class="post-tags">{tagl}</div>{nav}</div>'''
    write(p['slug'], layout(p['title'], shell(esc(p['title']), body, fi, dim=50), 1, text(p['excerpt'])[:160], body_class='post-template-default single single-post'))

# other static pages
for slug in ('law-school-toolbox', 'energy-transition-talk'):
    pg = pages[slug]
    write(slug, layout(pg['title'], shell(esc(pg['title']), f'<div data-pagefind-body>{rewrite(pg["content"])}</div>'), 1))
contact = '''<p class="has-text-align-center">Thank you for visiting my site and reaching out! I welcome any suggestions on topics that might be interesting for future posts, and would love to hear from you :)</p>
<!-- TODO: replace with your real address -->
<div class="wp-block-buttons is-content-justification-center is-layout-flex"><div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="mailto:hello@example.com">Email me</a></div></div>'''
write('contact', layout('Contact', shell('Contact', contact), 1))

# listings
listing('Blog', posts, 'blog/', 1)
travel = [p for p in posts if 'travel' in cslugs(p) or any(c['parent'] == cats['travel']['ID'] for c in p['categories'].values())]
listing('Travel', travel, 'travel/', 1)
for s, c in cats.items():
    items = [p for p in posts if s in cslugs(p)]
    if items: listing(c['name'], items, f'category/{s}/', 2)
for s, t in tags.items():
    items = [p for p in posts if s in tslugs(p)]
    if items: listing(f'#{t["name"]}', items, f'tag/{s}/', 2)
for ym in sorted({p['date'][:7] for p in posts}):
    items = [p for p in posts if p['date'][:7] == ym]
    listing(datetime.strptime(ym, '%Y-%m').strftime('%B %Y'), items, f'{ym[:4]}/{ym[5:7]}/', 2)

print(f'wrote {sum(1 for r,_,f in os.walk(OUT) for x in f if x == "index.html")} html pages into {OUT}')
print('images referenced but not in manifest:', dict(unmapped) or 'none')
print('internal links left unmapped:', dict(ext_links) or 'none')
