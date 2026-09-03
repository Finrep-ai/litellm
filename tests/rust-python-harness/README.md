# Rust ↔ Python SDK parity harness

This folder is the operator-facing harness for the Rust migration test plan. It runs pytest normally, listens to test events in-process, and redraws a live matrix grouped by testing strategy and SDK-level function.

The matrix always has these SDK columns:

- `ocr / aocr`
- `messages / amessages`
- `responses / aresponses`
- `count_tokens`

The harness has three deliberately broad test-strategy folders:

| Strategy | Folder |
| --- | --- |
| Public SDK parity over generated and recorded inputs | [`e2e_fuzz_tests/`](e2e_fuzz_tests/) |
| Focused tests of Rust-owned behavior | [`unit_tests_rust/`](unit_tests_rust/) |
| Isolated transform and Python-to-Rust helper coverage | [`validate_sub_methods/`](validate_sub_methods/) |

## Run it

This harness is manual-only. CI does not run its parity tests, fixture-generation checks, or recording commands

From the repository root:

```bash
poetry run python -m tests.rust-python-harness
```

The default runs every configured test once and updates all matching cells in real time. Narrow a run by strategy, SDK function, or both:

```bash
poetry run python -m tests.rust-python-harness --strategy e2e_fuzz_tests
poetry run python -m tests.rust-python-harness --function messages
poetry run python -m tests.rust-python-harness --strategy validate_sub_methods --function ocr
```

For a guided run, use the interactive picker. It asks which strategy rows and SDK
function columns to include, then hands the terminal to the live dashboard. It never
captures keys while tests are running, so Ctrl-C and pytest debugging remain safe.

```bash
poetry run python -m tests.rust-python-harness --interactive
```

Useful operator options:

```bash
# Inspect coverage and pytest selectors without running anything.
poetry run python -m tests.rust-python-harness --list

# Stable line-oriented output for CI logs or redirected output.
poetry run python -m tests.rust-python-harness --plain

# Measure Python reference lines exercised by this parity run and build an HTML heatmap.
poetry run python -m tests.rust-python-harness --coverage

# Forward pytest options. Use the equals form when the value begins with a dash.
poetry run python -m tests.rust-python-harness --pytest-arg=-x
```

The process returns pytest's exit code. A configured selector that collects no test is also a failure. A planned cell has no selector yet and does not fail the run.

The dashboard adapts to narrow terminals, shows elapsed time and unique-test progress,
and prints the three slowest tests when the run ends. Each failure includes a focused
`poetry run pytest ... -q` command. Redirected output and CI automatically use the
line-oriented plain renderer; `--plain` lets you opt into it locally.

The final screen includes a confidence score for every SDK section. It is the direct
ratio of required strategy rows with passing evidence, such as `1/3 = 33%`; High means
all required strategies passed, Medium means some passed, and Low means none passed.
This behavioral score is intentionally shown separately from Python and Rust LOC.

Coverage reports are written outside the three strategy folders at
`target/rust-python-harness/`. Open `python-html/index.html` to inspect executed and
missing Python lines; `python.json` and `python.xml` are available for automation.
Coverage is finalized after pytest exits, because worker processes must flush their
data first.

## Port coverage and confidence

Treat these as separate signals instead of one ambiguous coverage percentage:

| Signal | Tool | What it proves |
| --- | --- | --- |
| Python reference LOC | `coverage.py` / `pytest-cov` via `--coverage` | The mapped Python behavior ran |
| Rust port LOC | `cargo-llvm-cov` | The mapped Rust implementation ran |
| Parity contracts | This harness matrix | Python and Rust had the same observable behavior |

`validate_sub_methods/` owns the future source-section inventory that maps a stable
Python qualified symbol to its Rust symbol. That inventory is the denominator for
per-function rollups; raw coverage for the entire LiteLLM repository would obscure
the port's real gaps. `unit_tests_rust/` owns direct `cargo-llvm-cov` runs, while
`e2e_fuzz_tests/` owns behavioral parity and fuzz-case counts. Keep Python, Rust, and
parity percentages visible side by side and label section confidence High only when
the mapped implementation exists, every required strategy passes, and both sides meet
their LOC thresholds. Generated Rust LCOV/HTML and the combined index also belong in
`target/rust-python-harness/`, not in a fourth strategy folder.

## Read the matrix

| Mark | Meaning |
| --- | --- |
| `✓` | All collected tests passed |
| `✗` | At least one test failed |
| `!` | Test setup or teardown failed |
| `↷` | All collected tests skipped |
| `?` | A configured selector did not collect a test |
| `—` | Strategy is planned but has no test yet |
| `n/a` | Strategy does not apply to this SDK function |
| `◐` | The configured tests cover only part of the TDD's parity contract |

OCR runs committed provider recordings through both SDK implementations. Its strategy manifest references the existing bridge checks in `tests/test_litellm/ocr/`. OCR remains partial: invalid-model provider errors differ between Python and Rust, and Reducto lacks a Rust contract. Messages and Responses retain their partial bridge coverage, and unimplemented cells remain planned

## Attach parity tests

Each of the three folders contains a concise `README.md` and a `strategy.json`. Add a pytest file or node ID to the appropriate SDK function's `selectors` list:

```json
{
  "coverage": "complete",
  "selectors": [
    "tests/rust-python-harness/validate_sub_methods/test_messages.py"
  ]
}
```

Selectors use the same syntax as pytest. A file selector aggregates every test in the file; a node selector can target one test or parametrized family. The runner deduplicates selectors, so one test may intentionally prove more than one cell without executing twice.

Use these coverage values:

- `complete`: implements the full strategy contract for that SDK function.
- `partial`: useful coverage exists, but the TDD contract is not fully proven.
- `planned`: no runnable parity test exists yet.
- `not_applicable`: the strategy cannot apply, such as streaming for OCR.

Keep comparison mechanics in shared harness modules and provider/function facts in the owning strategy folder. A Python/Rust mismatch is a test failure; do not normalize away observable return types, exception classes, private response fields, chunk ordering, or callback payload differences merely to make a cell green.

## Architecture

- `catalog.py` validates and loads every strategy manifest.
- `models.py` owns typed strategy, case, coverage, and run-state models.
- `runner.py` maps live pytest events back to one or more matrix cells.
- `ui.py` renders the interactive Rich dashboard and a dependency-free plain fallback.
- `cli.py` handles filtering and preserves pytest exit semantics.

The harness is driven from Python, matching the SDK surface and existing test tooling. Rust remains responsible for the implementation under comparison; the harness does not move provider semantics into the PyO3 bridge.

## OCR fixtures and harness checks

`parity/` owns shared recording, replay, comparison, streaming, media generation, and cassette persistence. `e2e_fuzz_tests/ocr/` owns OCR input strategies, provider configuration, fixture generation, committed cassettes, and SDK parity tests. `validate_sub_methods/strategy.json` selects the existing OCR bridge tests without moving or changing them

Run recorded OCR parity without provider credentials:

```bash
uv run python -m tests.rust-python-harness --strategy e2e_fuzz_tests --function ocr --plain
```

Generate or refresh provider fixtures with configured credentials:

```bash
uv run python -m tests.rust-python-harness.e2e_fuzz_tests.ocr.fixtures.record --examples 1000
```

See [OCR fixture setup](e2e_fuzz_tests/ocr/fixtures/README.md) for provider credentials, input generation, and migration. `LITELLM_OCR_FIXTURE_DIR` and `--fixture-dir` still override the default cassette directory

Run the shared machinery and OCR fixture-generation checks alongside parity:

```bash
uv run pytest -o consider_namespace_packages=true tests/rust-python-harness tests/test_rust_python_harness.py -q
```

The harness is manual-only and is listed in `.github/ci-coverage-allowlist.yml`. Its CLI enables pytest namespace-package discovery for that invocation so the hyphenated harness directory supports relative imports. Other test runs keep the repository's default import behavior. Subprocess parity workers use the same package through `python -m`

HTTP recording helpers live in `parity/http.py`. The harness does not change the proxy E2E recorder or Python production code. SDK parity failures expose differences in the implementations under test
