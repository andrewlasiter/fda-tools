# fda-tools bash completion
# Install:
#   source tools/completions/fda-tools.bash        # one-time in current shell
#   echo 'source /path/to/fda-tools.bash' >> ~/.bashrc  # permanent
# Or: make completion-install

# ---------------------------------------------------------------------------
# Shared option sets
# ---------------------------------------------------------------------------

_FDA_GLOBAL_OPTS="--help --version"

_FDA_PRODUCT_CODE_OPTS="--product-codes --years --limit --output --format"
_FDA_PROJECT_OPTS="--project-name --project-dir --data-dir"
_FDA_API_OPTS="--api-key --rate-limit"

# ---------------------------------------------------------------------------
# Per-command completions
# ---------------------------------------------------------------------------

_fda_batchfetch() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--product-codes --years --limit --output --format
                --enrich --full-auto --api-key --rate-limit --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_gap_analysis() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--project-name --project-dir --data-dir
                --output --format --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_batch_analyze() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--input --output --format --round
                --compare --baseline --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_batch_seed() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--suite --round --output-dir --dry-run
                --config --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_backup_project() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--project-name --project-dir --data-dir
                --output --compress --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_setup_api_key() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--key --keyring --env --test --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_migrate_keyring() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--dry-run --force --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_auto_standards() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--project-name --project-dir --data-dir
                --product-code --device-class --output --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_check_version() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--json --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

_fda_update_manager() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local opts="--check --install --channel --yes --dry-run --help"
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
}

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

complete -F _fda_batchfetch      fda-batchfetch
complete -F _fda_gap_analysis    fda-gap-analysis
complete -F _fda_batch_analyze   fda-batch-analyze
complete -F _fda_batch_seed      fda-batch-seed
complete -F _fda_backup_project  fda-backup-project
complete -F _fda_setup_api_key   fda-setup-api-key
complete -F _fda_migrate_keyring fda-migrate-keyring
complete -F _fda_auto_standards  fda-auto-standards
complete -F _fda_check_version   fda-check-version
complete -F _fda_update_manager  fda-update-manager
