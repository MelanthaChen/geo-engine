# Xiaohongshu Retrieval Backend

GEO Engine uses MediaCrawler as the default Xiaohongshu retrieval backend when
`external/MediaCrawler` is present.

By default, the backend runs:

```bash
uv run main.py \
  --platform xhs \
  --lt qrcode \
  --type search \
  --keywords "<query>" \
  --get_comment true \
  --get_sub_comment false \
  --headless false \
  --save_data_option jsonl \
  --save_data_path "<temporary directory>" \
  --crawler_max_notes_count "<limit>"
```

Then GEO reads MediaCrawler's real note and comment JSONL output from:

```text
<temporary directory>/xhs/jsonl/search_contents_*.jsonl
<temporary directory>/xhs/jsonl/search_comments_*.jsonl
```

If you need a different retrieval backend, set a command adapter:

```bash
XIAOHONGSHU_RETRIEVAL_COMMAND="python /path/to/xhs_geo_wrapper.py --query {query} --output {output} --session {session_path} --limit {limit}"
```

The command should write JSON or JSONL to `{output}` or stdout. It can also
write MediaCrawler-style files to `{save_data_path}`.

## Expected Output

The adapter accepts either a JSON array, JSONL, or an object with one of:

```json
{
  "notes": []
}
```

Supported note fields:

```json
{
  "title": "note title",
  "body": "note body",
  "url": "https://www.xiaohongshu.com/...",
  "author": "nickname",
  "hashtags": ["#tag"],
  "liked_count": 12,
  "collected_count": 4,
  "comment_count": 3,
  "share_count": 1,
  "created_at": "2026-07-02T12:00:00Z"
}
```

Alternative field names from external engines are normalized in
`app/services/faq_discovery/platform_faq_service.py`.

## Session Reuse

Custom commands receive `{session_path}` from GEO. Preferred path:

```text
sessions/xiaohongshu/storage_state.json
```

GEO resolves Xiaohongshu sessions through the shared `SessionResolver` used by
the publisher. Account-specific `session_path` values are checked first, then
the shared platform defaults. When the resolved Playwright storage state exists,
GEO converts its Xiaohongshu/Rednote cookies into MediaCrawler's
`--lt cookie --cookies ...` login mode. This reuses the same session file
created by:

```bash
python save_platform_state.py xiaohongshu
```

If no GEO storage state exists, MediaCrawler falls back to its own QR/CDP login
state under its working directory. GEO does not create a second account system.

## Fallback Order

When Xiaohongshu retrieval runs:

1. Retry real retrieval.
2. Return cached `platform_questions` rows for Xiaohongshu if available.
3. Raise a retrieval error.

GEO does not generate synthetic Xiaohongshu notes or synthetic platform
questions. Everything before FAQ generation must come from real retrieved
Xiaohongshu content or previously cached real rows.
