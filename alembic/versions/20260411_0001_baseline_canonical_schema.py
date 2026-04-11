"""baseline canonical schema

Revision ID: 20260411_0001
Revises:
Create Date: 2026-04-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260411_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_users_user_id", "users", ["user_id"], unique=False)

    op.create_table(
        "meal_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("parent_log_id", sa.Integer(), sa.ForeignKey("meal_logs.id"), nullable=True),
        sa.Column("pending_question", sa.Text(), nullable=True),
        sa.Column("meal_title", sa.String(length=512), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False),
        sa.Column("carb_g", sa.Integer(), nullable=False),
        sa.Column("fat_g", sa.Integer(), nullable=False),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("debug_steps_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_meal_logs_user_id", "meal_logs", ["user_id"], unique=False)
    op.create_index("ix_meal_logs_timestamp", "meal_logs", ["timestamp"], unique=False)
    op.create_index("ix_meal_logs_status", "meal_logs", ["status"], unique=False)

    op.create_table(
        "message_buffer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("linked_meal_log_id", sa.Integer(), sa.ForeignKey("meal_logs.id"), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_message_buffer_user_id", "message_buffer", ["user_id"], unique=False)
    op.create_index("ix_message_buffer_created_at", "message_buffer", ["created_at"], unique=False)
    op.create_index("ix_message_buffer_linked_meal_log_id", "message_buffer", ["linked_meal_log_id"], unique=False)

    op.create_table(
        "meal_threads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("thread_kind", sa.String(length=32), nullable=False),
        sa.Column("active_version_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_meal_threads_user_id", "meal_threads", ["user_id"], unique=False)
    op.create_index("ix_meal_threads_thread_kind", "meal_threads", ["thread_kind"], unique=False)
    op.create_index("ix_meal_threads_active_version_id", "meal_threads", ["active_version_id"], unique=False)
    op.create_index("ix_meal_threads_created_at", "meal_threads", ["created_at"], unique=False)
    op.create_index("ix_meal_threads_updated_at", "meal_threads", ["updated_at"], unique=False)

    op.create_table(
        "meal_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meal_thread_id", sa.Integer(), sa.ForeignKey("meal_threads.id"), nullable=False),
        sa.Column("parent_version_id", sa.Integer(), sa.ForeignKey("meal_versions.id"), nullable=True),
        sa.Column("version_status", sa.String(length=32), nullable=False),
        sa.Column("version_reason", sa.String(length=64), nullable=False),
        sa.Column("reason_payload_json", sa.JSON(), nullable=False),
        sa.Column("meal_title", sa.String(length=512), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("source_request_id", sa.String(length=64), nullable=True),
        sa.Column("planner_intent", sa.String(length=64), nullable=True),
        sa.Column("resolution_status", sa.String(length=32), nullable=False),
        sa.Column("total_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False),
        sa.Column("carb_g", sa.Integer(), nullable=False),
        sa.Column("fat_g", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("local_date", sa.String(length=32), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_meal_versions_meal_thread_id", "meal_versions", ["meal_thread_id"], unique=False)
    op.create_index("ix_meal_versions_parent_version_id", "meal_versions", ["parent_version_id"], unique=False)
    op.create_index("ix_meal_versions_version_status", "meal_versions", ["version_status"], unique=False)
    op.create_index("ix_meal_versions_source_request_id", "meal_versions", ["source_request_id"], unique=False)
    op.create_index("ix_meal_versions_planner_intent", "meal_versions", ["planner_intent"], unique=False)
    op.create_index("ix_meal_versions_resolution_status", "meal_versions", ["resolution_status"], unique=False)
    op.create_index("ix_meal_versions_occurred_at", "meal_versions", ["occurred_at"], unique=False)
    op.create_index("ix_meal_versions_local_date", "meal_versions", ["local_date"], unique=False)
    op.create_index("ix_meal_versions_created_at", "meal_versions", ["created_at"], unique=False)

    op.create_table(
        "meal_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meal_version_id", sa.Integer(), sa.ForeignKey("meal_versions.id"), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("quantity_hint", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("evidence_role", sa.String(length=64), nullable=False),
        sa.Column("estimate_basis", sa.String(length=64), nullable=False),
        sa.Column("confidence_tier", sa.String(length=16), nullable=False),
        sa.Column("estimated_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False),
        sa.Column("carb_g", sa.Integer(), nullable=False),
        sa.Column("fat_g", sa.Integer(), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("classification_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_meal_items_meal_version_id", "meal_items", ["meal_version_id"], unique=False)
    op.create_index("ix_meal_items_created_at", "meal_items", ["created_at"], unique=False)

    op.create_table(
        "legacy_meal_log_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meal_log_id", sa.Integer(), sa.ForeignKey("meal_logs.id"), nullable=False, unique=True),
        sa.Column("meal_thread_id", sa.Integer(), sa.ForeignKey("meal_threads.id"), nullable=False),
        sa.Column("meal_version_id", sa.Integer(), sa.ForeignKey("meal_versions.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_legacy_meal_log_map_meal_log_id", "legacy_meal_log_map", ["meal_log_id"], unique=False)
    op.create_index("ix_legacy_meal_log_map_meal_thread_id", "legacy_meal_log_map", ["meal_thread_id"], unique=False)
    op.create_index("ix_legacy_meal_log_map_meal_version_id", "legacy_meal_log_map", ["meal_version_id"], unique=False)
    op.create_index("ix_legacy_meal_log_map_created_at", "legacy_meal_log_map", ["created_at"], unique=False)

    op.create_table(
        "day_budget_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("local_date", sa.String(length=32), nullable=False),
        sa.Column("budget_kcal", sa.Integer(), nullable=False),
        sa.Column("consumed_kcal", sa.Integer(), nullable=False),
        sa.Column("adjustment_kcal", sa.Integer(), nullable=False),
        sa.Column("remaining_kcal", sa.Integer(), nullable=False),
        sa.Column("last_recomputed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_day_budget_ledger_user_id", "day_budget_ledger", ["user_id"], unique=False)
    op.create_index("ix_day_budget_ledger_local_date", "day_budget_ledger", ["local_date"], unique=False)
    op.create_index("ix_day_budget_ledger_last_recomputed_at", "day_budget_ledger", ["last_recomputed_at"], unique=False)
    op.create_index("ix_day_budget_ledger_created_at", "day_budget_ledger", ["created_at"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("local_date", sa.String(length=32), nullable=False),
        sa.Column("entry_type", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("delta_kcal", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ledger_entries_user_id", "ledger_entries", ["user_id"], unique=False)
    op.create_index("ix_ledger_entries_local_date", "ledger_entries", ["local_date"], unique=False)
    op.create_index("ix_ledger_entries_entry_type", "ledger_entries", ["entry_type"], unique=False)
    op.create_index("ix_ledger_entries_source_type", "ledger_entries", ["source_type"], unique=False)
    op.create_index("ix_ledger_entries_source_id", "ledger_entries", ["source_id"], unique=False)
    op.create_index("ix_ledger_entries_created_at", "ledger_entries", ["created_at"], unique=False)

    op.create_table(
        "body_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("observation_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("local_date", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_body_observations_user_id", "body_observations", ["user_id"], unique=False)
    op.create_index("ix_body_observations_observation_type", "body_observations", ["observation_type"], unique=False)
    op.create_index("ix_body_observations_observed_at", "body_observations", ["observed_at"], unique=False)
    op.create_index("ix_body_observations_local_date", "body_observations", ["local_date"], unique=False)
    op.create_index("ix_body_observations_created_at", "body_observations", ["created_at"], unique=False)

    op.create_table(
        "body_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_status", sa.String(length=32), nullable=False),
        sa.Column("plan_label", sa.String(length=128), nullable=False),
        sa.Column("estimated_tdee", sa.Integer(), nullable=False),
        sa.Column("daily_budget_kcal", sa.Integer(), nullable=False),
        sa.Column("safety_floor_kcal", sa.Integer(), nullable=False),
        sa.Column("target_pace_kg_per_week", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_body_plans_user_id", "body_plans", ["user_id"], unique=False)
    op.create_index("ix_body_plans_plan_status", "body_plans", ["plan_status"], unique=False)
    op.create_index("ix_body_plans_started_at", "body_plans", ["started_at"], unique=False)
    op.create_index("ix_body_plans_created_at", "body_plans", ["created_at"], unique=False)

    op.create_table(
        "proposal_containers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("proposal_type", sa.String(length=64), nullable=False),
        sa.Column("proposal_status", sa.String(length=32), nullable=False),
        sa.Column("top_option_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_proposal_containers_user_id", "proposal_containers", ["user_id"], unique=False)
    op.create_index("ix_proposal_containers_proposal_type", "proposal_containers", ["proposal_type"], unique=False)
    op.create_index("ix_proposal_containers_proposal_status", "proposal_containers", ["proposal_status"], unique=False)
    op.create_index("ix_proposal_containers_top_option_id", "proposal_containers", ["top_option_id"], unique=False)
    op.create_index("ix_proposal_containers_created_at", "proposal_containers", ["created_at"], unique=False)

    op.create_table(
        "proposal_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proposal_container_id", sa.Integer(), sa.ForeignKey("proposal_containers.id"), nullable=False),
        sa.Column("option_type", sa.String(length=64), nullable=False),
        sa.Column("option_label", sa.String(length=255), nullable=False),
        sa.Column("option_summary", sa.Text(), nullable=False),
        sa.Column("rank_order", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("effect_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_proposal_options_proposal_container_id", "proposal_options", ["proposal_container_id"], unique=False)
    op.create_index("ix_proposal_options_option_type", "proposal_options", ["option_type"], unique=False)
    op.create_index("ix_proposal_options_created_at", "proposal_options", ["created_at"], unique=False)

    op.create_table(
        "proactive_triggers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trigger_type", sa.String(length=64), nullable=False),
        sa.Column("trigger_status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_proactive_triggers_user_id", "proactive_triggers", ["user_id"], unique=False)
    op.create_index("ix_proactive_triggers_trigger_type", "proactive_triggers", ["trigger_type"], unique=False)
    op.create_index("ix_proactive_triggers_trigger_status", "proactive_triggers", ["trigger_status"], unique=False)
    op.create_index("ix_proactive_triggers_created_at", "proactive_triggers", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("proactive_triggers")
    op.drop_table("proposal_options")
    op.drop_table("proposal_containers")
    op.drop_table("body_plans")
    op.drop_table("body_observations")
    op.drop_table("ledger_entries")
    op.drop_table("day_budget_ledger")
    op.drop_table("legacy_meal_log_map")
    op.drop_table("meal_items")
    op.drop_table("meal_versions")
    op.drop_table("meal_threads")
    op.drop_table("message_buffer")
    op.drop_table("meal_logs")
    op.drop_table("users")
