# End-to-end fuzz tests

Runs the same SDK call through the Python and Rust paths using generated inputs and recorded provider responses. It compares public results, streams, callbacks, and exceptions to catch behavior differences a unit test can miss.

OCR cases, input strategies, generation commands, and recorded cassettes live in `ocr/`. The manifest selects `ocr/test_sdk_parity.py`; fixture and recorder self-tests run through the full harness pytest directory
