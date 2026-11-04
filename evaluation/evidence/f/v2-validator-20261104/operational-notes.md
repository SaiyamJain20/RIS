# Operational notes

The scheduled lock is an existing flock FILE, not a mkdir lock. The initial
mkdir probe refused that file. A first fcntl probe then acquired/released at
stdin EOF; a persistent TTY fcntl holder subsequently acquired before any
repository/document reads or mutations. It remains held through handoff and
must be released by newline, without deleting the inode. The separate
hmbc-coordinator.lock was acquired before owned writes and stays held through
the local checkpoint. No active prior holder was displaced.

Initial `git fetch origin agent-1 agent-2 agent-3` returned exit0 and advanced
origin/agent-1 from d8eddf1 to aef3daa. It left origin/agent-2 at5639e8f and
origin/agent-3 at2f2af3c. This receipt is transcribed from the actual tool output;
no separately captured initial-fetch timestamp/output file is asserted.
Three later attempts failed with the same public-key error; all logs/exits are
retained. The per-command HTTPS fallbacks did not change persistent Git config
or remotes and still reached SSH. `ssh-add -l` reported no identities; it was
read-only. The connected GitHub metadata probe also returned404. No credential
or access setting was changed. Local work is preserved for a normal later push.

Final lock release and actual commit/push outcome are recorded in the automation
memory outside the repository so this evidence does not need self-referential
commit hashes or a false predeclared successful push.

The first staged `git diff --cached --check` returned2 solely for a CR byte at
the end of each of the three raw SSH error lines. Those original log bytes and
output hashes are retained. The final staged check permits CR-at-EOL using a
per-command core.whitespace override while retaining the other default checks;
no persistent Git setting or evidence byte is normalized to hide that diagnostic.
