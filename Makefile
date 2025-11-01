.PHONY: smoke smoke-json smoke-csv clean-venv

VENV ?= .venv

$(VENV)/bin/activate:
	python -m venv $(VENV)
	. $(VENV)/bin/activate; pip install -U pip
	. $(VENV)/bin/activate; pip install -e campaign-core -e campaign-cli -e campaign-contracts

/tmp/jobs.json:
	@mkdir -p /tmp
	@printf '{ "jobs":[{"job_id":"J1","activities":["A1"],"portal":"legacyphoto"}] }\n' > /tmp/jobs.json

smoke: $(VENV)/bin/activate /tmp/jobs.json
	. $(VENV)/bin/activate; python -m campaign_cli.cli build --jobs /tmp/jobs.json --both --json --concurrency 8 --retries 3 | head -n 50

smoke-json: $(VENV)/bin/activate /tmp/jobs.json
	. $(VENV)/bin/activate; python -m campaign_cli.cli build --jobs /tmp/jobs.json --both --json --concurrency 8 --retries 3 | jq '.[0]'

smoke-csv: $(VENV)/bin/activate /tmp/jobs.json
	. $(VENV)/bin/activate; python -m campaign_cli.cli build --jobs /tmp/jobs.json --both --concurrency 8 --retries 3 > /tmp/out.csv
	@head -n 5 /tmp/out.csv; echo ""; echo "CSV at /tmp/out.csv"

clean-venv:
	rm -rf $(VENV)