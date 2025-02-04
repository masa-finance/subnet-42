run-miner:
	python scripts/run_miner.py

run-validator:
	python scripts/run_validator.py

test-routing-table:
	python -m unittest tests/test_routing_table.py

test-metagraph-unit:
	pytest tests/test_metagraph_unit.py


