"""
Alembic миграция для создания таблицы emailactions.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '202412_create_emailactions'
down_revision = None  # Указать предыдущую миграцию при интеграции
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание таблицы emailactions."""
    op.create_table(
        'emailactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('emailid', sa.BigInteger(), nullable=False),
        sa.Column(
            'actiontype',
            sa.String(50),
            nullable=False,
            comment='Тип действия: createorder, updateinvoice, createticket, sendquote',
        ),
        sa.Column(
            'actionpayload',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='JSON с параметрами действия',
        ),
        sa.Column(
            'erpentitytype',
            sa.String(50),
            nullable=True,
            comment='Тип сущности ERP: Order, Invoice, Ticket, Quote',
        ),
        sa.Column(
            'erpentityid',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='UUID созданной/обновленной сущности в ERP',
        ),
        sa.Column(
            'status',
            sa.String(50),
            nullable=False,
            server_default='pending',
            comment='Статус: pending, executing, completed, failed',
        ),
        sa.Column(
            'errormessage',
            sa.Text(),
            nullable=True,
            comment='Сообщение об ошибке при неудачном выполнении',
        ),
        sa.Column(
            'retrycount',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Количество попыток выполнения',
        ),
        sa.Column(
            'executedat',
            sa.DateTime(),
            nullable=True,
            comment='Время выполнения действия',
        ),
        sa.Column(
            'createdat',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('NOW()'),
            comment='Время создания записи',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['emailid'],
            ['emails.id'],
            name='fk_emailactions_emailid',
            ondelete='CASCADE',
        ),
    )

    # Индексы для оптимизации запросов
    op.create_index(
        'ix_emailactions_emailid',
        'emailactions',
        ['emailid'],
    )
    op.create_index(
        'ix_emailactions_status',
        'emailactions',
        ['status'],
    )
    op.create_index(
        'ix_emailactions_actiontype',
        'emailactions',
        ['actiontype'],
    )
    op.create_index(
        'ix_emailactions_createdat',
        'emailactions',
        ['createdat'],
    )
    op.create_index(
        'ix_emailactions_erpentityid',
        'emailactions',
        ['erpentityid'],
        postgresql_where=sa.text('erpentityid IS NOT NULL'),
    )


def downgrade() -> None:
    """Удаление таблицы emailactions."""
    op.drop_index('ix_emailactions_erpentityid', table_name='emailactions')
    op.drop_index('ix_emailactions_createdat', table_name='emailactions')
    op.drop_index('ix_emailactions_actiontype', table_name='emailactions')
    op.drop_index('ix_emailactions_status', table_name='emailactions')
    op.drop_index('ix_emailactions_emailid', table_name='emailactions')
    op.drop_table('emailactions')
