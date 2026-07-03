# Xiaohongshu Retrieval Backend

GEO Engine does not import MediaCrawler internals directly.

Instead, Xiaohongshu retrieval is connected through a command adapter:

```bash
XIAOHONGSHU_RETRIEVAL_COMMAND="python /path/to/xhs_geo_wrapper.py --query {query} --output {output} --session {session_path} --limit {limit}"
```

The command should write JSON or JSONL to `{output}` or stdout.

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

## MediaCrawler

MediaCrawler can be used as the external retrieval engine or wrapped by a small
script that:

1. Runs MediaCrawler for `--platform xhs --type search`.
2. Reads its stored Xiaohongshu results.
3. Writes normalized JSON/JSONL to the path passed as `{output}`.

Keep MediaCrawler installed outside this repository so GEO can replace or
upgrade the retrieval backend without changing application code.

## Session Reuse

The command receives `{session_path}` from GEO. Preferred path:

```text
sessions/xiaohongshu/storage_state.json
```

If your external backend uses its own cookie/cache format, the wrapper should
translate or copy GEO's session state into the backend-specific format.

## Fallback Order

When Xiaohongshu retrieval runs:

1. Retry the external command.
2. Return cached `platform_questions` rows for Xiaohongshu if available.
3. Use synthetic Xiaohongshu note-angle fallback only as the final fallback.

Synthetic rows are marked with:

```json
{
  "retrieval_method": "synthetic_fallback",
  "raw_metadata": {
    "fallback": true
  }
}
```
