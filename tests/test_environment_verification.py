from scripts.verify_environment import (
    classify_runtime_authority,
    resolve_verification_runtime,
)


def test_python_312_without_docker_is_allowed_local_fallback() -> None:
    result = resolve_verification_runtime(
        docker_available=False,
        python_version=(3, 12, 10),
        venv_path=".venv312",
    )

    assert result["status"] == "local_fallback"
    assert result["authoritative_for"] == ["local_phase_c_verification"]
    assert result["not_authoritative_for"] == ["container_parity", "os_service_parity"]
    assert result["ci_final_authority"] is True


def test_python_39_is_not_authoritative_even_when_docker_is_missing() -> None:
    result = resolve_verification_runtime(
        docker_available=False,
        python_version=(3, 9, 6),
        venv_path=None,
    )

    assert result["status"] == "blocked"
    assert result["blocker"] == "python_312_runtime_missing"
    assert result["do_not_change_product_code_for_python_39"] is True


def test_docker_runtime_is_preferred_when_available() -> None:
    result = resolve_verification_runtime(
        docker_available=True,
        python_version=(3, 9, 6),
        venv_path=None,
    )

    assert result["status"] == "docker_preferred"
    assert result["authoritative_for"] == ["local_phase_c_verification", "container_parity"]


def test_runtime_authority_classification() -> None:
    assert classify_runtime_authority((3, 12, 0)) == "python_312_plus"
    assert classify_runtime_authority((3, 11, 9)) == "not_authoritative"
