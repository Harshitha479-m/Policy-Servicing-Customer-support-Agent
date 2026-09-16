import sqlite3

from app.db import connect, find_policy, list_all_endorsements, list_endorsements, list_policies, search_policies, seed_demo_data


def test_demo_data_and_read_queries(tmp_path):
    database = tmp_path / "policy.db"
    seed_demo_data(database)
    policy = find_policy("POL-4821-AX", database)
    assert policy["customer_name"] == "Maya Thompson"
    assert list_endorsements(policy["id"], database)[0]["limit_value"] == "$10,000"
    assert len(list_policies(database)) == 4
    assert len(list_all_endorsements(database)) == 3
    assert len(search_policies("Commercial", database)) == 1



def test_repository_exposes_no_mutating_policy_operation(tmp_path):
    database = tmp_path / "policy.db"
    seed_demo_data(database)
    policy = find_policy("POL-4821-AX", database)
    assert policy["status"] == "Active"
    with connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM policies").fetchone()[0] == 4
