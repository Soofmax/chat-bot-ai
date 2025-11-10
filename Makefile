.PHONY: dashboards clean

dashboards:
\tpython scripts/build_dashboards.py -i dashboard/clients.json -o dist

clean:
\trm -rf dist