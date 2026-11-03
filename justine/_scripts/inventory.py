"""Build an image manifest from the WordPress.com API dumps.
Usage: python3 -I inventory.py <mirror_dir>
Writes <mirror_dir>/manifest.json
"""
import json, re, sys, os, collections
from urllib.parse import urlsplit, unquote
from html import unescape
M = sys.argv[1]
posts = json.load(open(f'{M}/posts.json'))['posts']
pages = json.load(open(f'{M}/pages.json'))['posts']
items = posts + pages
# extra rendered HTML (archived theme chrome / home page) to scan for images
import glob
for f in glob.glob(f'{M}/wayback/*-*.html'):
    items.append({'content': open(f).read(), 'featured_image': None})

VAR = re.compile(r'^(.*?)(-\d+x\d+)?(-scaled)?(\.(jpe?g|png|gif|webp))$', re.I)

def canon(url):
    """Return (origin_path, is_variant, base_origin_path) or None for non-upload images.
    origin_path like 'justine-huang.com/wp-content/uploads/2017/09/img_7166.jpeg'
    """
    url = unescape(url)
    u = urlsplit(url)
    host, path = u.netloc.lower(), unquote(u.path)
    if host in ('i0.wp.com', 'i1.wp.com', 'i2.wp.com', 'i3.wp.com'):
        path = path.lstrip('/')               # 'justine-huang.com/wp-content/...'
        host, _, path = path.partition('/')
        path = '/' + path
    if host == 'justine-huang.com' and path.startswith('/wp-content/uploads/'):
        pass
    elif host == 'strawberry19blog.files.wordpress.com':
        pass
    elif host == 'strawberry19blog.wordpress.com' and path.startswith('/wp-content/uploads/'):
        host, path = 'strawberry19blog.files.wordpress.com', path.replace('/wp-content/uploads', '', 1)
    else:
        return None
    m = VAR.match(path)
    if not m:
        return None
    base = m.group(1) + m.group(4)
    is_variant = bool(m.group(2) or m.group(3))
    return host + path, is_variant, host + base

refs = collections.defaultdict(set)   # base_origin -> set of referenced origin paths
external = collections.Counter()
featured_bases = set()
for it in items:
    c = it['content']
    urls = re.findall(r'<img[^>]+\ssrc="([^"]+)"', c)
    urls += re.findall(r'\ssrcset="([^"]+)"', c)
    flat = []
    for u in urls:
        for part in unescape(u).split(','):
            flat.append(part.strip().split(' ')[0])
    flat += re.findall(r'url\((?:&quot;|["\'])?(https?://[^)"\'&]+)', c)
    for u in re.findall(r'<a [^>]*href="([^"]+)"', c):
        if re.search(r'\.(jpe?g|png|gif|webp)(\?|$)', u, re.I):
            flat.append(u)
    if it.get('featured_image'):
        flat.append(it['featured_image'])
        cf = canon(it['featured_image'])
        if cf: featured_bases.add(cf[2])
    for u in flat:
        if not u or u.startswith('data:'): continue
        r = canon(u)
        if r is None:
            external[urlsplit(unescape(u)).netloc] += 1
        else:
            refs[r[2]].add(r[0])

site = json.load(open(f'{M}/site.json'))
logo = canon(site['logo']['url'])
if logo: refs[logo[2]].add(logo[0])          # site logo (used in header + favicon)
manifest = []
for base, variants in sorted(refs.items()):
    host, _, path = base.partition('/')
    # local path: img/<Y/M/name>.webp ; old blog under img/old/
    rel = ('/' + path).replace('/wp-content/uploads/', '/') if host == 'justine-huang.com' else '/old/' + path
    stem, ext = os.path.splitext(rel)
    ext_l = ext.lower()
    local = 'img' + stem + ('.gif' if ext_l == '.gif' else '.webp')
    manifest.append({
        'base': base,
        'variants': sorted(variants),
        'download': f'https://i0.wp.com/{base}',
        'local': local,
        'thumb': 'img' + stem + '-480.webp' if base in featured_bases else None,
        'featured': base in featured_bases,
    })
json.dump(manifest, open(f'{M}/manifest.json', 'w'), indent=1)
all_refs = sum(len(v) for v in refs.values())
variant_refs = sum(1 for v in refs.values() for p in v if VAR.match(p) and (VAR.match(p).group(2) or VAR.match(p).group(3)))
print(f'unique referenced upload URLs (query stripped): {all_refs}')
print(f'  of which WP size variants (-WxH / -scaled): {variant_refs}')
print(f'unique base images to download: {len(manifest)}')
print(f'  from justine-huang.com: {sum(1 for m in manifest if m["base"].startswith("justine"))}, from old wordpress.com blog: {sum(1 for m in manifest if m["base"].startswith("strawberry"))}')
print(f'  featured (get 480px thumbs): {sum(1 for m in manifest if m["featured"])}')
print(f'  gif: {sum(1 for m in manifest if m["local"].endswith(".gif"))}, png: {sum(1 for m in manifest if m["base"].lower().endswith(".png"))}')
print('non-upload image hosts (left as-is):', dict(external))
