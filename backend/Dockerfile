FROM python:3.12-slim

WORKDIR /app

# System deps: psycopg2, cryptography, Java (for Liquibase migrations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Install Liquibase (PostgreSQL JDBC driver is bundled)
ARG LIQUIBASE_VERSION=4.29.2
RUN mkdir -p /opt/liquibase \
    && curl -fsSL https://github.com/liquibase/liquibase/releases/download/v${LIQUIBASE_VERSION}/liquibase-${LIQUIBASE_VERSION}.tar.gz \
       | tar xz -C /opt/liquibase \
    && ln -s /opt/liquibase/liquibase /usr/local/bin/liquibase

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command runs the API; Railway uses start.sh which runs migrations first
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
