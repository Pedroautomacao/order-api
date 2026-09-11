"""seed units of measure

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-09-10

As unidades nunca foram criadas por migration — só pelo seed.py, que não roda
em produção. Sem elas a tela de produtos não tem o que selecionar.

Os três códigos são os mesmos que seed.py cria (kg, un, cx). created_at,
is_active e is_deleted entram explícitos porque são NOT NULL e o default está
no model (Python), não no banco: um INSERT cru não o recebe.
"""
from alembic import op


revision = "f0a1b2c3d4e5"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO units_of_measure (code, name, is_active, is_deleted, created_at)
        VALUES
            ('kg', 'Quilograma', true, false, now()),
            ('un', 'Unidade',    true, false, now()),
            ('cx', 'Caixa',      true, false, now())
        ON CONFLICT (code) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Só remove a unidade que nenhum produto usa: apagar uma em uso quebraria
    # a FK e derrubaria o downgrade inteiro.
    op.execute(
        """
        DELETE FROM units_of_measure u
        WHERE u.code IN ('kg', 'un', 'cx')
          AND NOT EXISTS (
              SELECT 1 FROM products p WHERE p.unit_of_measure_id = u.id
          );
        """
    )
