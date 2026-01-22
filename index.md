
Collection of small utilities, easily run from anywhere via the wonderful package, `uv` ([link](https://docs.astral.sh/uv/)).

_(In usage examples below, where a line ends in a backslash, that backslash is used to break the line into multiple lines for readability. The backslash is not part of the command. It can be removed and the command can be run as a single line.)_

---


## random_id_maker

Generates a random ID without confusing characters (e.g., the letter `O` and the number `0`).

Example:
```
uv run https://birkin.github.io/utilities-project/random_id_maker.py
N8Wfw3KR96

uv run https://birkin.github.io/utilities-project/random_id_maker.py --length 20
DwWXeM5nnbayAwePTetv
```

[Code](https://github.com/birkin/utilities-project/blob/main/random_id_maker.py)

---


## load_gsheet_data

Loads public google sheet as polars dataframe using httpx.

Example:
```
uv run https://birkin.github.io/utilities-project/load_gsheet_data.py \
--sheet_id 1qXEqjk56TDF6Zupwqsb-bFrS8G4kS8GXSVzo3-PiZlQ \
--gid 0 

Installed 9 packages in 10ms
shape: (2, 6)
┌─────┬──────────┬─────────────────┬───────────────────────┬─────────────┬────────────┐
│ id  ┆ title    ┆ filename        ┆ keywords              ┆ some-number ┆ some-date  │
│ --- ┆ ---      ┆ ---             ┆ ---                   ┆ ---         ┆ ---        │
│ str ┆ str      ┆ str             ┆ str                   ┆ i64         ┆ str        │
╞═════╪══════════╪═════════════════╪═══════════════════════╪═════════════╪════════════╡
│ aa  ┆ aa-title ┆ aa-filename.pdf ┆ incredible, awesome   ┆ 0           ┆ 2025-07-03 │
│ bb  ┆ bb-title ┆ bb-filename.pdf ┆ astounding, marvelous ┆ 1           ┆ 1960-02-02 │
└─────┴──────────┴─────────────────┴───────────────────────┴─────────────┴────────────┘
```

That's from a [public example gsheet](https://docs.google.com/spreadsheets/d/1qXEqjk56TDF6Zupwqsb-bFrS8G4kS8GXSVzo3-PiZlQ/edit?gid=0#gid=0) with dummy data.

[Code](https://github.com/birkin/utilities-project/blob/main/load_gsheet_data.py)

---


## html_to_markdown

Converts HTML input (URL or local file) to Markdown using Pandoc via pypandoc. Pandoc does not need to be pre-installed.

Example:
```
uv run https://birkin.github.io/utilities-project/html_to_markdown.py \
--in_url 'https://lib.brown.edu' \
--out_markdown '~/brown_lib_home_page.md'
```

...or...

```
uv run https://birkin.github.io/utilities-project/html_to_markdown.py \
--in_html '~/brown_lib_home_page.html' \
--out_markdown '~/brown_lib_home_page.md'
```

[Code](https://github.com/birkin/utilities-project/blob/main/html_to_markdown.py)

---

