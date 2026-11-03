# How this folder was built

Static copy of justine-huang.com (WordPress + Jetpack), generated from the public
WordPress.com REST API rather than a wget mirror (the site's Cloudflare settings
block non-browser fetches of HTML pages, but not of images or the API).

Pipeline (run from this directory; needs Node + `npm install`, Python 3, and curl):

```sh
MIRROR=/path/to/scratch/mirror   # raw API dumps + downloaded images, never committed
OUT=..                           # this folder

# 1. API dumps (posts.json, pages.json, categories.json, tags.json, tags2.json, site.json)
API=https://public-api.wordpress.com/rest/v1.1/sites/justine-huang.com
F=ID,URL,slug,title,date,modified,excerpt,content,categories,tags,featured_image,post_thumbnail,format,status,type,parent
curl -s "$API/posts/?number=100&fields=$F&status=publish"           -o $MIRROR/posts.json
curl -s "$API/posts/?number=100&type=page&fields=$F&status=publish" -o $MIRROR/pages.json
curl -s "$API/categories/?number=100"                               -o $MIRROR/categories.json
curl -s "$API/tags/?number=100"                                     -o $MIRROR/tags.json
curl -s "$API/tags/?number=100&offset=100"                          -o $MIRROR/tags2.json
curl -s "$API/?fields=ID,name,description,URL,icon,logo"            -o $MIRROR/site.json

# 1b. Theme chrome: an archived render of the live site (the Wayback Machine has snapshots; HTML on the
#     live host is behind a Cloudflare challenge, but its CSS/fonts/images are not). Save the raw archived
#     home page and About page to $MIRROR/wayback/{home2026,about}.html (gunzip if needed), then split each
#     into -head/-header/-main/-after/-footer.html pieces (see git history of build.py for the regexes), and
#     fetch into $MIRROR/wayback/css/ and $MIRROR/wayback/fonts/ the stylesheets and woff2 files the head links.
python3 -I theme.py $MIRROR          # 1c. bundle the theme CSS in load order -> wayback/theme.css (+ extras.css)

python3 -I inventory.py $MIRROR      # 2. one entry per unique base image -> manifest.json (also scans wayback/*.html)
./download.sh $MIRROR                # 3. fetch each once via the Jetpack CDN, pre-sized to 1600px
node images.js $MIRROR $OUT          # 4. WebP q78, 1600px long edge (+480px thumbs for featured images)
python3 -I build.py $MIRROR $OUT     # 5. generate HTML (all links relative)
(cd $OUT && npx -y pagefind --site .)  # 6. static search index
```

Jekyll ignores this `_scripts` directory, so it is not published.
