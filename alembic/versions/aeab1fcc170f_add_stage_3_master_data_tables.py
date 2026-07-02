"""add stage 3 master data tables

Revision ID: aeab1fcc170f
Revises: d7a2fb41812b
Create Date: 2026-07-01 17:40:19.285555

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "aeab1fcc170f"
down_revision: str | None = "d7a2fb41812b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 1. districts, blocks, villages, departments, specializations ---
    op.create_table(
        "districts",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_districts_code"), "districts", ["code"], unique=True)

    op.create_table(
        "blocks",
        sa.Column("district_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("district_id", "code", name="uq_blocks_district_id_code"),
    )
    op.create_index(op.f("ix_blocks_district_id"), "blocks", ["district_id"], unique=False)
    op.create_index(op.f("ix_blocks_code"), "blocks", ["code"], unique=False)

    op.create_table(
        "villages",
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("pincode", sa.String(length=10), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_villages_block_id"), "villages", ["block_id"], unique=False)

    op.create_table(
        "departments",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_departments_name"),
    )

    op.create_table(
        "specializations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_specializations_name"),
    )

    # --- 2. alter health_centres ---
    op.drop_index("ix_health_centres_district_id", table_name="health_centres")

    op.drop_column("health_centres", "lat")
    op.drop_column("health_centres", "lng")
    op.drop_column("health_centres", "catchment_population")
    op.drop_column("health_centres", "bed_capacity")
    op.drop_column("health_centres", "performance_score")

    op.add_column("health_centres", sa.Column("block_id", sa.UUID(), nullable=True))
    op.add_column("health_centres", sa.Column("village_id", sa.UUID(), nullable=True))
    op.add_column("health_centres", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("health_centres", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("health_centres", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("health_centres", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("health_centres", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("health_centres", sa.Column("opening_time", sa.Time(), nullable=True))
    op.add_column("health_centres", sa.Column("closing_time", sa.Time(), nullable=True))

    op.alter_column(
        "health_centres", "type", existing_type=sa.String(length=20), type_=sa.String(length=30)
    )

    op.create_foreign_key(
        "fk_health_centres_district_id_districts",
        "health_centres",
        "districts",
        ["district_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_health_centres_block_id_blocks",
        "health_centres",
        "blocks",
        ["block_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_health_centres_village_id_villages",
        "health_centres",
        "villages",
        ["village_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        op.f("ix_health_centres_district_id"), "health_centres", ["district_id"], unique=False
    )
    op.create_index(
        op.f("ix_health_centres_block_id"), "health_centres", ["block_id"], unique=False
    )
    op.create_index(
        op.f("ix_health_centres_village_id"), "health_centres", ["village_id"], unique=False
    )

    op.create_unique_constraint(
        "uq_health_centres_district_id_name", "health_centres", ["district_id", "name"]
    )

    # --- 3. wards, rooms, staff_assignments ---
    op.create_table(
        "wards",
        sa.Column("health_centre_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["health_centre_id"], ["health_centres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("health_centre_id", "name", name="uq_wards_health_centre_id_name"),
    )
    op.create_index(op.f("ix_wards_health_centre_id"), "wards", ["health_centre_id"], unique=False)
    op.create_index(op.f("ix_wards_department_id"), "wards", ["department_id"], unique=False)

    op.create_table(
        "rooms",
        sa.Column("ward_id", sa.UUID(), nullable=False),
        sa.Column("room_number", sa.String(length=50), nullable=False),
        sa.Column("floor", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ward_id", "room_number", name="uq_rooms_ward_id_room_number"),
    )
    op.create_index(op.f("ix_rooms_ward_id"), "rooms", ["ward_id"], unique=False)

    op.create_table(
        "staff_assignments",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("health_centre_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("designation", sa.String(length=100), nullable=True),
        sa.Column("joined_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["health_centre_id"], ["health_centres.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_staff_assignments_user_id"), "staff_assignments", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_staff_assignments_health_centre_id"),
        "staff_assignments",
        ["health_centre_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_assignments_department_id"),
        "staff_assignments",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        "ux_staff_assignments_one_active_per_user",
        "staff_assignments",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    # --- reverse of 3: staff_assignments, rooms, wards ---
    op.drop_index("ux_staff_assignments_one_active_per_user", table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_department_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_health_centre_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_user_id"), table_name="staff_assignments")
    op.drop_table("staff_assignments")

    op.drop_index(op.f("ix_rooms_ward_id"), table_name="rooms")
    op.drop_table("rooms")

    op.drop_index(op.f("ix_wards_department_id"), table_name="wards")
    op.drop_index(op.f("ix_wards_health_centre_id"), table_name="wards")
    op.drop_table("wards")

    # --- reverse of 2: revert health_centres alterations ---
    op.drop_constraint("uq_health_centres_district_id_name", "health_centres", type_="unique")

    op.drop_index(op.f("ix_health_centres_village_id"), table_name="health_centres")
    op.drop_index(op.f("ix_health_centres_block_id"), table_name="health_centres")
    op.drop_index(op.f("ix_health_centres_district_id"), table_name="health_centres")

    op.drop_constraint(
        "fk_health_centres_village_id_villages", "health_centres", type_="foreignkey"
    )
    op.drop_constraint("fk_health_centres_block_id_blocks", "health_centres", type_="foreignkey")
    op.drop_constraint(
        "fk_health_centres_district_id_districts", "health_centres", type_="foreignkey"
    )

    op.alter_column(
        "health_centres", "type", existing_type=sa.String(length=30), type_=sa.String(length=20)
    )

    op.drop_column("health_centres", "closing_time")
    op.drop_column("health_centres", "opening_time")
    op.drop_column("health_centres", "email")
    op.drop_column("health_centres", "phone")
    op.drop_column("health_centres", "longitude")
    op.drop_column("health_centres", "latitude")
    op.drop_column("health_centres", "address")
    op.drop_column("health_centres", "village_id")
    op.drop_column("health_centres", "block_id")

    op.add_column(
        "health_centres",
        sa.Column("performance_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "health_centres",
        sa.Column("bed_capacity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "health_centres",
        sa.Column("catchment_population", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "health_centres", sa.Column("lng", sa.Float(), nullable=False, server_default="0")
    )
    op.add_column(
        "health_centres", sa.Column("lat", sa.Float(), nullable=False, server_default="0")
    )

    op.alter_column("health_centres", "performance_score", server_default=None)
    op.alter_column("health_centres", "bed_capacity", server_default=None)
    op.alter_column("health_centres", "catchment_population", server_default=None)
    op.alter_column("health_centres", "lng", server_default=None)
    op.alter_column("health_centres", "lat", server_default=None)

    op.create_index(
        op.f("ix_health_centres_district_id"), "health_centres", ["district_id"], unique=False
    )

    # --- reverse of 1: departments, specializations, villages, blocks, districts ---
    op.drop_table("specializations")
    op.drop_table("departments")

    op.drop_index(op.f("ix_villages_block_id"), table_name="villages")
    op.drop_table("villages")

    op.drop_index(op.f("ix_blocks_code"), table_name="blocks")
    op.drop_index(op.f("ix_blocks_district_id"), table_name="blocks")
    op.drop_table("blocks")

    op.drop_index(op.f("ix_districts_code"), table_name="districts")
    op.drop_table("districts")
