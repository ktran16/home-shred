# HomeShred — Docker Compose helpers.
#   DEV  (docker-compose.yml):      postgres (host :5434) + adminer (host :8080).
#                                   backend/frontend run on the host (uv run / pnpm dev).
#   PROD (docker-compose.prod.yml): db + backend + frontend (host :3006), reads .env.prod.
#
# Run `make help` for the full target list.

DC          := docker compose
DEV         := $(DC) -f docker-compose.yml
PROD        := $(DC) -f docker-compose.prod.yml
SEED        := python -m app.seed.seed_exercises

.DEFAULT_GOAL := help

PIPER_VOICES := en/en_US/lessac/high/en_US-lessac-high.onnx \
                en/en_US/lessac/high/en_US-lessac-high.onnx.json \
                vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx \
                vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json
PIPER_BASE   := https://huggingface.co/rhasspy/piper-voices/resolve/main

.PHONY: help \
        up down logs ps restart adminer tts-voices tts-f5 \
        prod-up prod-down prod-logs prod-ps prod-restart prod-build \
        prod-seed prod-reset prod-shell prod-psql prod-health prod-tts-voices \
        prod-backup prod-restore-test prod-restore

## ----------------------------------------------------------------------------
## Meta
## ----------------------------------------------------------------------------

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## ----------------------------------------------------------------------------
## Dev — Postgres + Adminer only (backend/frontend run on host)
## ----------------------------------------------------------------------------

up: ## Start dev db + adminer
	$(DEV) up -d

down: ## Stop dev stack (keeps data)
	$(DEV) down

logs: ## Tail dev logs
	$(DEV) logs -f

ps: ## Show dev container status
	$(DEV) ps

restart: ## Restart dev stack
	$(DEV) restart

adminer: ## Print the Adminer URL
	@echo "Adminer: http://localhost:8080  (server: db, user: homeshred, db: homeshred)"

tts-voices: ## Download Piper EN+VI voice models for dev (backend/media/tts/voices)
	cd backend && sh scripts/fetch-piper-voices.sh media/tts/voices

tts-f5: ## Download the optional high-quality Vietnamese F5-TTS model (backend/media/tts/f5)
	cd backend && sh scripts/fetch-f5-voice.sh media/tts/f5
	@echo "Next: install extras on this host (uv pip install -e '.[f5]') and set TTS_VI_ENGINE=f5"

## ----------------------------------------------------------------------------
## Prod — full stack (db + backend + frontend on :3006), reads .env.prod
## ----------------------------------------------------------------------------

prod-up: ## Build + start the prod stack (detached)
	$(PROD) up -d --build

prod-build: ## Rebuild prod images without starting
	$(PROD) build

prod-down: ## Stop the prod stack (keeps data)
	$(PROD) down

prod-logs: ## Tail prod logs (override: make prod-logs S=backend)
	$(PROD) logs -f $(S)

prod-ps: ## Show prod container status
	$(PROD) ps

prod-restart: ## Restart the prod stack
	$(PROD) restart

prod-seed: ## Seed the 54 exercises into the prod db
	$(PROD) run --rm backend $(SEED)

prod-shell: ## Open a shell in the backend container
	$(PROD) exec backend sh

prod-psql: ## Open psql in the prod db
	$(PROD) exec db psql -U homeshred -d homeshred

prod-health: ## Curl the public frontend + /api/health on :3006
	@echo -n "FE:        "; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3006
	@echo -n "API health: "; curl -s http://localhost:3006/api/health; echo

prod-tts-voices: ## Download Piper voice models into the prod backend media volume
	$(PROD) exec backend sh -c 'mkdir -p /app/media/tts/voices && \
	  for f in $(PIPER_VOICES); do \
	    curl -fsSL -o /app/media/tts/voices/$$(basename $$f) $(PIPER_BASE)/$$f; done' \
	  && echo "Voices downloaded into the media volume."

prod-backup: ## Dump prod db + media into ./backups (keeps 7 daily + 4 weekly)
	sh scripts/prod-backup.sh

prod-restore-test: ## Restore FILE=backups/.../x.dump into a throwaway db, print row counts
	sh scripts/prod-restore.sh test "$(FILE)"

prod-restore: ## DESTRUCTIVE: replace prod db + media with FILE=... (needs CONFIRM=yes)
	CONFIRM="$(CONFIRM)" sh scripts/prod-restore.sh prod "$(FILE)"

# WARNING: drops the pgdata volume (erases the DB), then rebuilds + re-seeds.
# Required after any DB password change — Postgres only applies POSTGRES_PASSWORD
# on the FIRST init of an empty data dir (see HANDOFF.md "Deploy fix").
prod-reset: ## DESTRUCTIVE: drop db volume, rebuild, re-seed
	$(PROD) down -v
	$(PROD) up -d --build
	$(PROD) run --rm backend $(SEED)
	@$(MAKE) prod-health
