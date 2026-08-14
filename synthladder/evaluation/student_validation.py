"""Compatibility facade for student validation module."""

from synthladder.evaluation.pipeline.student_validation import *  # noqa: F401,F403


if __name__ == "__main__":
    from synthladder.evaluation.cli.student_validation import main

    main()

