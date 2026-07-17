from pathlib import Path


class SessionResolver:
    PLATFORM_DEFAULTS = {
        "reddit": "sessions/reddit/profile",
        "xiaohongshu": {
            "creator": "sessions/xiaohongshu/creator/profile",
            "web": "sessions/xiaohongshu/web/profile",
        },
    }
    STORAGE_STATE_FALLBACKS = {
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

    def canonical_profile_dir(
        self,
        platform: str,
        purpose: str | None = None,
    ) -> Path:
        normalized_platform = (platform or "").strip().lower()

        if normalized_platform not in {"reddit", "xiaohongshu"}:
            raise ValueError(
                f"No canonical persistent profile directory for platform: {platform}"
            )

        return self.canonical_path(
            platform=normalized_platform,
            purpose=purpose,
        )

    def canonical_storage_state_path(
        self,
        platform: str,
        purpose: str | None = None,
    ) -> Path:
        normalized_platform = (platform or "").strip().lower()

        fallback_path = self._path_from_mapping(
            mapping=self.STORAGE_STATE_FALLBACKS,
            platform=normalized_platform,
            purpose=purpose,
        )

        if not fallback_path:
            raise ValueError(
                f"No canonical storage state path for platform: {platform} "
                f"purpose: {purpose}"
            )

        return fallback_path

    def profile_candidate_paths(
        self,
        platform: str,
        profile_path: str | Path | None = None,
        purpose: str | None = None,
    ) -> list[Path]:
        canonical_path = self.canonical_profile_dir(
            platform=platform,
            purpose=purpose,
        )

        normalized_profile_path = (
            self._normalize_path(profile_path)
            if profile_path
            else None
        )

        if (
            normalized_platform := (platform or "").strip().lower()
        ) == "reddit" and normalized_profile_path == self.canonical_storage_state_path(
            platform=normalized_platform,
            purpose=purpose,
        ):
            normalized_profile_path = canonical_path

        if normalized_profile_path and normalized_profile_path != canonical_path:
            raise ValueError(
                f"Invalid profile path for {platform}: {profile_path}. "
                f"Canonical profile path is {canonical_path}."
            )

        return [canonical_path]

    def storage_state_candidate_paths(
        self,
        platform: str,
        session_path: str | Path | None = None,
        purpose: str | None = None,
    ) -> list[Path]:
        canonical_path = self.canonical_storage_state_path(
            platform=platform,
            purpose=purpose,
        )

        if session_path and self._normalize_path(session_path) != canonical_path:
            raise ValueError(
                f"Invalid storage state path for {platform}: {session_path}. "
                f"Canonical storage state path is {canonical_path}."
            )

        return [canonical_path]

    def resolve_profile(
        self,
        platform: str,
        profile_path: str | Path | None = None,
        purpose: str | None = None,
    ) -> Path:
        candidates = self.profile_candidate_paths(
            platform=platform,
            profile_path=profile_path,
            purpose=purpose,
        )

        for path in candidates:
            if path.exists():
                return path

        candidate_list = ", ".join(str(path) for path in candidates)
        raise FileNotFoundError(
            f"No saved browser profile found for {platform}. "
            f"Expected one of: {candidate_list}."
        )

    def resolve_storage_state(
        self,
        platform: str,
        session_path: str | Path | None = None,
        purpose: str | None = None,
    ) -> Path:
        candidates = self.storage_state_candidate_paths(
            platform=platform,
            session_path=session_path,
            purpose=purpose,
        )

        for path in candidates:
            if path.exists():
                return path

        candidate_list = ", ".join(str(path) for path in candidates)
        raise FileNotFoundError(
            f"No saved storage state found for {platform}. "
            f"Expected one of: {candidate_list}."
        )

    def _normalize_path(self, path: str | Path) -> Path:
        raw_path = Path(path)

        if raw_path.is_absolute():
            if len(raw_path.parts) > 1 and raw_path.parts[1] == "sessions":
                return self.repo_root / raw_path.relative_to("/")

            return raw_path

        return self.repo_root / raw_path

    def _path_from_mapping(
        self,
        mapping: dict,
        platform: str,
        purpose: str | None = None,
    ) -> Path | None:
        default_path = mapping.get(platform)

        if not default_path:
            return None

        if isinstance(default_path, dict):
            normalized_purpose = (purpose or "creator").strip().lower()
            default_path = default_path.get(normalized_purpose)

            if not default_path:
                return None

        return self.repo_root / default_path

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
