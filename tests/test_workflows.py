from pathlib import Path

import yaml


WORKFLOWS = Path(".github/workflows")


def load_workflow(name):
    return yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)


def test_github_workflows_parse_as_yaml():
    for path in WORKFLOWS.glob("*.yml"):
        assert load_workflow(path.name)


def test_ci_uses_read_only_contents_permission():
    assert load_workflow("ci.yml")["permissions"] == {"contents": "read"}


def test_pipeline_schedule_and_dispatch_contract():
    workflow = load_workflow("pipeline.yml")
    assert workflow["permissions"] == {"contents": "read"}
    assert [entry["cron"] for entry in workflow["on"]["schedule"]] == ["0 */6 * * *", "3 */6 * * *"]
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert inputs["source"]["options"] == ["remoteok", "remotive"]
    assert inputs["source"]["default"] == "remoteok"
    assert inputs["mode"]["options"] == ["dry-run", "notify"]
    assert inputs["mode"]["default"] == "dry-run"


def test_pipeline_concurrency_secrets_and_cli_mapping():
    workflow = load_workflow("pipeline.yml")
    assert workflow["concurrency"] == {"group": "smart-job-radar-pipeline", "cancel-in-progress": "false"}
    env = workflow["jobs"]["run"]["env"]
    assert env == {
        "DATABASE_URL": "${{ secrets.DATABASE_URL }}",
        "TELEGRAM_BOT_TOKEN": "${{ secrets.TELEGRAM_BOT_TOKEN }}",
        "TELEGRAM_CHAT_ID": "${{ secrets.TELEGRAM_CHAT_ID }}",
    }
    steps = workflow["jobs"]["run"]["steps"]
    assert any(step.get("run") == "python src/main.py --run-remoteok --notify" for step in steps)
    assert any(step.get("run") == "python src/main.py --run-remotive --notify" for step in steps)
    assert any(step.get("run") == "python src/main.py --run-${{ inputs.source }} ${{ inputs.mode == 'notify' && '--notify' || '--dry-run' }}" for step in steps)
