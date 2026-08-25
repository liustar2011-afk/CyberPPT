# Agent usage examples

User: `把 page-08.png 画质提升一下，不要改内容。`

Agent behavior:

```bash
python tools/doctor.py
python enhance.py "page-08.png"
```

If no AI backend is ready and the page would benefit from one:

```bash
python tools/bootstrap.py --backend auto
python enhance.py "page-08.png"
```

The agent returns `page-08_enhanced.png`; the user does not need to know which SR model was selected.
