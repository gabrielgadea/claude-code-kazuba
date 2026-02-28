# Testing Rules

Testing is a first-class engineering activity, not an afterthought.
Untested code is hypothesis — execute, observe, validate.

---

## TDD Workflow

Follow the Red-Green-Refactor cycle:

1. **Red**: Write a failing test that describes the desired behavior.
2. **Green**: Write the minimum code to make the test pass.
3. **Refactor**: Clean up the code while keeping all tests green.

- Write tests BEFORE implementation, not after.
- Each test should fail for exactly one reason.
- If you cannot write a test, clarify the requirement first.
- Never skip the refactor step — that is where quality lives.

---

## Coverage Targets

- **Minimum 90% coverage per file** (not project average).
  - A project at 95% average can hide files at 30%.
- **Branch coverage** enabled — test both sides of conditionals.
- **Coverage is a floor, not a ceiling.** 100% coverage does not mean bug-free.
- **Exclude only**: `if TYPE_CHECKING:`, `if __name__ == "__main__":`, `pragma: no cover`.
- **Never game coverage.** Tests must assert meaningful behavior, not just execute lines.

---

## Test Pyramid

Maintain a healthy ratio of test types:

```
         /  E2E  \        Few, slow, expensive
        /----------\
       / Integration \    Moderate count and speed
      /----------------\
     /    Unit Tests     \  Many, fast, isolated
    /______________________\
```

- **Unit tests** (70-80%): Fast, isolated, test single functions or classes.
  - No I/O, no network, no database. Use mocks/fakes for external dependencies.
- **Integration tests** (15-20%): Test interactions between components.
  - Database queries, API client + server, file I/O.
- **E2E tests** (5-10%): Test complete user workflows.
  - Slow and brittle — keep count low, focus on critical paths.

---

## Test Naming Conventions

Test names describe the scenario and expected outcome:

```
test_<function_or_method>_<scenario>_<expected_result>
```

Examples:
- `test_calculate_total_with_discount_returns_reduced_price`
- `test_login_with_invalid_password_returns_401`
- `test_parse_empty_input_raises_value_error`

For test classes:
- `TestClassName` — groups tests for a single class or module.
- `TestFeatureName` — groups tests for a feature or behavior.

---

## Fixture Management

- **Fixtures over setup/teardown.** Use `@pytest.fixture` with proper scoping.
- **Smallest scope possible.** Prefer `function` scope; use `session` only for expensive setup.
- **Explicit dependencies.** Fixtures should declare their dependencies, not use globals.
- **Factory fixtures** for creating test objects with default values:
  ```python
  @pytest.fixture
  def make_user():
      def _make(name="test", email="test@example.com"):
          return User(name=name, email=email)
      return _make
  ```
- **Cleanup is automatic.** Use `yield` fixtures for teardown, not manual cleanup.
- **Shared fixtures in `conftest.py`** at the appropriate directory level.
- **No test-to-test dependencies.** Each test must be independently runnable.

---

## Test Quality Principles

- **Arrange-Act-Assert** (AAA) structure in every test.
- **One assertion per concept** (not necessarily per test method).
- **Deterministic.** No flaky tests. Mock time, randomness, and external services.
- **Fast.** Unit test suite should complete in under 10 seconds.
- **Readable.** A test is documentation. Someone should understand the feature from the test.
- **No logic in tests.** No loops, no conditionals, no try-except in test code.
