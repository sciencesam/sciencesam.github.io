"""Bundle the theme's CSS (as loaded by the archived home page, in document order) into one local file.
Usage: python3 -I theme.py <mirror_dir>   -> writes <mirror_dir>/wayback/theme.css
"""
import re, sys, os
M = sys.argv[1]; W = f'{M}/wayback'
SKIP = ('wp-emoji-styles', 'jetpack-block-subscriptions', 'jetpack_likes', 'akismet-widget-style', 'wp-block-comments')
def blocks(f):
    h = open(f).read()
    for m in re.finditer(r"<link[^>]*rel='stylesheet'[^>]*href='([^']+)'|<style[^>]*id='([^']+)'[^>]*>(.*?)</style>", h, re.S):
        yield (m.group(1), m.group(2), m.group(3))
out = []; seen = set(); lib_done = False
def local_css(href):
    path = re.sub(r'\?.*', '', href).replace('https://justine-huang.com/', '')
    f = f'{W}/css/' + path.replace('/', '_')
    return open(f).read() if os.path.exists(f) else None
for href, sid, css in blocks(f'{W}/home2026-head.html'):
    if href:
        if 'dashicons' in href: continue
        c = local_css(href)
        if c: out.append(f'/* {href} */\n' + c); seen.add(href)
        continue
    sid = sid.replace('-inline-css', '')
    if sid.startswith(SKIP): continue
    if re.match(r'wp-block-[a-z-]+$', sid) and sid != 'wp-block-library' and not sid.endswith('-theme'):
        if not lib_done:   # the per-block inline chunks are subsets of the full block library stylesheet
            out.append('/* wp-includes/css/dist/block-library/style.min.css */\n' + open(f'{W}/css/wp-includes_css_dist_block-library_style.min.css').read()); lib_done = True
        continue
    out.append(f'/* {sid} */\n' + css); seen.add(sid)
# page-specific layout rules + theme chunks that only the About page loaded
for href, sid, css in blocks(f'{W}/about-head.html'):
    if href: continue
    sid = sid.replace('-inline-css', '')
    if sid in ('core-block-supports',) or (sid.endswith('-theme') and sid not in seen):
        out.append(f'/* about: {sid} */\n' + css)
out.append('/* jetpack tiled gallery */\n' + open(f'{W}/css/wp-content_plugins_jetpack__inc_blocks_tiled-gallery_view.css').read())
out.append('/* static-site extras */\n' + open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extras.css')).read())
css = '\n'.join(out)
css = css.replace('https://justine-huang.com/wp-content/themes/basal-fse/assets/fonts/', 'fonts/')
left = sorted(set(re.findall(r'https?://[^)"\' ]*justine-huang\.com[^)"\' ]*', css)))
open(f'{W}/theme.css', 'w').write(css)
print(f'theme.css {len(css)//1024} KB; remaining justine-huang.com refs in css: {left[:5] or "none"}')
