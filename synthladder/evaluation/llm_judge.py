"""Compatibility facade for judge module."""

from synthladder.evaluation.pipeline.llm_judge import *  # noqa: F401,F403


if __name__ == "__main__":
    from synthladder.evaluation.cli.llm_judge import main

    main()

