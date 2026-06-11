from sqlalchemy import inspect, text


ADDITIVE_COLUMNS = {
    "contents": {
        "generation_mode": "VARCHAR",
        "strategy_type": "VARCHAR",
        "target_url": "VARCHAR",
        "evidence_json": "TEXT",
        "ai_faq": "TEXT",
        "platform_faq": "TEXT",
        "reddit_title": "VARCHAR",
        "reddit_body": "TEXT",
        "preview_title": "VARCHAR",
        "preview_subreddit": "VARCHAR",
        "preview_url": "VARCHAR",
        "preview_screenshot": "VARCHAR",
        "preview_timestamp": "TIMESTAMP WITH TIME ZONE",
    },
    "accounts": {
        "account_key": "VARCHAR",
        "agent_name": "VARCHAR",
        "state_identifier": "VARCHAR",
        "is_active": "BOOLEAN DEFAULT TRUE",
    },
    "citation_tests": {
        "source_type": "VARCHAR",
        "citation_target": "TEXT",
        "evidence_found": "BOOLEAN DEFAULT FALSE",
        "citation_type": "VARCHAR",
        "confidence_score": "INTEGER",
    },
}


def ensure_additive_columns(engine):
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name, columns in ADDITIVE_COLUMNS.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }

            for column_name, column_type in columns.items():
                if column_name in existing_columns:
                    continue

                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
