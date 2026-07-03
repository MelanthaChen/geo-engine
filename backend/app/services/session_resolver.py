from pathlib import Path


class SessionResolver:
    PLATFORM_DEFAULTS = {
        "reddit": [
            "sessions/reddit/storage_state.json",
            "reddit_state.json",
        ],
        "xiaohongshu": [
            "sessions/xiaohongshu/storage_state.json",
            "xiaohongshu_state.json",
        ],
    }

    def __init__(self, backend_root: Path | None = None):
        self.backend_root = backend_root or Path(__file__).resolve().parents[2]

    def candidate_paths(
        self,
        platform: str,
        session_path: str | Path | None = None,
    ) -> list[Path]:
        normalized_platform = (platform or "").strip().lower()
        candidates = []

        if session_path:
            candidates.extend(self._expand_path(session_path))

        for default_path in self.PLATFORM_DEFAULTS.get(normalized_platform, []):
            candidates.extend(self._expand_path(default_path))

        return self._dedupe(candidates)

    def resolve(
        self,
        platform: str,
        session_path: str | Path | None = None,
    ) -> Path:
        candidates = self.candidate_paths(
            platform=platform,
            session_path=session_path,
        )

        for path in candidates:
            if path.exists():
                return path

        candidate_list = ", ".join(str(path) for path in candidates)
        raise FileNotFoundError(
            f"No saved login state found for {platform}. "
            f"Expected one of: {candidate_list}. Generate it before publishing."
        )

    def _expand_path(self, path: str | Path) -> list[Path]:
        raw_path = Path(path)

        if raw_path.is_absolute():
            return [raw_path]

        return [
            raw_path,
            self.backend_root / raw_path,
        ]

    @staticmethod
    def _dedupe(paths: list[Path]) -> list[Path]:
        seen = set()
        deduped = []

        for path in paths:
            normalized = str(path)

            if normalized in seen:
                continue

            seen.add(normalized)
            deduped.append(path)

        return deduped
