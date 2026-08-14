# Release-history notice

The current tree excludes PMechDB-derived chemical payloads. Earlier Git
objects in the original repository contain those payloads. Adding this commit
to the existing branch does not remove prior objects from repository history.

Before publishing the revised release, the maintainer should use one of these
approaches:

1. publish the current tree as the initial commit of a new clean release
   repository; or
2. rewrite the existing repository history, remove the affected objects, and
   force-update the remote after coordinating with collaborators.

A normal merge or cherry-pick is sufficient for manuscript review but is not a
history purge. After preparing a clean release, run:

```text
python scripts/audit_release_payloads.py --repo .
```

The audit checks the current tree. The maintainer must separately verify that
the published Git history contains no earlier unredacted objects.
