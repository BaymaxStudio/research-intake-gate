# Contributing

Issues and focused pull requests are welcome.

## Development checks

Use Python 3.10 or newer. The core CLI uses only the standard library.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_structure.py
python3 scripts/check_private_data.py
```

To rebuild the showcase, install the optional demo dependency and run:

```bash
python3 -m pip install -r requirements-demo.txt
python3 scripts/make_demo.py
```

Keep changes narrow. New validation rules should include a failing fixture and a passing counterpart. Do not add network access, automatic review decisions, destructive cleanup, or forced overwrite behavior without a separate design discussion.
