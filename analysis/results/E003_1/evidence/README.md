# Preserved E003.1 synthetic evidence

`E003_1-smoke` contains the original bartOS report, manifest and optimizer
states. `E003_1-synthetic` contains the manifest and available checkpoint
states from the incomplete blind run. There was no final report to archive
for that run. These JSON files were copied byte for byte. Finder metadata and
the execution lock were omitted. The prior `synthetic-controls` directory
preserves the nine independent diagnostics and their original reproduction
script and notes. The preserved historical manifests retain their original
schema, while E003.2 adds explicit configured and effective settings.

The E003.1 synthetic computation was still writing checkpoints during E003.2.
The separate follow-up inventory references unchanged first-snapshot files and
preserves any new or changed JSON bytes in a separate directory. It represents
a live run observed at a later point and can predate further optimizer output.
