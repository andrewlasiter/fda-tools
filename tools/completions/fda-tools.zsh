#compdef fda-batchfetch fda-gap-analysis fda-batch-analyze fda-batch-seed \
#        fda-backup-project fda-setup-api-key fda-migrate-keyring \
#        fda-auto-standards fda-check-version fda-update-manager

# fda-tools zsh completion
# Install:
#   fpath=(tools/completions $fpath) && autoload -Uz compinit && compinit
#   # Add to ~/.zshrc for permanent effect — see README "Shell Completion" section
# Or: make completion-install

# ---------------------------------------------------------------------------
# fda-batchfetch
# ---------------------------------------------------------------------------

_fda_batchfetch() {
    _arguments \
        '--product-codes[Comma-separated FDA product codes to fetch]:codes:' \
        '--years[Number of years of history to fetch]:years:(1 2 3 5 10)' \
        '--limit[Maximum number of records to return]:limit:' \
        '--output[Output file path]:file:_files' \
        '--format[Output format]:format:(csv json tsv)' \
        '--enrich[Enrich results with Phase 1+2 intelligence data]' \
        '--full-auto[Run without interactive prompts]' \
        '--api-key[openFDA API key]:key:' \
        '--rate-limit[Requests per minute]:rate:' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-gap-analysis
# ---------------------------------------------------------------------------

_fda_gap_analysis() {
    _arguments \
        '--project-name[Project name]:name:' \
        '--project-dir[Project directory]:dir:_files -/' \
        '--data-dir[FDA data directory]:dir:_files -/' \
        '--output[Output file path]:file:_files' \
        '--format[Output format]:format:(markdown html json)' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-batch-analyze
# ---------------------------------------------------------------------------

_fda_batch_analyze() {
    _arguments \
        '--input[Input directory or file]:path:_files' \
        '--output[Output file or directory]:path:_files' \
        '--format[Output format]:format:(markdown html json csv)' \
        '--round[Round name/label]:round:' \
        '--compare[Compare against another round]:round:' \
        '--baseline[Baseline round for comparison]:round:' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-batch-seed
# ---------------------------------------------------------------------------

_fda_batch_seed() {
    _arguments \
        '--suite[Path to test suite JSON config]:file:_files' \
        '--round[Round name/label]:round:' \
        '--output-dir[Output directory for seeded projects]:dir:_files -/' \
        '--dry-run[Print what would be done without executing]' \
        '--config[Additional config file]:file:_files' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-backup-project
# ---------------------------------------------------------------------------

_fda_backup_project() {
    _arguments \
        '--project-name[Project name to back up]:name:' \
        '--project-dir[Project directory]:dir:_files -/' \
        '--data-dir[FDA data root directory]:dir:_files -/' \
        '--output[Backup output path]:file:_files' \
        '--compress[Compress the backup archive]' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-setup-api-key
# ---------------------------------------------------------------------------

_fda_setup_api_key() {
    _arguments \
        '--key[openFDA API key to store]:key:' \
        '--keyring[Store in OS keyring (recommended)]' \
        '--env[Print export statement for shell profile]' \
        '--test[Test the stored key against the openFDA API]' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-migrate-keyring
# ---------------------------------------------------------------------------

_fda_migrate_keyring() {
    _arguments \
        '--dry-run[Preview migration without making changes]' \
        '--force[Overwrite existing keyring entry]' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-auto-standards
# ---------------------------------------------------------------------------

_fda_auto_standards() {
    _arguments \
        '--project-name[Project name]:name:' \
        '--project-dir[Project directory]:dir:_files -/' \
        '--data-dir[FDA data root directory]:dir:_files -/' \
        '--product-code[FDA product code]:code:' \
        '--device-class[Device class]:class:(I II III)' \
        '--output[Output file path]:file:_files' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-check-version
# ---------------------------------------------------------------------------

_fda_check_version() {
    _arguments \
        '--json[Output version info as JSON]' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# fda-update-manager
# ---------------------------------------------------------------------------

_fda_update_manager() {
    _arguments \
        '--check[Check for available updates without installing]' \
        '--install[Install the latest available update]' \
        '--channel[Update channel]:channel:(stable beta dev)' \
        '--yes[Auto-confirm all prompts]' \
        '--dry-run[Preview update without applying it]' \
        '--help[Show help message and exit]'
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_fda_tools_dispatch() {
    local cmd="${words[1]}"
    case "$cmd" in
        fda-batchfetch)      _fda_batchfetch ;;
        fda-gap-analysis)    _fda_gap_analysis ;;
        fda-batch-analyze)   _fda_batch_analyze ;;
        fda-batch-seed)      _fda_batch_seed ;;
        fda-backup-project)  _fda_backup_project ;;
        fda-setup-api-key)   _fda_setup_api_key ;;
        fda-migrate-keyring) _fda_migrate_keyring ;;
        fda-auto-standards)  _fda_auto_standards ;;
        fda-check-version)   _fda_check_version ;;
        fda-update-manager)  _fda_update_manager ;;
    esac
}

_fda_tools_dispatch "$@"
