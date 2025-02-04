run-miner:
	python scripts/run_miner.py

run-validator:
	python scripts/run_validator.py

test-routing-table:
	python -m unittest tests/test_routing_table.py

test-metagraph-syncing:
	python -m unittest tests/test_metagraph_syncing.py

test-all:
	python -m unittest discover -s tests
