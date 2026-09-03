FROM python:3.12-slim

# git is required at runtime to compute diffs when not reviewing a
# GitHub/GitLab event or a saved diff file.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

WORKDIR /workspace
ENTRYPOINT ["prsentinel"]
CMD ["--help"]
