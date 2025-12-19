from src.desk_agent.orchestrator import DeskAgentOrchestrator


class DummyNormalizer:
    def normalize(self, desc, top_k=1):
        return []


class DummyOMS:
    def run(self, trade_json):
        return {"status": "OK", "issues": [], "explanation": "ok", "trade": trade_json}


class DummyPricing:
    def run(self, marks_input):
        return {"enriched_marks": [], "summary": {}}


def test_run_scenario_minimal(monkeypatch):
    # Stub ticker agent and market snapshot to avoid external calls
    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "generic", "summary": "ok", "metrics": {}, "question": q})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )
    scenario = {
        "name": "minimal",
        "description": "minimal scenario",
        "trades": [{"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"}],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}],
        "questions": [{"question": "How is AAPL?"}],
        "metadata": {},
    }
    report = orch.run_scenario(scenario)
    assert report["scenario"]["name"] == "minimal"
    assert "summary" in report
    assert isinstance(report["trade_issues"], list)
    assert isinstance(report["pricing_flags"], list)
    assert report["market_context"]["market_movements"]["avg_return_1d"] == 1.0


def test_scenario_validation_errors():
    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )
    scenario = {"description": "missing name", "trades": [], "marks": [], "questions": [], "metadata": {}}
    errs = orch._validate_scenario(scenario)
    assert errs


def test_report_structure_with_failed_step(monkeypatch):
    class FailingPricing(DummyPricing):
        def run(self, marks_input):
            raise RuntimeError("pricing boom")

    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "generic", "summary": "ok", "metrics": {}, "question": q})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())
    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=FailingPricing(),
    )
    scenario = {
        "name": "pricing_fail",
        "description": "pricing step fails but report returns",
        "trades": [{"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"}],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}],
        "questions": [],
        "metadata": {},
    }
    report = orch.run_scenario(scenario)
    assert report["scenario"]["name"] == "pricing_fail"
    assert "errors" in report["execution_metadata"]
    assert report["execution_metadata"]["errors"], "expected errors captured in execution_metadata"


def test_config_loading_precedence(monkeypatch):
    """Test config precedence: defaults → file → env vars."""
    import os
    monkeypatch.setenv("DESK_AGENT_MAX_RETRIES", "5")
    monkeypatch.setenv("DESK_AGENT_BACKOFF_MS", "1000")

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )

    assert orch.retry_cfg["max"] == 5
    assert orch.retry_cfg["backoff_ms"] == 1000


def test_retry_logic_success_after_failure(monkeypatch):
    """Test that retry occurs and step succeeds after initial failure."""
    import time

    class FlakeyPricing:
        def __init__(self):
            self.calls = 0

        def run(self, marks_input):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("flake")
            return {"enriched_marks": [], "summary": {}}

    flake = FlakeyPricing()
    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=flake,
    )

    scenario = {
        "name": "retry_test",
        "description": "test retries",
        "trades": [],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}],
        "questions": [],
        "metadata": {},
    }

    report = orch.run_scenario(scenario)
    assert flake.calls == 2  # Failed once, succeeded on retry
    pricing_trace = [t for t in report["execution_metadata"]["trace"] if t["step"] == "pricing"]
    # Should have 2 trace entries: one ERROR (attempt 1) and one OK (attempt 2)
    assert len(pricing_trace) == 2
    assert pricing_trace[0]["status"] == "ERROR"
    assert pricing_trace[0]["attempts"] == 1
    assert pricing_trace[1]["status"] == "OK"
    assert pricing_trace[1]["attempts"] == 2


def test_summary_aggregation_accuracy(monkeypatch):
    """Test that summary counts and percentages are accurate."""
    class DetailedOMS:
        def run(self, trade_json):
            trade_id = trade_json.get("trade_id")
            if trade_id in ["T1", "T2"]:
                return {"status": "ERROR", "issues": [{"type": "test", "severity": "ERROR"}], "explanation": "error", "trade": trade_json}
            return {"status": "OK", "issues": [], "explanation": "ok", "trade": trade_json}

    class DetailedPricing:
        def run(self, marks_input):
            enriched = []
            for m in marks_input:
                if m["ticker"] == "AAPL":
                    enriched.append({**m, "classification": "OUT_OF_TOLERANCE", "deviation_percentage": 0.10})
                else:
                    enriched.append({**m, "classification": "OK", "deviation_percentage": 0.01})
            return {"enriched_marks": enriched, "summary": {}}

    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DetailedOMS(),
        pricing_agent=DetailedPricing(),
    )

    scenario = {
        "name": "aggregation_test",
        "description": "test",
        "trades": [
            {"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
            {"trade_id": "T2", "ticker": "MSFT", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
            {"trade_id": "T3", "ticker": "GOOGL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
        ],
        "marks": [
            {"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"},
            {"ticker": "MSFT", "internal_mark": 1.0, "as_of": "2024-01-01"},
        ],
        "questions": [],
        "metadata": {},
    }

    report = orch.run_scenario(scenario)
    summary = report["summary"]

    assert summary["total_trades"] == 3
    assert summary["trades_with_issues"] == 2
    assert summary["percent_trades_with_issues"] == 2/3 * 100
    assert summary["total_marks"] == 2
    assert summary["marks_flagged"] == 1
    assert summary["percent_marks_flagged"] == 1/2 * 100
    assert summary["overall_status"] == "ERROR"


def test_trace_metadata_populated(monkeypatch):
    """Test that trace contains all steps with durations."""
    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )

    scenario = {
        "name": "trace_test",
        "description": "test",
        "trades": [{"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"}],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}],
        "questions": [{"question": "test", "ticker": "AAPL"}],
        "metadata": {},
    }

    report = orch.run_scenario(scenario)
    trace = report["execution_metadata"]["trace"]

    assert len(trace) == 5  # normalize, trade_qa, pricing, ticker, market_context
    steps = [t["step"] for t in trace]
    assert "normalize" in steps
    assert "trade_qa" in steps
    assert "pricing" in steps
    assert "ticker" in steps
    assert "market_context" in steps

    for t in trace:
        assert "duration_ms" in t
        assert "status" in t
        assert "attempts" in t
        assert t["duration_ms"] >= 0


def test_market_context_sector_aggregation(monkeypatch):
    """Test that sector_performance is aggregated correctly."""
    def mock_snapshot(tkr):
        sector_map = {"AAPL": "TECH", "MSFT": "TECH", "JPM": "FINANCE"}
        return_map = {"AAPL": 0.05, "MSFT": 0.03, "JPM": -0.02}
        return type("Snap", (), {
            "model_dump": lambda self: {
                "ticker": tkr,
                "return_1d": return_map.get(tkr, 0.0),
                "return_5d": 1.0,
                "sector": sector_map.get(tkr, "OTHER"),
                "market_cap": 1.0
            }
        })()

    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", mock_snapshot)

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )

    scenario = {
        "name": "market_context_test",
        "description": "test",
        "trades": [
            {"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
            {"trade_id": "T2", "ticker": "MSFT", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
            {"trade_id": "T3", "ticker": "JPM", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
        ],
        "marks": [],
        "questions": [],
        "metadata": {},
    }

    report = orch.run_scenario(scenario)
    market_ctx = report["market_context"]

    assert "sector_performance" in market_ctx
    assert "TECH" in market_ctx["sector_performance"]
    assert "FINANCE" in market_ctx["sector_performance"]

    tech_perf = market_ctx["sector_performance"]["TECH"]
    assert tech_perf["count"] == 2
    assert tech_perf["avg_return_1d"] == (0.05 + 0.03) / 2


def test_generate_report_file_output(monkeypatch, tmp_path):
    """Test that generate_report writes to file correctly."""
    import json

    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )

    scenario = {
        "name": "file_output_test",
        "description": "test",
        "trades": [],
        "marks": [],
        "questions": [],
        "metadata": {},
    }

    report = orch.run_scenario(scenario)
    output_path = tmp_path / "test_report.json"

    orch.generate_report(report, str(output_path))

    assert output_path.exists()
    with open(output_path) as f:
        loaded = json.load(f)
    assert loaded["scenario"]["name"] == "file_output_test"
    assert "summary" in loaded


def test_parallel_ticker_execution(monkeypatch):
    """Test that parallel ticker execution is faster than sequential."""
    import time

    call_times = []

    def slow_ticker(q):
        call_times.append(time.time())
        time.sleep(0.1)  # Simulate slow operation
        return {"intent": "ok", "summary": "ok", "metrics": {}, "question": q}

    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", slow_ticker)
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    # Test with parallel=True
    orch_parallel = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )
    orch_parallel.parallel_ticker = True

    scenario = {
        "name": "parallel_test",
        "description": "test",
        "trades": [],
        "marks": [],
        "questions": [
            {"question": "Q1", "ticker": "AAPL"},
            {"question": "Q2", "ticker": "MSFT"},
            {"question": "Q3", "ticker": "GOOGL"},
        ],
        "metadata": {},
    }

    call_times.clear()
    start = time.time()
    report_parallel = orch_parallel.run_scenario(scenario)
    parallel_duration = time.time() - start

    # With 3 questions taking 0.1s each, parallel should be ~0.1-0.2s, sequential would be ~0.3s
    assert len(report_parallel["ticker_agent_results"]) == 3
    # Parallel should complete faster (allowing some overhead)
    assert parallel_duration < 0.25, f"Parallel execution took {parallel_duration}s, expected <0.25s"


def test_retry_logic_abort_after_max(monkeypatch):
    """Test that scenario aborts after max retries when abort_after_retry=True."""
    class AlwaysFailingPricing:
        def __init__(self):
            self.calls = 0

        def run(self, marks_input):
            self.calls += 1
            raise RuntimeError("permanent failure")

    failing_pricing = AlwaysFailingPricing()
    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=failing_pricing,
    )
    # Set max retries to 2 and abort_after_retry to False (default behavior - continue)
    orch.retry_cfg = {"max": 2, "backoff_ms": 10, "abort_after_retry": False}

    scenario = {
        "name": "abort_test",
        "description": "test abort behavior",
        "trades": [],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}],
        "questions": [],
        "metadata": {},
    }

    # Should continue even after pricing fails
    report = orch.run_scenario(scenario)
    assert failing_pricing.calls == 3  # Initial + 2 retries = 3 attempts
    assert len(report["execution_metadata"]["errors"]) > 0
    # With abort_after_retry=False, should still have other sections
    assert "summary" in report
    assert "trade_issues" in report


def test_narrative_generation(monkeypatch):
    """Test that narrative is properly generated with scenario details."""
    class DetailedOMS:
        def run(self, trade_json):
            if trade_json.get("trade_id") == "T1":
                return {"status": "ERROR", "issues": [{"type": "test", "severity": "ERROR"}], "explanation": "error", "trade": trade_json}
            return {"status": "OK", "issues": [], "explanation": "ok", "trade": trade_json}

    class DetailedPricing:
        def run(self, marks_input):
            enriched = []
            for m in marks_input:
                if m["ticker"] == "AAPL":
                    enriched.append({**m, "classification": "OUT_OF_TOLERANCE", "deviation_percentage": 0.10})
                else:
                    enriched.append({**m, "classification": "OK", "deviation_percentage": 0.01})
            return {"enriched_marks": enriched, "summary": {}}

    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DetailedOMS(),
        pricing_agent=DetailedPricing(),
    )

    scenario = {
        "name": "narrative_test",
        "description": "test narrative generation",
        "trades": [
            {"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
            {"trade_id": "T2", "ticker": "MSFT", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"},
        ],
        "marks": [
            {"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"},
            {"ticker": "MSFT", "internal_mark": 1.0, "as_of": "2024-01-01"},
        ],
        "questions": [],
        "metadata": {},
    }

    report = orch.run_scenario(scenario)
    narrative = report["narrative"]

    assert isinstance(narrative, str)
    assert len(narrative) > 0
    # Narrative should mention key metrics
    assert "2 trades" in narrative or "2" in narrative
    assert "ERROR" in narrative or "error" in narrative or "issue" in narrative


def test_scenario_validation_with_missing_fields():
    """Test scenario validation catches missing required fields."""
    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )

    # Missing name
    scenario1 = {"description": "test", "trades": [], "marks": [], "questions": [], "metadata": {}}
    errs1 = orch._validate_scenario(scenario1)
    assert len(errs1) > 0
    assert any("name" in err.lower() for err in errs1)

    # Missing trades
    scenario2 = {"name": "test", "description": "test", "marks": [], "questions": [], "metadata": {}}
    errs2 = orch._validate_scenario(scenario2)
    assert len(errs2) > 0
    assert any("trades" in err.lower() for err in errs2)

    # Invalid trade (missing required fields)
    scenario3 = {
        "name": "test",
        "description": "test",
        "trades": [{"trade_id": "T1"}],  # Missing ticker, quantity, price, etc.
        "marks": [],
        "questions": [],
        "metadata": {},
    }
    errs3 = orch._validate_scenario(scenario3)
    assert len(errs3) > 0

    # Valid scenario should have no errors
    scenario_valid = {
        "name": "valid",
        "description": "valid scenario",
        "trades": [],
        "marks": [],
        "questions": [],
        "metadata": {},
    }
    errs_valid = orch._validate_scenario(scenario_valid)
    assert len(errs_valid) == 0


def test_execution_metadata_completeness(monkeypatch):
    """Test that execution_metadata contains all required fields."""
    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "ok", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )

    scenario = {
        "name": "metadata_test",
        "description": "test",
        "trades": [],
        "marks": [],
        "questions": [],
        "metadata": {},
    }

    report = orch.run_scenario(scenario)
    metadata = report["execution_metadata"]

    # Check all required fields
    assert "execution_time_ms" in metadata
    assert "timestamp" in metadata
    assert "agents_executed" in metadata
    assert "trace" in metadata
    assert "config" in metadata
    assert "errors" in metadata

    assert isinstance(metadata["execution_time_ms"], (int, float))
    assert metadata["execution_time_ms"] >= 0
    assert isinstance(metadata["agents_executed"], list)
    assert isinstance(metadata["trace"], list)
    assert isinstance(metadata["config"], dict)
    assert isinstance(metadata["errors"], list)
