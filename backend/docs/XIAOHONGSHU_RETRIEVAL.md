# Xiaohongshu Retrieval Notes

This document is retained for backend-specific notes. The canonical setup guide is now:

- [../../docs/PlatformSetup.md](../../docs/PlatformSetup.md)

Current Xiaohongshu retrieval architecture:

```text
Frontend
  -> Backend creates retrieval task
  -> Local retriever_agent.py polls task
  -> XiaohongshuRetriever opens local Chrome profile
  -> Retrieved posts are normalized
  -> Backend stores platform_questions
  -> Frontend displays Trending Posts
```

The retrieval browser profile is:

```text
sessions/xiaohongshu/web/profile/
```

Initialize it with:

```bash
cd backend
source venv/bin/activate
python save_platform_state.py xiaohongshu --purpose web
```

Run the retriever with:

```bash
BACKEND_URL=http://localhost:8000 python -u retriever_agent.py
```

or, for Render:

```bash
BACKEND_URL=https://geo-engine.onrender.com python -u retriever_agent.py
```

Do not use the Creator profile for retrieval. Creator publishing uses:

```text
sessions/xiaohongshu/creator/profile/
```

Initialize Creator publishing separately:

```bash
python save_platform_state.py xiaohongshu --purpose creator
```
