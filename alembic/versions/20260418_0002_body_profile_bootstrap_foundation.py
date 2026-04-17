"""body profile bootstrap foundation

Revision ID: 20260418_0002
Revises: 20260411_0001
Create Date: 2026-04-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260418_0002"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "body_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("profile_status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("sex", sa.String(length=32), nullable=False, server_default="female"),
        sa.Column("age_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("height_cm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_weight_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("activity_level", sa.String(length=32), nullable=False, server_default="sedentary"),
        sa.Column("goal_type", sa.String(length=32), nullable=False, server_default="lose_weight"),
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
        sa.Column("weekly_target_rate_kg", sa.Float(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_body_profiles_user_id"), "body_profiles", ["user_id"], unique=False)
    op.create_index(op.f("ix_body_profiles_profile_status"), "body_profiles", ["profile_status"], unique=False)
    op.create_index(op.f("ix_body_profiles_created_at"), "body_profiles", ["created_at"], unique=False)
    op.create_index(op.f("ix_body_profiles_updated_at"), "body_profiles", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_body_profiles_updated_at"), table_name="body_profiles")
    op.drop_index(op.f("ix_body_profiles_created_at"), table_name="body_profiles")
    op.drop_index(op.f("ix_body_profiles_profile_status"), table_name="body_profiles")
    op.drop_index(op.f("ix_body_profiles_user_id"), table_name="body_profiles")
    op.drop_table("body_profiles")
