from pathlib import Path


source = Path("jarvis.py").read_text()

assert source.count("def run_chill_mode(chill_seconds):") == 1
assert source.count("as chill_stream:") == 1

initial_route = """chill_seconds = parse_chill_seconds(text)

                        if chill_seconds is not None:
                            run_chill_mode(chill_seconds)
                            reconnect_requested = True
                            break"""

assert initial_route in source

followup_route = """chill_seconds = parse_chill_seconds(
                                    followup_text
                                )

                                if chill_seconds is not None:
                                    run_chill_mode(chill_seconds)
                                    reconnect_requested = True
                                    break"""

assert followup_route in source

followup_chill = source.index(
    "chill_seconds = parse_chill_seconds(\n"
    "                                    followup_text"
)

followup_ai = source.index(
    "answer_question(\n"
    "                                        followup_text",
    followup_chill,
)

assert followup_chill < followup_ai

print("ALL CHILL ROUTING REGRESSION TESTS PASSED")
