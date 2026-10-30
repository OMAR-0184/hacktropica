"""Initial Cognimap relational schema.

Revision ID: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older deployments created these tables through SQLAlchemy create_all()
    # before Alembic was added. Adopt that schema after validating its columns,
    # then add indexes that the old bootstrap omitted. Alembic records this
    # revision after upgrade() returns.
    inspector = None
    if not op.get_context().as_sql:
        inspector = sa.inspect(op.get_bind())
        existing_tables = set(inspector.get_table_names())
    else:
        existing_tables = set()
    app_tables = {"users", "sessions", "nodes"}
    existing_app_tables = existing_tables & app_tables
    if existing_app_tables:
        assert inspector is not None
        if existing_app_tables != app_tables:
            missing_tables = sorted(app_tables - existing_app_tables)
            raise RuntimeError(
                "Cannot adopt a partial Cognimap schema; missing tables: "
                + ", ".join(missing_tables)
            )

        required_columns = {
            "users": {"id", "email", "username", "password_hash", "created_at"},
            "sessions": {
                "id", "user_id", "topic", "status", "error_message",
                "current_phase", "course_mode", "langgraph_thread_id",
                "created_at", "updated_at",
            },
            "nodes": {
                "id", "session_id", "node_id", "node_type", "status",
                "content", "score", "created_at",
            },
        }
        for table_name, required in required_columns.items():
            actual = {column["name"] for column in inspector.get_columns(table_name)}
            missing_columns = sorted(required - actual)
            if missing_columns:
                raise RuntimeError(
                    f"Cannot adopt {table_name}; missing columns: "
                    + ", ".join(missing_columns)
                )

        expected_indexes = {
            "users": [
                ("ix_users_email", ["email"], True),
                ("ix_users_id", ["id"], False),
                ("ix_users_username", ["username"], True),
            ],
            "sessions": [
                ("ix_sessions_id", ["id"], False),
                ("ix_sessions_langgraph_thread_id", ["langgraph_thread_id"], True),
                ("ix_sessions_topic", ["topic"], False),
                ("ix_sessions_user_status", ["user_id", "status"], False),
            ],
            "nodes": [
                ("ix_nodes_id", ["id"], False),
                ("ix_nodes_score", ["score"], False),
                ("ix_nodes_session_node", ["session_id", "node_id"], False),
            ],
        }
        for table_name, indexes in expected_indexes.items():
            existing_indexes = {
                index["name"]: index for index in inspector.get_indexes(table_name)
            }
            for name, columns, unique in indexes:
                existing = existing_indexes.get(name)
                if existing is not None:
                    if existing["column_names"] != columns or bool(existing["unique"]) != unique:
                        raise RuntimeError(f"Existing index {name} does not match the expected schema")
                    continue
                op.create_index(name, table_name, columns, unique=unique)
        return

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("current_phase", sa.String(), nullable=True),
        sa.Column("course_mode", sa.String(), nullable=True),
        sa.Column("langgraph_thread_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_id", "sessions", ["id"], unique=False)
    op.create_index("ix_sessions_langgraph_thread_id", "sessions", ["langgraph_thread_id"], unique=True)
    op.create_index("ix_sessions_topic", "sessions", ["topic"], unique=False)
    op.create_index("ix_sessions_user_status", "sessions", ["user_id", "status"], unique=False)

    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("node_id", sa.String(), nullable=True),
        sa.Column("node_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nodes_id", "nodes", ["id"], unique=False)
    op.create_index("ix_nodes_score", "nodes", ["score"], unique=False)
    op.create_index("ix_nodes_session_node", "nodes", ["session_id", "node_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_nodes_session_node", table_name="nodes")
    op.drop_index("ix_nodes_score", table_name="nodes")
    op.drop_index("ix_nodes_id", table_name="nodes")
    op.drop_table("nodes")
    op.drop_index("ix_sessions_user_status", table_name="sessions")
    op.drop_index("ix_sessions_topic", table_name="sessions")
    op.drop_index("ix_sessions_langgraph_thread_id", table_name="sessions")
    op.drop_index("ix_sessions_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
