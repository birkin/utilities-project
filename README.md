# birkin-utilities-project


## Purpose

To assemble a collection of little utilities to be able to run via [uv](https://docs.astral.sh/uv/).


## Usage


Example for calculating a collection size:
```bash
$ uv run ./calc_collection_size.py --collection-pid bdr:XXXXXXX
```

## Developer/IDE-agent Notes

- Do not use `python3 ...` directly. Always run commands using `uv run` with the local script path. For example:
    ```bash
    $ uv run ./prefix_with_date_time --source "foo bar"
    ```

- Similarly, run tests like:
    ```bash
    $ uv run -m unittest discover -v
    ```
