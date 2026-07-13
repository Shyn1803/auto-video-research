# Embedded font assets

Production builds place licensed Inter and Noto Sans Vietnamese `.woff2` files in this directory and register them through `@remotion/fonts`. The default theme keeps this local asset path/stack explicit so no renderer fetches a web font at runtime.
