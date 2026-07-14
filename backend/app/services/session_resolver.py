from pathlib import Path


class SessionResolver:
    PLATFORM_DEFAULTS = {
        "reddit": "sessions/reddit/storage_state.json",
        "xiaohongshu": {
            "creator": "sessions/xiaohongshu/creator/storage_state.json",
            "web": "sessions/xiaohongshu/web/storage_state.json",
        },
    }

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]

    def candidate_paths(
        self,
        platform: str,
        session_path: str | Path | None = None,
        purpose: str | None = None,
    ) -> list[Path]:
        canonical_path = self.canonical_path(
            platform=platform,
            purpose=purpose,
        )

        if session_path and self._normalize_path(session_path) != canonical_path:
            raise ValueError(
                f"Invalid session path for {platform}: {session_path}. "
                f"Canonical path is {canonical_path}."
            )

        return [canonical_path]

    def canonical_path(
        self,
        platform: str,
        purpose: str | None = None,
    ) -> Path:
        normalized_platform = (platform or "").strip().lower()
        default_path = self.PLATFORM_DEFAULTS.get(normalized_platform)

        if not default_path:
            raise ValueError(f"No canonical session path for platform: {platform}")

        if isinstance(default_path, dict):
            normalized_purpose = (purpose or "creator").strip().lower()
            default_path = default_path.get(normalized_purpose)

            if not default_path:
                raise ValueError(
                    f"No canonical session path for platform: {platform} "
                    f"purpose: {purpose}"
                )

        return self.repo_root / default_path

    def _normalize_path(self, path: str | Path) -> Path:
        raw_path = Path(path)

        if raw_path.is_absolute():
            return raw_path

        return self.repo_root / raw_path

    def resolve(
        self,
        platform: str,
        session_path: str | Path | None = None,
        purpose: str | None = None,
    ) -> Path:
        candidates = self.candidate_paths(
            platform=platform,
            session_path=session_path,
            purpose=purpose,
        )

        for path in candidates:
            if path.exists():
                return path

        candidate_list = ", ".join(str(path) for path in candidates)
        raise FileNotFoundError(
            f"No saved login state found for {platform}. "
            f"Expected one of: {candidate_list}. Generate it before publishing."
        )
