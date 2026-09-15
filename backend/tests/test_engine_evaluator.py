from app.engine.evaluator import evaluate_condition, get_field


def test_get_field_dotted_path():
    data = {"loan": {"apr": 19.5}}
    assert get_field(data, "loan.apr") == 19.5
    assert get_field(data, "loan.missing") is None
    assert get_field(data, "missing.path") is None


def test_all_operator_true_when_every_child_true():
    condition = {"all": [
        {"field": "loan.apr", "operator": "greater_than", "value": 18},
        {"field": "borrower.type", "operator": "equals", "value": "consumer"},
    ]}
    data = {"loan": {"apr": 19.5}, "borrower": {"type": "consumer"}}
    result = evaluate_condition(condition, data)
    assert result["result"] is True


def test_all_operator_false_when_one_child_false():
    condition = {"all": [
        {"field": "loan.apr", "operator": "greater_than", "value": 18},
        {"field": "borrower.type", "operator": "equals", "value": "consumer"},
    ]}
    data = {"loan": {"apr": 10}, "borrower": {"type": "consumer"}}
    assert evaluate_condition(condition, data)["result"] is False


def test_any_operator():
    condition = {"any": [
        {"field": "borrower.military", "operator": "is_true", "value": True},
        {"field": "borrower.age", "operator": "less_than", "value": 21},
    ]}
    assert evaluate_condition(condition, {"borrower": {"military": False, "age": 19}})["result"] is True
    assert evaluate_condition(condition, {"borrower": {"military": False, "age": 40}})["result"] is False


def test_not_operator():
    condition = {"not": {"field": "borrower.military", "operator": "is_true", "value": True}}
    assert evaluate_condition(condition, {"borrower": {"military": False}})["result"] is True
    assert evaluate_condition(condition, {"borrower": {"military": True}})["result"] is False


def test_nested_conditions():
    condition = {"all": [
        {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
        {"any": [
            {"field": "borrower.military", "operator": "is_true", "value": True},
            {"field": "borrower.age", "operator": "less_than", "value": 21},
        ]},
        {"field": "loan.apr", "operator": "greater_than", "value": 20},
    ]}
    data = {
        "loan": {"product_type": "consumer_loan", "apr": 25},
        "borrower": {"military": False, "age": 19},
    }
    assert evaluate_condition(condition, data)["result"] is True


def test_missing_field_never_matches_without_raising():
    condition = {"field": "loan.apr", "operator": "greater_than", "value": 18}
    result = evaluate_condition(condition, {})
    assert result["result"] is False
    assert result["actual"] is None
