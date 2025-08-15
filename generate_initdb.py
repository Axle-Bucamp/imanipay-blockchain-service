from sqlalchemy import create_engine, MetaData
from sqlalchemy.schema import CreateTable
from app.database import Base  # Import your SQLAlchemy declarative base

# Optional: If you want PostgreSQL UUID functions
from sqlalchemy.dialects import postgresql

def generate_sql(filename="init-db.sql"):
    metadata: MetaData = Base.metadata
    sql_statements = []

    for table in metadata.sorted_tables:
        stmt = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        sql_statements.append(stmt + ";\n")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("-- Auto-generated init-db.sql from SQLAlchemy models\n\n")
        f.write("\n".join(sql_statements))

    print(f"SQL script generated: {filename}")

if __name__ == "__main__":
    generate_sql()